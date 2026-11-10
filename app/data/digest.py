"""Daily, source-grounded briefing.

Sent to active users unless they explicitly unsubscribe. Reading is snapshot-only, so the job
never touches third-party sites. The sender paces itself to stay clear of Telegram's limits.
"""

from __future__ import annotations

import asyncio
import html
import logging
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.context import BotContext
from app.bot.formatters import esc, format_number
from app.channels.base import Channel, Reply
from app.config import Settings
from app.data.cache import latest_snapshot
from app.data.config_loader import load_festivals
from app.data.models import User
from app.utils.bs_calendar import ad_to_bs, format_bs, weekday_name
from app.utils.timeutil import today_npt

logger = logging.getLogger(__name__)


async def send_digests(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    channel: Channel,
) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(
                User.is_active.is_(True),
                User.daily_briefing_opt_out.is_(False),
            )
        )
        users = list(result.scalars().all())

    sent = 0
    for user in users:
        async with session_factory() as session:
            text = await _digest_text(session, user, settings)
        if text is None:
            continue
        try:
            await channel.send(user.tg_user_id, Reply(text=text))
            sent += 1
        except Exception:  # noqa: BLE001 - one failed send must not stop the batch
            logger.exception("digest_send_failed", extra={"user": user.tg_user_id})
        await asyncio.sleep(1.0 / max(1, settings.digest_rate_per_second))
    logger.info("digest_sent", extra={"count": sent})
    return sent


async def _digest_text(session: AsyncSession, user: User, settings: Settings) -> str | None:
    ctx = BotContext(session=session, user=user, settings=settings)
    t = ctx.t
    language = ctx.language
    day = today_npt()
    bs_date = format_bs(ad_to_bs(day), language)
    weekday = weekday_name(day, language)
    lines = [
        t("digest_header"),
        t("digest_date", weekday=weekday, bs=bs_date, ad=day.strftime("%d %b %Y")),
        "",
        t("briefing_headlines"),
    ]
    has_content = False

    news = await latest_snapshot(session, "news", ok_only=True)
    payload = (news.payload or {}) if news else {}
    items = payload.get(language) or payload.get("en") or []
    for index, item in enumerate(items[:5], start=1):
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        if len(title) > 180:
            title = title[:177].rstrip() + "..."
        link = str(item.get("link") or "").strip()
        source = str(item.get("source") or "").strip()
        safe_link = html.escape(link, quote=True)
        headline = f"{index}. <a href=\"{safe_link}\">{esc(title)}</a>" if link else f"{index}. {esc(title)}"
        if source:
            headline += f" — <i>{esc(source)}</i>"
        lines.append(headline)
        has_content = True
    if not any(item.get("title") for item in items[:5]):
        lines.append(t("briefing_no_headlines"))

    lines.extend(["", t("briefing_snapshot")])

    calendar = load_festivals(settings.data_dir)
    todays_festivals = [
        entry.get("name_ne" if language == "ne" else "name_en")
        for entry in calendar
        if entry.get("ad_date") == day.isoformat()
    ]
    if todays_festivals:
        lines.append(t("briefing_calendar_event", event=esc(", ".join(filter(None, todays_festivals)))))
    else:
        lines.append(t("briefing_calendar_date", weekday=weekday, bs=bs_date))
    has_content = True

    fx = await latest_snapshot(session, "forex", ok_only=True)
    rates = ((fx.payload or {}).get("rates") or {}) if fx else {}
    usd = rates.get("USD")
    if usd:
        has_content = True
        lines.append(
            t(
                "briefing_forex",
                buy=esc(usd.get("buy", "-")),
                sell=esc(usd.get("sell", "-")),
                date=esc((fx.payload or {}).get("date") or "-"),
            )
        )

    metals = await latest_snapshot(session, "metals", ok_only=True)
    metal_prices = ((metals.payload or {}).get("today") or {}) if metals else {}
    if metal_prices:
        has_content = True
        lines.append(
            t(
                "briefing_metals",
                gold=_format_number(metal_prices.get("gold_tola")),
                silver=_format_number(metal_prices.get("silver_tola")),
                date=esc((metals.payload or {}).get("effective") or "-"),
            )
        )

    vegetables = await latest_snapshot(session, "vegetables", ok_only=True)
    veg_items = ((vegetables.payload or {}).get("items") or []) if vegetables else []
    veg_prices = [
        f"{esc(item.get('name', ''))} रू {_format_number(item['avg'])}/{esc(item.get('unit') or 'kg')}"
        for item in veg_items[:3]
        if item.get("name") and item.get("avg") not in (None, "")
    ]
    if veg_prices:
        has_content = True
        lines.append(t("briefing_vegetables", prices=", ".join(veg_prices)))

    fuel = await latest_snapshot(session, "fuel", ok_only=True)
    fuel_payload = (fuel.payload or {}) if fuel else {}
    fuel_prices = fuel_payload.get("prices") or {}
    if fuel_prices:
        has_content = True
        lines.append(
            t(
                "briefing_fuel",
                petrol=esc(fuel_prices.get("petrol", "-")),
                diesel=esc(fuel_prices.get("diesel", "-")),
                date=esc(fuel_payload.get("effective") or "-"),
            )
        )

    weather = await latest_snapshot(session, "weather", ok_only=True)
    kathmandu = ((weather.payload or {}).get("cities") or {}).get("kathmandu") if weather else None
    if kathmandu:
        has_content = True
        lines.append(
            t(
                "briefing_weather",
                low=esc(kathmandu.get("low", "-")),
                high=esc(kathmandu.get("high", "-")),
                rain=esc(kathmandu.get("rain", "-")),
            )
        )

    lines.append(t("briefing_share_market_unavailable"))

    if not has_content:
        return None

    lines.append("")
    if settings.bot_link:
        lines.append(f"<a href=\"{esc(settings.bot_link)}\">{esc(settings.bot_link)}</a>")
    return "\n".join(lines)


def _format_number(value: object) -> str:
    if value is None:
        return "-"
    try:
        return esc(format_number(Decimal(str(value))))
    except (InvalidOperation, ValueError):
        return esc(value)
