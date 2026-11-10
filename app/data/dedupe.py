"""Inbound update dedupe.

Telegram retries a webhook delivery when it does not receive a timely 200, and polling can
re-present the same update. We keep an in-memory high-water mark plus a short recent-ids set,
and persist each processed ``update_id`` so a restart cannot replay old updates.
"""

from __future__ import annotations

from collections import deque
from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.data.models import UpdateRecord
from app.utils.timeutil import now_utc

RECENT_MAX = 256


class Deduper:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._high: int | None = None
        self._recent: deque[int] = deque(maxlen=RECENT_MAX)
        self._recent_set: set[int] = set()

    async def register(self, update_id: int | None) -> bool:
        """Return True when this update is new (process it), False when already seen."""
        if update_id is None:
            return True
        if update_id in self._recent_set or (self._high is not None and update_id <= self._high):
            return False

        async with self._session_factory() as session:
            if await session.get(UpdateRecord, update_id) is not None:
                self._remember(update_id)
                return False
            session.add(UpdateRecord(update_id=update_id, received_at=now_utc()))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                self._remember(update_id)
                return False

        self._remember(update_id)
        return True

    def _remember(self, update_id: int) -> None:
        if self._high is None or update_id > self._high:
            self._high = update_id
        if update_id not in self._recent_set:
            if len(self._recent) == self._recent.maxlen:
                self._recent_set.discard(self._recent[0])
            self._recent.append(update_id)
            self._recent_set.add(update_id)


async def purge_updates(session: AsyncSession, ttl_hours: int) -> int:
    cutoff = now_utc() - timedelta(hours=ttl_hours)
    result = await session.execute(delete(UpdateRecord).where(UpdateRecord.received_at <= cutoff))
    await session.flush()
    return int(result.rowcount or 0)
