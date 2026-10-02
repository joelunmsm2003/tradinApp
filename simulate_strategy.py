"""Simulación histórica (backtest) de estrategias simples usando las señales ya
validadas, comparadas contra Buy & Hold. Esto NO es asesoría financiera ni una
recomendación de inversión — es una simulación retrospectiva con datos históricos,
sin comisiones, sin slippage, sin impuestos. Rendimiento pasado no garantiza
rendimiento futuro. Sirve para ver con números concretos qué tan bien (o mal)
hubieran funcionado estas señales como regla mecánica de entrada/salida.

Estrategias:
  1. Buy & Hold: compra $1000 el primer día y nunca vende.
  2. Golden/Death Cross: invertido en BTC solo cuando EMA50 > EMA200 (Golden Cross
     activo); en cash (0% de retorno) cuando hay Death Cross. Es la señal individual
     más validada del backtest (backtest_signals.py).
  3. Score combinado: invertido cuando net_score (bull_score - bear_score) > 0;
     en cash cuando es <= 0. Ya sabemos que es más débil/ruidoso que Golden Cross solo.
"""
import logging

import pandas as pd

from backtest_signals import CFG, _load_btc, _load_fng, compute_score_series

log = logging.getLogger(__name__)

INITIAL_CAPITAL = 1000.0


def simulate(close: pd.Series, invested: pd.Series, initial_capital: float = INITIAL_CAPITAL) -> dict:
    """invested: bool Series (True = en BTC ese día, False = en cash). Sin comisiones."""
    daily_return = close.pct_change().fillna(0)
    invested_prev = invested.shift(1).fillna(False).astype(bool)
    strategy_return = daily_return.where(invested_prev, 0.0)
    equity = (1 + strategy_return).cumprod() * initial_capital

    trades = int((invested != invested.shift(1)).sum())
    days_invested = int(invested.sum())

    return {
        "final_value": float(equity.iloc[-1]),
        "return_pct": float(equity.iloc[-1] / initial_capital - 1) * 100,
        "trades": trades,
        "days_invested": days_invested,
        "days_total": len(close),
        "equity_curve": equity,
    }


def max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    dd = equity / running_max - 1
    return float(dd.min()) * 100


def run() -> None:
    log.info("Descargando datos y calculando señales...")
    df = _load_btc()
    fng = _load_fng()
    scores = compute_score_series(df, fng, CFG)
    close = scores["close"]

    strategies = {
        "Buy & Hold": pd.Series(True, index=close.index),
        "Golden/Death Cross": scores["bull_golden_cross"] > 0,
        "Score combinado (net_score > 0)": scores["net_score"] > 0,
    }

    print("=" * 78)
    print(f"SIMULACIÓN: ${INITIAL_CAPITAL:,.0f} invertidos desde {close.index[0].date()} hasta {close.index[-1].date()}")
    print("(sin comisiones, sin slippage, sin impuestos — NO es asesoría financiera)")
    print("=" * 78)

    results = {}
    for name, invested in strategies.items():
        r = simulate(close, invested)
        dd = max_drawdown(r["equity_curve"])
        results[name] = r
        print(f"\n{name}")
        print(f"  Valor final:        ${r['final_value']:,.2f}  ({r['return_pct']:+.1f}%)")
        print(f"  Máximo drawdown:    {dd:.1f}%")
        print(f"  Días invertido:     {r['days_invested']} / {r['days_total']} ({r['days_invested']/r['days_total']*100:.0f}%)")
        print(f"  Cambios de posición: {r['trades']}")

    print("\n" + "=" * 78)
    bh = results["Buy & Hold"]["final_value"]
    for name, r in results.items():
        if name == "Buy & Hold":
            continue
        diff = r["final_value"] - bh
        label = "mejor" if diff > 0 else "peor"
        print(f"{name} vs Buy & Hold: ${diff:+,.2f} ({label} que solo comprar y mantener)")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
