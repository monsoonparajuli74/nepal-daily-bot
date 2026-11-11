"""Request-scoped context passed to every bot handler.

Handlers never build channel payloads: they format HTML text plus a channel-agnostic Reply
affordance and call ``ctx.reply``. Sending, splitting, analytics and language handling live
here, so a handler is transport-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.i18n import make_translator, normalise_language
from app.channels.base import Channel, InboundEvent, InboundKind, Reply
from app.config import Settings
from app.data.analytics import hash_user_id, track_event_async
from app.data.models import User

logger = logging.getLogger(__name__)


@dataclass
class BotContext:
    session: AsyncSession
    user: User
    settings: Settings
    channel: Channel | None = None
    inbound: InboundEvent | None = None
    language: str = "en"
    actions: list[str] = field(default_factory=list)
    #: True when the current inbound turn is the user's first message in a long while.
    is_returning: bool = False
    #: Session factory for fire-and-forget analytics (optional; see ``track``).
    session_factory: async_sessionmaker[AsyncSession] | None = None

    def __post_init__(self) -> None:
        self.language = normalise_language(self.language or self.user.language)
        self._t = make_translator(self.language)

    @property
    def tg_id(self) -> int:
        # Prefer the immutable inbound id: ORM attributes may be expired after rollback.
        if self.inbound is not None:
            return self.inbound.user_id
        return self.user.tg_user_id

    @property
    def chat_id(self) -> int:
        return self.inbound.chat_id if self.inbound is not None else self.user.tg_user_id

    @property
    def is_group(self) -> bool:
        return bool(self.inbound and self.inbound.is_group)

    @property
    def t(self):
        return self._t

    def set_language(self, language: str) -> None:
        self.language = normalise_language(language)
        self._t = make_translator(self.language)

    async def reply(
        self,
        text: str,
        *,
        inline: list[list] | None = None,
        reply_keyboard: list[list[str]] | None = None,
        remove_keyboard: bool = False,
        edit: bool = False,
        preview: bool = False,
    ) -> None:
        """Send a reply through the active channel (text is split if too long)."""
        if self.channel is None:
            return
        reply = Reply(
            text=text,
            inline=inline,
            reply_keyboard=reply_keyboard,
            remove_keyboard=remove_keyboard,
            edit_message=edit,
            preview=preview,
        )
        await self.send(reply)

    async def send(self, reply: Reply) -> None:
        if self.channel is None:
            return
        # Only a callback turn has a bot-owned message we may edit in place.
        message_id = (
            self.inbound.message_id
            if self.inbound is not None and self.inbound.kind is InboundKind.CALLBACK
            else None
        )
        await self.channel.send(
            self.chat_id,
            reply,
            message_id=message_id,
            callback_query_id=self.inbound.callback_query_id if self.inbound else None,
        )

    def track(self, event: str, *, module: str | None = None, source: str | None = None) -> None:
        """Record an analytics event without ever slowing or breaking this reply.

        Writes happen in the background on their own session; failures are logged, never
        raised. The interface language at the time is stored as ``lang``.
        """
        if self.session_factory is None:
            logger.debug("analytics_skipped_no_session_factory", extra={"event": event})
            return
        track_event_async(
            self.session_factory,
            self.settings.analytics_salt,
            self.tg_id,
            event,
            module=module,
            lang=self.language,
            source=source,
        )

    def user_hash(self) -> str:
        return hash_user_id(self.tg_id, self.settings.analytics_salt)

    def bot_link(self) -> str:
        return self.settings.bot_link

    @property
    def start_link(self) -> str:
        return self.settings.start_link
