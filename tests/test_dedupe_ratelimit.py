"""Update-id dedupe and the in-process rate limiter."""

from __future__ import annotations

from app.bot.ratelimit import RateLimiter
from app.data.dedupe import Deduper, purge_updates


async def test_deduper_ignores_replays(session_factory):
    deduper = Deduper(session_factory)
    assert await deduper.register(10) is True
    assert await deduper.register(10) is False
    assert await deduper.register(9) is False  # below the high-water mark
    assert await deduper.register(11) is True


async def test_deduper_without_id_always_processes(session_factory):
    deduper = Deduper(session_factory)
    assert await deduper.register(None) is True
    assert await deduper.register(None) is True


async def test_purge_updates_removes_old_records(session, session_factory):
    deduper = Deduper(session_factory)
    await deduper.register(1)
    removed = await purge_updates(session, ttl_hours=0)
    assert removed >= 1


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(per_minute=2, window_seconds=60)
    assert limiter.allow("u") is True
    assert limiter.allow("u") is True
    assert limiter.allow("u") is False
    assert limiter.allow("other") is True
