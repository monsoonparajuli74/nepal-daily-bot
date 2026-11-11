"""Analytics: HMAC hashing, event recording, retention and the stats report."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.data import analytics
from app.data.models import Event, Snapshot, SourceState, User
from app.utils.timeutil import now_utc

SALT = "test-salt"


def test_hash_user_id_is_hmac_and_stable():
    first = analytics.hash_user_id(12345, SALT)
    assert first == analytics.hash_user_id(12345, SALT)
    assert first != analytics.hash_user_id(12345, "another-salt")
    assert first != analytics.hash_user_id(12346, SALT)
    assert len(first) == 64
    assert "12345" not in first


async def test_record_event_stores_metadata_not_raw_ids(session):
    await analytics.record_event(session, 987654, "view", SALT, module="weather", lang="ne", source="share_fx")
    rows = (await session.execute(select(Event))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_hash == analytics.hash_user_id(987654, SALT)
    assert row.event == "view"
    assert row.module == "weather"
    assert row.lang == "ne"
    assert row.source == "share_fx"
    assert "987654" not in row.user_hash


async def test_record_event_clamps_long_source(session):
    await analytics.record_event(session, 1, "start", SALT, source="x" * 200)
    rows = (await session.execute(select(Event))).scalars().all()
    assert rows[0].source == "x" * 64


async def test_track_event_async_writes_on_its_own_session(session_factory):
    analytics.track_event_async(session_factory, SALT, 42, "view", module="fuel", lang="en")
    await analytics.drain_tracked_events()
    async with session_factory() as db_session:
        rows = (await db_session.execute(select(Event))).scalars().all()
    assert [row.event for row in rows] == ["view"]
    assert rows[0].user_hash == analytics.hash_user_id(42, SALT)
    assert rows[0].module == "fuel"


async def test_purge_events_removes_only_old_rows(session):
    old = Event(user_hash="h", event="view", ts=now_utc() - timedelta(days=400))
    fresh = Event(user_hash="h", event="view", ts=now_utc())
    session.add_all([old, fresh])
    await session.commit()

    removed = await analytics.purge_events(session, retention_days=180)
    await session.commit()

    assert removed == 1
    remaining = (await session.execute(select(Event))).scalars().all()
    assert remaining == [fresh]


async def test_cohort_retention_uses_npt_day_boundaries(session):
    active_now = now_utc()
    start, _end = analytics.npt_day_bounds(1)
    joined_midday_yesterday_npt = start + timedelta(hours=12)
    session.add(
        User(tg_user_id=10, language="en", is_active=True, first_seen_at=joined_midday_yesterday_npt, last_seen_at=active_now)
    )
    session.add(
        User(tg_user_id=11, language="en", is_active=True, first_seen_at=joined_midday_yesterday_npt, last_seen_at=active_now)
    )
    session.add(Event(user_hash=analytics.hash_user_id(10, SALT), event="view", ts=active_now))
    await session.commit()

    share = await analytics.cohort_retention(session, SALT, cohort_days_ago=1)
    assert share == 0.5
    empty = await analytics.cohort_retention(session, SALT, cohort_days_ago=7)
    assert empty is None


async def test_build_stats_report_counts_users_and_views(session):
    now = now_utc()
    session.add_all(
        [
            User(tg_user_id=1, language="ne", is_active=True, first_seen_at=now, last_seen_at=now),
            User(tg_user_id=2, language="en", is_active=True, first_seen_at=now, last_seen_at=now),
            User(tg_user_id=3, language="en", is_active=False, first_seen_at=now, last_seen_at=now),
        ]
    )
    for uid, module in ((1, "weather"), (1, "weather"), (2, "news")):
        session.add(Event(user_hash=analytics.hash_user_id(uid, SALT), event="view", module=module, ts=now))
    session.add(Event(user_hash=analytics.hash_user_id(2, SALT), event="start", source="direct", ts=now))
    await session.commit()

    report = await analytics.build_stats_report(session, SALT)

    assert "New users: 3 today · 3 (7d) · 3 (30d)" in report
    assert "DAU 2 · WAU 2 · MAU 2" in report
    assert "Requests today: 4" in report
    assert "weather — 2" in report
    assert "news — 1" in report
    assert "direct — 1 users" in report
    assert "ne 1" in report
    assert "en 2" in report
    assert "Blocked users: 1" in report
    assert "D1 -" in report  # no yesterday cohort


async def test_build_stats_report_supports_7_and_30_day_windows(session):
    now = now_utc()
    session.add(Event(user_hash=analytics.hash_user_id(1, SALT), event="view", module="weather", ts=now))
    session.add(Event(user_hash=analytics.hash_user_id(1, SALT), event="view", module="news", ts=now - timedelta(days=10)))
    await session.commit()

    week = await analytics.build_stats_report(session, SALT, 7)
    month = await analytics.build_stats_report(session, SALT, "30")

    assert "Top modules (7d)" in week
    assert "weather — 1" in week
    assert "news — 1" not in week
    assert "Top modules (30d)" in month
    assert "news — 1" in month


async def test_build_stats_report_lists_last_refresh_per_source(session):
    refreshed = now_utc() - timedelta(hours=1)
    session.add(
        Snapshot(
            source="weather",
            payload={},
            fetched_at=refreshed,
            checked_at=refreshed,
            content_hash="x",
            ok=True,
        )
    )
    session.add(SourceState(source="news", last_success_at=refreshed))
    await session.commit()

    report = await analytics.build_stats_report(session, SALT)

    assert "Last data refresh" in report
    assert "weather —" in report
    assert "news —" in report
    assert "NPT" in report
