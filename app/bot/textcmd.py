"""Free-text command mapping.

Telegram has a persistent keyboard, so the home labels are routed by :mod:`app.bot.labels`.
This module handles the other free text: typed words ("menu", "rates", "stop", both scripts)
and slash commands (``/horoscope leo``, ``/weather pokhara``).
"""

from __future__ import annotations

import re

from app.bot import actions

PLAIN_COMMANDS: dict[str, str] = {
    # Navigation
    "menu": actions.HOME,
    "0": actions.HOME,
    "hi": actions.HOME,
    "hello": actions.HOME,
    "start": actions.HOME,
    "namaste": actions.HOME,
    "नमस्ते": actions.HOME,
    "मेनु": actions.HOME,
    # Help
    "help": actions.HELP,
    "सहयोग": actions.HELP,
    # Opt out / in
    "stop": actions.STOP,
    "unsubscribe": actions.STOP,
    "band": actions.STOP,
    "बन्द": actions.STOP,
    "off": actions.STOP,
    # Language
    "lang": actions.LANG_TOGGLE,
    "language": actions.LANG_TOGGLE,
    "भाषा": actions.LANG_TOGGLE,
    "en": actions.LANG_EN,
    "english": actions.LANG_EN,
    "ne": actions.LANG_NE,
    "nepali": actions.LANG_NE,
    "नेपाली": actions.LANG_NE,
    # Features
    "news": actions.NEWS_LATEST,
    "समाचार": actions.NEWS_LATEST,
    "rates": actions.FOREX_RATES,
    "forex": actions.FOREX_RATES,
    "dollar": actions.FOREX_RATES,
    "विदेशी मुद्रा": actions.FOREX_RATES,
    "weather": actions.WX_MENU,
    "मौसम": actions.WX_MENU,
    "veg": actions.VEG_MENU,
    "vegetables": actions.VEG_MENU,
    "तरकारी": actions.VEG_MENU,
    "gold": actions.METALS_TODAY,
    "silver": actions.METALS_TODAY,
    "metals": actions.METALS_TODAY,
    "सुन": actions.METALS_TODAY,
    "fuel": actions.FUEL_TODAY,
    "petrol": actions.FUEL_TODAY,
    "इन्धन": actions.FUEL_TODAY,
    "calendar": actions.CAL_TODAY,
    "date": actions.CAL_TODAY,
    "पात्रो": actions.CAL_TODAY,
    "horoscope": actions.HOROSCOPE_MENU,
    "rashifal": actions.HOROSCOPE_MENU,
    "राशिफल": actions.HOROSCOPE_MENU,
}

#: Slash command word -> action. Commands that take an argument are handled in the router.
SLASH_COMMANDS: dict[str, str] = {
    "start": actions.HOME,
    "menu": actions.HOME,
    "help": actions.HELP,
    "stop": actions.STOP,
    "language": actions.LANG_TOGGLE,
    "lang": actions.LANG_TOGGLE,
    "deletedata": actions.DELETEDATA,
    "subscribe": actions.SUBSCRIBE,
    "unsubscribe": actions.UNSUBSCRIBE,
    "news": actions.NEWS_LATEST,
    "calendar": actions.CAL_TODAY,
    "gold": actions.METALS_TODAY,
    "forex": actions.FOREX_RATES,
    "fuel": actions.FUEL_TODAY,
    "veg": actions.VEG_MENU,
    "horoscope": actions.HOROSCOPE_MENU,
    "rashifal": actions.HOROSCOPE_MENU,
    "weather": actions.WX_MENU,
    "mausam": actions.WX_MENU,
}

_NUMBER_RE = re.compile(r"^[0-9]+$")


def resolve_plain(text: str) -> str | None:
    """Map a typed word to an action id, or None if it isn't a known command."""
    key = (text or "").strip().lower()
    return PLAIN_COMMANDS.get(key)


def command_name(text: str) -> str | None:
    """Return the bare slash-command word (without ``/`` or ``@bot``), or None."""
    stripped = (text or "").strip()
    if not stripped.startswith("/"):
        return None
    token = stripped.split()[0][1:]
    return token.split("@", 1)[0].lower() or None


def command_args(text: str) -> list[str]:
    stripped = (text or "").strip()
    if not stripped.startswith("/"):
        return []
    return stripped.split()[1:]


def as_index(text: str) -> int | None:
    """Return a 1-based index if the text is a bare number, else None."""
    key = (text or "").strip()
    if _NUMBER_RE.match(key):
        value = int(key)
        return value if value > 0 else None
    return None
