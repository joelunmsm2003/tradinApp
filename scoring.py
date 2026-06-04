"""
Sistema de scoring por confluencia de indicadores.
Cada indicador aporta puntos cuando está activo.
Score alcista >= umbral → alerta de compra de alta confianza.
Score bajista >= umbral → alerta de venta de alta confianza.
"""
import pandas as pd
from indicators import _rsi, _ema, _macd, _stoch_rsi


BULLISH_RULES = [
    # (nombre, puntos, función que devuelve bool dado df + series calculadas)
    ("RSI oversold",      2, lambda s: float(s["rsi"].iloc[-1]) < s["cfg"]["rsi_oversold"]),
    ("MACD alcista",      2, lambda s: float(s["macd"].iloc[-1]) > float(s["signal"].iloc[-1])),
    ("Precio bajo BB",    2, lambda s: float(s["close"].iloc[-1]) < float(s["bb_lower"].iloc[-1])),
    ("Stoch RSI oversold",1, lambda s: float(s["stoch_k"].iloc[-1]) < 20 and
                                       float(s["stoch_k"].iloc[-1]) > float(s["stoch_d"].iloc[-1])),
    ("Golden Cross",      1, lambda s: float(s["ema_fast"].iloc[-1]) > float(s["ema_slow"].iloc[-1])),
    ("Volumen spike",     1, lambda s: _vol_spike(s)),
]

BEARISH_RULES = [
    ("RSI overbought",    2, lambda s: float(s["rsi"].iloc[-1]) > s["cfg"]["rsi_overbought"]),
    ("MACD bajista",      2, lambda s: float(s["macd"].iloc[-1]) < float(s["signal"].iloc[-1])),
    ("Precio sobre BB",   2, lambda s: float(s["close"].iloc[-1]) > float(s["bb_upper"].iloc[-1])),
    ("Stoch RSI overbought",1,lambda s: float(s["stoch_k"].iloc[-1]) > 80 and
                                        float(s["stoch_k"].iloc[-1]) < float(s["stoch_d"].iloc[-1])),
    ("Death Cross",       1, lambda s: float(s["ema_fast"].iloc[-1]) < float(s["ema_slow"].iloc[-1])),
    ("Volumen spike",     1, lambda s: _vol_spike(s)),
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
