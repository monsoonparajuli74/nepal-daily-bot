"""Print the admin analytics report (no message content is ever stored).

Usage::

    python scripts/stats.py
"""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.data.analytics import build_stats_report
from app.db import build_engine, build_session_factory


async def main() -> int:
    settings = get_settings()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        report = await build_stats_report(session, settings.analytics_salt)
    for tag in ("<b>", "</b>", "<i>", "</i>"):
        report = report.replace(tag, "")
    print(report)
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
