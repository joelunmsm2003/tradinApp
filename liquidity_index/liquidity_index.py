"""Liquidity Index v1 — suma ponderada transparente de series normalizadas (z-score).

Pesos definidos en config.WEIGHTS: PROVISIONALES, no asumidos como óptimos.
Se validan estadísticamente en la Fase 7 (backtest.py). El índice se calcula
al leer (no se persiste todavía) — persistirlo en su propia tabla solo tiene
sentido cuando los pesos se estabilicen después del backtesting.
"""
import pandas as pd

from liquidity_index import db
from liquidity_index.config import INVERT_SIGN, STABLECOIN_INDICATOR, WEIGHTS
from liquidity_index.normalization import invert_sign, zscore


def _load_normalized_series(conn) -> dict[str, pd.Series]:
    tables = {
        "M2SL": "series_economicas",
        "WALCL": "series_economicas",
        "RRPONTSYD": "series_economicas",
        "WTREGEN": "series_economicas",
        "DGS10": "series_economicas",
        "DXY": "mercado",
        STABLECOIN_INDICATOR: "stablecoins",
    }
    out = {}
    for indicador, table in tables.items():
        s = db.read_series(conn, table, indicador)
        if s.empty:
            continue
        z = zscore(s)
        if INVERT_SIGN.get(indicador):
            z = invert_sign(z)
        out[indicador] = z
    return out


def calculate_liquidity_index(conn=None) -> pd.Series:
    """Retorna una pandas.Series (fecha -> valor del índice) alineada por fecha común."""
    own_conn = conn is None
    if own_conn:
        conn = db.get_connection()
    try:
        normalized = _load_normalized_series(conn)
    finally:
        if own_conn:
            conn.close()

    weighted_cols = []
    for indicador, weight in WEIGHTS.items():
        if indicador not in normalized:
            continue
        weighted_cols.append(normalized[indicador].rename(indicador) * weight)

    if not weighted_cols:
        return pd.Series(dtype=float)

    df = pd.concat(weighted_cols, axis=1)
    return df.sum(axis=1, skipna=True).rename("liquidity_index")


if __name__ == "__main__":
    idx = calculate_liquidity_index()
    print(idx.tail(20))
