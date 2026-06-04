import json
import logging
import os
import time
from datetime import datetime, timedelta

import schedule
import yfinance as yf

from alerts import format_alert, save_alert_history, send_telegram
from config import (
    CHECK_INTERVAL_MINUTES,
    CONFLUENCE_THRESHOLD,
    COOLDOWN_HOURS,
    DATA_INTERVAL,
    DATA_PERIOD,
    SYMBOLS,
)
from scoring import calculate_score
from indicators import (
    check_atr,
    check_bollinger_bands,
    check_death_cross,
    check_golden_cross,
    check_macd,
    check_rsi,
    check_rsi_overbought,
    check_stoch_rsi,
    check_vix_spike,
    check_volume_spike,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

COOLDOWNS_FILE = "cooldowns.json"


def load_cooldowns() -> dict:
    if os.path.exists(COOLDOWNS_FILE):
        with open(COOLDOWNS_FILE) as f:
            return json.load(f)
    return {}


def save_cooldowns(cooldowns: dict) -> None:
    with open(COOLDOWNS_FILE, "w") as f:
        json.dump(cooldowns, f)


def is_on_cooldown(cooldowns: dict, symbol: str, indicator: str) -> bool:
    key = f"{symbol}::{indicator}"
    if key not in cooldowns:
        return False
    last_time = datetime.fromisoformat(cooldowns[key])
    return datetime.now() - last_time < timedelta(hours=COOLDOWN_HOURS)


def set_cooldown(cooldowns: dict, symbol: str, indicator: str) -> None:
    cooldowns[f"{symbol}::{indicator}"] = datetime.now().isoformat()


def get_checks_for_symbol(symbol: str):
    """Retorna lista de (nombre_indicador, función) aplicables al símbolo."""
    checks = [
        ("RSI",            check_rsi),
        ("RSI Overbought", check_rsi_overbought),
        ("MACD",           check_macd),
        ("Bollinger Bands",check_bollinger_bands),
        ("Stoch RSI",      check_stoch_rsi),
        ("Volume Spike",   check_volume_spike),
        ("ATR",            check_atr),
    ]
    if symbol != "^VIX":
        checks.append(("Golden Cross", check_golden_cross))
        checks.append(("Death Cross",  check_death_cross))
    if symbol == "^VIX":
        checks.append(("VIX Spike", check_vix_spike))
    return checks


def run_checks() -> None:
    log.info("Iniciando chequeo de indicadores...")
    cooldowns = load_cooldowns()
    all_symbols = SYMBOLS["crypto"] + SYMBOLS["indices"]

    for symbol in all_symbols:
        log.info(f"  Descargando datos de {symbol}")
        try:
            df = yf.download(symbol, period=DATA_PERIOD, interval=DATA_INTERVAL, progress=False, auto_adjust=True)
        except Exception as e:
            log.warning(f"  Error descargando {symbol}: {e}")
            continue

        if df.empty or len(df) < 5:
            log.warning(f"  Datos insuficientes para {symbol}")
            continue

        # Aplanar columnas MultiIndex si existen (yfinance a veces las genera)
        if isinstance(df.columns, type(df.columns)) and hasattr(df.columns, "levels"):
            df.columns = df.columns.droplevel(1)

        for indicator_name, check_fn in get_checks_for_symbol(symbol):
            if is_on_cooldown(cooldowns, symbol, indicator_name):
                log.debug(f"  [{symbol}] {indicator_name}: en cooldown, omitido")
                continue
            try:
                triggered, detail = check_fn(df)
            except Exception as e:
                log.warning(f"  [{symbol}] {indicator_name}: error en cálculo: {e}")
                continue

            if triggered:
                log.info(f"  *** ALERTA: [{symbol}] {indicator_name} — {detail}")
                message = format_alert(symbol, indicator_name, detail)
                send_telegram(message)
                save_alert_history(symbol, indicator_name, detail)
                set_cooldown(cooldowns, symbol, indicator_name)
            else:
                log.info(f"  [{symbol}] {indicator_name}: sin señal")

        # Alerta de confluencia (scoring)
        cfg_defaults = {
            "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
            "bb_period": 20, "bb_std": 2.0, "macd_fast": 12,
            "macd_slow": 26, "macd_signal": 9, "ema_fast": 50, "ema_slow": 200,
        }
        try:
            score = calculate_score(df, cfg_defaults)
            for direction, sc, signals in [
                ("ALCISTA", score["bull_score"], score["bull_signals"]),
                ("BAJISTA", score["bear_score"], score["bear_signals"]),
            ]:
                if sc >= CONFLUENCE_THRESHOLD:
                    key = f"Confluencia {direction}"
                    if not is_on_cooldown(cooldowns, symbol, key):
                        names  = ", ".join(s["name"] for s in signals)
                        detail = f"Score {sc}/{score['max_score']} — {names}"
                        log.info(f"  *** CONFLUENCIA {direction}: [{symbol}] {detail}")
                        message = format_alert(symbol, key, detail)
                        send_telegram(message)
                        save_alert_history(symbol, key, detail)
                        set_cooldown(cooldowns, symbol, key)
        except Exception as e:
            log.warning(f"  [{symbol}] Scoring error: {e}")

    save_cooldowns(cooldowns)
    log.info("Chequeo finalizado.\n")


def main() -> None:
    log.info(f"Monitor iniciado. Chequeo cada {CHECK_INTERVAL_MINUTES} minutos.")
    run_checks()  # correr inmediatamente al arrancar
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(run_checks)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
