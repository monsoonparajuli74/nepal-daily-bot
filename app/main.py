"""FastAPI application: Telegram webhook / polling, health check and background processing."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.bot.handlers.admin import send_daily_summary
from app.bot.processor import Processor
from app.bot.ratelimit import RateLimiter
from app.bot.users import mark_inactive
from app.channels.telegram import webhook as telegram_webhook
from app.channels.telegram.client import TelegramChannel
from app.channels.telegram.commands import configure_bot, delete_webhook, set_webhook
from app.config import Settings, get_settings
from app.data.analytics import track_event_async
from app.data.cache import latest_snapshot, snapshot_is_stale
from app.data.config_loader import load_festivals
from app.data.dedupe import Deduper
from app.data.digest import send_digests
from app.data.scheduler import build_scheduler, refresh_all_once
from app.data.sources import get_adapters
from app.db import build_engine, build_session_factory, init_models

logger = logging.getLogger(__name__)


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )


def _digest_trigger(digest_time_npt: str) -> CronTrigger:
    try:
        hour, minute = (int(part) for part in digest_time_npt.split(":", 1))
    except (ValueError, AttributeError):
        hour, minute = 7, 0
    return CronTrigger(hour=hour, minute=minute, timezone="Asia/Kathmandu")


def watch_task(task: asyncio.Task, name: str) -> asyncio.Task:
    """Log if a background task dies unexpectedly (otherwise asyncio hides it)."""

    def _done(finished: asyncio.Task) -> None:
        if finished.cancelled():
            return
        exc = finished.exception()
        if exc is not None:
            logger.error("background_task_failed", extra={"task": name, "error": str(exc)})

    task.add_done_callback(_done)
    return task


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    configure_logging(settings.log_level)

    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory

    if settings.auto_create_tables:
        await init_models(engine)

    app.state.adapters = get_adapters(settings)

    async def on_blocked(chat_id: int) -> None:
        async with session_factory() as session:
            await mark_inactive(session, chat_id)
            await session.commit()
        track_event_async(session_factory, settings.analytics_salt, chat_id, "blocked")

    channel = TelegramChannel(settings, on_blocked=on_blocked)
    app.state.channel = channel
    app.state.dedupe = Deduper(session_factory)
    app.state.user_limiter = RateLimiter(settings.rate_limit_per_minute)
    app.state.group_limiter = RateLimiter(settings.group_rate_limit_per_minute)
    app.state.processor = Processor(
        settings,
        session_factory,
        channel,
        app.state.dedupe,
        app.state.user_limiter,
        app.state.group_limiter,
    )

    load_festivals(settings.data_dir)
    app.state.calendar_loaded = True

    scheduler = None
    if settings.scheduler_enabled:
        scheduler = build_scheduler(settings, session_factory, app.state.adapters)
        if settings.feature_daily_digest:
            scheduler.add_job(
                send_digests,
                trigger=_digest_trigger(settings.digest_time_npt),
                args=[settings, session_factory, channel],
                id="digest:daily",
                name="daily digest",
                replace_existing=True,
            )
        if settings.feature_admin_daily_summary and settings.admin_telegram_ids:
            scheduler.add_job(
                send_daily_summary,
                trigger=CronTrigger(hour=21, minute=0, timezone="Asia/Kathmandu"),
                args=[settings, session_factory, channel],
                id="admin:daily_summary",
                name="admin daily summary",
                replace_existing=True,
            )
        scheduler.start()
    app.state.scheduler = scheduler

    if settings.refresh_on_startup:
        app.state.startup_refresh_task = watch_task(
            asyncio.create_task(refresh_all_once(settings, session_factory, app.state.adapters)),
            "startup_refresh",
        )
    else:
        app.state.startup_refresh_task = None

    app.state.polling_task = None
    if settings.telegram_bot_token and settings.telegram_setup_on_startup:
        await configure_bot(channel.bot, settings)
        if settings.telegram_mode == "polling":
            await delete_webhook(channel.bot, drop_pending=settings.telegram_drop_pending_updates)
            app.state.polling_task = watch_task(
                asyncio.create_task(
                    telegram_webhook.poll_forever(channel, app.state.processor, settings)
                ),
                "telegram_polling",
            )
        else:
            await set_webhook(channel.bot, settings)

    try:
        yield
    finally:
        for task_attr in ("startup_refresh_task", "polling_task"):
            task = getattr(app.state, task_attr, None)
            if task is not None and not task.done():
                task.cancel()
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        await channel.aclose()
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Sajilo Nepal", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings

    @app.get("/")
    async def index() -> dict[str, str]:
        return {"service": "Sajilo Nepal", "status": "ok", "docs": "/healthz"}

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        session_factory = app.state.session_factory
        sources: dict[str, Any] = {}
        degraded = False
        async with session_factory() as session:
            for adapter in app.state.adapters:
                row = await latest_snapshot(session, adapter.name, ok_only=True)
                if row is None:
                    sources[adapter.name] = {"status": "missing"}
                    degraded = True
                    continue
                stale = snapshot_is_stale(row, adapter.stale_after)
                sources[adapter.name] = {
                    "status": "stale" if stale else "ok",
                    "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                    "checked_at": row.checked_at.isoformat() if row.checked_at else None,
                }
                degraded = degraded or stale
        sources["calendar"] = {"status": "ok" if getattr(app.state, "calendar_loaded", False) else "missing"}
        return JSONResponse(
            {
                "status": "degraded" if degraded else "ok",
                "sources": sources,
                "scheduler": bool(app.state.scheduler),
            },
            status_code=200,
        )

    app.include_router(telegram_webhook.router)
    return app


app = create_app()
