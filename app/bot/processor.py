"""Inbound pipeline: dedupe, group gating, rate limits, context assembly and routing.

This is the one place that turns a normalised :class:`InboundEvent` into handler calls. It
owns the database session for the turn and commits once, so handlers stay simple.
"""

from __future__ import annotations

import logging
import re
import traceback
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot import router
from app.bot.context import BotContext
from app.bot.handlers.common import welcome_menu
from app.bot.ratelimit import RateLimiter
from app.bot.users import get_or_create_user, get_user, mark_inactive, set_source
from app.channels.base import Channel, InboundEvent, InboundKind
from app.config import Settings
from app.data import analytics
from app.data.dedupe import Deduper
from app.utils.timeutil import ensure_utc, now_utc

logger = logging.getLogger(__name__)

#: Telegram bot tokens look like ``123456789:AA...``; never write them to logs.
_BOT_TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{30,}")


def _redact_secrets(value: str) -> str:
    return _BOT_TOKEN_RE.sub("<redacted>", value or "")


def _traceback_frames(exc: BaseException) -> list[str]:
    return [
        f"{frame.filename}:{frame.lineno} in {frame.name}"
        for frame in traceback.extract_tb(exc.__traceback__)
    ]


def _traceback_location(exc: BaseException) -> str:
    frames = _traceback_frames(exc)
    return frames[-1] if frames else "<unknown>"


def _traceback_text(exc: BaseException) -> str:
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return _redact_secrets(formatted)


class Processor:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        channel: Channel,
        dedupe: Deduper,
        user_limiter: RateLimiter,
        group_limiter: RateLimiter,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.channel = channel
        self.dedupe = dedupe
        self.user_limiter = user_limiter
        self.group_limiter = group_limiter

    async def handle(self, event: InboundEvent) -> None:
        if not await self.dedupe.register(event.update_id):
            return

        if event.kind is InboundKind.MEMBER:
            await self._member(event)
            return

        if event.kind is InboundKind.CALLBACK:
            await self.channel.answer_callback(event.callback_query_id or "")

        # In groups we only ever answer commands and explicit mentions.
        if event.is_group and not event.is_self_service():
            return

        if event.is_group:
            if not self.group_limiter.allow(str(event.chat_id)):
                return
        elif not self.user_limiter.allow(str(event.user_id)):
            return

        if event.kind is InboundKind.OTHER:
            if not event.is_group:
                await self._unsupported(event)
            return

        if event.kind not in (InboundKind.TEXT, InboundKind.CALLBACK):
            return

        await self._dispatch(event)

    # ---- internals ----

    async def _member(self, event: InboundEvent) -> None:
        if event.member_status != "left":
            return
        async with self.session_factory() as session:
            await mark_inactive(session, event.user_id)
            await session.commit()
        # my_chat_member "left"/"kicked": the bot was removed from a chat.
        analytics.track_event_async(
            self.session_factory, self.settings.analytics_salt, event.user_id, "blocked"
        )

    async def _unsupported(self, event: InboundEvent) -> None:
        async with self.session_factory() as session:
            user = await get_or_create_user(session, event.user_id, event.display_name)
            ctx = self._context(session, user, event)
            await ctx.reply(ctx.t("unsupported_media_hint"))
            await session.commit()

    async def _dispatch(self, event: InboundEvent) -> None:
        async with self.session_factory() as session:
            ctx: BotContext | None = None
            try:
                existing = await get_user(session, event.user_id)
                returning = existing is not None and (not existing.is_active or self._is_stale(existing))
                was_inactive = existing is not None and not existing.is_active
                user = await get_or_create_user(session, event.user_id, event.display_name)
                source = self._start_source(event)
                if source:
                    await set_source(session, user, source)
                ctx = self._context(session, user, event)
                ctx.is_returning = returning

                if was_inactive:
                    ctx.track("unblocked")
                if event.kind is InboundKind.CALLBACK:
                    await router.route_action(ctx, event.action or "")
                elif self._is_start(event) or (returning and not event.is_group and not event.is_command):
                    if self._is_start(event):
                        ctx.track("start", source=source or "direct")
                    else:
                        ctx.track("menu_open", module="home")
                    await ctx.send(welcome_menu(ctx))
                else:
                    await router.route_text(ctx, event.text or "")

                await session.commit()
            except Exception as exc:  # noqa: BLE001 - one bad turn must not kill the worker
                logger.error(
                    "turn_failed at %s\n%s",
                    _traceback_location(exc),
                    _traceback_text(exc),
                    extra={
                        "chat": event.chat_id,
                        "error_type": type(exc).__name__,
                        "location": _traceback_location(exc),
                        "trace": _traceback_frames(exc),
                    },
                )
                try:
                    await session.rollback()
                except Exception as rollback_exc:  # noqa: BLE001 - best effort
                    logger.error(
                        "turn_rollback_failed at %s\n%s",
                        _traceback_location(rollback_exc),
                        _traceback_text(rollback_exc),
                        extra={
                            "chat": event.chat_id,
                            "error_type": type(rollback_exc).__name__,
                            "location": _traceback_location(rollback_exc),
                        },
                    )
                # Record the failure outside the turn's session: after rollback ORM
                # attributes may be expired and a sync access would try to lazy-load.
                analytics.track_event_async(
                    self.session_factory, self.settings.analytics_salt, event.user_id, "error"
                )

    def _context(self, session: AsyncSession, user, event: InboundEvent) -> BotContext:
        return BotContext(
            session=session,
            user=user,
            settings=self.settings,
            channel=self.channel,
            inbound=event,
            language=user.language,
            session_factory=self.session_factory,
        )

    def _is_stale(self, user) -> bool:
        last_seen = ensure_utc(user.last_seen_at)
        if last_seen is None:
            return True
        return (now_utc() - last_seen) > timedelta(days=self.settings.welcome_after_silence_days)

    @staticmethod
    def _is_start(event: InboundEvent) -> bool:
        return event.kind is InboundKind.TEXT and event.command == "start"

    @staticmethod
    def _start_source(event: InboundEvent) -> str | None:
        if event.kind is InboundKind.TEXT and event.command == "start":
            args = event.command_args
            if args:
                return args[0][:64]
        return None
