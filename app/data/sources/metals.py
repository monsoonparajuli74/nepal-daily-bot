"""FENEGOSIDA (Federation of Nepal Gold and Silver Dealers' Association) daily rates.

Uses the association's public JSON API (verified 2026)::

    GET https://api.fenegosida.org/api/website/v1/Dashboard/today

Returns four rows: hallmark gold per 10g, hallmark gold per tola, silver per 10g and
silver per tola. Values are NPR. Tejabi gold is not exposed by the API; the field is
only included when a future payload provides it.
"""

from __future__ import annotations

import re
from datetime import timedelta

from app.config import Settings
from app.data.sources.base import NOT_MODIFIED, HttpFetcher, Snapshot, SourceError
from app.utils.timeutil import now_utc

FENEGOSIDA_API = "https://api.fenegosida.org/api/website/v1/Dashboard/today"

_GOLD_10G = "10"
_TOLA = "तोला"


def _classify(rate_type: str) -> tuple[str, str] | None:
    text = rate_type or ""
    if "सुन" in text:
        commodity = "gold"
    elif "चाँदी" in text:
        commodity = "silver"
    else:
        return None
    unit = "10g" if "10" in text or "१०" in text else "tola"
    return commodity, unit


class MetalsAdapter:
    name = "metals"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.refresh_interval = timedelta(seconds=settings.refresh_metals_seconds)
        self.stale_after = timedelta(hours=36)
        self.fetcher = HttpFetcher(settings.user_agent, settings.http_timeout_seconds)

    async def fetch(self, etag: str | None = None, last_modified: str | None = None) -> Snapshot:
        data = await self.fetcher.get_json(FENEGOSIDA_API, etag=etag, last_modified=last_modified)
        if data is NOT_MODIFIED:
            return Snapshot(source=self.name, payload={}, not_modified=True)
        if not isinstance(data, list) or not data:
            raise SourceError(self.name, "unexpected FENEGOSIDA payload (schema changed?)")

        today: dict[str, str] = {}
        yesterday: dict[str, str] = {}
        effective = None
        for row in data:
            if not isinstance(row, dict):
                continue
            classified = _classify(str(row.get("rateType", "")))
            if classified is None:
                continue
            commodity, unit = classified
            key = "gold_10g" if (commodity, unit) == ("gold", "10g") else (
                "gold_tola" if commodity == "gold" else (
                    "silver_10g" if unit == "10g" else "silver_tola"
                )
            )
            today_value = row.get("todayBaseRatePerGram")
            yesterday_value = row.get("yestardayBaseRatePerGram")
            if today_value is None:
                continue
            today[key] = str(today_value)
            if yesterday_value is not None:
                yesterday[key] = str(yesterday_value)
            if effective is None and row.get("todayDate"):
                effective = row["todayDate"]

        if "gold_tola" not in today or "silver_tola" not in today:
            raise SourceError(self.name, "gold/silver rows not found (schema changed?)")

        payload = {
            "effective": effective,
            "today": today,
            "yesterday": yesterday,
        }
        return Snapshot(source=self.name, payload=payload, fetched_at=now_utc())


def parse_number(value: str) -> float | None:
    """Parse a numeric cell, tolerating thousand separators."""
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(value))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None
