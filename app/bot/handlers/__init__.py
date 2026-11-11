"""Feature handlers. Each module exposes async entry points taking a BotContext."""

from __future__ import annotations

from app.bot.handlers import (  # noqa: F401
    admin,
    calendar,
    forex,
    fuel,
    horoscope,
    language,
    lifecycle,
    metals,
    news,
    share,
    veg,
    weather,
)

__all__ = [
    "admin",
    "calendar",
    "forex",
    "fuel",
    "horoscope",
    "language",
    "lifecycle",
    "metals",
    "news",
    "share",
    "veg",
    "weather",
]
