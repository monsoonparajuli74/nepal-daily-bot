"""RSS news adapter. Headlines and links only - never article bodies (publisher copyright)."""

from __future__ import annotations

import logging
from datetime import timedelta

import feedparser
import httpx

from app.config import Settings
from app.data.config_loader import load_news_feeds
from app.data.sources.base import HttpFetcher, Snapshot, SourceError
from app.utils.timeutil import now_utc

logger = logging.getLogger(__name__)

MAX_PER_FEED = 8
MAX_PER_LANGUAGE = 12


def _interleave(groups: list[list[dict]]) -> list[dict]:
    """Round-robin across feeds so one prolific outlet cannot fill every slot."""
    merged: list[dict] = []
    depth = max((len(group) for group in groups), default=0)
    for index in range(depth):
        for group in groups:
            if index < len(group):
                merged.append(group[index])
    return merged[:MAX_PER_LANGUAGE]


class NewsAdapter:
    name = "news"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.refresh_interval = timedelta(hours=settings.refresh_news_hours)
        self.stale_after = timedelta(hours=3)
        self.fetcher = HttpFetcher(settings.user_agent, settings.http_timeout_seconds)

    async def fetch(self, etag: str | None = None, last_modified: str | None = None) -> Snapshot:
        feeds_by_lang = load_news_feeds(self.settings.data_dir)
        payload: dict[str, list[dict]] = {"en": [], "ne": []}
        failures = 0
        total_feeds = 0

        for lang, feeds in feeds_by_lang.items():
            groups: list[list[dict]] = []
            for feed in feeds:
                total_feeds += 1
                try:
                    items = await self._fetch_feed(feed["url"], feed["source"])
                except Exception as exc:  # noqa: BLE001 - one bad feed must not kill news
                    failures += 1
                    logger.warning("news_feed_failed", extra={"url": feed["url"], "error": str(exc)})
                    continue
                groups.append(items)
            payload[lang] = _interleave(groups)[:MAX_PER_LANGUAGE]

        if total_feeds and failures == total_feeds:
            raise SourceError(self.name, "every news feed failed")

        return Snapshot(source=self.name, payload=payload, fetched_at=now_utc())

    async def _fetch_feed(self, url: str, source: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": self.settings.user_agent})
            response.raise_for_status()
            parsed = feedparser.parse(response.content)

        if getattr(parsed, "bozo", 0) and not parsed.entries:
            raise SourceError(self.name, f"unparseable feed: {url}")

        items: list[dict] = []
        for entry in parsed.entries[:MAX_PER_FEED]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue
            items.append({"title": title, "link": link, "source": source})
        return items
