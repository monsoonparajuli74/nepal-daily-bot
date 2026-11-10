"""Per-user conversation state machine (10-minute TTL)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import ConversationState
from app.utils.timeutil import ensure_utc, now_utc

STATE_TTL = timedelta(minutes=10)

STATE_IDLE = "idle"
STATE_AWAITING_AMOUNT = "awaiting_amount"
STATE_NEWS = "news"


async def get_state(session: AsyncSession, tg_user_id: int) -> ConversationState | None:
    row = await session.get(ConversationState, tg_user_id)
    if row is None:
        return None
    expires = ensure_utc(row.expires_at) or ensure_utc(row.updated_at)
    if expires is not None and now_utc() > expires:
        await session.delete(row)
        await session.flush()
        return None
    return row


async def set_state(
    session: AsyncSession,
    tg_user_id: int,
    state: str,
    context: dict[str, Any] | None = None,
    *,
    attempts: int = 0,
) -> ConversationState:
    now = now_utc()
    row = await session.get(ConversationState, tg_user_id)
    if row is None:
        row = ConversationState(
            tg_user_id=tg_user_id,
            state=state,
            context=context or {},
            attempts=attempts,
            updated_at=now,
            expires_at=now + STATE_TTL,
        )
        session.add(row)
    else:
        row.state = state
        row.context = context or {}
        row.attempts = attempts
        row.updated_at = now
        row.expires_at = now + STATE_TTL
    await session.flush()
    return row


async def clear_state(session: AsyncSession, tg_user_id: int) -> None:
    row = await session.get(ConversationState, tg_user_id)
    if row is not None:
        await session.delete(row)
        await session.flush()


async def purge_expired_states(session: AsyncSession) -> int:
    cutoff = now_utc()
    result = await session.execute(select(ConversationState).where(ConversationState.expires_at < cutoff))
    rows = result.scalars().all()
    for row in rows:
        await session.delete(row)
    await session.flush()
    return len(rows)
