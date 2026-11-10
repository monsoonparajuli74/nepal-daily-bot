"""Time helpers. Nepal Time is UTC+5:45 with no daylight saving."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

NPT = timezone(timedelta(hours=5, minutes=45))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_npt() -> datetime:
    return datetime.now(NPT)


def today_npt() -> date:
    return now_npt().date()


def to_npt(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(NPT)


def format_npt(value: datetime, fmt: str = "%d %b %Y, %I:%M %p") -> str:
    return to_npt(value).strftime(fmt)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
