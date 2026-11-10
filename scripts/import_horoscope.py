"""Import authored horoscope content into the database.

Accepts a JSON file shaped like ``app/data/horoscope_seed/default.json``::

    {"signs": {"aries": {"en": "...", "ne": "..."}, ...}}

Usage::

    python scripts/import_horoscope.py path/to/file.json 2083-10-20
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date

from app.config import get_settings
from app.data.models import Horoscope
from app.db import build_engine, build_session_factory, init_models


async def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_horoscope.py <file.json> [YYYY-MM-DD]")
        return 1
    path = sys.argv[1]
    day = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()

    with open(path, encoding="utf-8") as handle:
        content = json.load(handle)
    signs = content.get("signs") or {}

    settings = get_settings()
    engine = build_engine(settings)
    await init_models(engine)
    session_factory = build_session_factory(engine)
    inserted = 0
    async with session_factory() as session:
        for slug, texts in signs.items():
            session.add(
                Horoscope(sign=slug, date=day, text_en=texts.get("en", ""), text_ne=texts.get("ne", ""))
            )
            inserted += 1
        await session.commit()
    await engine.dispose()
    print(f"Imported {inserted} horoscope readings for {day.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
