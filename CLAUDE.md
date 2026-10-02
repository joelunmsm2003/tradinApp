# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the monitor

```bash
python monitor.py
```

Runs a check immediately on startup, then every `CHECK_INTERVAL_MINUTES` (default: 15 min). Logs each indicator result to stdout.

## Testing indicators without Telegram

```bash
python -c "
import yfinance as yf
from indicators import check_rsi, check_macd, check_bollinger_bands, check_golden_cross, check_vix_spike
df = yf.download('BTC-USD', period='120d', interval='1d', progress=False, auto_adjust=True)
print(check_rsi(df), check_macd(df))
"
```

To force an alert, temporarily lower `RSI_OVERSOLD = 80` in `config.py`.

## Setup

1. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
2. `pip install -r requirements.txt`
3. `python monitor.py`

## Architecture

- **`config.py`** — all thresholds and symbol lists. Edit here to add symbols or change sensitivity.
- **`indicators.py`** — 5 pure-pandas indicator functions, each returns `(bool, str)`. No external TA libraries (incompatible with numpy 2.x/Python 3.13). Calculations are manual EMA/RSI/MACD/BB.
- **`alerts.py`** — Telegram sender via `python-telegram-bot` v20 async. Falls back to `print` if `.env` is missing.
- **`monitor.py`** — main loop. Downloads OHLCV via `yfinance`, runs all applicable indicators per symbol, enforces cooldown stored in `cooldowns.json`.

## Indicators and signals (bearish → bullish reversals)

| Indicator | Trigger |
|-----------|---------|
| RSI | RSI crosses above 30 (exits oversold) |
| Golden Cross | EMA50 crosses above EMA200 |
| VIX Spike | VIX rises ≥ 20% in one session |
| MACD | MACD line crosses above signal line |
| Bollinger Bands | Price closes below lower band |

VIX Spike only runs on `^VIX`. Golden Cross is skipped for `^VIX`.

## Cooldown

`cooldowns.json` tracks last alert time per `symbol::indicator`. Same signal won't re-fire within `COOLDOWN_HOURS` (default 24h). Delete the file to reset all cooldowns.

## Liquidity Index (liquidity_index/)

Separate sub-project: studies whether US/global liquidity (M2, Fed balance sheet, RRP, TGA,
DXY, Treasury 10Y, stablecoin market cap) correlates with BTC price and halving cycles.
Independent from the monitor/alerts system above — own storage, own pipeline.

### Setup

```bash
cd liquidity_index
docker compose --env-file ../.env up -d   # Postgres local
cd ..
python -m liquidity_index.run_daily --once
```

Requires `FRED_API_KEY` (free, https://fred.stlouisfed.org/docs/api/api_key.html) and
`POSTGRES_*` vars in `.env` (see `.env.example`). Without `FRED_API_KEY` the FRED collector
logs an error and skips — the market (BTC/DXY) and stablecoin collectors still run fine.

### Architecture

- **`config.py`** — series/tickers, sign-inversion map, index weights (provisional, not
  validated), halving dates, backtest cycle window.
- **`db.py`** — psycopg2 connection + idempotent upsert helpers (`ON CONFLICT ... DO UPDATE
  ... WHERE value IS DISTINCT FROM`, so reruns don't duplicate rows or bump timestamps
  on unchanged data).
- **`collectors/`** — one module per source: `fred_collector.py` (FRED REST API, no `fredapi`
  dep), `market_collector.py` (yfinance, same pattern as `web.py::_get_btc_df`),
  `stablecoin_collector.py` (DefiLlama public API, no key).
- **`normalization.py`** — pct_change, yoy_change, zscore, rolling_mean, invert_sign.
- **`liquidity_index.py`** — v1 index = weighted sum of z-scored series (computed on read,
  not persisted — weights aren't stable enough yet to justify a table).
- **`halvings.py`** — historical + estimated halving dates; BTC returns/drawdown/volatility.
- **`backtest.py`** — correlation vs BTC (level + forward returns), and per-halving-cycle
  analysis using an **asymmetric window (-180d / +540d)**, not symmetric ±90/180 — BTC cycle
  tops historically land 12-18 months *after* the halving, not on the date itself. Also
  reports where the index *fails* to correlate, not just where it works.
- **`run_daily.py --once`** — full pipeline (collect → validate → upsert). Meant to be
  triggered by Windows Task Scheduler daily, not run as a long-lived process like `monitor.py`.
- Dashboard: `/liquidity` route in `web.py` (own template `templates/liquidity.html`),
  reads via `/api/liquidity`. Reuses lightweight-charts, no build step.

### Known gotcha

lightweight-charts' `fitContent()` doesn't auto-shrink enough for ~16 years of daily data —
had to explicitly set both `barSpacing` and `minBarSpacing` low in the chart options
(see `templates/liquidity.html`), or it silently clamps the visible range to the most
recent ~80 bars.
