"""Backtesting del Liquidity Index.

RESULTADO PRINCIPAL: correlación del índice vs precio de BTC y vs retornos futuros de
BTC, usando TODO el histórico diario disponible (miles de observaciones). Esta es la
prueba estadísticamente válida de la hipótesis "la liquidez global correlaciona con
BTC" — no depende de eventos puntuales ni de ventanas recortadas.

REFERENCIA CONTEXTUAL (no es una prueba estadística): desglose por ciclo de halving,
solo para anotar visualmente en el dashboard dónde cae cada ciclo narrativo de BTC.
Con apenas 3-4 halvings históricos (n=3 útiles, yfinance no tiene BTC-USD antes de
2014) cualquier "patrón" ahí es anécdota, no evidencia — el halving es un evento de
OFERTA de Bitcoin (mecánica interna, fecha fija), mientras que el índice mide
demanda/macro; no hay mecanismo por el cual uno cause al otro, así que una
coincidencia de calendario en un ciclo no prueba nada por sí sola.

Reporta también los casos donde el índice general FALLA — no solo los que confirman
la hipótesis (principio explícito del spec original).
"""
import csv
import json
import logging
import os
from datetime import datetime, timezone

import pandas as pd

from liquidity_index import db
from liquidity_index.config import CYCLE_WINDOW_DAYS_AFTER, CYCLE_WINDOW_DAYS_BEFORE, HALVINGS
from liquidity_index.liquidity_index import calculate_liquidity_index

log = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "backtest_output")


def _load_btc_price(conn) -> pd.Series:
    return db.read_series(conn, "mercado", "BTC-USD")


def correlation_report(index: pd.Series, btc: pd.Series, horizons=(7, 30, 90, 180)) -> dict:
    aligned = pd.concat([index.rename("index"), btc.rename("btc")], axis=1).dropna()
    report = {
        "n_obs": len(aligned),
        "corr_pearson_level": float(aligned["index"].corr(aligned["btc"], method="pearson")),
        "corr_spearman_level": float(aligned["index"].corr(aligned["btc"], method="spearman")),
        "forward_return_corr": {},
    }
    btc_full = btc.reindex(index.index.union(btc.index)).sort_index()
    for h in horizons:
        fwd_return = btc_full.pct_change(periods=h).shift(-h)
        pair = pd.concat([index.rename("index"), fwd_return.rename("fwd")], axis=1).dropna()
        if len(pair) > 5:
            c = pair["index"].corr(pair["fwd"])
            report["forward_return_corr"][h] = None if pd.isna(c) else float(c)
        else:
            report["forward_return_corr"][h] = None
    return report


def halving_cycle_windows(btc: pd.Series, index: pd.Series) -> list[dict]:
    results = []
    for h in HALVINGS:
        if h["es_estimado"]:
            continue
        fecha = pd.Timestamp(h["fecha"])
        start = fecha - pd.Timedelta(days=CYCLE_WINDOW_DAYS_BEFORE)
        end = fecha + pd.Timedelta(days=CYCLE_WINDOW_DAYS_AFTER)

        btc_window = btc[(btc.index >= start) & (btc.index <= end)]
        idx_window = index[(index.index >= start) & (index.index <= end)]
        if btc_window.empty or idx_window.empty:
            results.append({"halving": h["fecha"], "numero": h["numero"], "status": "sin datos suficientes"})
            continue

        pair = pd.concat([idx_window.rename("index"), btc_window.rename("btc")], axis=1).dropna()
        corr = pair["index"].corr(pair["btc"]) if len(pair) > 5 else None
        corr = None if corr is None or pd.isna(corr) else float(corr)
        btc_return_window = btc_window.iloc[-1] / btc_window.iloc[0] - 1 if len(btc_window) > 1 else None
        btc_return_window = None if btc_return_window is None else float(btc_return_window)

        results.append({
            "halving": h["fecha"],
            "numero": h["numero"],
            "ventana": f"{start.date()} -> {end.date()}",
            "corr_index_btc": corr,
            "retorno_btc_ventana": btc_return_window,
            "n_obs": len(pair),
        })
    return results


def run(save_csv: bool = True) -> dict:
    conn = db.get_connection()
    try:
        index = calculate_liquidity_index(conn)
        btc = _load_btc_price(conn)
    finally:
        conn.close()

    if index.empty or btc.empty:
        log.warning("No hay suficientes datos para backtesting (índice o BTC vacíos).")
        return {}

    corr = correlation_report(index, btc)
    cycles = halving_cycle_windows(btc, index)

    print("=" * 70)
    print("RESULTADO PRINCIPAL — correlación general (todo el histórico, n_obs=%d)" % corr["n_obs"])
    print("=" * 70)
    print(f"  Nivel — Pearson:  {corr['corr_pearson_level']:.3f}")
    print(f"  Nivel — Spearman: {corr['corr_spearman_level']:.3f}")
    print("  (nivel = compara si ambas series suben/bajan juntas en 16 años — puede")
    print("   estar inflado por tendencia compartida, no implica poder predictivo)")
    print("\n  Retorno futuro de BTC (esto sí mide poder predictivo):")
    forward_corrs = []
    for h, c in corr["forward_return_corr"].items():
        label = f"{c:+.3f}" if c is not None else "sin datos suficientes"
        print(f"    +{h}d: {label}")
        if c is not None:
            forward_corrs.append(abs(c))

    no_signal = bool(forward_corrs and max(forward_corrs) < 0.1)
    if no_signal:
        veredicto = ("Sin relación predictiva significativa con retornos futuros de BTC en "
                     "ningún horizonte. El índice v1 describe contexto de nivel, NO debe "
                     "usarse como señal de entrada/salida.")
        print("\n  VEREDICTO: sin relación predictiva significativa con retornos futuros")
        print("  de BTC en ningún horizonte. El índice v1 describe contexto de nivel,")
        print("  NO debe usarse como señal de entrada/salida (esto es justo lo que")
        print("  advierte el spec original: no usar el índice como predictor automático).")
    else:
        veredicto = "Hay indicios de relación con retornos futuros — revisar antes de confiar."
        print("\n  VEREDICTO: hay indicios de relación con retornos futuros — revisar")
        print("  el horizonte con mayor |correlación| antes de sacar conclusiones.")

    print("\n" + "=" * 70)
    print("REFERENCIA CONTEXTUAL (NO es prueba estadística — solo %d halvings," % len([c for c in cycles if "status" not in c]))
    print("muestra insuficiente para conclusiones; solo para anotar en el dashboard)")
    print("=" * 70)
    for c in cycles:
        print(f"  Halving #{c['numero']} ({c['halving']}): {c}")

    if save_csv:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = os.path.join(OUTPUT_DIR, "halving_cycles.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["halving", "numero", "ventana", "corr_index_btc", "retorno_btc_ventana", "n_obs", "status"])
            writer.writeheader()
            for c in cycles:
                writer.writerow({k: c.get(k, "") for k in writer.fieldnames})
        log.info(f"Reporte de ciclos guardado en {path}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "liquidity_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "correlation": corr,
            "veredicto": veredicto,
            "no_signal": no_signal,
            "cycles": cycles,
        }, f, indent=2, ensure_ascii=False)
    log.info(f"Reporte JSON guardado en {report_path}")

    return {"correlation": corr, "cycles": cycles}


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
