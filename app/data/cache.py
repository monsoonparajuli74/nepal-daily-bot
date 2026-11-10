"""Snapshot cache: read/write frozen source payloads and staleness logic.

The cache is the reason a user tap never touches a third-party site. Handlers always
read the newest *successful* snapshot; the scheduler refreshes in the background.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import Snapshot
from app.data.sources.base import Snapshot as SourceSnapshot
from app.data.sources.base import SourceAdapter, SourceError
from app.utils.timeutil import ensure_utc, now_utc

logger = logging.getLogger(__name__)

#: Keep this many snapshots per source so "vs yesterday" comparisons work.
MAX_SNAPSHOTS_PER_SOURCE = 10


def content_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def latest_snapshot(session: AsyncSession, source: str, *, ok_only: bool = False) -> Snapshot | None:
    stmt = select(Snapshot).where(Snapshot.source == source)
    if ok_only:
        stmt = stmt.where(Snapshot.ok.is_(True))
    stmt = stmt.order_by(Snapshot.fetched_at.desc(), Snapshot.id.desc()).limit(1)
    result = await session.execute(stmt)
    return result.scalars().first()


async def previous_ok_snapshot(session: AsyncSession, source: str) -> Snapshot | None:
    stmt = (
        select(Snapshot)
        .where(Snapshot.source == source, Snapshot.ok.is_(True))
        .order_by(Snapshot.fetched_at.desc(), Snapshot.id.desc())
        .limit(2)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return rows[1] if len(rows) > 1 else None


async def save_snapshot(session: AsyncSession, snapshot: SourceSnapshot) -> Snapshot:
    """Persist a fetched snapshot, skipping duplicate payloads but refreshing ``checked_at``."""
    new_hash = content_hash(snapshot.payload)
    current = await latest_snapshot(session, snapshot.source)

    if current is not None and current.content_hash == new_hash and snapshot.ok:
        current.checked_at = now_utc()
        current.etag = snapshot.etag or current.etag
        current.last_modified = snapshot.last_modified or current.last_modified
        await session.flush()
        return current

    row = Snapshot(
        source=snapshot.source,
        fetched_at=snapshot.fetched_at,
        checked_at=now_utc(),
        payload=snapshot.payload,
        content_hash=new_hash,
        ok=snapshot.ok,
        etag=snapshot.etag,
        last_modified=snapshot.last_modified,
    )
    session.add(row)
    await session.flush()
    await _prune(session, snapshot.source)
    return row


async def save_failure(session: AsyncSession, source: str, error: str) -> Snapshot:
    row = Snapshot(
        source=source,
        fetched_at=now_utc(),
        checked_at=now_utc(),
        payload={"error": error},
        content_hash="",
        ok=False,
        etag=None,
        last_modified=None,
    )
    session.add(row)
    await session.flush()
    await _prune(session, source)
    return row


async def _prune(session: AsyncSession, source: str) -> None:
    stmt = (
        select(Snapshot.id)
        .where(Snapshot.source == source)
        .order_by(Snapshot.fetched_at.desc(), Snapshot.id.desc())
        .offset(MAX_SNAPSHOTS_PER_SOURCE)
    )
    result = await session.execute(stmt)
    stale_ids = list(result.scalars().all())
    if stale_ids:
        await session.execute(delete(Snapshot).where(Snapshot.id.in_(stale_ids)))


async def update_checked_at(session: AsyncSession, row: Snapshot) -> None:
    row.checked_at = now_utc()
    await session.flush()


def snapshot_is_stale(row: Snapshot, stale_after) -> bool:
    checked = ensure_utc(row.checked_at)
    if checked is None:
        return True
    return (now_utc() - checked) > stale_after


async def refresh_source(session: AsyncSession, adapter: SourceAdapter) -> Snapshot | None:
    """Run one adapter fetch and update the cache. Never raises to the caller."""
    current = await latest_snapshot(session, adapter.name, ok_only=True)
    etag = current.etag if current else None
    last_modified = current.last_modified if current else None

    try:
        snapshot = await adapter.fetch(etag=etag, last_modified=last_modified)
    except SourceError as exc:
        logger.warning("source_fetch_failed", extra={"source": adapter.name, "error": exc.message})
        await save_failure(session, adapter.name, exc.message)
        return None
    except Exception as exc:  # noqa: BLE001 - a broken source must never crash the bot
        logger.exception("source_fetch_crashed", extra={"source": adapter.name})
        await save_failure(session, adapter.name, str(exc))
        return None

    if snapshot.not_modified and current is not None:
        await update_checked_at(session, current)
        return current

    row = await save_snapshot(session, snapshot)
    persist = getattr(adapter, "persist", None)
    if persist is not None and snapshot.ok:
        try:
            await persist(session, snapshot)
        except Exception:  # noqa: BLE001 - persistence failure shouldn't break the cache
            logger.exception("source_persist_failed", extra={"source": adapter.name})
    return row


def payload_of(row: Snapshot | None) -> dict[str, Any]:
    if row is None or not row.ok:
        return {}
    return row.payload or {}


def fetched_at_of(row: Snapshot | None) -> datetime | None:
    return row.fetched_at if row is not None else None
