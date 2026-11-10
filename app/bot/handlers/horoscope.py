"""Horoscope handlers (pluggable, seed-backed source; daily, monthly and yearly)."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.bot import menus
from app.bot.context import BotContext
from app.bot.formatters import esc, format_bs_date
from app.bot.i18n import SIGN_NAMES, sign_name
from app.data.cache import latest_snapshot
from app.data.config_loader import load_horoscope_periods, load_horoscope_seed
from app.data.models import Horoscope
from app.utils.timeutil import format_npt, now_utc, today_npt

logger = logging.getLogger(__name__)

#: ``hs:p:<period>:<sign>`` params accepted by :func:`period`.
PERIODS: tuple[str, ...] = ("w", "m", "y")


async def menu(ctx: BotContext, param: str | None = None) -> None:
    if ctx.user.default_zodiac:
        await render_reading(ctx, ctx.user.default_zodiac)
        return
    await ctx.track("horo_menu")
    await ctx.send(menus.zodiac_menu(ctx.t, ctx.language))


async def change(ctx: BotContext, param: str | None = None) -> None:
    await ctx.send(menus.zodiac_menu(ctx.t, ctx.language))


async def sign(ctx: BotContext, param: str | None = None) -> None:
    slug = (param or "").lower()
    if not slug:
        await change(ctx)
        return
    await render_reading(ctx, slug)


async def period(ctx: BotContext, param: str | None = None) -> None:
    """``m:leo`` / ``y:capricorn`` — monthly or yearly reading for a sign."""
    period_code, sep, slug = (param or "").partition(":")
    if not sep or period_code not in PERIODS or slug.lower() not in SIGN_NAMES:
        await change(ctx)
        return
    await render_reading(ctx, slug.lower(), period=period_code)


async def save(ctx: BotContext, param: str | None = None) -> None:
    slug = (param or "").lower()
    if not slug:
        await change(ctx)
        return
    from app.bot.users import set_default_zodiac

    await set_default_zodiac(ctx.session, ctx.user, slug)
    await ctx.track("horo_save_default")
    prefix = ctx.t("horo_saved", sign=sign_name(slug, ctx.language))
    await render_reading(ctx, slug, prefix=prefix)


async def render_reading(
    ctx: BotContext,
    slug: str,
    *,
    prefix: str | None = None,
    period: str = "d",
) -> None:
    found = await _get_reading(ctx, slug, period)
    if found is None:
        await ctx.reply(ctx.t("horo_no_reading"))
        await ctx.send(menus.zodiac_menu(ctx.t, ctx.language))
        return
    reading, _source_title = found

    await ctx.track("horo_read")
    # Reading text stays Nepali, but the sign name follows the interface language.
    display = sign_name(slug, ctx.language)
    today = today_npt()

    if period == "w":
        heading = ctx.t("horo_weekly_title")
    elif period == "m":
        heading = ctx.t("horo_monthly_title")
    elif period == "y":
        heading = ctx.t("horo_yearly_title")
    else:
        heading = ctx.t("horo_title")

    _weekday, bs_text = format_bs_date(ctx.language, today)
    ad_text = format_npt(now_utc(), fmt="%d %b %Y")
    date_line = f"📅 {bs_text} BS | {ad_text}"

    lines = [
        f"<b>{heading}</b> • {esc(display)}",
        date_line,
    ]
    lines += ["", esc(reading), "", ctx.t("horo_footer")]
    if prefix:
        lines.insert(0, prefix)
    body = "\n".join(lines)

    compact = f"🔮 {display} - {reading}"
    can_save = ctx.user.default_zodiac != slug
    buttons = menus.horoscope_buttons(
        ctx.t,
        slug,
        can_save=can_save,
        share_url=ctx.share_url(compact),
        period=period,
    )
    await ctx.reply(body, inline=buttons)


async def _get_reading(ctx: BotContext, slug: str, period: str = "d") -> tuple[str, str] | None:
    """Reading text + source title. Content is Nepali regardless of UI language."""
    row = await latest_snapshot(ctx.session, "horoscope", ok_only=True)
    periods = ((row.payload if row else {}) or {}).get("periods") or {}
    bucket = periods.get(period)
    if bucket:
        text = (bucket.get("signs") or {}).get(slug)
        if text:
            return text, bucket.get("title") or ""

    if period in ("w", "d"):
        stmt = (
            select(Horoscope)
            .where(Horoscope.sign == slug, Horoscope.date <= today_npt())
            .order_by(Horoscope.date.desc())
            .limit(1)
        )
        result = await ctx.session.execute(stmt)
        db_row = result.scalars().first()
        if db_row is not None:
            return db_row.text_ne or db_row.text_en, ""

        seed = load_horoscope_seed(ctx.settings.data_dir)
        entry = (seed.get("signs") or {}).get(slug) or {}
        text = entry.get("ne") or entry.get("en")
        return (text, "") if text else None

    data = load_horoscope_periods(ctx.settings.data_dir)
    bucket_name = "monthly" if period == "m" else "yearly"
    entry = (data.get(bucket_name) or {}).get(slug) or {}
    text = entry.get("ne") or entry.get("en")
    return (text, "") if text else None
