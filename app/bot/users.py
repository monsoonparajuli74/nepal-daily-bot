"""User repository. Stores only the numeric Telegram id plus preferences; never logged, and
purged after opt-out."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.i18n import normalise_language
from app.data.models import User
from app.utils.timeutil import ensure_utc, now_utc

DEFAULT_DIGEST_TIME = "07:00"


async def get_user(session: AsyncSession, tg_user_id: int) -> User | None:
    return await session.get(User, tg_user_id)


async def get_or_create_user(
    session: AsyncSession,
    tg_user_id: int,
    name: str | None = None,
) -> User:
    """Fetch or create a user and record an inbound interaction.

    A user who previously stopped the bot and messages again is reactivated.
    """
    now = now_utc()
    user = await session.get(User, tg_user_id)
    if user is None:
        user = User(
            tg_user_id=tg_user_id,
            name=name,
            language="ne",
            is_active=True,
            digest_opt_in=False,
            digest_time=DEFAULT_DIGEST_TIME,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(user)
    else:
        if name and user.name != name:
            user.name = name
        user.last_seen_at = now
        if not user.is_active:
            user.is_active = True
    await session.flush()
    return user


async def set_language(session: AsyncSession, user: User, language: str) -> User:
    user.language = normalise_language(language)
    await session.flush()
    return user


async def toggle_language(session: AsyncSession, user: User) -> User:
    user.language = "ne" if user.language == "en" else "en"
    await session.flush()
    return user


async def set_default_zodiac(session: AsyncSession, user: User, sign: str | None) -> User:
    user.default_zodiac = sign
    await session.flush()
    return user


async def set_source(session: AsyncSession, user: User, source: str | None) -> User:
    """Record the acquisition payload from a /start deep link (analytics only)."""
    if source and not user.source:
        user.source = source[:64]
        await session.flush()
    return user


async def set_digest_opt_in(session: AsyncSession, tg_user_id: int, opt_in: bool) -> User | None:
    user = await session.get(User, tg_user_id)
    if user is not None:
        user.digest_opt_in = opt_in
        user.daily_briefing_opt_out = not opt_in
        await session.flush()
    return user


async def mark_inactive(session: AsyncSession, tg_user_id: int) -> None:
    user = await session.get(User, tg_user_id)
    if user is not None:
        user.is_active = False
        user.digest_opt_in = False
        await session.flush()


async def mark_active(session: AsyncSession, tg_user_id: int) -> None:
    user = await session.get(User, tg_user_id)
    if user is not None:
        user.is_active = True
        await session.flush()


async def purge_inactive(session: AsyncSession, retention_days: int) -> int:
    """Delete records for users inactive longer than the retention window."""
    cutoff = now_utc() - timedelta(days=retention_days)
    result = await session.execute(select(User).where(User.is_active.is_(False)))
    removed = 0
    for user in result.scalars().all():
        last_seen = ensure_utc(user.last_seen_at)
        if last_seen is not None and last_seen < cutoff:
            await session.delete(user)
            removed += 1
    await session.flush()
    return removed


async def delete_user(session: AsyncSession, tg_user_id: int) -> None:
    await session.execute(delete(User).where(User.tg_user_id == tg_user_id))
