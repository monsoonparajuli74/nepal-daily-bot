"""Adapter registry. Swap or add a source here; nothing else needs to change."""

from __future__ import annotations

from app.config import Settings
from app.data.sources.base import SourceAdapter
from app.data.sources.forex import ForexAdapter
from app.data.sources.fuel import FuelAdapter
from app.data.sources.horoscope import HoroscopeAdapter
from app.data.sources.metals import MetalsAdapter
from app.data.sources.news import NewsAdapter
from app.data.sources.veg import VegetablesAdapter
from app.data.sources.weather import WeatherAdapter


def get_adapters(settings: Settings) -> list[SourceAdapter]:
    return [
        ForexAdapter(settings),
        MetalsAdapter(settings),
        FuelAdapter(settings),
        VegetablesAdapter(settings),
        WeatherAdapter(settings),
        NewsAdapter(settings),
        HoroscopeAdapter(settings),
    ]


__all__ = [
    "ForexAdapter",
    "FuelAdapter",
    "HoroscopeAdapter",
    "MetalsAdapter",
    "NewsAdapter",
    "VegetablesAdapter",
    "WeatherAdapter",
    "get_adapters",
]
