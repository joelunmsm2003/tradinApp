"""Recolector de precios de mercado (BTC-USD, DXY) vía yfinance.

Reutiliza el mismo patrón de descarga que web.py::_get_btc_df, pero sin caché TTL
(esto corre una vez al día, no por request HTTP).
"""
import logging

import yfinance as yf

from liquidity_index import db
from liquidity_index.config import MARKET_TICKERS

log = logging.getLogger(__name__)


def _download(ticker: str, start: str = "2010-01-01"):
    df = yf.download(ticker, start=start, interval="1d", progress=False, auto_adjust=True)
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.droplevel(1)
    return df


def run() -> None:
    conn = db.get_connection()
    try:
        for indicador, ticker in MARKET_TICKERS.items():
            log.info(f"Descargando mercado: {indicador} ({ticker})")
            try:
                df = _download(ticker)
            except Exception as e:
                log.warning(f"  Error descargando {ticker}: {e}")
                continue

            if df.empty or "Close" not in df.columns:
                log.warning(f"  {indicador}: sin datos válidos, se omite")
                continue

            count = 0
            for ts, row in df.iterrows():
                close = row["Close"]
                if close != close:  # NaN check
                    continue
                db.upsert_mercado(conn, indicador, ts.date(), float(close), fuente="yfinance")
                count += 1
            conn.commit()
            log.info(f"  {indicador}: {count} observaciones guardadas")
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
