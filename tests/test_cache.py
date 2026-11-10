from __future__ import annotations

from app.data.cache import latest_snapshot, previous_ok_snapshot, save_snapshot, snapshot_is_stale
from app.data.sources.base import Snapshot as SourceSnapshot
from app.utils.timeutil import now_utc


async def test_save_and_read_snapshot(session):
    payload = {"rates": {"USD": {"buy": "133", "sell": "134", "unit": 1}}}
    await save_snapshot(session, SourceSnapshot(source="forex", payload=payload, fetched_at=now_utc()))
    await session.commit()

    row = await latest_snapshot(session, "forex", ok_only=True)
    assert row is not None
    assert row.payload["rates"]["USD"]["buy"] == "133"


async def test_duplicate_payload_updates_checked_at(session):
    payload = {"prices": {"petrol": "197"}}
    first = await save_snapshot(session, SourceSnapshot(source="fuel", payload=payload))
    await session.commit()
    second = await save_snapshot(session, SourceSnapshot(source="fuel", payload=payload))
    await session.commit()
    assert first.id == second.id


async def test_previous_snapshot_requires_two(session):
    await save_snapshot(session, SourceSnapshot(source="metals", payload={"today": {"gold_tola": "1"}}))
    await session.commit()
    assert await previous_ok_snapshot(session, "metals") is None

    await save_snapshot(session, SourceSnapshot(source="metals", payload={"today": {"gold_tola": "2"}}))
    await session.commit()
    prev = await previous_ok_snapshot(session, "metals")
    assert prev is not None
    assert prev.payload["today"]["gold_tola"] == "1"


async def test_staleness(session):
    await save_snapshot(session, SourceSnapshot(source="news", payload={"en": []}))
    await session.commit()
    row = await latest_snapshot(session, "news")
    assert row is not None
    from datetime import timedelta

    assert snapshot_is_stale(row, timedelta(hours=1)) is False


async def test_successful_unchanged_refresh_updates_freshness(session):
    from datetime import timedelta

    from app.data.models import Snapshot

    checked_at = now_utc() - timedelta(hours=2)
    row = Snapshot(
        source="news",
        fetched_at=now_utc() - timedelta(days=1),
        checked_at=checked_at,
        payload={"en": []},
        content_hash="test",
        ok=True,
    )
    session.add(row)
    await session.commit()

    assert snapshot_is_stale(row, timedelta(hours=1)) is True
    row.checked_at = now_utc()
    await session.commit()
    assert snapshot_is_stale(row, timedelta(hours=1)) is False
