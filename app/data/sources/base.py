"""Common interfaces for data source adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol, runtime_checkable

import httpx

from app.utils.timeutil import now_utc

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class SourceError(RuntimeError):
    """Raised when a source cannot be fetched or its payload schema changed."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"[{source}] {message}")
        self.source = source
        self.message = message


@dataclass
class Snapshot:
    """The frozen output of a source fetch."""

    source: str
    payload: dict[str, Any]
    fetched_at: datetime = field(default_factory=now_utc)
    ok: bool = True
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


@runtime_checkable
class SourceAdapter(Protocol):
    name: str
    refresh_interval: timedelta
    stale_after: timedelta

    async def fetch(self, etag: str | None = None, last_modified: str | None = None) -> Snapshot:
        """Fetch the source. Raises SourceError on failure."""

    async def persist(self, session, snapshot: Snapshot) -> None:  # pragma: no cover - optional hook
        """Optional hook to persist structured rows beyond the generic snapshot."""
        return None


class HttpFetcher:
    """Polite HTTP client wrapper: descriptive UA, timeout, retries with backoff.

    Supports conditional requests via ETag / If-Modified-Since. Returns 304 sentinels so
    adapters can tell the cache "nothing changed".
    """

    def __init__(self, user_agent: str, timeout: float = 10.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
        accept: str | None = None,
        max_attempts: int = 3,
    ) -> httpx.Response:
        request_headers = {"User-Agent": self.user_agent}
        if accept:
            request_headers["Accept"] = accept
        if headers:
            request_headers.update(headers)
        if etag:
            request_headers["If-None-Match"] = etag
        if last_modified:
            request_headers["If-Modified-Since"] = last_modified

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, verify=False) as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(url, headers=request_headers, params=params)
                    if response.status_code == 304:
                        return response
                    if response.status_code in RETRYABLE_STATUS and attempt < max_attempts - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    response.raise_for_status()
                    return response
                except (httpx.HTTPError, httpx.TimeoutException) as exc:
                    last_error = exc
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2**attempt)
                        continue
            raise httpx.HTTPError(str(last_error) if last_error else "request failed")

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        response = await self.get(url, accept="application/json", **kwargs)
        if response.status_code == 304:
            return NOT_MODIFIED
        return response.json()

    async def get_text(self, url: str, **kwargs: Any) -> str | None:
        response = await self.get(url, **kwargs)
        if response.status_code == 304:
            return None
        return response.text


class _NotModified:
    pass


NOT_MODIFIED = _NotModified()


def conditional_headers(etag: str | None, last_modified: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return headers


def extract_validators(response: httpx.Response) -> tuple[str | None, str | None]:
    return response.headers.get("ETag"), response.headers.get("Last-Modified")
