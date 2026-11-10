"""HttpxSession: per-method timeouts and multipart uploads (artwork delivery)."""

from __future__ import annotations

import httpx
import pytest
import respx
from aiogram import Bot
from aiogram.types import FSInputFile

from app.channels.telegram.session import HttpxSession

TOKEN = "1:AAtest"
API = f"https://api.telegram.org/bot{TOKEN}/getUpdates"


def _bot(session: HttpxSession) -> Bot:
    return Bot(token=TOKEN, session=session, default=None)


def test_get_updates_timeout_outlives_global_timeout():
    session = HttpxSession(timeout=10)
    get_updates = type("M", (), {"__api_method__": "getUpdates", "timeout": 30})()
    send_message = type("M", (), {"__api_method__": "sendMessage"})()
    assert session._request_timeout(get_updates, None) == 45
    assert session._request_timeout(send_message, None) == 10
    assert session._request_timeout(send_message, 7) == 7


@respx.mock
@pytest.mark.asyncio
async def test_get_updates_request_allows_the_full_long_poll():
    session = HttpxSession(timeout=10)
    route = respx.post(API).mock(
        return_value=httpx.Response(200, json={"ok": True, "result": []})
    )

    from aiogram.methods import GetUpdates

    await _bot(session)(GetUpdates(timeout=30))
    request = route.calls[0].request
    assert request.extensions["timeout"]["read"] == 45
    await session.close()


@respx.mock
@pytest.mark.asyncio
async def test_photo_upload_uses_multipart_form_data(tmp_path):
    image = tmp_path / "welcome.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    route = respx.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "result": {"message_id": 1, "date": 0, "chat": {"id": 5, "type": "private"}},
            },
        )
    )
    session = HttpxSession(timeout=10)
    bot = _bot(session)
    await bot.send_photo(chat_id=5, photo=FSInputFile(image), caption="hi")
    request = route.calls[0].request
    assert request.headers["content-type"].startswith("multipart/form-data")
    body = await request.aread()
    assert b'name="caption"' in body
    assert b'name="photo"' in body
    assert b'filename="welcome.png"' in body
    await session.close()
