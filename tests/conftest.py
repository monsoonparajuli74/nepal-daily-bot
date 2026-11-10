"""Shared pytest fixtures: temp database, settings and an app with a fake Telegram channel."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.channels.base import Reply
from app.channels.telegram.client import TelegramChannel
from app.config import Settings
from app.data.models import Snapshot, User
from app.db import build_engine, build_session_factory, init_models
from app.main import create_app
from app.utils.timeutil import now_utc

TEST_TOKEN = "123456789:AAHtesttoken_abcdefghijklmnopqrstuvwxyz0"


def make_settings(db_path: Path, **overrides) -> Settings:
    base: dict = {
        "telegram_bot_token": TEST_TOKEN,
        "telegram_webhook_secret": "",
        "telegram_mode": "webhook",
        "telegram_setup_on_startup": False,
        "bot_username": "everydaynepal_test_bot",
        "public_base_url": "https://example.test",
        "database_url": f"sqlite+aiosqlite:///{db_path.as_posix()}",
        "auto_create_tables": True,
        "scheduler_enabled": False,
        "refresh_on_startup": False,
        "data_dir": "app/data",
        "analytics_salt": "test-salt",
        "rate_limit_per_minute": 1000,
        "group_rate_limit_per_minute": 1000,
    }
    base.update(overrides)
    return Settings(**base)


class FakeTelegramChannel(TelegramChannel):
    """Captures outbound Replies instead of calling the Bot API.

    Parsing/verification are inherited from the real channel; only delivery is stubbed.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.sent: list[dict] = []
        self.callbacks: list[str] = []

    async def send(
        self,
        chat_id: int,
        reply: Reply,
        *,
        message_id: int | None = None,
        callback_query_id: str | None = None,
    ) -> None:
        self.sent.append({"chat_id": chat_id, "reply": reply, "message_id": message_id})

    async def answer_callback(self, callback_query_id: str, text: str | None = None) -> None:
        self.callbacks.append(callback_query_id)

    async def aclose(self) -> None:
        await self.bot.session.close()

    def last(self) -> dict:
        return self.sent[-1]

    def last_text(self) -> str:
        return self.sent[-1]["reply"].text if self.sent else ""

    def texts(self) -> list[str]:
        return [entry["reply"].text for entry in self.sent]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path / "test.db")


@pytest_asyncio.fixture
async def session_factory(settings: Settings):
    engine = build_engine(settings)
    await init_models(engine)
    factory = build_session_factory(engine)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def app(settings: Settings):
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        fake = FakeTelegramChannel(settings)
        application.state.channel = fake
        application.state.processor.channel = fake
        application.state.fake_channel = fake
        yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def seed_snapshot(session, source: str, payload: dict, *, ok: bool = True) -> Snapshot:
    row = Snapshot(
        source=source,
        payload=payload,
        fetched_at=now_utc(),
        checked_at=now_utc(),
        content_hash="test",
        ok=ok,
    )
    session.add(row)
    await session.flush()
    return row


async def ensure_user(factory, tg_user_id: int = 15550001111, *, language: str = "en") -> None:
    """Pre-create a user so the first inbound message isn't treated as first contact."""
    async with factory() as db_session:
        if await db_session.get(User, tg_user_id) is None:
            now = now_utc()
            db_session.add(
                User(
                    tg_user_id=tg_user_id,
                    name="Test",
                    language=language,
                    is_active=True,
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )
            await db_session.commit()
