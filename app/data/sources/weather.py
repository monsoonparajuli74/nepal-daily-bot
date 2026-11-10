"""Open-Meteo weather and air-quality adapter (free, no API key).

Verified 2026::

    https://api.open-meteo.com/v1/forecast
    https://air-quality-api.open-meteo.com/v1/air-quality

One snapshot holds every configured city so a tap never triggers a network call.
"""

from __future__ import annotations

from datetime import timedelta

from app.config import Settings
from app.data.config_loader import city_list
from app.data.sources.base import NOT_MODIFIED, HttpFetcher, Snapshot, SourceError
from app.utils.timeutil import now_utc

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


class WeatherAdapter:
    name = "weather"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.refresh_interval = timedelta(seconds=settings.refresh_weather_seconds)
        self.stale_after = timedelta(hours=3)
        self.fetcher = HttpFetcher(settings.user_agent, settings.http_timeout_seconds)

    async def fetch(self, etag: str | None = None, last_modified: str | None = None) -> Snapshot:
        cities = city_list(self.settings.data_dir)
        results: dict[str, dict] = {}
        errors: list[str] = []

        for key, city in cities.items():
            try:
                record = await self._fetch_city(city.lat, city.lon)
            except SourceError as exc:
                errors.append(f"{key}: {exc.message}")
                continue
            results[key] = record

        if not results:
            raise SourceError(self.name, "all city fetches failed: " + "; ".join(errors))

        return Snapshot(source=self.name, payload={"cities": results}, fetched_at=now_utc())

    async def _fetch_city(self, lat: float, lon: float) -> dict:
        forecast_params = {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m,wind_direction_10m,is_day"
            ),
            "daily": (
                "temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
                "sunrise,sunset,uv_index_max"
            ),
            "timezone": "Asia/Kathmandu",
            "forecast_days": 1,
        }
        aqi_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "us_aqi,pm2_5",
            "timezone": "Asia/Kathmandu",
        }

        forecast = await self.fetcher.get_json(FORECAST_URL, params=forecast_params)
        if forecast is NOT_MODIFIED:
            raise SourceError(self.name, "unexpected 304 for forecast request")
        if not isinstance(forecast, dict) or "current" not in forecast:
            raise SourceError(self.name, "forecast payload missing current (schema changed?)")

        aqi = None
        pm25 = None
        try:
            aqi_data = await self.fetcher.get_json(AQI_URL, params=aqi_params)
            if isinstance(aqi_data, dict):
                aqi_current = aqi_data.get("current") or {}
                aqi = aqi_current.get("us_aqi")
                pm25 = aqi_current.get("pm2_5")
        except Exception:  # noqa: BLE001 - AQI is optional, weather still shows
            aqi = None

        current = forecast.get("current") or {}
        daily = forecast.get("daily") or {}
        highs = daily.get("temperature_2m_max") or [None]
        lows = daily.get("temperature_2m_min") or [None]
        rains = daily.get("precipitation_probability_max") or [None]
        sunrises = daily.get("sunrise") or [None]
        sunsets = daily.get("sunset") or [None]
        uvs = daily.get("uv_index_max") or [None]

        return {
            "temp": current.get("temperature_2m"),
            "feels": current.get("apparent_temperature"),
            "code": current.get("weather_code"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "wind": current.get("wind_speed_10m"),
            "wind_dir": current.get("wind_direction_10m"),
            "is_day": current.get("is_day"),
            "high": highs[0] if highs else None,
            "low": lows[0] if lows else None,
            "rain": rains[0] if rains else None,
            "uv": uvs[0] if uvs else None,
            "sunrise": sunrises[0] if sunrises else None,
            "sunset": sunsets[0] if sunsets else None,
            "aqi": aqi,
            "pm25": pm25,
            "observed_at": current.get("time"),
        }
