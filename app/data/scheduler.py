"""In-process APScheduler jobs.

Job bodies are thin wrappers around ``cache.refresh_source`` so this module can later be
extracted into a separate worker without touching adapter code.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.state import purge_expired_states
from app.bot.users import purge_inactive
from app.config import Settings
from app.data.cache import refresh_source
from app.data.dedupe import purge_updates
from app.data.sources.base import SourceAdapter

logger = logging.getLogger(__name__)

NPT = timezone(timedelta(hours=5, minutes=45))


def build_scheduler(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    adapters: list[SourceAdapter],
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=NPT)

    daily_refresh_times = {
        "forex": (settings.refresh_forex_hour_npt, settings.refresh_forex_minute_npt),
        "metals": (settings.refresh_metals_hour_npt, settings.refresh_metals_minute_npt),
        "fuel": (settings.refresh_fuel_hour_npt, settings.refresh_fuel_minute_npt),
        "vegetables": (settings.refresh_vegetables_hour_npt, settings.refresh_vegetables_minute_npt),
    }

    for adapter in adapters:
        if adapter.name == "horoscope":
            trigger = CronTrigger(hour=settings.horoscope_hour_npt, minute=0, timezone=NPT)
        elif adapter.name in daily_refresh_times:
            hour, minute = daily_refresh_times[adapter.name]
            trigger = CronTrigger(hour=hour, minute=minute, timezone=NPT)
        elif adapter.name == "news":
            trigger = CronTrigger(hour=f"*/{settings.refresh_news_hours}", minute=0, timezone=NPT)
        else:
            trigger = IntervalTrigger(seconds=int(adapter.refresh_interval.total_seconds()), timezone=NPT)
        scheduler.add_job(
            _refresh_job,
            trigger=trigger,
            args=[adapter, session_factory],
            id=f"refresh:{adapter.name}",
            name=f"refresh {adapter.name}",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
            replace_existing=True,
        )

    scheduler.add_job(
        _cleanup_job,
        trigger=CronTrigger(hour=3, minute=0, timezone=NPT),
        args=[settings, session_factory],
        id="cleanup:retention",
        name="privacy retention cleanup",
        replace_existing=True,
    )
    return scheduler

async def _refresh_job(adapter: SourceAdapter, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        try:
            await refresh_source(session, adapter)
            await session.commit()
        except Exception:  # noqa: BLE001 - scheduler must never die
            logger.exception("scheduled_refresh_failed", extra={"source": adapter.name})
            await session.rollback()


async def _cleanup_job(settings: Settings, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        try:
            removed = await purge_inactive(session, settings.user_data_retention_days)
            await purge_expired_states(session)
            await purge_updates(session, settings.dedupe_ttl_hours)
            await session.commit()
            if removed:
                logger.info("retention_cleanup", extra={"removed_users": removed})
        except Exception:  # noqa: BLE001
            logger.exception("retention_cleanup_failed")
            await session.rollback()


async def refresh_all_once(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    adapters: list[SourceAdapter],
) -> None:
    """Initial warm-up, run in the background at startup."""
    for adapter in adapters:
        async with session_factory() as session:
            try:
                await refresh_source(session, adapter)
                await session.commit()
            except Exception:  # noqa: BLE001
                logger.exception("startup_refresh_failed", extra={"source": adapter.name})
                await session.rollback()
        await asyncio.sleep(0.5)


def nightly_horoscope_time(hour_npt: int) -> datetime:
    now = datetime.now(NPT)
    candidate = now.replace(hour=hour_npt, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate
