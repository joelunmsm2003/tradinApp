import json
import os
import re
import time
import uuid
import urllib.request

import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, render_template, request

from alerts import HISTORY_FILE

from indicators import _ema, _macd, _rsi, _stoch_rsi, classify_regime
from scoring import _get_fng_value, calculate_score

app = Flask(__name__)

_DF_TTL     = 1800  # 30 min
_STATUS_TTL = 300   # 5 min

# Configuración por intervalo: yf_iv=intervalo yfinance, resample=resampleo opcional
_IV_CFG = {
    "1d":  {"yf_iv": "1d",  "start": "2020-01-01", "period": None,   "resample": None},
    "4h":  {"yf_iv": "1h",  "start": None,          "period": "730d", "resample": "4h"},
    "1wk": {"yf_iv": "1wk", "start": "2015-01-01", "period": None,   "resample": None},
}

_df_cache:     dict = {}  # interval -> {"df": df, "ts": float}
_status_cache: dict = {}  # interval -> {"data": dict, "ts": float}


def _get_btc_df(interval: str = "1d") -> pd.DataFrame:
    now   = time.time()
    cache = _df_cache.get(interval, {"df": None, "ts": 0.0})
    if cache["df"] is not None and now - cache["ts"] < _DF_TTL:
        return cache["df"]

    cfg = _IV_CFG.get(interval, _IV_CFG["1d"])
    kw  = dict(progress=False, auto_adjust=True, interval=cfg["yf_iv"])
    if cfg["start"]:
        kw["start"] = cfg["start"]
    else:
        kw["period"] = cfg["period"]

    try:
        df = yf.download("BTC-USD", **kw)
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.droplevel(1)

        if cfg["resample"]:
            df = df.resample(cfg["resample"]).agg(
                {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
            ).dropna()

        if df.empty:
            raise ValueError("yfinance devolvió un DataFrame vacío")
    except Exception as e:
        # Falla transitoria de yfinance (rate limit, hipo de red, etc.) — si hay un
        # dato bueno previo en memoria (aunque esté vencido), usarlo en vez de romper
        # el endpoint. No cacheamos el resultado vacío/fallido para no quedar pegados.
        if cache["df"] is not None:
            print(f"[_get_btc_df] fetch falló ({e}), usando último dato cacheado ({interval})")
            return cache["df"]
        raise

    _df_cache[interval] = {"df": df, "ts": now}
    return df

WEB_CONFIG_FILE = "web_config.json"

DEFAULTS = {
    "rsi_period":           14,
    "rsi_ma_period":        14,
    "rsi_oversold":         30,
    "rsi_overbought":       70,
    "bb_period":            20,
    "bb_std":               2.0,
    "macd_fast":            12,
    "macd_slow":            26,
    "macd_signal":          9,
    "ema_fast":             50,
    "ema_slow":             200,
    "confluence_threshold": 4,
    "extra_emas": [  # 5 EMAs adicionales listas para activar — [{"period","color","visible"}]
        {"period": 9,   "color": "#3fb950", "visible": False},
        {"period": 21,  "color": "#58a6ff", "visible": False},
        {"period": 55,  "color": "#f0883e", "visible": False},
        {"period": 100, "color": "#bc8cff", "visible": False},
        {"period": 150, "color": "#da3633", "visible": False},
    ],
}

_HEX_RE = re.compile(r'^#[0-9a-fA-F]{6}$')
_MAX_EXTRA_EMAS = 5


def _sanitize_extra_emas(raw) -> list:
    if not isinstance(raw, list):
        return []
    out, seen = [], set()
    for item in raw[:_MAX_EXTRA_EMAS]:
        if not isinstance(item, dict):
            continue
        try:
            period = int(item.get("period"))
        except (TypeError, ValueError):
            continue
        if not (2 <= period <= 500) or period in seen:
            continue
        seen.add(period)
        color = item.get("color", "#e6edf3")
        if not isinstance(color, str) or not _HEX_RE.match(color):
            color = "#e6edf3"
        out.append({"period": period, "color": color, "visible": bool(item.get("visible", True))})
    return out


def load_config() -> dict:
    if os.path.exists(WEB_CONFIG_FILE):
        with open(WEB_CONFIG_FILE) as f:
            saved = json.load(f)
        return {**DEFAULTS, **saved}
    return dict(DEFAULTS)


def save_config(cfg: dict) -> None:
    with open(WEB_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def _current_signals(close, df, rsi_series, macd_line, signal_line,
                     bb_upper, bb_lower, ema_fast_s, ema_slow_s,
                     stoch_k, stoch_d, atr_series, cfg):
    signals = []

    rsi_val = float(rsi_series.iloc[-1])
    bullish = rsi_val > 50
    if rsi_val > cfg["rsi_overbought"]:
        label = f"RSI = {rsi_val:.1f} — sobrecompra (>{cfg['rsi_overbought']})"
    elif rsi_val >= 50:
        label = f"RSI = {rsi_val:.1f} — zona alcista"
    elif rsi_val >= cfg["rsi_oversold"]:
        label = f"RSI = {rsi_val:.1f} — zona bajista"
    else:
        label = f"RSI = {rsi_val:.1f} — sobreventa (<{cfg['rsi_oversold']})"
    signals.append({"name": "RSI", "triggered": bullish, "detail": label, "points": 2})

    m = float(macd_line.iloc[-1])
    s = float(signal_line.iloc[-1])
    macd_bull = m > s
    signals.append({
        "name": "MACD",
        "triggered": macd_bull,
        "detail": f"MACD {m:+.2f} {'>' if macd_bull else '<'} Signal {s:+.2f}",
        "points": 2,
    })

    price = float(close.iloc[-1])
    upper = float(bb_upper.iloc[-1])
    lower = float(bb_lower.iloc[-1])
    sma20 = (upper + lower) / 2  # (mid+2std + mid-2std)/2 = mid exacto
    prev_price = float(close.iloc[-2])
    prev_lower = float(bb_lower.iloc[-2])
    was_outside = prev_price < prev_lower
    returned_in = price >= lower

    if was_outside and returned_in:
        bb_bull  = True
        bb_label = f"BB rebote confirmado: {price:,.0f} cruzó ↑ banda inf {lower:,.0f}"
    elif was_outside and price > prev_price:
        bb_bull  = True
        bb_label = f"BB posible rebote: sube {prev_price:,.0f}→{price:,.0f} (banda inf {lower:,.0f})"
    elif price < lower:
        bb_bull  = False
        bb_label = f"BB ruptura bajista: {price:,.0f} bajo banda inf {lower:,.0f} — sin rebote aún"
    elif price > upper:
        bb_bull  = False
        bb_label = f"BB sobrecompra: {price:,.0f} sobre banda sup {upper:,.0f}"
    elif price > sma20:
        bb_bull  = True
        bb_label = f"BB alcista: {price:,.0f} sobre SMA20 {sma20:,.0f}"
    else:
        bb_bull  = False
        bb_label = f"BB bajista: {price:,.0f} bajo SMA20 {sma20:,.0f}"
    signals.append({"name": "Bollinger Bands", "triggered": bb_bull, "detail": bb_label, "points": 2})

    ef = float(ema_fast_s.iloc[-1])
    es = float(ema_slow_s.iloc[-1])
    golden = ef > es
    cross = "Golden Cross activo" if golden else "Death Cross activo"
    signals.append({
        "name": f"EMA {cfg['ema_fast']}/{cfg['ema_slow']}",
        "triggered": golden,
        "detail": f"{cross}: EMA{cfg['ema_fast']} {ef:,.0f} {'>' if golden else '<'} EMA{cfg['ema_slow']} {es:,.0f}",
        "points": 3,
    })

    # Stoch RSI — alcista si %K > %D y ambos < 80
    k_val = float(stoch_k.iloc[-1])
    d_val = float(stoch_d.iloc[-1])
    if not (pd.isna(k_val) or pd.isna(d_val)):
        stoch_bull = k_val > d_val and k_val < 80
        if k_val < 20:
            stoch_label = f"StochRSI %K={k_val:.1f} < 20 (sobreventa)"
        elif k_val > 80:
            stoch_label = f"StochRSI %K={k_val:.1f} > 80 (sobrecompra)"
        elif stoch_bull:
            stoch_label = f"StochRSI %K={k_val:.1f} > %D={d_val:.1f} (alcista)"
        else:
            stoch_label = f"StochRSI %K={k_val:.1f} < %D={d_val:.1f} (bajista)"
        signals.append({"name": "Stoch RSI", "triggered": stoch_bull, "detail": stoch_label, "points": 1})

    # Volume spike — alcista si volumen > 2× promedio (interés del mercado)
    if "Volume" in df.columns:
        vol = df["Volume"]
        curr_vol = float(vol.iloc[-1])
        avg_vol  = float(vol.iloc[-21:-1].mean())
        if avg_vol > 0:
            ratio = curr_vol / avg_vol
            vol_spike = ratio >= 2.0
            signals.append({
                "name": "Volumen",
                "triggered": vol_spike,
                "detail": f"Vol {curr_vol:,.0f} = {ratio:.1f}× promedio 20d",
                "points": 1,
            })

    # ATR — True Range de HOY vs ATR promedio (respuesta inmediata a velas grandes)
    atr_avg    = float(atr_series.iloc[-1])  # ATR suavizado = baseline
    high_today = float(df["High"].iloc[-1])
    low_today  = float(df["Low"].iloc[-1])
    prev_close = float(close.iloc[-2])
    curr_close = float(close.iloc[-1])
    tr_today   = max(high_today - low_today,
                     abs(high_today - prev_close),
                     abs(low_today  - prev_close))
    if not pd.isna(atr_avg) and atr_avg > 0:
        atr_ratio  = tr_today / atr_avg
        atr_calm   = atr_ratio < 1.5
        direccion  = "alcista" if curr_close >= prev_close else "bajista"
        vol_label  = "calmo" if atr_calm else "volátil"
        signals.append({
            "name": "ATR",
            "triggered": curr_close >= prev_close,
            "detail": f"Vela={tr_today:,.0f} = {atr_ratio:.1f}× ATR ({vol_label}) — {direccion}",
            "points": 1,
        })

    fng_val = _get_fng_value()
    if fng_val is not None:
        # Miedo extremo movido a bajista: backtest_signals.py mostró correlación negativa
        # y estable con retornos futuros de BTC (históricamente siguió cayendo, no rebotó).
        if fng_val <= 25:
            fng_label, fng_bull = f"F&G = {fng_val} — miedo extremo", False
        elif fng_val >= 75:
            fng_label, fng_bull = f"F&G = {fng_val} — codicia extrema", False
        else:
            fng_label, fng_bull = f"F&G = {fng_val} — zona neutral", fng_val >= 50
        signals.append({
            "name": "Fear & Greed",
            "triggered": fng_bull,
            "detail": fng_label,
            "points": 1 if (fng_val <= 25 or fng_val >= 75) else 0,
        })

    return signals


def _series_to_list(timestamps, series: pd.Series, decimals: int = 4) -> list:
    out = []
    for ts, val in zip(timestamps, series):
        if pd.isna(val):
            continue
        out.append({"time": int(ts.timestamp()), "value": round(float(val), decimals)})
    return out


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/liquidity")
def liquidity_page():
    return render_template("liquidity.html")


SIGNALS_REPORT_PATH = os.path.join("backtest_output", "signals_report.json")
LIQUIDITY_REPORT_PATH = os.path.join("liquidity_index", "backtest_output", "liquidity_report.json")


def _load_json_report(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.route("/backtests")
def backtests_page():
    return render_template("backtests.html")


@app.route("/api/backtests")
def api_backtests():
    return jsonify({
        "signals": _load_json_report(SIGNALS_REPORT_PATH),
        "liquidity": _load_json_report(LIQUIDITY_REPORT_PATH),
    })


@app.route("/signals-history")
def signals_history_page():
    return render_template("signals_history.html")


_signals_history_cache = {"data": None, "ts": 0.0}
_SIGNALS_HISTORY_TTL = 1800  # 30 min, igual que _get_btc_df


@app.route("/api/signals-history")
def api_signals_history():
    from backtest_signals import CFG, _load_fng, compute_score_series

    now = time.time()
    cache = _signals_history_cache
    if cache["data"] is not None and now - cache["ts"] < _SIGNALS_HISTORY_TTL:
        return jsonify(cache["data"])

    df = _get_btc_df("1d")
    fng = _load_fng()
    scores = compute_score_series(df, fng, CFG)
    scores["regime"] = classify_regime(scores["close"])
    scores["net_score_ma14"] = scores["net_score"].rolling(14).mean()

    def series(col):
        return [
            {"time": int(ts.timestamp()), "value": round(float(v), 4)}
            for ts, v in scores[col].items() if v == v
        ]

    result = {
        "close": series("close"),
        "bull_score": series("bull_score"),
        "bear_score": series("bear_score"),
        "net_score": series("net_score"),
        "net_score_ma14": series("net_score_ma14"),
    }
    cache["data"] = result
    cache["ts"] = now
    return jsonify(result)


@app.route("/api/liquidity")
def api_liquidity():
    from liquidity_index import db as li_db
    from liquidity_index.liquidity_index import calculate_liquidity_index

    conn = li_db.get_connection()
    try:
        index_series = calculate_liquidity_index(conn)
        btc_series = li_db.read_series(conn, "mercado", "BTC-USD")
        with conn.cursor() as cur:
            cur.execute("SELECT fecha, numero, es_estimado FROM halvings ORDER BY fecha")
            halvings = [
                {"time": int(pd.Timestamp(row[0]).timestamp()), "numero": row[1], "es_estimado": row[2]}
                for row in cur.fetchall()
            ]
    finally:
        conn.close()

    def series_to_points(s):
        return [
            {"time": int(ts.timestamp()), "value": round(float(v), 6)}
            for ts, v in s.items()
            if v == v  # descarta NaN
        ]

    return jsonify({
        "liquidity_index": series_to_points(index_series),
        "btc": series_to_points(btc_series),
        "halvings": halvings,
    })


@app.route("/sw.js")
def sw():
    from flask import send_from_directory
    return send_from_directory("static", "sw.js", mimetype="application/javascript")


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def post_config():
    data = request.get_json(force=True)
    cfg = load_config()
    for key in DEFAULTS:
        if key == "extra_emas" or key not in data:
            continue
        val = data[key]
        cfg[key] = float(val) if key == "bb_std" else int(val)
    if "extra_emas" in data:
        cfg["extra_emas"] = _sanitize_extra_emas(data["extra_emas"])
    save_config(cfg)
    _status_cache.clear()  # invalidar todos los intervalos al cambiar parámetros
    return jsonify({"ok": True, "config": cfg})


@app.route("/api/status")
def status():
    interval = request.args.get("interval", "1d")
    if interval not in _IV_CFG:
        interval = "1d"

    now   = time.time()
    cache = _status_cache.get(interval, {"data": None, "ts": 0.0})
    if cache["data"] is not None and now - cache["ts"] < _STATUS_TTL:
        return jsonify(cache["data"])

    cfg = load_config()
    df = _get_btc_df(interval)

    ts = df.index
    close = df["Close"]

    ohlcv = [
        {
            "time": int(t.timestamp()),
            "open": round(float(r["Open"]), 2),
            "high": round(float(r["High"]), 2),
            "low": round(float(r["Low"]), 2),
            "close": round(float(r["Close"]), 2),
        }
        for t, (_, r) in zip(ts, df.iterrows())
    ]

    rsi_series = _rsi(close, cfg["rsi_period"])
    rsi_ma = rsi_series.rolling(cfg["rsi_ma_period"]).mean()

    macd_line, signal_line = _macd(close, cfg["macd_fast"], cfg["macd_slow"], cfg["macd_signal"])
    histogram = macd_line - signal_line
    macd_data = []
    for t, m, s, h in zip(ts, macd_line, signal_line, histogram):
        if any(pd.isna(v) for v in [m, s, h]):
            continue
        macd_data.append({
            "time": int(t.timestamp()),
            "macd": round(float(m), 4),
            "signal": round(float(s), 4),
            "histogram": round(float(h), 4),
        })

    mid = close.rolling(cfg["bb_period"]).mean()
    std_dev = close.rolling(cfg["bb_period"]).std(ddof=0)  # poblacional, igual que TradingView
    bb_upper = mid + cfg["bb_std"] * std_dev
    bb_lower = mid - cfg["bb_std"] * std_dev

    ema_fast = _ema(close, cfg["ema_fast"])
    ema_slow = _ema(close, cfg["ema_slow"])
    sma200 = close.rolling(200).mean()  # usada para clasificar régimen (classify_regime)

    extra_emas_data = [
        {
            "period":  item["period"],
            "color":   item["color"],
            "visible": True,
            "data":    _series_to_list(ts, _ema(close, item["period"]), 2),
        }
        for item in cfg.get("extra_emas", [])
        if item["visible"]
    ]

    # Stoch RSI
    stoch_k, stoch_d = _stoch_rsi(close)

    # ATR (Wilder)
    prev_close = close.shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr_series = tr.ewm(alpha=1/14, adjust=False).mean()

    signals = _current_signals(close, df, rsi_series, macd_line, signal_line,
                               bb_upper, bb_lower, ema_fast, ema_slow,
                               stoch_k, stoch_d, atr_series, cfg)

    # Score de confluencia
    score = calculate_score(df, cfg)

    # Stoch RSI data para chart
    stoch_data = []
    for t, k, d in zip(ts, stoch_k, stoch_d):
        if pd.isna(k) or pd.isna(d):
            continue
        stoch_data.append({"time": int(t.timestamp()), "k": round(float(k), 2), "d": round(float(d), 2)})

    # Régimen de mercado (alcista/bajista/lateral) — siempre sobre daily, independiente
    # del timeframe activo del chart, porque es contexto macro, no algo que deba
    # cambiar al alternar 1D/4H/1W. Ver backtest_signals.py: Golden Cross pierde toda
    # capacidad predictiva en lateral, y el score combinado es contraproducente en bajista.
    daily_df = df if interval == "1d" else _get_btc_df("1d")
    regime_series = classify_regime(daily_df["Close"])
    regime_label = regime_series.iloc[-1] if not regime_series.empty else None
    regime_label = str(regime_label) if regime_label is not None else None

    result = {
        "symbol": "BTC-USD",
        "price": round(float(close.iloc[-1]), 2),
        "regime": regime_label,
        "signals": signals,
        "ohlcv": ohlcv,
        "rsi": _series_to_list(ts, rsi_series, 2),
        "rsi_ma": _series_to_list(ts, rsi_ma, 2),
        "rsi_oversold": cfg["rsi_oversold"],
        "rsi_overbought": cfg["rsi_overbought"],
        "macd": macd_data,
        "bb_upper": _series_to_list(ts, bb_upper, 2),
        "bb_mid": _series_to_list(ts, mid, 2),
        "bb_lower": _series_to_list(ts, bb_lower, 2),
        "ema_fast": _series_to_list(ts, ema_fast, 2),
        "ema_slow": _series_to_list(ts, ema_slow, 2),
        "sma200": _series_to_list(ts, sma200, 2),
        "extra_emas_data": extra_emas_data,
        "volume": [
            {
                "time": int(t.timestamp()),
                "value": round(float(r["Volume"]), 0),
                "color": "#3fb950aa" if float(r["Close"]) >= float(r["Open"]) else "#da3633aa",
            }
            for t, (_, r) in zip(ts, df.iterrows())
            if not pd.isna(r["Volume"]) and r["Volume"] > 0
        ],
        "volume_ma": _series_to_list(ts, df["Volume"].rolling(20).mean(), 0),
        "stoch": stoch_data,
        "score": score,
        "atr": _series_to_list(ts, atr_series, 2),
        "config": cfg,
    }
    _status_cache[interval] = {"data": result, "ts": time.time()}
    return jsonify(result)


DRAWINGS_FILE = "drawings.json"


def _load_drawings() -> list:
    if not os.path.exists(DRAWINGS_FILE):
        return []
    with open(DRAWINGS_FILE) as f:
        return json.load(f)


def _save_drawings(data: list) -> None:
    with open(DRAWINGS_FILE, "w") as f:
        json.dump(data, f)


@app.route("/api/drawings", methods=["GET"])
def get_drawings():
    return jsonify(_load_drawings())


@app.route("/api/drawings", methods=["POST"])
def post_drawing():
    drawing = request.get_json(force=True)
    _ALLOWED = {"type", "price", "time", "p1", "p2", "color"}
    _REQUIRED = {"type", "color"}
    drawing = {k: v for k, v in drawing.items() if k in _ALLOWED}
    if not _REQUIRED.issubset(drawing):
        return jsonify({"error": "campos requeridos: type, color"}), 400
    drawing["id"] = str(uuid.uuid4())
    drawings = _load_drawings()
    drawings.append(drawing)
    _save_drawings(drawings)
    return jsonify(drawing)


@app.route("/api/drawings/<drawing_id>", methods=["PATCH"])
def patch_drawing(drawing_id):
    update = request.get_json(force=True)
    _ALLOWED = {"type", "price", "time", "p1", "p2", "color"}
    safe = {k: v for k, v in update.items() if k in _ALLOWED}
    drawings = _load_drawings()
    for d in drawings:
        if d["id"] == drawing_id:
            d.update(safe)
            break
    _save_drawings(drawings)
    return jsonify({"ok": True})


@app.route("/api/drawings/<drawing_id>", methods=["DELETE"])
def delete_drawing(drawing_id):
    drawings = [d for d in _load_drawings() if d["id"] != drawing_id]
    _save_drawings(drawings)
    return jsonify({"ok": True})


@app.route("/api/history")
def history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])
    with open(HISTORY_FILE) as f:
        data = json.load(f)
    return jsonify(list(reversed(data)))


_fng_cache: dict = {"data": None, "ts": 0.0}
_FNG_TTL = 3600  # 1 hora — el índice solo cambia una vez al día


@app.route("/api/fng")
def fear_and_greed():
    now = time.time()
    if _fng_cache["data"] is not None and now - _fng_cache["ts"] < _FNG_TTL:
        return jsonify(_fng_cache["data"])
    try:
        with urllib.request.urlopen(
            "https://api.alternative.me/fng/?limit=7", timeout=5
        ) as resp:
            raw = json.loads(resp.read())
        data = raw.get("data", [])
        result = {
            "value":       int(data[0]["value"]),
            "label":       data[0]["value_classification"],
            "history":     [{"value": int(d["value"]), "label": d["value_classification"]} for d in data],
        }
        _fng_cache["data"] = result
        _fng_cache["ts"]   = now
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


_EXCHANGES = {
    "binance": ("Binance", "https://api.binance.com/api/v3/ticker/price",
                lambda d: {re.sub(r"(USDT|USDC|FDUSD|BUSD|BTC|ETH|BNB|EUR|TRY)$", "", x["symbol"]) for x in d if re.search(r"(USDT|USDC|FDUSD)$", x["symbol"])}),
    "coinbase": ("Coinbase", "https://api.exchange.coinbase.com/products",
                 lambda d: {x["base_currency"] for x in d if x.get("status") == "online"}),
    "kraken": ("Kraken", "https://api.kraken.com/0/public/AssetPairs",
               lambda d: {(x.get("wsname") or "").split("/")[0].replace("XBT", "BTC") for x in d["result"].values()}),
    "bybit": ("Bybit", "https://api.bybit.com/v5/market/instruments-info?category=spot&limit=1000",
              lambda d: {x["baseCoin"] for x in d["result"]["list"] if x.get("status") == "Trading"}),
    "okx": ("OKX", "https://www.okx.com/api/v5/public/instruments?instType=SPOT",
            lambda d: {x["baseCcy"] for x in d["data"] if x.get("state") == "live"}),
    "kucoin": ("KuCoin", "https://api.kucoin.com/api/v2/symbols",
               lambda d: {x["baseCurrency"] for x in d["data"] if x.get("enableTrading")}),
    "gateio": ("Gate.io", "https://api.gateio.ws/api/v4/spot/currency_pairs",
               lambda d: {x["base"] for x in d if x.get("trade_status") == "tradable"}),
    "bitget": ("Bitget", "https://api.bitget.com/api/v2/spot/public/symbols",
               lambda d: {x["baseCoin"] for x in d["data"] if x.get("status") == "online"}),
}
_ex_cache: dict = {}
_EX_TTL = 3600


def _exchange_symbols(key):
    cached = _ex_cache.get(key)
    if cached and time.time() - cached[0] < _EX_TTL:
        return cached[1]
    _, url, parse = _EXCHANGES[key]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            syms = {s.upper() for s in parse(json.loads(resp.read())) if s}
        _ex_cache[key] = (time.time(), syms)
        return syms
    except Exception:
        return cached[1] if cached else None


@app.route("/api/exchanges")
def exchanges():
    out = {}
    for key, (label, _, _) in _EXCHANGES.items():
        syms = _exchange_symbols(key)
        if syms:
            out[key] = {"label": label, "symbols": sorted(syms)}
    return jsonify(out)


@app.route("/simulador")
def simulador_page():
    return render_template("simulador.html")


@app.route("/api/simulador")
def simulador_api():
    import momentum_sim
    try:
        a = request.args
        kw = dict(
            fee=float(a.get("fee", 0.1)) / 100,
            slippage=float(a.get("slippage", 0.1)) / 100,
            min_vol=float(a.get("min_vol", 100000)),
            max_rise=float(a["max_rise"]) / 100 if a.get("max_rise") else None,
            exclude=tuple(x.strip() for x in a.get("exclude", "").split(",") if x.strip()),
        )
        result = momentum_sim.simulate(
            threshold=float(a.get("threshold", 3)) / 100, hold_h=int(a.get("hold", 4)),
            capital=float(a.get("capital", 1000)), size=float(a.get("size", 100)), **kw)
        result["grid"] = momentum_sim.grid(**kw)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


_movers_cache: dict = {"data": None, "ts": 0.0}
_MOVERS_TTL = 60  # CoinGecko free tier limita requests


@app.route("/movers")
def movers_page():
    return render_template("movers.html")


@app.route("/api/movers")
def movers():
    now = time.time()
    if _movers_cache["data"] is not None and now - _movers_cache["ts"] < _MOVERS_TTL:
        return jsonify(_movers_cache["data"])
    try:
        url = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
               "&order=market_cap_desc&per_page=250&page=1&price_change_percentage=1h,24h")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read())
        coins = [
            {
                "symbol": c["symbol"].upper(),
                "name": c["name"],
                "image": c.get("image"),
                "price": c["current_price"],
                "chg_1h": c["price_change_percentage_1h_in_currency"],
                "chg_24h": c.get("price_change_percentage_24h_in_currency"),
                "volume": c.get("total_volume") or 0,
            }
            for c in raw
            if c.get("price_change_percentage_1h_in_currency") is not None
        ]
        result = {"coins": coins, "ts": int(now)}
        _movers_cache["data"] = result
        _movers_cache["ts"] = now
        return jsonify(result)
    except Exception as e:
        if _movers_cache["data"] is not None:
            return jsonify(_movers_cache["data"])
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    port  = int(os.getenv("PORT", 5050))
    app.run(host='0.0.0.0', debug=debug, port=port)
