"""Recolector de capitalización total de stablecoins vía la API pública de DefiLlama.

Formato verificado en vivo: cada fila es
{"date": "<unix ts string>", "totalCirculatingUSD": {"peggedUSD": <float>, ...otras monedas...}}
Usamos totalCirculatingUSD.peggedUSD como la cap. total de stablecoins en USD.
"""
import logging
from datetime import date, datetime, timezone

import requests

from liquidity_index import db
from liquidity_index.config import DEFILLAMA_STABLECOINS_URL

log = logging.getLogger(__name__)


def fetch_stablecoin_mcap() -> list[tuple[date, float]]:
    resp = requests.get(DEFILLAMA_STABLECOINS_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    out = []
    for row in data:
        try:
            ts = int(row["date"])
            valor = float(row["totalCirculatingUSD"]["peggedUSD"])
        except (KeyError, TypeError, ValueError):
            continue
        fecha = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        if fecha > date.today():
            continue
        out.append((fecha, valor))
    return out


def run() -> None:
    conn = db.get_connection()
    try:
        log.info("Descargando cap. total de stablecoins (DefiLlama)")
        try:
            rows = fetch_stablecoin_mcap()
        except Exception as e:
            log.warning(f"  Error descargando stablecoins: {e}")
            return

        if not rows:
            log.warning("  Sin datos válidos, se omite")
            return

        for fecha, valor in rows:
            db.upsert_stablecoin(conn, fecha, valor)
        conn.commit()
        log.info(f"  {len(rows)} observaciones guardadas ({rows[0][0]} -> {rows[-1][0]})")
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
