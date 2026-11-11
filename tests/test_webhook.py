"""End-to-end webhook: post Telegram updates, assert the bot responded."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.channels.telegram.client import TelegramChannel
from app.data.analytics import drain_tracked_events
from app.data.models import Event, User
from app.main import create_app
from tests.conftest import FakeTelegramChannel, ensure_user, make_settings, seed_snapshot

USER = 15550001111
OTHER = 15550002222


def _message(update_id: int, text: str, *, user_id: int = USER, chat_id: int = USER, chat_type: str = "private"):
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": 1_700_000_000,
            "chat": {"id": chat_id, "type": chat_type},
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "text": text,
        },
    }


def _callback(update_id: int, data: str, *, user_id: int = USER, chat_id: int = USER):
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb-{update_id}",
            "chat_instance": "1",
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "data": data,
            "message": {
                "message_id": update_id,
                "date": 1_700_000_000,
                "chat": {"id": chat_id, "type": "private"},
            },
        },
    }


async def _post(client, payload):
    return await client.post("/telegram/webhook", json=payload)


async def test_start_sends_welcome_and_keyboard(client, app):
    response = await _post(client, _message(1, "/start"))
    assert response.status_code == 200
    fake: FakeTelegramChannel = app.state.fake_channel
    assert fake.sent, "no reply sent"
    reply = fake.last()["reply"]
    assert reply.reply_keyboard is not None
    assert len(reply.reply_keyboard) == 3


async def test_callback_shows_gold_screen(client, app, session_factory):
    async with session_factory() as session:
        await seed_snapshot(session, "metals", {"today": {"gold_tola": 120000}}, ok=True)
        await session.commit()
    response = await _post(client, _callback(10, "mt:t"))
    assert response.status_code == 200
    fake: FakeTelegramChannel = app.state.fake_channel
    assert "gold" in fake.last_text().lower() or "सुन" in fake.last_text()


async def test_more_news_callback_shows_next_five_headlines(client, app, session_factory):
    items = [
        {"title": f"Headline {index}", "source": "Test News", "link": f"https://example.test/{index}"}
        for index in range(1, 11)
    ]
    async with session_factory() as session:
        await seed_snapshot(session, "news", {"en": items}, ok=True)
        await session.commit()

    await ensure_user(session_factory, USER, language="en")
    await _post(client, _callback(11, "nw:l"))
    fake: FakeTelegramChannel = app.state.fake_channel
    first_reply = fake.last()["reply"]
    more_news_button = first_reply.inline[0][0]
    assert len(first_reply.inline[0]) == 2
    assert more_news_button.text == "More News"
    assert more_news_button.action == "nw:l1"
    assert first_reply.inline[0][1].action == "nav:home"
    assert "Headline 1" in first_reply.text
    assert "Headline 5" in first_reply.text
    assert "Headline 6" not in first_reply.text

    await _post(client, _callback(12, more_news_button.action))
    second_reply = fake.last()["reply"]
    assert "Headline 6" in second_reply.text
    assert "Headline 10" in second_reply.text
    assert "Headline 5" not in second_reply.text
    assert all(button.text != "More News" for button in second_reply.inline_buttons())


async def test_media_message_gets_hint(client, app):
    payload = {
        "update_id": 20,
        "message": {
            "message_id": 20,
            "date": 1_700_000_000,
            "chat": {"id": USER, "type": "private"},
            "from": {"id": USER, "is_bot": False, "first_name": "Test"},
            "photo": [{"file_id": "abc", "file_unique_id": "u", "width": 1, "height": 1}],
        },
    }
    await _post(client, payload)
    fake: FakeTelegramChannel = app.state.fake_channel
    assert fake.sent


async def test_group_ignores_plain_chatter(client, app):
    await _post(client, _message(30, "hello everyone", user_id=OTHER, chat_id=-100500, chat_type="supergroup"))
    fake: FakeTelegramChannel = app.state.fake_channel
    assert fake.sent == []


async def test_group_command_gets_answer(client, app):
    await _post(client, _message(31, "/menu", user_id=OTHER, chat_id=-100501, chat_type="supergroup"))
    fake: FakeTelegramChannel = app.state.fake_channel
    assert fake.sent


async def test_stop_deactivates_user(client, app, session_factory):
    await _post(client, _message(40, "/stop"))
    async with session_factory() as session:
        user = await session.get(User, USER)
        assert user is not None and user.is_active is False


async def test_deletedata_removes_user(client, app, session_factory):
    await _post(client, _message(41, "/start"))
    await _post(client, _message(42, "/deletedata"))
    async with session_factory() as session:
        user = await session.get(User, USER)
        assert user is None


async def test_language_command_switches(client, app, session_factory):
    await _post(client, _message(50, "भाषा"))
    async with session_factory() as session:
        user = await session.get(User, USER)
        assert user is not None and user.language == "en"


async def test_dedupe_ignores_repeated_update_id(client, app):
    first = await _post(client, _message(60, "/menu"))
    assert first.status_code == 200
    fake: FakeTelegramChannel = app.state.fake_channel
    count = len(fake.sent)
    await _post(client, _message(60, "/menu"))
    assert len(fake.sent) == count


def test_verify_secret_enforced(tmp_path):
    settings = make_settings(tmp_path / "sec.db", telegram_webhook_secret="s3cret")
    channel = TelegramChannel(settings)
    assert channel.verify_secret("s3cret") is True
    assert channel.verify_secret("wrong") is False
    assert channel.verify_secret(None) is False


def test_verify_secret_open_when_unset(tmp_path):
    settings = make_settings(tmp_path / "open.db", telegram_webhook_secret="")
    channel = TelegramChannel(settings)
    assert channel.verify_secret(None) is True


@pytest.mark.parametrize("command", ["/menu", "menu", "मेनु"])
async def test_commands_are_answered(client, app, command):
    await _post(client, _message(abs(hash((command, "x"))) % 100000, command))
    fake: FakeTelegramChannel = app.state.fake_channel
    assert fake.sent


async def test_start_records_start_event_with_deep_link_source(client, app, session_factory):
    await _post(client, _message(70, "/start share_weather"))
    await drain_tracked_events()
    async with session_factory() as session:
        rows = (await session.execute(select(Event))).scalars().all()
    starts = [row for row in rows if row.event == "start"]
    assert len(starts) == 1
    assert starts[0].source == "share_weather"


async def test_stop_then_message_records_unblocked(client, app, session_factory):
    await _post(client, _message(72, "/stop"))
    await _post(client, _message(73, "menu"))
    await drain_tracked_events()
    async with session_factory() as session:
        user = await session.get(User, USER)
        assert user is not None and user.is_active is True
        rows = (await session.execute(select(Event))).scalars().all()
    events = {(row.event, row.module) for row in rows}
    assert ("opt_out", None) in events
    assert ("unblocked", None) in events
    assert ("menu_open", "home") in events


async def test_share_button_callback_returns_picker_link(client, app, session_factory):
    async with session_factory() as session:
        await seed_snapshot(session, "metals", {"today": {"gold_tola": 120000}}, ok=True)
        await session.commit()
    await ensure_user(session_factory, USER)

    await _post(client, _callback(74, "mt:t"))
    fake: FakeTelegramChannel = app.state.fake_channel
    share_button = fake.last()["reply"].inline[0][0]
    assert share_button.action.startswith("share:")

    await _post(client, _callback(75, share_button.action))
    followup = fake.last()["reply"]
    assert "Share" in followup.text
    picker = followup.inline[0][0]
    assert picker.url is not None
    assert picker.url.startswith("https://t.me/share/url")
    assert "share_metals" in picker.url

    await drain_tracked_events()
    async with session_factory() as session:
        rows = (await session.execute(select(Event))).scalars().all()
    taps = [row for row in rows if row.event == "share_tap"]
    assert taps and taps[0].module == "metals"


async def test_stats_command_answers_only_the_admin(tmp_path):
    settings = make_settings(tmp_path / "admin.db", admin_telegram_id=USER)
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        fake = FakeTelegramChannel(settings)
        application.state.channel = fake
        application.state.processor.channel = fake
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await _post(client, _message(76, "/stats", user_id=OTHER))
            assert fake.sent == []

            await _post(client, _message(77, "/stats"))
            assert "New users" in fake.last_text()
            assert "Requests today" in fake.last_text()

            await _post(client, _message(78, "/stats 30"))
            assert "30d:" in fake.last_text()
        await drain_tracked_events()


async def test_stats_command_is_silent_in_group_chats_even_for_admin(tmp_path):
    settings = make_settings(tmp_path / "admin-group.db", admin_telegram_id=USER)
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        fake = FakeTelegramChannel(settings)
        application.state.channel = fake
        application.state.processor.channel = fake
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await _post(client, _message(79, "/stats", chat_id=-100502, chat_type="supergroup"))
            assert fake.sent == []
        await drain_tracked_events()


async def test_stats_command_supports_a_comma_separated_admin_list(tmp_path):
    settings = make_settings(tmp_path / "admin-list.db", admin_telegram_id=f"{USER}, {OTHER}")
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        fake = FakeTelegramChannel(settings)
        application.state.channel = fake
        application.state.processor.channel = fake
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await _post(client, _message(80, "/stats", user_id=OTHER))
            assert "New users" in fake.last_text()
        await drain_tracked_events()
