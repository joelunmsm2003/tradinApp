"""Backtest de momentum a 1h: ¿comprar una cripto porque subió >= X% en la última hora
es rentable tras comisiones? Simulación retrospectiva con velas de 1h de Binance
(~41 días). NO es asesoría financiera; rendimiento pasado no garantiza el futuro.

Regla: si la vela de 1h cerró con (close/open - 1) >= umbral, se compra al OPEN de la
vela siguiente (sin lookahead) y se vende `hold_h` horas después. Se descuenta
(comisión + slippage) por lado. Tras una entrada, esa moneda queda en cooldown hasta
la salida (sin posiciones solapadas).
"""
import heapq
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

BINANCE = "https://api.binance.com/api/v3"
STABLES = {"USDC", "FDUSD", "TUSD", "USDP", "BUSD", "DAI", "USD1", "USDE", "EUR", "EURI", "AEUR",
           "XUSD", "USDS", "U", "PYUSD", "RLUSD", "BFUSD", "UST", "USDT"}
UNIVERSE_SIZE = 100
CACHE_TTL = 3600
POSITION_SIZE = 100.0
INITIAL_CAPITAL = 1000.0

_cache: dict = {"klines": None, "ts": 0.0}


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def load_universe(n: int = UNIVERSE_SIZE) -> list[str]:
    """Top-n pares XUSDT por volumen 24h, sin stablecoins ni tokens apalancados."""
    rows = _get(f"{BINANCE}/ticker/24hr")
    out = []
    for r in rows:
        sym = r["symbol"]
        if not sym.endswith("USDT"):
            continue
        base = sym[:-4]
        if base in STABLES or base.endswith(("UP", "DOWN", "BULL", "BEAR")):
            continue
        out.append((float(r["quoteVolume"]), sym))
    out.sort(reverse=True)
    return [s for _, s in out[:n]]


def _load_one(symbol: str):
    raw = _get(f"{BINANCE}/klines?symbol={symbol}&interval=1h&limit=1000")
    df = pd.DataFrame(raw).iloc[:, :8]
    df.columns = ["t", "open", "high", "low", "close", "vol", "ct", "qvol"]
    df = df.iloc[:-1]  # descarta la vela en curso (incompleta)
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    for c in ("open", "close", "qvol"):
        df[c] = df[c].astype(float)
    return symbol, df[["t", "open", "close", "qvol"]].reset_index(drop=True)


def load_klines() -> dict:
    if _cache["klines"] is not None and time.time() - _cache["ts"] < CACHE_TTL:
        return _cache["klines"]
    symbols = load_universe()
    with ThreadPoolExecutor(max_workers=8) as ex:
        data = {}
        for res in ex.map(lambda s: _safe(_load_one, s), symbols):
            if res:
                data[res[0]] = res[1]
    _cache["klines"], _cache["ts"] = data, time.time()
    return data


def _safe(fn, arg):
    try:
        return fn(arg)
    except Exception:
        return None


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min()) * 100


def _trades(data: dict, threshold: float, hold_h: int, cost: float, min_vol: float,
            max_rise: float | None = None) -> pd.DataFrame:
    rows = []
    for sym, df in data.items():
        o = df["open"].to_numpy()
        ret1h = df["close"].to_numpy() / o - 1
        sig = (ret1h >= threshold) & (df["qvol"].to_numpy() >= min_vol)
        if max_rise is not None:  # ignora velas "pump" demasiado grandes (filtro de entrada, sin lookahead)
            sig &= ret1h <= max_rise
        n, i = len(df), 0
        while i < n - hold_h - 1:
            if sig[i]:
                entry, exit_ = i + 1, i + 1 + hold_h
                net = (o[exit_] / o[entry]) * (1 - cost) / (1 + cost) - 1
                rows.append((sym, df["t"].iloc[entry], df["t"].iloc[exit_], ret1h[i], net))
                i = exit_  # cooldown: sin posiciones solapadas en la misma moneda
            else:
                i += 1
    return pd.DataFrame(rows, columns=["symbol", "entry", "exit", "signal_ret", "net"])


def _baseline(data: dict, hold_h: int, cost: float) -> float:
    """Retorno medio neto de comprar en CUALQUIER hora (misma tenencia y costos)."""
    vals = []
    for df in data.values():
        o = df["open"].to_numpy()
        if len(o) > hold_h + 1:
            vals.append((o[hold_h + 1:] / o[1:-hold_h]) * (1 - cost) / (1 + cost) - 1)
    return float(np.concatenate(vals).mean() * 100) if vals else 0.0


def portfolio(tr: pd.DataFrame, capital: float, size: float) -> dict:
    """Cuenta real: solo abre una operación si hay efectivo libre (size). Si varias señales
    coinciden en la misma hora y no alcanza el efectivo, se prioriza la de mayor subida 1h.
    La equity mostrada es realizada (efectivo + dinero invertido a costo, sin marcar a mercado)."""
    order = tr.sort_values(["entry", "signal_ret"], ascending=[True, False])
    cash, open_pos, taken, curve = capital, [], [], [(int(order["entry"].iloc[0].timestamp()), capital)]
    invested, max_conc, skipped = 0.0, 0, 0

    def release(until):
        nonlocal cash, invested
        while open_pos and open_pos[0][0] <= until:
            t_exit, _, sz, net = heapq.heappop(open_pos)
            cash += sz * (1 + net)
            invested -= sz
            curve.append((int(t_exit.timestamp()), cash + invested))

    for i, r in enumerate(order.itertuples()):
        release(r.entry)
        if cash >= size:
            cash -= size
            invested += size
            heapq.heappush(open_pos, (r.exit, i, size, r.net))
            taken.append(True)
            max_conc = max(max_conc, len(open_pos))
        else:
            taken.append(False)
            skipped += 1
    release(pd.Timestamp.max)
    eq = pd.Series([v for _, v in curve])
    return {
        "taken_idx": dict(zip(order.index, taken)),
        "executed": int(sum(taken)), "skipped": skipped, "max_concurrent": max_conc,
        "final_capital": float(cash), "return_pct": float((cash / capital - 1) * 100),
        "max_drawdown_pct": max_drawdown(eq),
        "equity": [{"time": t, "value": float(v)} for t, v in curve],
    }


def simulate(threshold: float = 0.03, hold_h: int = 4, fee: float = 0.001,
             slippage: float = 0.001, min_vol: float = 100_000, data: dict | None = None,
             max_rise: float | None = None, exclude: tuple = (),
             capital: float = INITIAL_CAPITAL, size: float = POSITION_SIZE) -> dict:
    data = _without(data if data is not None else load_klines(), exclude)
    cost = fee + slippage
    tr = _trades(data, threshold, hold_h, cost, min_vol, max_rise)
    base = _baseline(data, hold_h, cost)
    if tr.empty:
        return {"trades": 0, "baseline_pct": base, "equity": []}

    tr = tr.sort_values("exit")
    pf = portfolio(tr, capital, size)
    taken = pf.pop("taken_idx")
    by_sym = tr.groupby("symbol")["net"].agg(["count", "mean"]).sort_values("count", ascending=False)
    return {
        "trades": int(len(tr)),
        "win_rate": float((tr["net"] > 0).mean() * 100),
        "avg_pct": float(tr["net"].mean() * 100),
        "median_pct": float(tr["net"].median() * 100),
        "best_pct": float(tr["net"].max() * 100),
        "worst_pct": float(tr["net"].min() * 100),
        "capital": capital, "size": size,
        "portfolio": pf,
        "final_equity": pf["final_capital"],
        "baseline_pct": base,
        "edge_pct": float(tr["net"].mean() * 100 - base),
        "days": int(max((df["t"].iloc[-1] - df["t"].iloc[0]).days for df in data.values())),
        "equity": pf["equity"],
        "trade_list": [
            {"symbol": r.symbol, "entry": int(r.entry.timestamp()), "exit": int(r.exit.timestamp()),
             "signal_pct": float(r.signal_ret * 100), "net_pct": float(r.net * 100), "pnl": float(r.net * size),
             "taken": bool(taken[r.Index])}
            for r in tr.itertuples()
        ],
        "top_symbols": [{"symbol": s, "trades": int(r["count"]), "avg_pct": float(r["mean"] * 100)}
                        for s, r in by_sym.iterrows()],
    }


def _without(data: dict, exclude) -> dict:
    ex = {e.upper().removesuffix("USDT") for e in exclude if e}
    return {k: v for k, v in data.items() if k.removesuffix("USDT") not in ex}


def grid(fee: float = 0.001, slippage: float = 0.001, min_vol: float = 100_000,
         max_rise: float | None = None, exclude: tuple = (),
         thresholds=(0.02, 0.03, 0.05, 0.08), holds=(1, 2, 4, 8, 24)) -> list[dict]:
    data = _without(load_klines(), exclude)
    cost = fee + slippage
    out = []
    for th in thresholds:
        for h in holds:
            tr = _trades(data, th, h, cost, min_vol, max_rise)
            out.append({
                "threshold": th, "hold": h, "trades": int(len(tr)),
                "win_rate": float((tr["net"] > 0).mean() * 100) if len(tr) else None,
                "avg_pct": float(tr["net"].mean() * 100) if len(tr) else None,
            })
    return out


if __name__ == "__main__":
    r = simulate()
    r.pop("equity", None)
    print(json.dumps(r, indent=2))
