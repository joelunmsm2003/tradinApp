"""Funciones de normalización — las variables tienen escalas distintas y no se pueden sumar directo."""
import pandas as pd


def pct_change(series: pd.Series, periods: int = 1) -> pd.Series:
    return series.pct_change(periods=periods)


def yoy_change(series: pd.Series) -> pd.Series:
    """Cambio interanual, asumiendo índice de fechas diario/irregular (~365 días atrás)."""
    daily = series.resample("D").ffill()
    return daily.pct_change(periods=365).reindex(series.index, method="ffill")


def zscore(series: pd.Series, window: int | None = None) -> pd.Series:
    if window is None:
        return (series - series.mean()) / series.std()
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (series - mean) / std


def rolling_mean(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def invert_sign(series: pd.Series) -> pd.Series:
    return -series
