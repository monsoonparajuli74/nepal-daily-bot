from __future__ import annotations

import httpx
import pytest
import respx

from app.config import Settings
from app.data.sources.base import SourceError
from app.data.sources.forex import NRB_API, ForexAdapter
from app.data.sources.fuel import FUEL_API_URL, FuelAdapter
from app.data.sources.metals import FENEGOSIDA_API, MetalsAdapter

NRB_RESPONSE = {
    "data": {
        "payload": [
            {
                "date": "2026-10-19",
                "published_on": "2026-10-19",
                "rates": [
                    {"currency": {"iso3": "USD", "name": "U.S. Dollar", "unit": 1}, "buy": "133.10", "sell": "133.70"},
                    {"currency": {"iso3": "INR", "name": "Indian Rupee", "unit": 100}, "buy": "160.00", "sell": "160.15"},
                ],
            }
        ]
    }
}

FENEGOSIDA_RESPONSE = [
    {
        "rateType": "छापावाल सुन (१० ग्राम)",
        "todayBaseRatePerGram": 248800,
        "yestardayBaseRatePerGram": 248300,
        "todayDate": "2026-10-19",
    },
    {
        "rateType": "छापावाल सुन (१ तोला)",
        "todayBaseRatePerGram": 290200,
        "yestardayBaseRatePerGram": 289600,
        "todayDate": "2026-10-19",
    },
    {
        "rateType": "असली चाँदी (१ तोला)",
        "todayBaseRatePerGram": 4185,
        "yestardayBaseRatePerGram": 4170,
        "todayDate": "2026-10-19",
    },
]

NEPALI_PATRO_FUEL_RESPONSE = {
    "last_updated_at": "2026-10-12 12:30:05.000000",
    "data": [
        {
            "city": "Kathmandu, Pokhara, Dipayal",
            "detail": [
                {"type": "Petrol(MS)", "currency": "NRs", "price": "200.0", "unit": "L"},
                {"type": "Diesel(HSD)", "currency": "NRs", "price": "200.0", "unit": "L"},
                {"type": "Kerosene(SKO)", "currency": "NRs", "price": "200.0", "unit": "L"},
                {"type": "LP Gas", "currency": "NRs", "price": "2060.0", "unit": "cyl"},
            ],
        }
    ],
}


@pytest.fixture
def settings():
    return Settings(database_url="sqlite+aiosqlite:///:memory:", user_agent="test-agent")


@pytest.mark.asyncio
@respx.mock
async def test_forex_adapter_parses(settings):
    respx.get(NRB_API).mock(return_value=httpx.Response(200, json=NRB_RESPONSE))
    snapshot = await ForexAdapter(settings).fetch()
    rates = snapshot.payload["rates"]
    assert rates["USD"]["buy"] == "133.10"
    assert rates["INR"]["unit"] == 100


@pytest.mark.asyncio
@respx.mock
async def test_metals_adapter_parses(settings):
    respx.get(FENEGOSIDA_API).mock(return_value=httpx.Response(200, json=FENEGOSIDA_RESPONSE))
    snapshot = await MetalsAdapter(settings).fetch()
    assert snapshot.payload["today"]["gold_tola"] == "290200"
    assert snapshot.payload["today"]["silver_tola"] == "4185"
    assert snapshot.payload["effective"] == "2026-10-19"


@pytest.mark.asyncio
@respx.mock
async def test_fuel_adapter_uses_nepali_patro_endpoint(settings):
    route = respx.get(FUEL_API_URL).mock(
        return_value=httpx.Response(200, json=NEPALI_PATRO_FUEL_RESPONSE)
    )
    snapshot = await FuelAdapter(settings).fetch()
    assert route.called
    assert snapshot.payload["city"] == "Kathmandu, Pokhara, Dipayal"
    assert snapshot.payload["prices"]["petrol"] == "200.0"


@pytest.mark.asyncio
@respx.mock
async def test_fuel_adapter_does_not_substitute_prices_when_unavailable(settings):
    respx.get(FUEL_API_URL).mock(return_value=httpx.Response(403))
    with pytest.raises(SourceError, match="Nepali Patro request failed"):
        await FuelAdapter(settings).fetch()
