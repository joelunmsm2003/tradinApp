import json
import os
import time
import uuid

import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, render_template, request

from alerts import HISTORY_FILE

from indicators import _ema, _macd, _rsi, _stoch_rsi
from scoring import calculate_score

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

    df = yf.download("BTC-USD", **kw)
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.droplevel(1)

    if cfg["resample"]:
        df = df.resample(cfg["resample"]).agg(
            {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
        ).dropna()

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
}


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
    signals.append({"name": "RSI", "triggered": bullish, "detail": label})

    m = float(macd_line.iloc[-1])
    s = float(signal_line.iloc[-1])
    macd_bull = m > s
    signals.append({
        "name": "MACD",
        "triggered": macd_bull,
        "detail": f"MACD {m:+.2f} {'>' if macd_bull else '<'} Signal {s:+.2f}",
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
    signals.append({"name": "Bollinger Bands", "triggered": bb_bull, "detail": bb_label})

    ef = float(ema_fast_s.iloc[-1])
    es = float(ema_slow_s.iloc[-1])
    golden = ef > es
    cross = "Golden Cross activo" if golden else "Death Cross activo"
    signals.append({
        "name": f"EMA {cfg['ema_fast']}/{cfg['ema_slow']}",
        "triggered": golden,
        "detail": f"{cross}: EMA{cfg['ema_fast']} {ef:,.0f} {'>' if golden else '<'} EMA{cfg['ema_slow']} {es:,.0f}",
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
        signals.append({"name": "Stoch RSI", "triggered": stoch_bull, "detail": stoch_label})

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
        if key in data:
            val = data[key]
            cfg[key] = float(val) if key == "bb_std" else int(val)
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

    result = {
        "symbol": "BTC-USD",
        "price": round(float(close.iloc[-1]), 2),
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
        "volume": [
            {
                "time": int(t.timestamp()),
                "value": round(float(r["Volume"]), 0),
                "color": "#3fb95044" if float(r["Close"]) >= float(r["Open"]) else "#da363344",
            }
            for t, (_, r) in zip(ts, df.iterrows())
            if not pd.isna(r["Volume"]) and r["Volume"] > 0
        ],
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
    drawing["id"] = str(uuid.uuid4())
    drawings = _load_drawings()
    drawings.append(drawing)
    _save_drawings(drawings)
    return jsonify(drawing)


@app.route("/api/drawings/<drawing_id>", methods=["PATCH"])
def patch_drawing(drawing_id):
    update = request.get_json(force=True)
    drawings = _load_drawings()
    for d in drawings:
        if d["id"] == drawing_id:
            d.update(update)
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


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5050)
