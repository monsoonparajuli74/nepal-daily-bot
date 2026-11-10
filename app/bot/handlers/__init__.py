"""Feature handlers. Each module exposes async entry points taking a BotContext."""

from __future__ import annotations

from app.bot.handlers import (  # noqa: F401
    calendar,
    forex,
    fuel,
    horoscope,
    language,
    lifecycle,
    metals,
    news,
    veg,
    weather,
)

__all__ = [
    "calendar",
    "forex",
    "fuel",
    "horoscope",
    "language",
    "lifecycle",
    "metals",
    "news",
    "veg",
    "weather",
]
