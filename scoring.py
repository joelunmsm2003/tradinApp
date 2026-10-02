"""
Sistema de scoring por confluencia de indicadores.
Cada indicador aporta puntos cuando está activo.
Score alcista >= umbral → alerta de compra de alta confianza.
Score bajista >= umbral → alerta de venta de alta confianza.
"""
import json
import time
import urllib.request

import pandas as pd
from indicators import _rsi, _ema, _macd, _stoch_rsi


_FNG_CACHE = {"value": None, "ts": 0.0}
_FNG_TTL = 3600  # 1 hora — el índice solo cambia una vez al día


def _get_fng_value():
    """Fear & Greed Index actual (0-100), cacheado. None si falla la request."""
    now = time.time()
    if _FNG_CACHE["value"] is not None and now - _FNG_CACHE["ts"] < _FNG_TTL:
        return _FNG_CACHE["value"]
    try:
        with urllib.request.urlopen("https://api.alternative.me/fng/?limit=1", timeout=5) as resp:
            data = json.loads(resp.read())
        value = int(data["data"][0]["value"])
        _FNG_CACHE["value"] = value
        _FNG_CACHE["ts"] = now
        return value
    except Exception:
        return None


BULLISH_RULES = [
    # (nombre, puntos, función que devuelve bool dado df + series calculadas)
    # Pesos validados contra backtest_signals.py (correlación con retornos futuros de
    # BTC, train/test 2023). RSI oversold, Precio bajo BB y Stoch RSI oversold dieron
    # correlación débil e inconsistente entre train/test — se dejan igual por ahora
    # (no hay evidencia suficiente para asegurar que estén "al revés", solo que son
    # ruidosas), pero no se les sube el peso.
    ("RSI oversold",      2, lambda s: float(s["rsi"].iloc[-1]) < s["cfg"]["rsi_oversold"]),
    # Antes estaba en BEARISH_RULES ("sobrecompra = vender"). El backtest mostró
    # correlación POSITIVA con retornos futuros de BTC, consistente en los tres
    # regímenes de mercado (alcista +0.11, bajista +0.10, lateral +0.16 a 90d) — no
    # es un artefacto de que BTC suba en promedio, se sostiene incluso dentro de
    # tendencias bajistas confirmadas. Movido a alcista según esa evidencia.
    ("RSI overbought",    2, lambda s: float(s["rsi"].iloc[-1]) > s["cfg"]["rsi_overbought"]),
    ("MACD alcista",      2, lambda s: float(s["macd"].iloc[-1]) > float(s["signal"].iloc[-1])),
    ("Precio bajo BB",    2, lambda s: float(s["close"].iloc[-1]) < float(s["bb_lower"].iloc[-1])),
    ("Stoch RSI oversold",1, lambda s: float(s["stoch_k"].iloc[-1]) < 20 and
                                       float(s["stoch_k"].iloc[-1]) > float(s["stoch_d"].iloc[-1])),
    # Golden Cross fue, por lejos, la señal individual más fuerte y estable del
    # backtest (train +0.26/+0.29, test +0.17/+0.14 a 90/180d) — más que el score
    # combinado completo. Peso subido de 1 a 3 para reflejar eso.
    ("Golden Cross",      3, lambda s: float(s["ema_fast"].iloc[-1]) > float(s["ema_slow"].iloc[-1])),
    ("Volumen spike",     1, lambda s: _vol_spike(s)),
]

BEARISH_RULES = [
    ("MACD bajista",      2, lambda s: float(s["macd"].iloc[-1]) < float(s["signal"].iloc[-1])),
    ("Precio sobre BB",   2, lambda s: float(s["close"].iloc[-1]) > float(s["bb_upper"].iloc[-1])),
    ("Stoch RSI overbought",1,lambda s: float(s["stoch_k"].iloc[-1]) > 80 and
                                        float(s["stoch_k"].iloc[-1]) < float(s["stoch_d"].iloc[-1])),
    ("Death Cross",       3, lambda s: float(s["ema_fast"].iloc[-1]) < float(s["ema_slow"].iloc[-1])),
    ("Volumen spike",     1, lambda s: _vol_spike(s)),
    ("Codicia extrema (F&G)",1, lambda s: s["fng"] is not None and s["fng"] >= 75),
    # Antes estaba en BULLISH_RULES ("miedo = comprar el pánico"). El backtest mostró
    # lo contrario de forma estable en train Y test: miedo extremo correlacionó
    # NEGATIVO con retornos futuros (-0.06 a -0.20 a 30/90/180d) — es decir, históricamente
    # BTC siguió cayendo después de miedo extremo más seguido de lo que rebotó. Movido
    # a bajista según esa evidencia.
    ("Miedo extremo (F&G)",1, lambda s: s["fng"] is not None and s["fng"] <= 25),
]

MAX_BULLISH = sum(p for _, p, _ in BULLISH_RULES) + 1  # +1 posible del ATR
MAX_BEARISH = sum(p for _, p, _ in BEARISH_RULES) + 1


def _vol_spike(s) -> bool:
    vol = s.get("volume")
    if vol is None or len(vol) < 21:
        return False
    curr = float(vol.iloc[-1])
    avg  = float(vol.iloc[-21:-1].mean())
    return avg > 0 and curr / avg >= 2.0


def _atr_elevated(df: pd.DataFrame) -> tuple[bool, float]:
    """True Range de hoy vs ATR suavizado. Retorna (elevado, ratio)."""
    close = df["Close"]
    prev  = close.shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev).abs(),
        (df["Low"]  - prev).abs(),
    ], axis=1).max(axis=1)
    atr    = tr.ewm(alpha=1/14, adjust=False).mean()
    tr_hoy = float(tr.iloc[-1])
    atr_base = float(atr.iloc[-1])
    if atr_base == 0 or pd.isna(tr_hoy):
        return False, 0.0
    ratio = tr_hoy / atr_base
    return ratio >= 1.5, round(ratio, 2)


def _build_series(df: pd.DataFrame, cfg: dict) -> dict:
    close = df["Close"]
    macd_line, signal_line = _macd(close, cfg["macd_fast"], cfg["macd_slow"], cfg["macd_signal"])
    mid      = close.rolling(cfg["bb_period"]).mean()
    std_dev  = close.rolling(cfg["bb_period"]).std(ddof=0)
    stoch_k, stoch_d = _stoch_rsi(close)
    return {
        "close":     close,
        "rsi":       _rsi(close, cfg["rsi_period"]),
        "macd":      macd_line,
        "signal":    signal_line,
        "bb_upper":  mid + cfg["bb_std"] * std_dev,
        "bb_lower":  mid - cfg["bb_std"] * std_dev,
        "ema_fast":  _ema(close, cfg["ema_fast"]),
        "ema_slow":  _ema(close, cfg["ema_slow"]),
        "stoch_k":   stoch_k,
        "stoch_d":   stoch_d,
        "volume":    df.get("Volume"),
        "cfg":       cfg,
        "fng":       _get_fng_value(),
    }


def calculate_score(df: pd.DataFrame, cfg: dict) -> dict:
    """
    Retorna:
      bull_score, bear_score, max_score,
      bull_signals [{name, points}],
      bear_signals [{name, points}]
    """
    s = _build_series(df, cfg)

    bull_signals, bull_score = [], 0
    for name, pts, fn in BULLISH_RULES:
        try:
            active = fn(s)
        except Exception:
            active = False
        if active:
            bull_signals.append({"name": name, "points": pts})
            bull_score += pts

    bear_signals, bear_score = [], 0
    for name, pts, fn in BEARISH_RULES:
        try:
            active = fn(s)
        except Exception:
            active = False
        if active:
            bear_signals.append({"name": name, "points": pts})
            bear_score += pts

    # ATR elevado → +1 a la dirección dominante (amplifica la señal con fuerza)
    atr_high, atr_ratio = _atr_elevated(df)
    if atr_high and bull_score != bear_score:
        atr_tag = {"name": f"ATR elevado {atr_ratio}×", "points": 1}
        if bull_score > bear_score:
            bull_score += 1
            bull_signals.append(atr_tag)
        else:
            bear_score += 1
            bear_signals.append(atr_tag)

    return {
        "bull_score":   bull_score,
        "bear_score":   bear_score,
        "max_score":    MAX_BULLISH,
        "bull_signals": bull_signals,
        "bear_signals": bear_signals,
    }
