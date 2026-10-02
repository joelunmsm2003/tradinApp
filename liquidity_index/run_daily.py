"""Pipeline diario: collect -> validate -> save -> (recalcular es on-read, sin paso aparte).

Pensado para Windows Task Scheduler con --once (corre una vez y termina),
no un loop infinito como monitor.py.
"""
import argparse
import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from liquidity_index import db
from liquidity_index.collectors import fred_collector, market_collector, stablecoin_collector
from liquidity_index.halvings import seed_halvings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run_pipeline() -> None:
    log.info("=== Liquidity Index: pipeline diario iniciado ===")

    conn = db.get_connection()
    try:
        db.init_schema(conn)
    finally:
        conn.close()

    seed_halvings()

    for name, collector in [
        ("FRED", fred_collector),
        ("Mercado (BTC/DXY)", market_collector),
        ("Stablecoins", stablecoin_collector),
    ]:
        log.info(f"--- Recolector: {name} ---")
        try:
            collector.run()
        except Exception as e:
            log.error(f"  Fallo en recolector {name}: {e}")

    log.info("=== Pipeline diario finalizado ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline diario del Liquidity Index")
    parser.add_argument("--once", action="store_true", help="Corre una sola vez y termina (para Task Scheduler)")
    args = parser.parse_args()

    if not args.once:
        log.warning("Este script está pensado para correr con --once desde Task Scheduler. Ejecutando de todos modos.")
    run_pipeline()


if __name__ == "__main__":
    main()
