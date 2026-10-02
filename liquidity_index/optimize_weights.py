"""Búsqueda de pesos para el Liquidity Index — Fase 7 (parte de backtesting).

Los pesos en config.WEIGHTS fueron elegidos a mano ("a ojo"). Este script prueba
muchas combinaciones al azar (búsqueda aleatoria sobre el símplex, todas positivas
y suman 1 — ver la nota en config.py sobre por qué positivas) y mide cuál correlaciona
mejor con el RETORNO FUTURO de BTC (no con el nivel, que es la métrica que realmente
importa para uso predictivo).

Importante — separación train/test para evitar sobreajuste:
Buscar en TODO el histórico y quedarnos con lo que mejor correlacionó ahí es exactamente
el error que el spec pide evitar ("no mirar solo resultados que funcionen"). Por eso:
  - TRAIN: datos antes de TRAIN_TEST_SPLIT_DATE — ahí se hace la búsqueda.
  - TEST:  datos desde esa fecha en adelante — ahí se valida si el mejor de train
           realmente generaliza o fue puro ajuste a ruido histórico.
Si la correlación se cae o cambia de signo en test, es la señal honesta de que esa
combinación de pesos no sirve, por más bien que se vea en train.
"""
import logging

import numpy as np
import pandas as pd

from liquidity_index import db
from liquidity_index.config import STABLECOIN_INDICATOR
from liquidity_index.liquidity_index import _load_normalized_series

log = logging.getLogger(__name__)

TRAIN_TEST_SPLIT_DATE = "2023-01-01"
FORWARD_HORIZON_DAYS = 90
N_RANDOM_SAMPLES = 3000
TOP_N_TO_VALIDATE = 8

COMPONENTS = ["M2SL", "WALCL", "RRPONTSYD", "WTREGEN", STABLECOIN_INDICATOR, "DXY", "DGS10"]


def _weighted_index(normalized: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    cols = [normalized[k].rename(k) * w for k, w in weights.items() if k in normalized]
    if not cols:
        return pd.Series(dtype=float)
    return pd.concat(cols, axis=1).sum(axis=1, skipna=True)


def _forward_return_corr(index: pd.Series, btc: pd.Series, horizon: int) -> float | None:
    btc_full = btc.reindex(index.index.union(btc.index)).sort_index()
    fwd = btc_full.pct_change(periods=horizon).shift(-horizon)
    pair = pd.concat([index.rename("index"), fwd.rename("fwd")], axis=1).dropna()
    if len(pair) < 30:
        return None
    return pair["index"].corr(pair["fwd"])


def _sample_weights(rng: np.random.Generator) -> dict[str, float]:
    raw = rng.dirichlet(np.ones(len(COMPONENTS)))
    return dict(zip(COMPONENTS, raw))


def run(horizon: int = FORWARD_HORIZON_DAYS, n_samples: int = N_RANDOM_SAMPLES) -> None:
    conn = db.get_connection()
    try:
        normalized = _load_normalized_series(conn)
        btc = db.read_series(conn, "mercado", "BTC-USD")
    finally:
        conn.close()

    available = [c for c in COMPONENTS if c in normalized]
    missing = [c for c in COMPONENTS if c not in normalized]
    if missing:
        log.warning(f"Componentes sin datos, se omiten de la búsqueda: {missing}")

    split = pd.Timestamp(TRAIN_TEST_SPLIT_DATE)
    train_mask = btc.index < split
    test_mask = ~train_mask
    btc_train, btc_test = btc[train_mask], btc[test_mask]

    log.info(f"Train: hasta {split.date()} ({train_mask.sum()} obs BTC) | Test: desde {split.date()} ({test_mask.sum()} obs BTC)")
    log.info(f"Buscando entre {n_samples} combinaciones aleatorias de pesos, horizonte +{horizon}d...")

    rng = np.random.default_rng(42)
    results = []
    for _ in range(n_samples):
        weights = _sample_weights(rng)
        idx = _weighted_index(normalized, weights)
        idx_train = idx[idx.index < split]
        corr_train = _forward_return_corr(idx_train, btc_train, horizon)
        if corr_train is None:
            continue
        results.append((corr_train, weights))

    if not results:
        log.error("No se pudo evaluar ninguna combinación (datos insuficientes).")
        return

    # Ordenar por |correlación| en train (nos interesa relación fuerte, sea + o -)
    results.sort(key=lambda r: abs(r[0]), reverse=True)
    top = results[:TOP_N_TO_VALIDATE]

    baseline_weights = {c: 1.0 / len(available) for c in available}
    baseline_idx = _weighted_index(normalized, baseline_weights)
    baseline_train = _forward_return_corr(baseline_idx[baseline_idx.index < split], btc_train, horizon)
    baseline_test = _forward_return_corr(baseline_idx[baseline_idx.index >= split], btc_test, horizon)

    print("=" * 78)
    print(f"BASELINE (pesos iguales, {len(available)} componentes) — horizonte +{horizon}d")
    print("=" * 78)
    print(f"  Train corr: {baseline_train:+.3f}" if baseline_train is not None else "  Train corr: sin datos")
    print(f"  Test  corr: {baseline_test:+.3f}" if baseline_test is not None else "  Test  corr: sin datos")

    print("\n" + "=" * 78)
    print(f"TOP {TOP_N_TO_VALIDATE} combinaciones por |correlación| en TRAIN, validadas en TEST")
    print("=" * 78)
    generalizan = 0
    sign_flips = 0
    for corr_train, weights in top:
        idx = _weighted_index(normalized, weights)
        corr_test = _forward_return_corr(idx[idx.index >= split], btc_test, horizon)
        w_str = ", ".join(f"{k}={v:.2f}" for k, v in sorted(weights.items(), key=lambda x: -x[1]))
        same_sign = corr_test is not None and (corr_train > 0) == (corr_test > 0)
        holds_up = bool(same_sign) and corr_test is not None and abs(corr_test) > 0.05
        if holds_up:
            generalizan += 1
        test_label = f"{corr_test:+.3f}" if corr_test is not None else "sin datos"
        if holds_up:
            veredicto = "generaliza"
        elif corr_test is not None and not same_sign:
            veredicto = "CAMBIA DE SIGNO en test"
            sign_flips += 1
        else:
            veredicto = "se diluye en test"
        print(f"  train={corr_train:+.3f}  test={test_label}  [{veredicto}]")
        print(f"    pesos: {w_str}")

    print("\n" + "=" * 78)
    print(f"VEREDICTO FINAL: {generalizan} de {TOP_N_TO_VALIDATE} combinaciones top-en-train")
    print(f"mantuvieron una relación real en test (mismo signo y |corr|>0.05).")
    if sign_flips >= TOP_N_TO_VALIDATE // 2:
        print(f"\nHALLAZGO NOTABLE: {sign_flips} de {TOP_N_TO_VALIDATE} combinaciones cambiaron de")
        print("signo entre train y test (no solo se diluyeron — se invirtieron). Eso sugiere")
        print("un cambio de régimen real entre el período pre-2023 y el actual (ej: ciclo de")
        print("suba de tasas de la Fed 2022-23, drenaje del RRP en 2023-24 coincidiendo con un")
        print("bull run de BTC) más que simple ruido — pero un cambio de régimen significa que")
        print("el índice sería, en el mejor de los casos, INESTABLE como señal, no confiable.")
    if generalizan == 0:
        print("Ninguna combinación de pesos probada generaliza fuera de muestra —")
        print("la búsqueda no encontró evidencia de que AJUSTAR LOS PESOS resuelva")
        print("la falta de poder predictivo. El problema probablemente no es el peso")
        print("relativo de las variables, sino el enfoque del índice v1 en sí")
        print("(zscore + suma lineal diaria) frente a la granularidad real de los datos.")
    print("=" * 78)


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
