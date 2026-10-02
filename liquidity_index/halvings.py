"""Halvings de Bitcoin + retornos/drawdown/volatilidad, mismos idioms de pandas que
indicators.py/scoring.py (rolling std, pct_change, drawdown vía máximo acumulado)."""
import pandas as pd

from liquidity_index import db
from liquidity_index.config import HALVINGS


def seed_halvings(conn=None) -> None:
    """Inserta/actualiza las fechas de halving conocidas en la tabla `halvings`."""
    own_conn = conn is None
    if own_conn:
        conn = db.get_connection()
    try:
        for h in HALVINGS:
            db.upsert_halving(conn, h["fecha"], h["numero"], h["es_estimado"], h["notas"])
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def btc_returns(price: pd.Series) -> pd.Series:
    return price.pct_change()


def btc_drawdown(price: pd.Series) -> pd.Series:
    running_max = price.cummax()
    return price / running_max - 1.0


def btc_volatility(price: pd.Series, window: int = 30) -> pd.Series:
    return btc_returns(price).rolling(window).std()


if __name__ == "__main__":
    seed_halvings()
    print("Halvings sembrados en la tabla `halvings`.")
