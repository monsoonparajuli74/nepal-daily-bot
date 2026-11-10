"""Loaders for the small, hand-editable configuration files under ``app/data``.

Keeping these as plain JSON means the operator can change the curated vegetable list,
add cities, festivals or horoscope content without touching code.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.utils.bs_calendar import BSDateError, bs_to_ad

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class City:
    key: str
    label_en: str
    label_ne: str
    lat: float
    lon: float

    def label(self, lang: str) -> str:
        return self.label_ne if lang == "ne" else self.label_en


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache
def load_vegetables(data_dir: str | None = None) -> dict:
    base = Path(data_dir) if data_dir else DATA_DIR
    return _read_json(base / "config" / "vegetables.json")


@lru_cache
def load_cities(data_dir: str | None = None) -> dict:
    base = Path(data_dir) if data_dir else DATA_DIR
    return _read_json(base / "config" / "cities.json")


def city_list(data_dir: str | None = None) -> dict[str, City]:
    raw = load_cities(data_dir)
    cities: dict[str, City] = {}
    for key, value in raw.items():
        if key == "terai":
            continue
        cities[key] = City(
            key=key,
            label_en=value["label_en"],
            label_ne=value["label_ne"],
            lat=float(value["lat"]),
            lon=float(value["lon"]),
        )
    return cities


def terai_keys(data_dir: str | None = None) -> list[str]:
    raw = load_cities(data_dir)
    return list(raw.get("terai", []))


@lru_cache
def load_news_feeds(data_dir: str | None = None) -> dict:
    base = Path(data_dir) if data_dir else DATA_DIR
    return _read_json(base / "config" / "news_feeds.json")


@lru_cache
def load_horoscope_seed(data_dir: str | None = None) -> dict:
    base = Path(data_dir) if data_dir else DATA_DIR
    default_file = base / "horoscope_seed" / "default.json"
    return _read_json(default_file)


@lru_cache
def load_horoscope_periods(data_dir: str | None = None) -> dict:
    """Monthly + yearly readings: ``{"monthly": {slug: {"en", "ne"}}, "yearly": {...}}``."""
    base = Path(data_dir) if data_dir else DATA_DIR
    return _read_json(base / "horoscope_seed" / "periods.json")


def load_festivals(data_dir: str | None = None) -> list[dict]:
    """Load and normalise every ``festivals_<BS year>.json`` file."""
    base = Path(data_dir) if data_dir else DATA_DIR
    festivals: list[dict] = []
    for path in sorted(base.glob("festivals_*.json")):
        try:
            entries = _read_json(path)
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - operator error
            logger.error("festival_file_invalid", extra={"path": str(path), "error": str(exc)})
            continue
        for entry in entries:
            normalised = dict(entry)
            if not normalised.get("ad_date"):
                try:
                    ad = bs_to_ad(
                        int(normalised["bs_year"]),
                        int(normalised["bs_month"]),
                        int(normalised["bs_day"]),
                    )
                    normalised["ad_date"] = ad.isoformat()
                except (KeyError, ValueError, BSDateError):
                    logger.warning("festival_entry_invalid", extra={"entry": entry, "path": str(path)})
                    continue
            festivals.append(normalised)
    festivals.sort(key=lambda item: item["ad_date"])
    return festivals


def reload_all() -> None:
    load_vegetables.cache_clear()
    load_cities.cache_clear()
    load_horoscope_seed.cache_clear()
    load_horoscope_periods.cache_clear()
    load_news_feeds.cache_clear()
