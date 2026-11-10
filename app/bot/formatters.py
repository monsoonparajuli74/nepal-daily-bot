"""Message formatting helpers and the central colour/emoji signal system.

All emoji "signals" live here so a change of convention happens in one place:

* Consumer prices (fuel, vegetables, LPG): fell = 🟢, rose = 🔴, unchanged = ➖.
* Market values (forex): value rose = 🟢, fell = 🔴.
* Gold/silver: 📈 / 📉 / ➖ (colour would imply good/bad for buyer vs seller).
* AQI: standard US AQI bands.
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta
from decimal import Decimal

from app.bot.i18n import make_translator, translate
from app.utils import nepali_digits as nd
from app.utils.bs_calendar import ad_to_bs, format_bs, weekday_name
from app.utils.timeutil import format_npt

UP = "🟢"
DOWN = "🔴"
FLAT = "➖"
METAL_UP = "📈"
METAL_DOWN = "📉"
METAL_FLAT = "➖"

AQI_BANDS: tuple[tuple[int, str, str], ...] = (
    (50, "aqi_band_good", "aqi_advice_good"),
    (100, "aqi_band_moderate", "aqi_advice_moderate"),
    (150, "aqi_band_sensitive", "aqi_advice_sensitive"),
    (200, "aqi_band_unhealthy", "aqi_advice_unhealthy"),
    (300, "aqi_band_very_unhealthy", "aqi_advice_very_unhealthy"),
)


def esc(value: object) -> str:
    """HTML-escape a dynamic value for use inside a parse_mode=HTML message."""
    return html.escape(str(value), quote=False)


def consumer_signal(delta: Decimal | float | int | None) -> str:
    """Emoji for a consumer price change (cheaper is good)."""
    if delta is None or delta == 0:
        return FLAT
    return DOWN if delta > 0 else UP


def market_signal(delta: Decimal | float | int | None) -> str:
    """Emoji for a market value change (higher value is good)."""
    if delta is None or delta == 0:
        return FLAT
    return UP if delta > 0 else DOWN


def metals_signal(delta: Decimal | float | int | None) -> str:
    if delta is None or delta == 0:
        return METAL_FLAT
    return METAL_UP if delta > 0 else METAL_DOWN


def aqi_band(aqi: float | int | None, lang: str) -> tuple[str, str]:
    """Return (band label, health advice) for a US AQI value."""
    if aqi is None:
        return translate(lang, "wx_aqi_unknown"), ""
    value = int(aqi)
    for threshold, band_key, advice_key in AQI_BANDS:
        if value <= threshold:
            return translate(lang, band_key), translate(lang, advice_key)
    return translate(lang, "aqi_band_hazardous"), translate(lang, "aqi_advice_hazardous")


def updated_line(lang: str, fetched_at: datetime, checked_at: datetime | None = None) -> str:
    moment = checked_at or fetched_at
    return translate(lang, "updated", time=format_npt(moment))


def is_stale(fetched_at: datetime, stale_after: timedelta, reference: datetime | None = None) -> bool:
    reference = reference or datetime.now(fetched_at.tzinfo)
    return (reference - fetched_at) > stale_after


def stale_prefix(lang: str, stale: bool) -> str:
    return translate(lang, "stale_prefix") if stale else ""


def format_money(value: Decimal | int, *, decimals: int | None = None) -> str:
    return nd.format_npr(value, decimals=decimals)


def format_number(value: Decimal | int) -> str:
    return nd.group_digits(value)


def format_bs_date(lang: str, value_date) -> tuple[str, str]:
    """Return (weekday, BS date string) for a Gregorian date."""
    bs = ad_to_bs(value_date)
    weekday = weekday_name(value_date, lang)
    bs_text = format_bs(bs, lang)
    if lang == "ne":
        bs_text = nd.to_devanagari_digits(bs_text)
    return weekday, bs_text


def change_text(delta: Decimal | None, *, symbol: str, lang: str) -> str:
    if delta is None or delta == 0:
        return f"{symbol} 0"
    sign = "+" if delta > 0 else "-"
    return f"{symbol} {sign}{format_number(abs(delta))}"


def t_for(lang: str):
    return make_translator(lang)
