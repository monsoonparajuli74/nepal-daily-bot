"""Request-scoped context passed to every bot handler.

Handlers never build channel payloads: they format HTML text plus a channel-agnostic Reply
affordance and call ``ctx.reply``. Sending, splitting, analytics and language handling live
here, so a handler is transport-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.i18n import make_translator, normalise_language
from app.channels.base import Channel, InboundEvent, InboundKind, Reply
from app.config import Settings
from app.data.analytics import hash_user_id, track_event
from app.data.models import User


@dataclass
class BotContext:
    session: AsyncSession
    user: User
    settings: Settings
    channel: Channel | None = None
    inbound: InboundEvent | None = None
    language: str = "en"
    actions: list[str] = field(default_factory=list)
    #: True when the current inbound turn is the user's first message in a long time.
    is_returning: bool = False

    def __post_init__(self) -> None:
        self.language = normalise_language(self.language or self.user.language)
        self._t = make_translator(self.language)

    @property
    def tg_id(self) -> int:
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

    async def track(self, event: str) -> None:
        await track_event(self.session, self.tg_id, event, self.settings.analytics_salt)

    def user_hash(self) -> str:
        return hash_user_id(self.tg_id, self.settings.analytics_salt)

    def share_url(self, compact: str) -> str:
        from app.utils.share import share_url

        return share_url(compact, self.settings.bot_username)

    def bot_link(self) -> str:
        return self.settings.bot_link

    @property
    def start_link(self) -> str:
        return self.settings.start_link
