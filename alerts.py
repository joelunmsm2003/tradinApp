import asyncio
import json
import os
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HISTORY_FILE = "alerts_history.json"

INDICATOR_EMOJIS = {
    "RSI": "📉",
    "Golden Cross": "✨",
    "VIX Spike": "⚡",
    "MACD": "📈",
    "Bollinger Bands": "🔵",
}


def format_alert(symbol: str, indicator: str, details: str) -> str:
    emoji = INDICATOR_EMOJIS.get(indicator, "🔔")
    return (
        f"{emoji} *ALERTA ALCISTA* {emoji}\n"
        f"*Símbolo:* `{symbol}`\n"
        f"*Indicador:* {indicator}\n"
        f"*Detalle:* {details}"
    )


async def _send_async(message: str) -> None:
    bot = Bot(token=_BOT_TOKEN)
    await bot.send_message(
        chat_id=_CHAT_ID,
        text=message,
        parse_mode="Markdown",
    )


def save_alert_history(symbol: str, indicator: str, detail: str) -> None:
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            history = json.load(f)
    history.append({
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "indicator": indicator,
        "detail": detail,
    })
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


def send_telegram(message: str) -> None:
    if not _BOT_TOKEN or not _CHAT_ID:
        print("[ALERTA - sin Telegram configurado]:", message)
        return
    asyncio.run(_send_async(message))
