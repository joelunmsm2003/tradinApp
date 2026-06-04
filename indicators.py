import pandas as pd
from config import RSI_OVERSOLD, RSI_OVERBOUGHT, VIX_SPIKE_PCT, VOLUME_SPIKE_MULT


def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    # Wilder's smoothing (alpha=1/length) — mismo método que Binance y TradingView
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _macd(series: pd.Series, fast=12, slow=26, signal=9):
    macd_line = _ema(series, fast) - _ema(series, slow)
    signal_line = _ema(macd_line, signal)
    return macd_line, signal_line


def _bbands(series: pd.Series, length: int = 20, std: float = 2.0):
    mid = series.rolling(length).mean()
    std_dev = series.rolling(length).std()
    lower = mid - std * std_dev
    return lower


def check_rsi(df: pd.DataFrame) -> tuple[bool, str]:
    """RSI cruza por encima de RSI_OVERSOLD (saliendo de sobreventa)."""
    rsi = _rsi(df["Close"])
    prev, curr = rsi.iloc[-2], rsi.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False, ""
    triggered = prev <= RSI_OVERSOLD < curr
    msg = f"RSI cruzó ↑ {RSI_OVERSOLD} (prev={prev:.1f} → curr={curr:.1f})"
    return triggered, msg


def check_golden_cross(df: pd.DataFrame) -> tuple[bool, str]:
    """EMA 50 cruza por encima de EMA 200 (Golden Cross)."""
    ema50 = _ema(df["Close"], 50)
    ema200 = _ema(df["Close"], 200)
    p50_prev, p50_curr = ema50.iloc[-2], ema50.iloc[-1]
    p200_prev, p200_curr = ema200.iloc[-2], ema200.iloc[-1]
    if any(pd.isna(v) for v in [p50_prev, p50_curr, p200_prev, p200_curr]):
        return False, ""
    triggered = p50_prev <= p200_prev and p50_curr > p200_curr
    msg = f"Golden Cross: EMA50={p50_curr:.2f} cruzó ↑ EMA200={p200_curr:.2f}"
    return triggered, msg


def check_vix_spike(df: pd.DataFrame) -> tuple[bool, str]:
    """VIX subió >= VIX_SPIKE_PCT% en la última sesión."""
    if len(df) < 2:
        return False, ""
    prev_close = df["Close"].iloc[-2]
    curr_close = df["Close"].iloc[-1]
    if pd.isna(prev_close) or prev_close == 0:
        return False, ""
    pct_change = (curr_close - prev_close) / prev_close * 100
    triggered = pct_change >= VIX_SPIKE_PCT
    msg = f"VIX Spike: subió {pct_change:.1f}% (de {prev_close:.2f} a {curr_close:.2f})"
    return triggered, msg


def check_macd(df: pd.DataFrame) -> tuple[bool, str]:
    """MACD cruza por encima de la línea de señal (momentum alcista)."""
    macd_line, signal_line = _macd(df["Close"])
    m_prev, m_curr = macd_line.iloc[-2], macd_line.iloc[-1]
    s_prev, s_curr = signal_line.iloc[-2], signal_line.iloc[-1]
    if any(pd.isna(v) for v in [m_prev, m_curr, s_prev, s_curr]):
        return False, ""
    triggered = m_prev <= s_prev and m_curr > s_curr
    msg = f"MACD cruzó ↑ señal (MACD={m_curr:.4f}, Signal={s_curr:.4f})"
    return triggered, msg


def check_bollinger_bands(df: pd.DataFrame) -> tuple[bool, str]:
    """Precio rebota desde fuera de la banda inferior: ayer estaba fuera, hoy vuelve o sube."""
    close = df["Close"]
    lower = _bbands(close)

    prev_price = float(close.iloc[-2])
    curr_price = float(close.iloc[-1])
    prev_lower = float(lower.iloc[-2])
    curr_lower = float(lower.iloc[-1])

    if any(pd.isna(v) for v in [prev_price, curr_price, prev_lower, curr_lower]):
        return False, ""

    was_outside = prev_price < prev_lower   # estaba fuera ayer
    returned_in = curr_price >= curr_lower  # volvió dentro hoy
    bouncing    = curr_price > prev_price   # sube aunque aún fuera

    if was_outside and returned_in:
        # Señal fuerte: cruce de vuelta dentro de la banda
        return True, (
            f"BB rebote confirmado: precio {curr_price:,.2f} cruzó ↑ banda inf {curr_lower:,.2f}"
        )
    if was_outside and bouncing:
        # Señal temprana: aún fuera pero el precio empieza a subir
        return True, (
            f"BB posible rebote: precio sube {prev_price:,.2f}→{curr_price:,.2f} "
            f"(aún bajo banda inf {curr_lower:,.2f})"
        )
    return False, f"BB: precio {curr_price:,.2f} vs banda inf {curr_lower:,.2f}"


# ── Fase 3 ────────────────────────────────────────────────────────────────────

def check_rsi_overbought(df: pd.DataFrame) -> tuple[bool, str]:
    """RSI cruza por debajo de RSI_OVERBOUGHT (saliendo de sobrecompra — señal bajista)."""
    rsi = _rsi(df["Close"])
    prev, curr = rsi.iloc[-2], rsi.iloc[-1]
    if pd.isna(prev) or pd.isna(curr):
        return False, ""
    triggered = prev >= RSI_OVERBOUGHT > curr
    msg = f"RSI cruzó ↓ {RSI_OVERBOUGHT} (prev={prev:.1f} → curr={curr:.1f})"
    return triggered, msg


def check_death_cross(df: pd.DataFrame) -> tuple[bool, str]:
    """EMA50 cruza por debajo de EMA200 (Death Cross — señal bajista)."""
    ema50  = _ema(df["Close"], 50)
    ema200 = _ema(df["Close"], 200)
    p50_prev,  p50_curr  = ema50.iloc[-2],  ema50.iloc[-1]
    p200_prev, p200_curr = ema200.iloc[-2], ema200.iloc[-1]
    if any(pd.isna(v) for v in [p50_prev, p50_curr, p200_prev, p200_curr]):
        return False, ""
    triggered = p50_prev >= p200_prev and p50_curr < p200_curr
    msg = f"Death Cross: EMA50={p50_curr:.2f} cruzó ↓ EMA200={p200_curr:.2f}"
    return triggered, msg


def check_volume_spike(df: pd.DataFrame) -> tuple[bool, str]:
    """Volumen actual supera VOLUME_SPIKE_MULT veces el promedio de 20 sesiones."""
    if "Volume" not in df.columns or len(df) < 21:
        return False, ""
    vol = df["Volume"]
    curr_vol = vol.iloc[-1]
    avg_vol  = vol.iloc[-21:-1].mean()
    if pd.isna(curr_vol) or pd.isna(avg_vol) or avg_vol == 0:
        return False, ""
    ratio = curr_vol / avg_vol
    triggered = ratio >= VOLUME_SPIKE_MULT
    msg = f"Volumen {curr_vol:,.0f} = {ratio:.1f}× promedio 20d ({avg_vol:,.0f})"
    return triggered, msg


def _stoch_rsi(series: pd.Series, rsi_len: int = 14, stoch_len: int = 14,
               k_smooth: int = 3, d_smooth: int = 3):
    rsi = _rsi(series, rsi_len)
    lo  = rsi.rolling(stoch_len).min()
    hi  = rsi.rolling(stoch_len).max()
    k   = 100 * (rsi - lo) / (hi - lo + 1e-10)
    k   = k.rolling(k_smooth).mean()
    d   = k.rolling(d_smooth).mean()
    return k, d


def check_stoch_rsi(df: pd.DataFrame) -> tuple[bool, str]:
    """Stoch RSI %K cruza por encima de %D desde zona de sobreventa (<20)."""
    k, d = _stoch_rsi(df["Close"])
    k_prev, k_curr = k.iloc[-2], k.iloc[-1]
    d_prev, d_curr = d.iloc[-2], d.iloc[-1]
    if any(pd.isna(v) for v in [k_prev, k_curr, d_prev, d_curr]):
        return False, ""
    triggered = k_prev <= d_prev and k_curr > d_curr and k_curr < 50
    msg = f"StochRSI %K={k_curr:.1f} cruzó ↑ %D={d_curr:.1f}"
    return triggered, msg


def check_atr(df: pd.DataFrame, length: int = 14, mult: float = 1.5) -> tuple[bool, str]:
    """ATR actual supera mult × ATR promedio de 20 sesiones (volatilidad elevada)."""
    if len(df) < length + 20:
        return False, ""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr     = tr.ewm(alpha=1 / length, adjust=False).mean()
    curr    = float(atr.iloc[-1])
    avg_atr = float(atr.iloc[-21:-1].mean())
    if pd.isna(curr) or avg_atr == 0:
        return False, ""
    ratio     = curr / avg_atr
    triggered = ratio >= mult
    msg = f"ATR={curr:.0f} = {ratio:.1f}× su promedio 20d (volatilidad elevada)"
    return triggered, msg
