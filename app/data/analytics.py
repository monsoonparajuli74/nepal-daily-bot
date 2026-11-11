"""Privacy-friendly analytics: only an HMAC of the Telegram id is stored.

Recording is fire-and-forget (its own session and task) so a slow or failed write never
delays or breaks a user-facing reply. The query helpers power the admin /stats report;
day boundaries follow Nepal Time (NPT) throughout.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from datetime import datetime, time, timedelta, timezone
from html import escape

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.data.models import Event, Snapshot, SourceState, User
from app.utils.timeutil import NPT, ensure_utc, format_npt, now_utc, today_npt

logger = logging.getLogger(__name__)


def hash_user_id(tg_user_id: int | str, salt: str) -> str:
    """HMAC-SHA256 of the Telegram id; unlinkable without the secret salt."""
    return hmac.new(salt.encode(), str(tg_user_id).encode(), hashlib.sha256).hexdigest()


# ---- Recording ----


async def record_event(
    session: AsyncSession,
    tg_user_id: int | str,
    event: str,
    salt: str,
    *,
    module: str | None = None,
    lang: str | None = None,
    source: str | None = None,
) -> None:
    """Write an event on the caller's session (commit stays the caller's job)."""
    session.add(
        Event(
            user_hash=hash_user_id(tg_user_id, salt),
            event=event,
            ts=now_utc(),
            module=module or None,
            lang=lang or None,
            source=(source.strip()[:64] or None) if source else None,
        )
    )
    await session.flush()


_pending_tasks: set[asyncio.Task[None]] = set()


def track_event_async(
    session_factory: async_sessionmaker[AsyncSession],
    salt: str,
    tg_user_id: int | str,
    event: str,
    *,
    module: str | None = None,
    lang: str | None = None,
    source: str | None = None,
) -> None:
    """Fire-and-forget: schedule a write on its own session; never raises."""
    try:
        task = asyncio.create_task(
            _write_event(session_factory, salt, tg_user_id, event, module=module, lang=lang, source=source)
        )
    except RuntimeError:  # pragma: no cover - no running event loop (plain scripts)
        return
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)


async def _write_event(
    session_factory: async_sessionmaker[AsyncSession],
    salt: str,
    tg_user_id: int | str,
    event: str,
    *,
    module: str | None = None,
    lang: str | None = None,
    source: str | None = None,
) -> None:
    try:
        async with session_factory() as session:
            await record_event(session, tg_user_id, event, salt, module=module, lang=lang, source=source)
            await session.commit()
    except Exception:  # noqa: BLE001 - analytics must never break a reply
        logger.exception("analytics_write_failed", extra={"event": event})


async def drain_tracked_events() -> None:
    """Wait until every scheduled write has landed (tests and shutdown)."""
    while _pending_tasks:
        await asyncio.gather(*list(_pending_tasks), return_exceptions=True)


# ---- NPT day boundaries ----


def npt_day_bounds(days_ago: int) -> tuple[datetime, datetime]:
    """UTC bounds [start, end) of the Nepal-Time calendar day ``days_ago`` days back."""
    start_npt = datetime.combine(today_npt() - timedelta(days=days_ago), time.min, tzinfo=NPT)
    end_npt = start_npt + timedelta(days=1)
    return start_npt.astimezone(timezone.utc), end_npt.astimezone(timezone.utc)


def _today_start_utc() -> datetime:
    return npt_day_bounds(0)[0]


# ---- Queries ----


async def count_events(session: AsyncSession, *, since: datetime) -> int:
    result = await session.execute(select(func.count(Event.id)).where(Event.ts >= since))
    return int(result.scalar() or 0)


async def active_users(session: AsyncSession, since: datetime) -> int:
    """Distinct users (by hash) with at least one event since ``since``."""
    result = await session.execute(
        select(func.count(func.distinct(Event.user_hash))).where(Event.ts >= since)
    )
    return int(result.scalar() or 0)


async def new_users_since(session: AsyncSession, since: datetime) -> int:
    result = await session.execute(select(func.count(User.tg_user_id)).where(User.first_seen_at >= since))
    return int(result.scalar() or 0)


async def top_modules(session: AsyncSession, since: datetime, limit: int = 5) -> list[tuple[str, int]]:
    """Most viewed modules (event='view') since ``since``."""
    result = await session.execute(
        select(Event.module, func.count(Event.id))
        .where(Event.ts >= since, Event.event == "view", Event.module.is_not(None))
        .group_by(Event.module)
        .order_by(func.count(Event.id).desc())
        .limit(limit)
    )
    return [(row[0], int(row[1])) for row in result.all()]


async def top_sources(session: AsyncSession, since: datetime, limit: int = 5) -> list[tuple[str, int]]:
    """Deep-link payloads users arrived with (event='start'), by distinct user."""
    result = await session.execute(
        select(Event.source, func.count(func.distinct(Event.user_hash)))
        .where(Event.ts >= since, Event.event == "start", Event.source.is_not(None))
        .group_by(Event.source)
        .order_by(func.count(func.distinct(Event.user_hash)).desc())
        .limit(limit)
    )
    return [(row[0], int(row[1])) for row in result.all()]


async def language_split(session: AsyncSession) -> list[tuple[str, int]]:
    result = await session.execute(select(User.language, func.count(User.tg_user_id)).group_by(User.language))
    return [(row[0], int(row[1])) for row in result.all()]


async def blocked_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.tg_user_id)).where(User.is_active.is_(False)))
    return int(result.scalar() or 0)


async def cohort_retention(session: AsyncSession, salt: str, *, cohort_days_ago: int) -> float | None:
    """Share of the NPT-day cohort that was active today (D1 for yesterday, D7 for a week ago).

    Cohort ids are hashed in Python so raw ids never need to be stored in events.
    """
    start, end = npt_day_bounds(cohort_days_ago)
    rows = (
        await session.execute(select(User.tg_user_id).where(User.first_seen_at >= start, User.first_seen_at < end))
    ).all()
    ids = [row[0] for row in rows]
    if not ids:
        return None
    hashes = [hash_user_id(tg_user_id, salt) for tg_user_id in ids]
    active_start, active_end = npt_day_bounds(0)
    result = await session.execute(
        select(func.count(func.distinct(Event.user_hash))).where(
            Event.user_hash.in_(hashes), Event.ts >= active_start, Event.ts < active_end
        )
    )
    return int(result.scalar() or 0) / len(ids)


async def purge_events(session: AsyncSession, retention_days: int) -> int:
    """Delete events older than the retention window; returns the number of rows removed."""
    cutoff = now_utc() - timedelta(days=retention_days)
    result = await session.execute(delete(Event).where(Event.ts < cutoff))
    return int(result.rowcount or 0)


async def last_refresh_times(session: AsyncSession) -> list[tuple[str, datetime | None]]:
    """Newest successful refresh timestamp per source (snapshots or scheduler state)."""
    latest: dict[str, datetime | None] = {}

    snapshots = await session.execute(
        select(Snapshot.source, func.max(Snapshot.fetched_at), func.max(Snapshot.checked_at)).group_by(Snapshot.source)
    )
    for source, fetched_at, checked_at in snapshots.all():
        stamps = [stamp for stamp in (ensure_utc(fetched_at), ensure_utc(checked_at)) if stamp is not None]
        latest[source] = max(stamps) if stamps else None

    states = await session.execute(
        select(SourceState.source, SourceState.last_success_at).where(SourceState.last_success_at.is_not(None))
    )
    for source, last_success_at in states.all():
        success = ensure_utc(last_success_at)
        current = latest.get(source)
        if success is not None and (current is None or success > current):
            latest[source] = success

    return sorted(latest.items())


# ---- Report ----


def _normalise_window(window_days: int | str | None) -> int:
    try:
        days = int(window_days)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 7
    return days if days in (7, 30) else 7


async def build_stats_report(session: AsyncSession, salt: str, window_days: int | str | None = 7) -> str:
    """The admin /stats report (all day boundaries are Nepal Time)."""
    window = _normalise_window(window_days)
    now = now_utc()
    today_start = _today_start_utc()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    window_start = now - timedelta(days=window)

    new_today = await new_users_since(session, today_start)
    new_week = await new_users_since(session, week_ago)
    new_month = await new_users_since(session, month_ago)
    dau = await active_users(session, today_start)
    wau = await active_users(session, week_ago)
    mau = await active_users(session, month_ago)
    requests_today = await count_events(session, since=today_start)
    requests_window = await count_events(session, since=window_start)
    modules = await top_modules(session, window_start)
    sources = await top_sources(session, window_start)
    languages = await language_split(session)
    blocked = await blocked_users(session)
    refreshes = await last_refresh_times(session)
    d1 = await cohort_retention(session, salt, cohort_days_ago=1)
    d7 = await cohort_retention(session, salt, cohort_days_ago=7)

    def pct(value: float | None) -> str:
        return "-" if value is None else f"{round(value * 100)}%"

    lines = [
        "<b>📊 Sajilo Nepal — stats</b>",
        f"<i>{escape(format_npt(now))} NPT</i>",
        "",
        f"👥 New users: {new_today} today · {new_week} (7d) · {new_month} (30d)",
        f"📈 Active: DAU {dau} · WAU {wau} · MAU {mau}",
        f"📨 Requests today: {requests_today} · {window}d: {requests_window}",
    ]
    if modules:
        lines.append("")
        lines.append(f"<b>Top modules ({window}d)</b>")
        lines.extend(f"  {index}. {escape(module)} — {count}" for index, (module, count) in enumerate(modules, start=1))
    if sources:
        lines.append("")
        lines.append(f"<b>Top sources ({window}d)</b>")
        lines.extend(f"  {index}. {escape(source)} — {count} users" for index, (source, count) in enumerate(sources, start=1))
    total_users = sum(count for _lang, count in languages)
    if languages:
        share = " · ".join(
            f"{escape(lang or '-')} {count}" + (f" ({round(count / total_users * 100)}%)" if total_users else "")
            for lang, count in sorted(languages, key=lambda item: item[1], reverse=True)
        )
        lines.append("")
        lines.append(f"🌐 Languages: {share}")
    lines.append(f"🚫 Blocked users: {blocked}")
    lines.append(f"🔁 Retention: D1 {pct(d1)} · D7 {pct(d7)}")
    lines.append("")
    lines.append("<b>Last data refresh</b>")
    if refreshes:
        for source, stamp in refreshes:
            when = f"{format_npt(stamp)} NPT" if stamp is not None else "-"
            lines.append(f"  {escape(source)} — {when}")
    else:
        lines.append("  no data yet")
    return "\n".join(lines)
