"""Backtest del score de confluencia de scoring.py (el que dispara alertas de Telegram
y el banner de "alta confianza" del dashboard) — misma metodología rigurosa que
liquidity_index/backtest.py: correlación con RETORNOS FUTUROS de BTC (no con el nivel),
separando train (antes de 2023) / test (2023 en adelante) para no quedarnos con un
resultado que solo "se ve bien" en una parte de la historia.

Reimplementa BULLISH_RULES/BEARISH_RULES de scoring.py de forma VECTORIZADA (sobre toda
la serie histórica, no solo el último valor) para poder correlacionar con el tiempo.
Cuidado con lookahead: todo rolling usa .shift(1) antes de promediar cuando corresponde,
igual que el cálculo original de volumen en scoring.py (excluye el día actual).
"""
import json
import logging
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from indicators import _ema, _macd, _rsi, _stoch_rsi, classify_regime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "backtest_output")
REPORT_PATH = os.path.join(OUTPUT_DIR, "signals_report.json")

log = logging.getLogger(__name__)

CFG = {
    "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
    "bb_period": 20, "bb_std": 2.0, "macd_fast": 12,
    "macd_slow": 26, "macd_signal": 9, "ema_fast": 50, "ema_slow": 200,
}

TRAIN_TEST_SPLIT_DATE = "2023-01-01"
HORIZONS = (7, 30, 90, 180)


def _load_btc() -> pd.DataFrame:
    df = yf.download("BTC-USD", start="2014-01-01", interval="1d", progress=False, auto_adjust=True)
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.droplevel(1)
    return df


def _load_fng() -> pd.Series:
    resp = requests.get("https://api.alternative.me/fng/?limit=0", timeout=20)
    data = resp.json()["data"]
    idx = pd.to_datetime([int(d["timestamp"]) for d in data], unit="s")
    vals = [int(d["value"]) for d in data]
    return pd.Series(vals, index=idx, name="fng").sort_index()


def compute_score_series(df: pd.DataFrame, fng: pd.Series, cfg: dict) -> pd.DataFrame:
    close = df["Close"]
    macd_line, signal_line = _macd(close, cfg["macd_fast"], cfg["macd_slow"], cfg["macd_signal"])
    mid = close.rolling(cfg["bb_period"]).mean()
    std = close.rolling(cfg["bb_period"]).std(ddof=0)
    bb_upper = mid + cfg["bb_std"] * std
    bb_lower = mid - cfg["bb_std"] * std
    ema_fast = _ema(close, cfg["ema_fast"])
    ema_slow = _ema(close, cfg["ema_slow"])
    rsi = _rsi(close, cfg["rsi_period"])
    stoch_k, stoch_d = _stoch_rsi(close)
    vol = df["Volume"]
    vol_avg20 = vol.shift(1).rolling(20).mean()
    vol_spike = (vol_avg20 > 0) & (vol / vol_avg20 >= 2.0)

    prev = close.shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(), (df["Low"] - prev).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    atr_ratio = tr / atr
    atr_high = atr_ratio >= 1.5

    fng_aligned = fng.reindex(close.index, method="ffill")

    bull = pd.DataFrame(index=close.index)
    bull["rsi_oversold"] = np.where(rsi < cfg["rsi_oversold"], 2, 0)
    bull["macd_bull"] = np.where(macd_line > signal_line, 2, 0)
    bull["bb_bajo"] = np.where(close < bb_lower, 2, 0)
    bull["stoch_oversold"] = np.where((stoch_k < 20) & (stoch_k > stoch_d), 1, 0)
    bull["golden_cross"] = np.where(ema_fast > ema_slow, 1, 0)
    bull["vol_spike"] = np.where(vol_spike, 1, 0)
    bull["fng_miedo"] = np.where(fng_aligned <= 25, 1, 0)
    bull_score = bull.sum(axis=1)

    bear = pd.DataFrame(index=close.index)
    bear["rsi_overbought"] = np.where(rsi > cfg["rsi_overbought"], 2, 0)
    bear["macd_bear"] = np.where(macd_line < signal_line, 2, 0)
    bear["bb_sobre"] = np.where(close > bb_upper, 2, 0)
    bear["stoch_overbought"] = np.where((stoch_k > 80) & (stoch_k < stoch_d), 1, 0)
    bear["death_cross"] = np.where(ema_fast < ema_slow, 1, 0)
    bear["vol_spike"] = np.where(vol_spike, 1, 0)
    bear["fng_codicia"] = np.where(fng_aligned >= 75, 1, 0)
    bear_score = bear.sum(axis=1)

    atr_bonus_bull = np.where(atr_high & (bull_score > bear_score), 1, 0)
    atr_bonus_bear = np.where(atr_high & (bear_score > bull_score), 1, 0)
    bull_score_final = bull_score + atr_bonus_bull
    bear_score_final = bear_score + atr_bonus_bear

    out = pd.DataFrame({"close": close})
    for col in bull.columns:
        out[f"bull_{col}"] = bull[col]
    for col in bear.columns:
        out[f"bear_{col}"] = bear[col]
    out["bull_atr_bonus"] = atr_bonus_bull
    out["bear_atr_bonus"] = atr_bonus_bear
    out["bull_score"] = bull_score_final
    out["bear_score"] = bear_score_final
    out["net_score"] = bull_score_final - bear_score_final
    return out


def _forward_return_corr(signal: pd.Series, close: pd.Series, horizon: int) -> float | None:
    fwd = close.pct_change(periods=horizon).shift(-horizon)
    pair = pd.concat([signal.rename("signal"), fwd.rename("fwd")], axis=1).dropna()
    if len(pair) < 30:
        return None
    corr = pair["signal"].corr(pair["fwd"])
    return None if pd.isna(corr) else float(corr)


def run() -> None:
    log.info("Descargando BTC-USD e histórico de Fear & Greed...")
    df = _load_btc()
    fng = _load_fng()
    scores = compute_score_series(df, fng, CFG)

    split = pd.Timestamp(TRAIN_TEST_SPLIT_DATE)
    train = scores[scores.index < split]
    test = scores[scores.index >= split]
    log.info(f"Train: hasta {split.date()} ({len(train)} obs) | Test: desde {split.date()} ({len(test)} obs)")

    aggregate_cols = ["bull_score", "bear_score", "net_score"]
    individual_cols = [c for c in scores.columns
                        if (c.startswith("bull_") or c.startswith("bear_")) and c not in aggregate_cols]

    train_test_report = {}

    def _report(cols, titulo):
        print("\n" + "#" * 78)
        print(f"# {titulo}")
        print("#" * 78)
        for signal_col in cols:
            print("-" * 78)
            print(f"SEÑAL: {signal_col}")
            train_test_report[signal_col] = {}
            for h in HORIZONS:
                c_train = _forward_return_corr(train[signal_col], train["close"], h)
                c_test = _forward_return_corr(test[signal_col], test["close"], h)
                t_train = f"{c_train:+.3f}" if c_train is not None else "sin datos"
                t_test = f"{c_test:+.3f}" if c_test is not None else "sin datos"
                flip = ""
                if c_train is not None and c_test is not None and (c_train > 0) != (c_test > 0):
                    flip = "  <- CAMBIA DE SIGNO"
                stable = c_train is not None and c_test is not None and not flip and min(abs(c_train), abs(c_test)) > 0.03
                mark = "  [estable]" if stable else ""
                print(f"  +{h:>3}d:  train={t_train}   test={t_test}{flip}{mark}")
                train_test_report[signal_col][h] = {
                    "train": c_train, "test": c_test,
                    "sign_flip": bool(flip), "stable": bool(stable),
                }

    _report(individual_cols, "POR SEÑAL INDIVIDUAL (sin combinar)")
    _report(aggregate_cols, "SCORE COMBINADO (para comparar)")

    # ---- Desglose por régimen (alcista/bajista/lateral) ----
    scores["regime"] = classify_regime(scores["close"])
    print("\n" + "#" * 78)
    print("# DESGLOSE POR RÉGIMEN DE MERCADO (alcista/bajista/lateral, todo el histórico)")
    print("# Nota: esto NO es train/test — es descriptivo, para ver si una señal solo")
    print("# 'funciona' porque coincide con el régimen dominante (BTC pasó más tiempo")
    print("# en alcista que en bajista/lateral en su historia).")
    print("#" * 78)
    counts = scores["regime"].value_counts()
    print(f"  Días por régimen: {dict(counts)}")

    # Retorno futuro calculado sobre la serie COMPLETA (90 días de calendario reales),
    # recién después se filtra por régimen — filtrar antes distorsionaría el horizonte
    # (saltaría sobre huecos de otros regímenes en vez de usar 90 días reales).
    fwd_90_full = scores["close"].pct_change(periods=90).shift(-90)

    interesting_cols = individual_cols + aggregate_cols
    regime_report = {"days": {k: int(v) for k, v in counts.items()}, "corr_90d": {}}
    for regime_name in ["alcista", "bajista", "lateral"]:
        mask = scores["regime"] == regime_name
        n_days = int(mask.sum())
        if n_days < 60:
            print(f"\n  Régimen '{regime_name}': muy pocos datos ({n_days} días), se omite")
            continue
        print(f"\n  --- Régimen: {regime_name} ({n_days} días) ---")
        regime_report["corr_90d"][regime_name] = {}
        for col in interesting_cols:
            pair = pd.concat([scores.loc[mask, col].rename("signal"), fwd_90_full.loc[mask].rename("fwd")], axis=1).dropna()
            corr_90 = pair["signal"].corr(pair["fwd"]) if len(pair) >= 30 else None
            if corr_90 is None:
                label = "sin datos"
                json_val = None
            elif pd.isna(corr_90):
                label = "sin variación (la señal no se activó en este régimen)"
                json_val = None
            else:
                label = f"{corr_90:+.3f}"
                json_val = round(float(corr_90), 4)
            print(f"    {col:<20} corr +90d: {label}")
            regime_report["corr_90d"][regime_name][col] = json_val

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "train_test_split": TRAIN_TEST_SPLIT_DATE,
        "horizons": list(HORIZONS),
        "train_test": train_test_report,
        "regime": regime_report,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log.info(f"Reporte guardado en {REPORT_PATH}")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
