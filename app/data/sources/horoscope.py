"""Rashifal source: Nepali Patro's public JSON feed (daily, weekly, monthly, yearly).

The site renders its rashifal page client-side and reads this JSON endpoint::

    GET https://nepalipatro.com.np/rashifal/getv5/type/dwmy

Each entry carries its period (``D``/``W``/``M``/``Y``), a Nepali title (the daily one is a
full panchang line) and one paragraph per zodiac sign. When the feed is unreachable the
last good snapshot stays in the cache; a cold start still has the bundled seed fallback.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import Settings
from app.data.models import Horoscope
from app.data.sources.base import NOT_MODIFIED, HttpFetcher, Snapshot, SourceError
from app.utils.timeutil import now_utc, today_npt

logger = logging.getLogger(__name__)

RASHIFAL_URL = "https://nepalipatro.com.np/rashifal/getv5/type/dwmy"

REQUIRED_SIGNS = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)

PERIOD_TYPES = {"D": "d", "W": "w", "M": "m", "Y": "y"}


class HoroscopeAdapter:
    name = "horoscope"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.refresh_interval = timedelta(hours=6)
        self.stale_after = timedelta(days=2)
        self.fetcher = HttpFetcher(settings.user_agent, settings.http_timeout_seconds)

    async def fetch(self, etag: str | None = None, last_modified: str | None = None) -> Snapshot:
        try:
            data = await self.fetcher.get_json(
                RASHIFAL_URL,
                headers={"Accept": "application/json"},
                etag=etag,
                last_modified=last_modified,
                max_attempts=2,
            )
        except httpx.HTTPError as exc:
            raise SourceError(self.name, f"rashifal request failed: {exc}") from exc

        if data is NOT_MODIFIED:
            return Snapshot(source=self.name, payload={}, not_modified=True)

        entries = (data or {}).get("np") if isinstance(data, dict) else None
        if not entries:
            raise SourceError(self.name, "rashifal payload has no entries (schema changed?)")

        periods: dict[str, dict] = {}
        for entry in entries:
            code = PERIOD_TYPES.get(str(entry.get("type", "")).upper())
            if code is None:
                continue
            signs = {slug: _clean(entry.get(slug)) for slug in REQUIRED_SIGNS}
            if not signs["aries"]:
                raise SourceError(self.name, f"period {code} has no readings (schema changed?)")
            periods[code] = {
                "title": _clean(entry.get("title")),
                "author": _clean(entry.get("author")),
                "todate": entry.get("todate") or "",
                "signs": signs,
            }

        if "d" not in periods:
            raise SourceError(self.name, "daily rashifal missing from feed")

        daily = periods["d"]["signs"]
        day = today_npt()
        payload = {
            "date": day.isoformat(),
            "periods": periods,
            "signs": {slug: {"en": daily[slug], "ne": daily[slug]} for slug in REQUIRED_SIGNS},
        }
        return Snapshot(source=self.name, payload=payload, fetched_at=now_utc())

    async def persist(self, session, snapshot: Snapshot) -> None:
        """Write structured rows so handlers (and the digest) can query by sign + date."""
        import datetime as dt  # noqa: PLC0415

        payload = snapshot.payload
        day = dt.date.fromisoformat(payload["date"])
        for slug, texts in payload["signs"].items():
            values = {"sign": slug, "date": day, "text_en": texts["en"], "text_ne": texts["ne"]}
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                stmt = pg_insert(Horoscope).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["sign", "date"],
                    set_={"text_en": values["text_en"], "text_ne": values["text_ne"]},
                )
                await session.execute(stmt)
            else:
                existing = await _find(session, slug, day)
                if existing is None:
                    session.add(Horoscope(**values))
                else:
                    existing.text_en = values["text_en"]
                    existing.text_ne = values["text_ne"]
        await session.flush()


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


async def _find(session, sign: str, day) -> Horoscope | None:
    from sqlalchemy import select

    stmt = select(Horoscope).where(Horoscope.sign == sign, Horoscope.date == day)
    result = await session.execute(stmt)
    return result.scalars().first()
