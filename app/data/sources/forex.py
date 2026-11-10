"""Nepal Rastra Bank official exchange rates.

Uses the public JSON API (verified 2026)::

    GET https://www.nrb.org.np/api/forex/v1/rates?page=1&per_page=100&from=YYYY-MM-DD&to=YYYY-MM-DD

The API quotes some currencies per 10 or 100 units (INR, JPY, KRW); the quoted unit is
stored alongside each rate so the formatter and calculator stay correct.
"""

from __future__ import annotations

from datetime import timedelta

from app.config import Settings
from app.data.sources.base import HttpFetcher, Snapshot, SourceError
from app.utils.timeutil import now_utc, today_npt

NRB_API = "https://www.nrb.org.np/api/forex/v1/rates"

#: Key remittance corridors first, then the remaining traded currencies.
KEY_CURRENCIES = ("USD", "AED", "SAR", "QAR", "MYR", "KWD", "OMR", "BHD")
OTHER_CURRENCIES = (
    "GBP",
    "EUR",
    "AUD",
    "CAD",
    "CHF",
    "CNY",
    "INR",
    "JPY",
    "KRW",
    "SGD",
)
ALL_CURRENCIES = KEY_CURRENCIES + OTHER_CURRENCIES

FLAGS: dict[str, str] = {
    "USD": "🇺🇸",
    "AED": "🇦🇪",
    "SAR": "🇸🇦",
    "QAR": "🇶🇦",
    "MYR": "🇲🇾",
    "KWD": "🇰🇼",
    "OMR": "🇴🇲",
    "BHD": "🇧🇭",
    "GBP": "🇬🇧",
    "EUR": "🇪🇺",
    "AUD": "🇦🇺",
    "CAD": "🇨🇦",
    "CHF": "🇨🇭",
    "CNY": "🇨🇳",
    "HKD": "🇭🇰",
    "INR": "🇮🇳",
    "JPY": "🇯🇵",
    "KRW": "🇰🇷",
    "SGD": "🇸🇬",
    "THB": "🇹🇭",
    "DKK": "🇩🇰",
    "SEK": "🇸🇪",
    "NPR": "🇳🇵",
}


def flag(code: str) -> str:
    return FLAGS.get(code.upper(), "🏳️")


class ForexAdapter:
    name = "forex"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.refresh_interval = timedelta(seconds=settings.refresh_forex_seconds)
        self.stale_after = timedelta(hours=36)
        self.fetcher = HttpFetcher(settings.user_agent, settings.http_timeout_seconds)

    async def fetch(self, etag: str | None = None, last_modified: str | None = None) -> Snapshot:
        today = today_npt()
        start = today - timedelta(days=7)
        params = {"page": 1, "per_page": 100, "from": start.isoformat(), "to": today.isoformat()}

        data = await self.fetcher.get_json(NRB_API, params=params, etag=etag, last_modified=last_modified)
        from app.data.sources.base import NOT_MODIFIED

        if data is NOT_MODIFIED:
            return Snapshot(source=self.name, payload={}, not_modified=True)

        payloads = (data or {}).get("data", {}).get("payload") or []
        if not payloads:
            raise SourceError(self.name, "NRB API returned no payloads")

        # Take the most recent published set.
        latest = sorted(payloads, key=lambda item: item.get("date", ""))[-1]
        rates_src = latest.get("rates") or []
        if not rates_src:
            raise SourceError(self.name, "NRB payload has no rates (schema changed?)")

        rates: dict[str, dict[str, str | int]] = {}
        for entry in rates_src:
            currency = entry.get("currency") or {}
            iso3 = currency.get("iso3")
            buy = entry.get("buy")
            sell = entry.get("sell")
            if not iso3 or buy is None or sell is None:
                raise SourceError(self.name, "rate entry missing fields (schema changed?)")
            rates[str(iso3).upper()] = {
                "name": currency.get("name") or iso3,
                "unit": int(currency.get("unit") or 1),
                "buy": str(buy),
                "sell": str(sell),
            }

        snapshot_payload = {
            "date": latest.get("date"),
            "published_on": latest.get("published_on"),
            "rates": rates,
        }
        return Snapshot(source=self.name, payload=snapshot_payload, fetched_at=now_utc())
