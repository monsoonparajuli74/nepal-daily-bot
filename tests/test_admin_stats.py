"""Admin /stats handler: builds its report on a fresh session and replies."""

from __future__ import annotations

from app.bot.context import BotContext
from app.bot.handlers import admin
from app.channels.base import InboundEvent, InboundKind
from app.data import analytics
from app.data.models import Event, User
from app.utils.timeutil import now_utc

ADMIN_ID = 15550009999


async def test_stats_handler_replies_on_a_fresh_session(app):
    settings = app.state.settings
    settings.admin_telegram_id = str(ADMIN_ID)
    factory = app.state.session_factory
    fake = app.state.fake_channel

    async with factory() as session:
        now = now_utc()
        user = User(tg_user_id=ADMIN_ID, language="en", is_active=True, first_seen_at=now, last_seen_at=now)
        session.add(user)
        session.add(
            Event(
                user_hash=analytics.hash_user_id(ADMIN_ID, settings.analytics_salt),
                event="view",
                module="weather",
                ts=now,
            )
        )
        await session.commit()

        inbound = InboundEvent(
            user_id=ADMIN_ID,
            chat_id=ADMIN_ID,
            kind=InboundKind.TEXT,
            text="/stats",
            update_id=1,
        )
        ctx = BotContext(
            session=session,
            user=user,
            settings=settings,
            channel=fake,
            inbound=inbound,
            session_factory=factory,
        )

        # The handler must not depend on this session: close it before the call.
        await session.close()
        await admin.stats(ctx)

    assert fake.sent
    report = fake.last_text()
    assert "New users" in report
    assert "Requests today" in report
    assert "weather — 1" in report
    assert str(ADMIN_ID) not in report
