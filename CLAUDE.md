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
