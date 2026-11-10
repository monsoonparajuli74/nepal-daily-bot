"""Register (or remove) the Telegram webhook for this bot.

Telegram exposes ``setWebhook`` on the Bot API, so no dashboard clicking is needed.

Usage::

    python scripts/set_webhook.py                       # uses settings (PUBLIC_BASE_URL)
    python scripts/set_webhook.py https://host/telegram/webhook
    python scripts/set_webhook.py --delete              # remove the webhook
"""

from __future__ import annotations

import asyncio
import sys

from aiogram import Bot

from app.channels.telegram.client import TelegramChannel
from app.channels.telegram.commands import configure_bot, delete_webhook, set_webhook
from app.config import get_settings


async def main() -> int:
    settings = get_settings()
    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN is not set.")
        return 1

    channel = TelegramChannel(settings)
    bot: Bot = channel.bot
    try:
        await configure_bot(bot, settings)

        if "--delete" in sys.argv:
            await delete_webhook(bot, drop_pending=settings.telegram_drop_pending_updates)
            print("Webhook deleted; the bot will not receive updates until you set one again.")
            return 0

        args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
        if args:
            settings.public_base_url = args[0].removesuffix("/telegram/webhook").rstrip("/")

        if not settings.webhook_url:
            print("No webhook URL. Set PUBLIC_BASE_URL or pass it as an argument.")
            return 1
        if not settings.webhook_url.startswith("https://"):
            print("Telegram requires an HTTPS webhook URL.")
            return 1

        await set_webhook(bot, settings)
        print("Webhook registered.")
        print(f"  URL    : {settings.webhook_url}")
        print(f"  Secret : {'set' if settings.telegram_webhook_secret else '(none - not recommended)'}")
        return 0
    finally:
        await channel.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
