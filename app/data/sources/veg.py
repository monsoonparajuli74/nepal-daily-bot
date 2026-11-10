"""Kalimati Fruits & Vegetable Market Development Board daily prices.

The board's public site exposes a small JSON endpoint (used by its own front end) that
returns every commodity for the latest trading day, in English or Nepali. It is far more
stable than the DataTables HTML page, so that is the only source we rely on.
"""

from __future__ import annotations

import re
from datetime import timedelta

import httpx

from app.config import Settings
from app.data.sources.base import NOT_MODIFIED, HttpFetcher, Snapshot, SourceError
from app.utils.timeutil import now_utc

KALIMATI_API = "https://kalimatimarket.gov.np/api/daily-prices/en"


class VegetablesAdapter:
    name = "vegetables"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.refresh_interval = timedelta(seconds=settings.refresh_vegetables_seconds)
        self.stale_after = timedelta(hours=36)
        self.fetcher = HttpFetcher(settings.user_agent, settings.http_timeout_seconds)

    async def fetch(self, etag: str | None = None, last_modified: str | None = None) -> Snapshot:
        try:
            payload = await self.fetcher.get_json(
                KALIMATI_API,
                etag=etag,
                last_modified=last_modified,
            )
        except httpx.HTTPError as exc:
            raise SourceError(self.name, f"request failed: {exc}") from exc

        if payload is NOT_MODIFIED:
            return Snapshot(source=self.name, payload={}, fetched_at=now_utc(), not_modified=True)
        if not isinstance(payload, dict):
            raise SourceError(self.name, "unexpected Kalimati API response")

        items = parse_vegetable_payload(payload)
        if not items:
            raise SourceError(self.name, "no price rows in Kalimati API response")
        return Snapshot(
            source=self.name,
            payload={"date": payload.get("date"), "items": items},
            fetched_at=now_utc(),
        )


def parse_vegetable_payload(payload: dict) -> list[dict]:
    """Flatten ``{"prices": [...]}`` into the shape handlers expect."""
    items: list[dict] = []
    for row in payload.get("prices") or []:
        if not isinstance(row, dict):
            continue
        name = (row.get("commodityname") or "").strip()
        if not name:
            continue
        items.append(
            {
                "name": name,
                "unit": (row.get("commodityunit") or "KG").strip().lower(),
                "min": _clean_number(row.get("minprice")),
                "max": _clean_number(row.get("maxprice")),
                "avg": _clean_number(row.get("avgprice")),
            }
        )
    return items


def _clean_number(value: object) -> str:
    return re.sub(r"[^0-9.]", "", str(value or ""))
