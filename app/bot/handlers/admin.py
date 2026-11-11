"""Admin-only tooling: the /stats report and the optional nightly summary."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.context import BotContext
from app.channels.base import Channel, Reply
from app.config import Settings
from app.data.analytics import build_stats_report

logger = logging.getLogger(__name__)


def is_admin(settings: Settings, tg_user_id: int) -> bool:
    return tg_user_id in settings.admin_telegram_ids


async def stats(ctx: BotContext, param: str | None = None) -> None:
    """Show the analytics report; only an ADMIN_TELEGRAM_ID in a private chat gets it."""
    if ctx.is_group or not is_admin(ctx.settings, ctx.tg_id):
        # Do nothing at all: never reveal that /stats exists.
        return
    report = await build_stats_report(ctx.session, ctx.settings.analytics_salt, param)
    await ctx.reply(report)


async def send_daily_summary(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    channel: Channel,
) -> None:
    """Nightly job body: DM each admin the same report /stats shows (21:00 NPT)."""
    admin_ids = settings.admin_telegram_ids
    if not admin_ids:
        return
    try:
        async with session_factory() as session:
            report = await build_stats_report(session, settings.analytics_salt)
    except Exception:  # noqa: BLE001 - the summary must never kill the scheduler
        logger.exception("admin_daily_summary_failed")
        return
    for admin_id in admin_ids:
        try:
            await channel.send(admin_id, Reply(text=report))
        except Exception:  # noqa: BLE001 - one failed DM must not skip the rest
            logger.exception("admin_daily_summary_failed", extra={"admin_id": admin_id})
