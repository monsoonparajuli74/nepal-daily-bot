"""Compact, Telegram-safe action id codec.

Telegram caps ``callback_data`` at **64 bytes**, so action ids are short and namespaced
(``nav:home``, ``hs:s:leo``, ``fx:cc:AED``, ``fx:ca:2500``). This module is the single
source of truth for building and parsing them; handlers and menus never inline raw strings
except through these helpers.
"""

from __future__ import annotations

from app.channels.base import CALLBACK_DATA_MAX

# ---- Navigation / settings ----
HOME = "nav:home"
HELP = "cmd:help"
STOP = "cmd:stop"
DELETEDATA = "cmd:deletedata"
SUBSCRIBE = "cmd:subscribe"
UNSUBSCRIBE = "cmd:unsubscribe"

LANG_TOGGLE = "lang:t"
LANG_EN = "lang:en"
LANG_NE = "lang:ne"

# ---- Horoscope ----
HOROSCOPE_MENU = "hs:m"
HOROSCOPE_CHANGE = "hs:c"


def horoscope_change() -> str:
    return HOROSCOPE_CHANGE


def horoscope_sign(slug: str) -> str:
    return f"hs:s:{slug}"


#: Period codes used inside ``hs:p:<period>:<sign>`` callback data.
HOROSCOPE_PERIODS: tuple[str, str, str, str] = ("d", "w", "m", "y")


def horoscope_period(period: str, slug: str) -> str:
    """A dated reading: ``hs:p:m:leo`` = monthly for Leo (daily stays ``hs:s:leo``)."""
    return f"hs:p:{period}:{slug}"


def horoscope_save(slug: str) -> str:
    return f"hs:save:{slug}"


# ---- Forex + calculator ----
FOREX_RATES = "fx:r"
FOREX_CALC = "fx:c"
FOREX_MORE = "fx:cm"
FOREX_TYPE_ANOTHER = "fx:cx"
FOREX_AGAIN = "fx:again"


def forex_currency(code: str) -> str:
    return f"fx:cc:{code}"


def forex_amount(amount: int | str) -> str:
    return f"fx:ca:{amount}"


# ---- Vegetables ----
VEG_MENU = "vg:m"
VEG_ESSENTIALS = "vg:e"
VEG_GREENS = "vg:g"
VEG_VEGETABLES = "vg:v"
VEG_FRUITS = "vg:f"
VEG_TRENDS = "vg:t"
VEG_MORE = "vg:o"

# ---- Weather ----
WX_MENU = "wx:m"
WX_MORE = "wx:mo"


def weather_city(key: str) -> str:
    return f"wx:c:{key}"


# ---- Single-screen modules ----
NEWS_LATEST = "nw:l"
CAL_TODAY = "cal:t"
METALS_TODAY = "mt:t"
FUEL_TODAY = "fu:t"


def share(what: str) -> str:
    return f"share:{what}"


#: Every namespace we recognise. Used for fast prefix routing and decoding.
NAMESPACES: tuple[str, ...] = (
    "nav",
    "cmd",
    "lang",
    "hs",
    "fx",
    "vg",
    "wx",
    "nw",
    "cal",
    "mt",
    "fu",
    "share",
)


def decode(action: str | None) -> tuple[str, list[str]] | None:
    """Split ``fx:cc:AED`` into ``("fx", ["cc", "AED"])``.

    Returns ``None`` for empty, unknown-namespace or malformed ids so callers can degrade
    stale/foreign callbacks to the home screen instead of crashing.
    """
    if not action:
        return None
    namespace, _, rest = action.partition(":")
    if namespace not in NAMESPACES or not rest:
        return None
    return namespace, rest.split(":")


def encoded_length(action: str) -> int:
    return len(action.encode("utf-8"))


def is_valid(action: str) -> bool:
    """True when an id decodes and fits the callback_data byte budget."""
    return decode(action) is not None and encoded_length(action) <= CALLBACK_DATA_MAX


def all_actions() -> list[str]:
    """Representative ids across every namespace, for the <= 64-byte property test."""
    from app.bot.i18n import SIGN_NAMES
    from app.data.config_loader import city_list
    from app.data.sources.forex import ALL_CURRENCIES

    actions: list[str] = [
        HOME,
        HELP,
        STOP,
        DELETEDATA,
        SUBSCRIBE,
        UNSUBSCRIBE,
        LANG_TOGGLE,
        LANG_EN,
        LANG_NE,
        HOROSCOPE_MENU,
        HOROSCOPE_CHANGE,
        FOREX_RATES,
        FOREX_CALC,
        FOREX_MORE,
        FOREX_TYPE_ANOTHER,
        FOREX_AGAIN,
        VEG_MENU,
        VEG_ESSENTIALS,
        VEG_GREENS,
        VEG_VEGETABLES,
        VEG_FRUITS,
        VEG_TRENDS,
        VEG_MORE,
        WX_MENU,
        NEWS_LATEST,
        CAL_TODAY,
        METALS_TODAY,
        FUEL_TODAY,
        share("fx"),
    ]
    actions += [horoscope_sign(slug) for slug in SIGN_NAMES]
    actions += [horoscope_save(slug) for slug in SIGN_NAMES]
    actions += [horoscope_period(period, slug) for period in HOROSCOPE_PERIODS[1:] for slug in SIGN_NAMES]
    actions += [forex_currency(code) for code in ALL_CURRENCIES]
    actions += [forex_amount(n) for n in (500, 1000, 2500, 5000, 10000)]
    actions += [weather_city(key) for key in city_list()]
    return actions
