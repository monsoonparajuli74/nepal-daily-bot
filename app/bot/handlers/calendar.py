"""Nepali calendar: today's BS date plus festivals and public holidays."""

from __future__ import annotations

import logging
from datetime import date

from app.bot import menus
from app.bot.context import BotContext
from app.bot.formatters import esc, updated_line
from app.data.cache import latest_snapshot
from app.data.config_loader import load_festivals
from app.utils import nepali_digits as nd
from app.utils.bs_calendar import ad_to_bs, format_bs, weekday_name
from app.utils.timeutil import now_npt, today_npt

logger = logging.getLogger(__name__)


async def today(ctx: BotContext, param: str | None = None) -> None:
    day = today_npt()
    bs = ad_to_bs(day)
    weekday = weekday_name(day, ctx.language)
    bs_text = format_bs(bs, ctx.language)
    ad_text = day.strftime("%d %b %Y")
    if ctx.language == "ne":
        bs_text = nd.to_devanagari_digits(bs_text)
        ad_text = nd.to_devanagari_digits(ad_text)

    festivals = load_festivals(ctx.settings.data_dir)
    todays = [f for f in festivals if f.get("ad_date") == day.isoformat()]
    upcoming = sorted([f for f in festivals if f.get("ad_date", "") > day.isoformat()], key=lambda f: f.get("ad_date", ""))[:5]
    panchang = await _panchang(ctx)

    await ctx.track("cal_today")
    lines = [
        ctx.t("cal_title"),
        ctx.t("cal_today", weekday=weekday, bs=bs_text, ad=ad_text),
    ]
    if panchang:
        lines.append(f"🕉 {esc(panchang)}")
    lines.append("")
    if todays:
        for entry in todays:
            lines.append(ctx.t("cal_festival_today", name=_name(entry, ctx.language)))
    else:
        lines.append(ctx.t("cal_no_festival"))

    if upcoming:
        lines.append("")
        lines.append(ctx.t("cal_upcoming"))
        for idx, entry in enumerate(upcoming, start=1):
            ad_date = entry["ad_date"]
            parsed_ad = date.fromisoformat(ad_date)
            days_left = (parsed_ad - day).days
            weekday_up = weekday_name(parsed_ad, ctx.language)
            if ctx.language == "ne":
                days_left_text = nd.to_devanagari_digits(str(days_left))
                days_left_str = f"({days_left_text} दिन बाँकी)"
            else:
                days_left_str = f"({days_left} days left)"
            short_date = _short_date(ad_date, ctx.language)
            num = nd.to_devanagari_digits(str(idx)) if ctx.language == "ne" else str(idx)
            if ctx.language == "ne":
                try:
                    bs_up = ad_to_bs(parsed_ad)
                    bs_up_text = nd.to_devanagari_digits(format_bs(bs_up, ctx.language))
                    lines.append(f"<b>{num}. {_name(entry, ctx.language)}</b> - {weekday_up}, {bs_up_text} BS | {short_date} {days_left_str}")
                except Exception:
                    lines.append(f"<b>{num}. {_name(entry, ctx.language)}</b> - {weekday_up}, {short_date} {days_left_str}")
            else:
                lines.append(f"<b>{num}. {_name(entry, ctx.language)}</b> - {weekday_up}, {short_date} {days_left_str}")
    else:
        lines.append("")
        lines.append(ctx.t("cal_none_upcoming"))

    lines.append("")
    lines.append(updated_line(ctx.language, now_npt(), now_npt()))
    body = "\n".join(lines)

    compact = f"🇳🇵 {weekday}, {bs_text} BS | {ad_text}"
    await ctx.reply(body, inline=menus.result_buttons(ctx.t, share_url=ctx.share_url(compact)))


async def _panchang(ctx: BotContext) -> str:
    """Today's tithi / nakshatra / moon-sign line from the rashifal snapshot."""
    row = await latest_snapshot(ctx.session, "horoscope", ok_only=True)
    periods = ((row.payload if row else {}) or {}).get("periods") or {}
    return ((periods.get("d") or {}).get("title") or "").strip()


def _name(entry: dict, lang: str) -> str:
    return entry.get("name_ne") if lang == "ne" else entry.get("name_en")


def _short_date(iso: str, lang: str) -> str:
    try:
        parsed = date.fromisoformat(iso)
    except ValueError:  # pragma: no cover - defensive
        return iso
    text = parsed.strftime("%d %b %Y")
    return nd.to_devanagari_digits(text) if lang == "ne" else text
