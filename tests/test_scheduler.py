from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.data.scheduler import build_scheduler
from app.main import _digest_trigger


@dataclass
class FakeAdapter:
    name: str
    refresh_interval: timedelta = timedelta(minutes=30)
    stale_after: timedelta = timedelta(hours=3)

    async def fetch(self, etag=None, last_modified=None):
        raise NotImplementedError


def _cron_fields(scheduler, source: str) -> dict[str, str]:
    job = scheduler.get_job(f"refresh:{source}")
    assert job is not None
    assert isinstance(job.trigger, CronTrigger)
    return {field.name: str(field) for field in job.trigger.fields}


def test_daily_refreshes_use_configured_nepal_times():
    settings = Settings(
        refresh_vegetables_hour_npt=5,
        refresh_vegetables_minute_npt=30,
        refresh_fuel_hour_npt=6,
        refresh_metals_hour_npt=10,
        refresh_metals_minute_npt=30,
        refresh_forex_hour_npt=11,
        refresh_forex_minute_npt=15,
    )
    scheduler = build_scheduler(
        settings,
        object(),
        [
            FakeAdapter("vegetables"),
            FakeAdapter("fuel"),
            FakeAdapter("metals"),
            FakeAdapter("forex"),
            FakeAdapter("horoscope"),
        ],
    )

    for source, expected in {
        "vegetables": ("5", "30"),
        "fuel": ("6", "0"),
        "metals": ("10", "30"),
        "forex": ("11", "15"),
        "horoscope": ("5", "0"),
    }.items():
        fields = _cron_fields(scheduler, source)
        assert (fields["hour"], fields["minute"]) == expected


def test_news_refreshes_every_two_nepal_time_hours():
    scheduler = build_scheduler(Settings(refresh_news_hours=2), object(), [FakeAdapter("news")])
    fields = _cron_fields(scheduler, "news")
    assert fields["hour"] == "*/2"
    assert fields["minute"] == "0"


def test_daily_briefing_runs_at_seven_in_nepal_time():
    trigger = _digest_trigger("07:00")
    fields = {field.name: str(field) for field in trigger.fields}
    assert (fields["hour"], fields["minute"]) == ("7", "0")
    assert str(trigger.timezone) == "Asia/Kathmandu"
