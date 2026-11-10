"""Reply-keyboard label routing.

A persistent keyboard sends its label back as an ordinary text message. This module maps
every home label — in **both** languages, at all times — back to its action id, ignoring
emoji, case and stray punctuation, so a Nepali-mode user can still tap an English-style
label and vice versa.
"""

from __future__ import annotations

import re

from app.bot import actions
from app.bot.i18n import make_translator

#: (action, i18n key) for the nine home grid buttons.
HOME_ITEMS: tuple[tuple[str, str], ...] = (
    (actions.HOROSCOPE_MENU, "btn_horoscope"),
    (actions.NEWS_LATEST, "btn_news"),
    (actions.CAL_TODAY, "btn_calendar"),
    (actions.METALS_TODAY, "btn_metals"),
    (actions.FOREX_RATES, "btn_forex"),
    (actions.FUEL_TODAY, "btn_fuel"),
    (actions.VEG_MENU, "btn_vegetables"),
    (actions.WX_MENU, "btn_weather"),
    (actions.LANG_TOGGLE, "btn_language"),
)

_NORMALISE_RE = re.compile(r"[^\w]+", re.UNICODE)


def home_keyboard(t) -> list[list[str]]:
    """The 3x3 persistent home keyboard, in the current language."""
    labels = [t(key) for _action, key in HOME_ITEMS]
    return [labels[0:3], labels[3:6], labels[6:9]]


def normalise_label(text: str) -> str:
    return _NORMALISE_RE.sub("", (text or "").strip().casefold())


def label_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for lang in ("en", "ne"):
        t = make_translator(lang)
        for action, key in HOME_ITEMS:
            mapping[normalise_label(t(key))] = action
    return mapping


def resolve_label(text: str) -> str | None:
    return label_map().get(normalise_label(text))
