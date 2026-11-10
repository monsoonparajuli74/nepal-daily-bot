"""Print simple analytics for the last 7 days (no message content is ever stored).

Usage::

    python scripts/stats.py [days]
"""

from __future__ import annotations

import asyncio
import sys

from app.config import get_settings
from app.data.analytics import daily_active_users, event_counts
from app.db import build_engine, build_session_factory


async def main() -> int:
    settings = get_settings()
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        counts = await event_counts(session, days)
        dau = await daily_active_users(session, days)

    print(f"Sajilo Nepal - last {days} days\n")
    print("Daily active users:")
    for day, users in dau:
        print(f"  {day}: {users}")
    print("\nEvents:")
    for event, count in counts:
        print(f"  {event}: {count}")
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
