"""Simple in-process per-user rate limiter (sliding window).

Deliberately in-memory: it protects a single process from a chatty client. If we later
run multiple workers, move this behind a shared store.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, per_minute: int, window_seconds: int = 60) -> None:
        self.per_minute = max(1, per_minute)
        self.window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._events[key]
        while bucket and (now - bucket[0]) > self.window:
            bucket.popleft()
        if len(bucket) >= self.per_minute:
            return False
        bucket.append(now)
        return True
