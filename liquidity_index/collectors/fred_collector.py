"""Recolector de series económicas de FRED (M2, balance Fed, RRP, TGA, Treasury 10Y).

Usa la API REST de FRED directamente (sin librería fredapi) vía `requests`.
Cada serie se descarga y valida por separado: si una falla, no tumba las demás
(mismo patrón que run_checks() en monitor.py).
"""
import logging
import os
from datetime import date, datetime

import requests
from dotenv import load_dotenv

from liquidity_index import db
from liquidity_index.config import FRED_SERIES

load_dotenv()

log = logging.getLogger(__name__)

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_fred_series(series_id: str, api_key: str) -> list[tuple[date, float]]:
    """Descarga una serie de FRED. Retorna lista de (fecha, valor), sin missing values."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    resp = requests.get(FRED_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    out = []
    for obs in data.get("observations", []):
        raw_value = obs.get("value")
        if raw_value is None or raw_value == ".":
            continue  # FRED usa "." para missing values
        try:
            fecha = datetime.strptime(obs["date"], "%Y-%m-%d").date()
            valor = float(raw_value)
        except (ValueError, KeyError):
            continue
        if fecha > date.today():
            continue  # descarta fechas futuras inválidas
        out.append((fecha, valor))
    return out


def run() -> None:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        log.error("FRED_API_KEY no configurada en .env — abortando recolección FRED.")
        return

    conn = db.get_connection()
    try:
        for series_id, unidad in FRED_SERIES.items():
            log.info(f"Descargando serie FRED: {series_id}")
            try:
                rows = fetch_fred_series(series_id, api_key)
            except Exception as e:
                log.warning(f"  Error descargando {series_id}: {e}")
                continue

            if not rows:
                log.warning(f"  {series_id}: sin datos válidos, se omite")
                continue

            for fecha, valor in rows:
                db.upsert_series_economica(conn, series_id, fecha, valor, unidad, fuente="FRED")
            conn.commit()
            log.info(f"  {series_id}: {len(rows)} observaciones guardadas ({rows[0][0]} -> {rows[-1][0]})")
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
