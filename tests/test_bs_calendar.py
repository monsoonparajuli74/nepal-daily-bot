from __future__ import annotations

from datetime import date

from app.utils.bs_calendar import ad_to_bs, bs_to_ad, format_bs


def test_anchor_point():
    assert bs_to_ad(2000, 1, 1) == date(1943, 4, 14)


def test_known_conversion():
    assert bs_to_ad(2081, 1, 1) == date(2024, 4, 13)


def test_round_trip_within_range():
    for ad in (date(2024, 4, 13), date(2026, 10, 19), date(2030, 1, 1)):
        bs = ad_to_bs(ad)
        assert bs_to_ad(bs.year, bs.month, bs.day) == ad


def test_spec_example():
    bs = ad_to_bs(date(2026, 10, 19))
    assert (bs.year, bs.month, bs.day) == (2083, 7, 2)


def test_format_bs_english():
    bs = ad_to_bs(date(2026, 10, 19))
    assert "2083" in format_bs(bs, "en")
