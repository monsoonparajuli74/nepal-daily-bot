"""Weather and air quality."""

from __future__ import annotations

import logging

from app.bot import actions, menus
from app.bot.context import BotContext
from app.bot.formatters import aqi_band, updated_line
from app.bot.handlers.common import send_error
from app.bot.i18n import wmo_description
from app.data.cache import latest_snapshot
from app.utils import nepali_digits as nd

logger = logging.getLogger(__name__)


async def menu(ctx: BotContext, param: str | None = None) -> None:
    await ctx.track("wx_menu")
    await ctx.send(menus.weather_city_grid(ctx.t))


async def more(ctx: BotContext, param: str | None = None) -> None:
    await ctx.track("wx_more")
    await ctx.send(menus.weather_city_grid(ctx.t, more=True))


async def city(ctx: BotContext, param: str | None = None) -> None:
    key = (param or "").lower()
    if not key:
        await menu(ctx)
        return

    row = await latest_snapshot(ctx.session, "weather", ok_only=True)
    if row is None:
        await send_error(ctx)
        return
    record = ((row.payload or {}).get("cities") or {}).get(key)
    if not record:
        await send_error(ctx)
        return

    await ctx.track("wx_city")
    label = ctx.t(f"city_{key}")
    temp = _fmt(record.get("temp"))
    feels = _fmt(record.get("feels"))
    desc = wmo_description(record.get("code"), ctx.language)
    high = _fmt(record.get("high"))
    low = _fmt(record.get("low"))
    rain = record.get("rain")
    rain_text = f"{int(rain)}" if rain is not None else "-"
    humidity = _fmt(record.get("humidity"))
    wind = _fmt(record.get("wind"))
    uv = _fmt(record.get("uv"))
    sunrise = _time(record.get("sunrise"), ctx.language)
    sunset = _time(record.get("sunset"), ctx.language)

    lines = [
        f"<b>{esc(ctx.t('wx_title', city=label))}</b>",
        "",
        f"<b>{ctx.t('wx_now').split(':')[0] if ':' in ctx.t('wx_now') else (ctx.t('wx_now', temp=temp, desc=desc).split(temp)[0].strip() or 'Now')}</b>: {temp}°C • {desc}",
        f"  {ctx.t('wx_feels', temp=feels) if feels != '-' else ''}",
    ]
    if feels == "-":
        lines.pop()
    lines.append("")
    lines.append(f"<b>{'Conditions' if ctx.language == 'en' else 'अवस्था'}</b>")
    if humidity != "-":
        lines.append(f"• {ctx.t('wx_humidity', value=humidity)}")
    if wind != "-":
        lines.append(f"• {ctx.t('wx_wind', value=wind)}")
    if uv != "-":
        lines.append(f"• {ctx.t('wx_uv', value=uv)}")
    lines.append("")
    lines.append(f"<b>{'Today' if ctx.language == 'en' else 'आज'}</b>")
    lines.append(f"• {ctx.t('wx_today', low=low, high=high, rain=rain_text)}")
    if sunrise != "-" and sunset != "-":
        lines.append(f"• {ctx.t('wx_sun', rise=sunrise, sett=sunset)}")

    lines.append("")
    lines.append(f"<b>{'Air Quality' if ctx.language == 'en' else 'वायु गुणस्तर'}</b>")
    aqi = record.get("aqi")
    pm25 = record.get("pm25")
    if aqi is None:
        lines.append(f"• {ctx.t('wx_aqi_unknown')}")
        advice = ""
    else:
        band, advice = aqi_band(aqi, ctx.language)
        extra = f" | PM2.5 {nd.to_devanagari_digits(str(_fmt(pm25))) if ctx.language == 'ne' and _fmt(pm25) != '-' else _fmt(pm25)} μg/m³" if pm25 is not None else ""
        aqi_disp = nd.to_devanagari_digits(str(int(aqi))) if ctx.language == 'ne' else str(int(aqi))
        lines.append(f"• AQI: {aqi_disp} — {band}{extra}")
    if advice:
        lines.append(f"  {advice}")
    lines.append("")
    lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
    body = "\n".join(lines)

    compact = f"{label}: {temp}°C, {desc}, AQI {int(aqi) if aqi is not None else 'n/a'}"
    await ctx.reply(
        body,
        inline=menus.result_buttons(ctx.t, back_action=actions.WX_MENU, share_url=ctx.share_url(compact)),
    )


def _time(value, language: str) -> str:
    if not value:
        return "-"
    text = str(value)
    clock = text[11:16] if len(text) >= 16 and "T" in text else text
    return nd.to_devanagari_digits(clock) if language == "ne" else clock


def _fmt(value) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return str(value)
    return f"{number:.0f}" if number == int(number) else f"{number:.1f}"
