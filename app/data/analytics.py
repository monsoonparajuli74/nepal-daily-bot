"""Privacy-friendly analytics: only a salted hash of the Telegram id is stored."""

from __future__ import annotations

import hashlib
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import Event
from app.utils.timeutil import now_utc


def hash_user_id(tg_user_id: int | str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{tg_user_id}".encode()).hexdigest()[:32]


async def track_event(session: AsyncSession, tg_user_id: int | str, event: str, salt: str) -> None:
    session.add(Event(tg_user_id_hash=hash_user_id(tg_user_id, salt), event=event, ts=now_utc()))
    await session.flush()


async def event_counts(session: AsyncSession, days: int = 7) -> list[tuple[str, int]]:
    since = now_utc() - timedelta(days=days)
    stmt = (
        select(Event.event, func.count(Event.id))
        .where(Event.ts >= since)
        .group_by(Event.event)
        .order_by(func.count(Event.id).desc())
    )
    result = await session.execute(stmt)
    return [(row[0], int(row[1])) for row in result.all()]


async def daily_active_users(session: AsyncSession, days: int = 7) -> list[tuple[str, int]]:
    since = now_utc() - timedelta(days=days)
    day = func.date(Event.ts)
    stmt = (
        select(day, func.count(func.distinct(Event.tg_user_id_hash)))
        .where(Event.ts >= since)
        .group_by(day)
        .order_by(day)
    )
    result = await session.execute(stmt)
    return [(str(row[0]), int(row[1])) for row in result.all()]
