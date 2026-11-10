"""Bot profile setup: slash-command menus (EN + NE), descriptions and the webhook.

Run once at startup (and by ``scripts/set_webhook.py``) so the Telegram client places a blue
"Menu" button next to the input field with our commands, in the user's language.
"""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, MenuButtonCommands

from app.bot.i18n import make_translator
from app.config import Settings

logger = logging.getLogger(__name__)

#: (command, i18n key for its description)
COMMANDS: tuple[tuple[str, str], ...] = (
    ("start", "cmd_desc_start"),
    ("menu", "cmd_desc_menu"),
    ("horoscope", "cmd_desc_horoscope"),
    ("news", "cmd_desc_news"),
    ("calendar", "cmd_desc_calendar"),
    ("gold", "cmd_desc_gold"),
    ("forex", "cmd_desc_forex"),
    ("fuel", "cmd_desc_fuel"),
    ("veg", "cmd_desc_veg"),
    ("weather", "cmd_desc_weather"),
    ("language", "cmd_desc_language"),
    ("help", "cmd_desc_help"),
    ("subscribe", "cmd_desc_subscribe"),
    ("unsubscribe", "cmd_desc_unsubscribe"),
    ("stop", "cmd_desc_stop"),
    ("deletedata", "cmd_desc_deletedata"),
)

ALLOWED_UPDATES = ["message", "callback_query", "my_chat_member"]


def _commands_for(language: str, *, include_digest: bool) -> list[BotCommand]:
    t = make_translator(language)
    hidden = set() if include_digest else {"subscribe", "unsubscribe"}
    return [
        BotCommand(command=command, description=t(key))
        for command, key in COMMANDS
        if command not in hidden
    ]


async def configure_bot(bot: Bot, settings: Settings) -> None:
    """Publish per-language command lists, descriptions and the menu button."""
    include_digest = settings.feature_daily_digest
    for language in ("en", "ne"):
        t = make_translator(language)
        try:
            await bot.set_my_commands(
                commands=_commands_for(language, include_digest=include_digest),
                scope=BotCommandScopeAllPrivateChats(),
                language_code=language,
            )
            await bot.set_my_description(description=t("bot_description"), language_code=language)
            await bot.set_my_short_description(
                short_description=t("bot_short_description"), language_code=language
            )
        except Exception:  # noqa: BLE001 - profile setup is best effort
            logger.exception("bot_profile_setup_failed", extra={"language": language})
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception:  # noqa: BLE001
        logger.exception("menu_button_setup_failed")


async def set_webhook(bot: Bot, settings: Settings) -> None:
    if not settings.webhook_url:
        logger.warning("webhook_url_missing")
        return
    kwargs = {
        "url": settings.webhook_url,
        "allowed_updates": ALLOWED_UPDATES,
        "drop_pending_updates": settings.telegram_drop_pending_updates,
    }
    if settings.telegram_webhook_secret:
        kwargs["secret_token"] = settings.telegram_webhook_secret
    await bot.set_webhook(**kwargs)
    logger.info("webhook_set", extra={"url": settings.webhook_url})


async def delete_webhook(bot: Bot, *, drop_pending: bool = False) -> None:
    await bot.delete_webhook(drop_pending_updates=drop_pending)
