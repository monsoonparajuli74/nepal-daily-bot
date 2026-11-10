"""Nepali Patro fuel prices for the Kathmandu region."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from httpx import HTTPError

from app.config import Settings
from app.data.sources.base import HttpFetcher, Snapshot, SourceError, extract_validators
from app.utils.timeutil import now_utc

logger = logging.getLogger(__name__)

FUEL_API_URL = "https://api.nepalipatro.com.np/api/noc/public/prices?lang=en"


class FuelAdapter:
    name = "fuel"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.refresh_interval = timedelta(seconds=settings.refresh_fuel_seconds)
        self.stale_after = timedelta(days=3)
        self.fetcher = HttpFetcher(settings.user_agent, settings.http_timeout_seconds)

    async def fetch(self, etag: str | None = None, last_modified: str | None = None) -> Snapshot:
        try:
            response = await self.fetcher.get(
                FUEL_API_URL,
                etag=etag,
                last_modified=last_modified,
                accept="application/json",
            )
            if response.status_code == 304:
                return Snapshot(source=self.name, payload={}, not_modified=True)
            try:
                payload = parse_nepali_patro_payload(response.json())
            except ValueError as exc:
                raise SourceError(self.name, "Nepali Patro returned invalid JSON") from exc
        except SourceError as exc:
            logger.warning("fuel_source_failed", extra={"error": exc.message})
            raise
        except HTTPError as exc:
            logger.warning("fuel_source_unreachable", extra={"error": str(exc)})
            raise SourceError(self.name, f"Nepali Patro request failed: {exc}") from exc

        etag_value, last_modified_value = extract_validators(response)
        return Snapshot(
            source=self.name,
            payload=payload,
            fetched_at=now_utc(),
            etag=etag_value,
            last_modified=last_modified_value,
        )


def parse_nepali_patro_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise SourceError("fuel", "Nepali Patro returned an unexpected response")

    updated_at = data.get("last_updated_at")
    if not isinstance(updated_at, str) or not updated_at.strip():
        raise SourceError("fuel", "Nepali Patro response is missing its update date")
    try:
        effective = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exc:
        raise SourceError("fuel", "Nepali Patro returned an invalid update date") from exc

    regions = data.get("data")
    if not isinstance(regions, list):
        raise SourceError("fuel", "Nepali Patro response is missing regional prices")

    for region in regions:
        if not isinstance(region, dict):
            continue
        city = region.get("city")
        if not isinstance(city, str) or "kathmandu" not in city.casefold():
            continue

        detail = region.get("detail")
        if not isinstance(detail, list):
            continue
        prices: dict[str, str] = {}
        for item in detail:
            if not isinstance(item, dict):
                continue
            label = str(item.get("type", "")).strip().casefold()
            key = next(
                (
                    name
                    for prefix, name in (
                        ("petrol", "petrol"),
                        ("diesel", "diesel"),
                        ("kerosene", "kerosene"),
                        ("lp gas", "lpg"),
                        ("lpg", "lpg"),
                    )
                    if label.startswith(prefix)
                ),
                None,
            )
            if key is None:
                continue
            currency = str(item.get("currency", "")).strip().casefold()
            unit = str(item.get("unit", "")).strip().casefold()
            expected_units = {"cyl", "cylinder"} if key == "lpg" else {"l", "litre", "liter"}
            if currency not in {"nrs", "rs", "npr"} or unit not in expected_units:
                continue

            raw_price = item.get("price")
            try:
                price = Decimal(str(raw_price))
            except (InvalidOperation, ValueError):
                continue
            if price.is_finite() and price > 0:
                prices[key] = str(raw_price)

        required_prices = {"petrol", "diesel", "kerosene", "lpg"}
        if required_prices.issubset(prices):
            return {
                "effective": effective,
                "city": city,
                "prices": prices,
            }

    raise SourceError("fuel", "Nepali Patro response has no complete Kathmandu price list")
