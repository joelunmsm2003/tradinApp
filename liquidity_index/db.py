"""Conexión a PostgreSQL + helpers de upsert idempotente para el Liquidity Index."""
import logging
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "liquidity_index"),
        user=os.getenv("POSTGRES_USER", "liquidity"),
        password=os.getenv("POSTGRES_PASSWORD", "liquidity"),
    )


def init_schema(conn) -> None:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        ddl = f.read()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _upsert(conn, table: str, indicador: str, fecha, valor: float, unidad: str, fuente: str) -> None:
    sql = f"""
        INSERT INTO {table} (indicador, fecha, valor, unidad, fuente, fecha_actualizacion)
        VALUES (%s, %s, %s, %s, %s, now())
        ON CONFLICT (indicador, fecha)
        DO UPDATE SET valor = EXCLUDED.valor, fecha_actualizacion = now()
        WHERE {table}.valor IS DISTINCT FROM EXCLUDED.valor
    """
    with conn.cursor() as cur:
        cur.execute(sql, (indicador, fecha, valor, unidad, fuente))


def upsert_series_economica(conn, indicador: str, fecha, valor: float, unidad: str, fuente: str = "FRED") -> None:
    _upsert(conn, "series_economicas", indicador, fecha, valor, unidad, fuente)


def upsert_mercado(conn, indicador: str, fecha, valor: float, unidad: str = "USD", fuente: str = "yfinance") -> None:
    _upsert(conn, "mercado", indicador, fecha, valor, unidad, fuente)


def upsert_stablecoin(conn, fecha, valor: float, unidad: str = "USD", fuente: str = "DefiLlama") -> None:
    _upsert(conn, "stablecoins", "stablecoin_total_mcap", fecha, valor, unidad, fuente)


def upsert_halving(conn, fecha, numero: int, es_estimado: bool, notas: str | None) -> None:
    sql = """
        INSERT INTO halvings (fecha, numero, es_estimado, notas)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (fecha) DO UPDATE SET numero = EXCLUDED.numero,
                                           es_estimado = EXCLUDED.es_estimado,
                                           notas = EXCLUDED.notas
    """
    with conn.cursor() as cur:
        cur.execute(sql, (fecha, numero, es_estimado, notas))


def read_series(conn, table: str, indicador: str):
    """Devuelve una pandas.Series indexada por fecha para un indicador de una tabla dada."""
    import pandas as pd

    sql = f"SELECT fecha, valor FROM {table} WHERE indicador = %s ORDER BY fecha"
    with conn.cursor() as cur:
        cur.execute(sql, (indicador,))
        rows = cur.fetchall()
    if not rows:
        return pd.Series(dtype=float)
    idx = pd.to_datetime([r[0] for r in rows])
    return pd.Series([float(r[1]) for r in rows], index=idx, name=indicador)
