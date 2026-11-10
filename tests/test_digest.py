from __future__ import annotations

from app.data.digest import send_digests
from app.data.models import User
from tests.conftest import ensure_user, seed_snapshot


async def test_morning_briefing_sends_five_headlines_to_active_users_not_opted_out(
    app,
    session_factory,
    settings,
):
    opted_in_user = 15550003111
    opted_out_user = 15550003112
    inactive_user = 15550003113
    await ensure_user(session_factory, opted_in_user, language="en")
    await ensure_user(session_factory, opted_out_user, language="en")
    await ensure_user(session_factory, inactive_user, language="en")

    async with session_factory() as session:
        opted_out = await session.get(User, opted_out_user)
        inactive = await session.get(User, inactive_user)
        assert opted_out is not None
        assert inactive is not None
        opted_out.daily_briefing_opt_out = True
        inactive.is_active = False
        await seed_snapshot(
            session,
            "news",
            {
                "en": [
                    {"title": f"Headline {index}", "source": "Test News", "link": f"https://example.test/{index}"}
                    for index in range(1, 7)
                ]
            },
        )
        await seed_snapshot(
            session,
            "forex",
            {"date": "2026-11-04", "rates": {"USD": {"buy": "133.1", "sell": "133.7"}}},
        )
        await seed_snapshot(
            session,
            "metals",
            {"effective": "2026-11-04", "today": {"gold_tola": "290200", "silver_tola": "4185"}},
        )
        await seed_snapshot(
            session,
            "vegetables",
            {"items": [{"name": "Tomato", "avg": "95.50", "unit": "kg"}]},
        )
        await seed_snapshot(
            session,
            "fuel",
            {
                "effective": "2026-08-02",
                "city": "Kathmandu, Pokhara, Dipayal",
                "prices": {"petrol": "200.00", "diesel": "200.00"},
            },
        )
        await seed_snapshot(
            session,
            "weather",
            {
                "cities": {
                    "kathmandu": {"low": 10, "high": 20, "rain": 15},
                }
            },
        )
        await session.commit()

    fake = app.state.fake_channel
    assert await send_digests(settings, session_factory, fake) == 1
    assert len(fake.sent) == 1
    assert fake.sent[0]["chat_id"] == opted_in_user
    message = fake.last_text()
    assert "Headline 1" in message
    assert "Headline 5" in message
    assert "Headline 6" not in message
    assert "USD/NRB" in message
    assert "Gold" in message
    assert "Kalimati" in message
    assert "Fuel (Nepali Patro)" in message
    assert "Kathmandu today" in message
    assert "NEPSE data source is configured" in message
