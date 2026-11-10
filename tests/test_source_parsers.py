from __future__ import annotations

import pytest

from app.data.sources.base import SourceError
from app.data.sources.fuel import parse_nepali_patro_payload
from app.data.sources.metals import _classify
from app.data.sources.veg import parse_vegetable_payload

FUEL_API = {
    "last_updated_at": "2026-10-12 12:30:05.000000",
    "data": [
        {
            "city": "Charali, Biratnagar",
            "detail": [
                {"type": "Petrol(MS)", "currency": "NRs", "price": "197.5", "unit": "L"},
            ],
        },
        {
            "city": "Kathmandu, Pokhara, Dipayal",
            "detail": [
                {"type": "Petrol(MS)", "currency": "NRs", "price": "200.0", "unit": "L"},
                {"type": "Diesel(HSD)", "currency": "NRs", "price": "200.0", "unit": "L"},
                {"type": "Kerosene(SKO)", "currency": "NRs", "price": "200.0", "unit": "L"},
                {"type": "LP Gas", "currency": "NRs", "price": "2060.0", "unit": "cyl"},
            ],
        },
    ],
}

VEG_API = {
    "status": 200,
    "date": "2026-10-19",
    "prices": [
        {
            "commodityname": "Tomato Small(Local)",
            "commodityunit": "KG",
            "minprice": "70.00",
            "maxprice": "85.00",
            "avgprice": "77.00",
        },
        {
            "commodityname": "Potato Red(Long)",
            "commodityunit": "KG",
            "minprice": "55.00",
            "maxprice": "60.00",
            "avgprice": "57.50",
        },
    ],
}


def test_parse_nepali_patro_fuel_payload():
    payload = parse_nepali_patro_payload(FUEL_API)
    assert payload["effective"] == "2026-10-12"
    assert payload["city"] == "Kathmandu, Pokhara, Dipayal"
    assert payload["prices"]["petrol"] == "200.0"
    assert payload["prices"]["lpg"] == "2060.0"


def test_parse_nepali_patro_fuel_payload_rejects_incomplete_prices():
    incomplete = {
        "last_updated_at": "2026-10-12 12:30:05.000000",
        "data": [{"city": "Kathmandu", "detail": [{"type": "Petrol(MS)", "price": "200.0"}]}],
    }
    with pytest.raises(SourceError, match="complete Kathmandu price list"):
        parse_nepali_patro_payload(incomplete)


def test_parse_nepali_patro_fuel_payload_rejects_missing_update_date():
    with pytest.raises(SourceError, match="missing its update date"):
        parse_nepali_patro_payload({"data": FUEL_API["data"]})


def test_parse_vegetable_payload():
    items = parse_vegetable_payload(VEG_API)
    assert len(items) == 2
    assert items[0]["name"] == "Tomato Small(Local)"
    assert items[0]["avg"] == "77.00"
    assert items[0]["unit"] == "kg"


def test_metals_classify():
    assert _classify("छापावाल सुन (१० ग्राम)") == ("gold", "10g")
    assert _classify("छापावाल सुन (१ तोला)") == ("gold", "tola")
    assert _classify("असली चाँदी (१ तोला)") == ("silver", "tola")
    assert _classify("unknown") is None
