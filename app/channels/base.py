"""Channel-agnostic reply model and Channel protocol.

Handlers build a :class:`Reply` (HTML text plus optional inline buttons and a persistent
reply keyboard) and a channel renders it. Handlers must never know whether the transport is
Telegram or anything else, and must never emit platform JSON directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

# ---- Telegram Bot API limits, enforced by the renderer and asserted in tests ----
TEXT_BODY_MAX = 4096  # max characters after entity parsing
CAPTION_MAX = 1024  # max characters in a photo caption
CALLBACK_DATA_MAX = 64  # BYTES, not characters
INLINE_BUTTONS_PER_ROW_MAX = 8
INLINE_BUTTONS_TOTAL_MAX = 100
HOME_GRID_COLUMNS = 3
HOME_GRID_ROWS = 3


@dataclass(frozen=True)
class Btn:
    """An inline button.

    Exactly one of ``action`` (callback_data) or ``url`` (a link) must be set.
    ``action`` is limited to :data:`CALLBACK_DATA_MAX` bytes by the renderer.
    """

    text: str
    action: str | None = None
    url: str | None = None

    def __post_init__(self) -> None:
        if (self.action is None) == (self.url is None):
            raise ValueError("Btn requires exactly one of action or url")

    @property
    def is_url(self) -> bool:
        return self.url is not None


@dataclass
class Reply:
    """One outbound logical message.

    ``inline`` is a list of rows of inline buttons (each row <= 8 buttons, <= 100 total).
    ``reply_keyboard`` is the persistent home keyboard grid (rows of label strings).
    When ``remove_keyboard`` is set the reply keyboard is removed instead of shown.
    ``edit_message`` asks the channel to try an in-place edit of the triggering message,
    falling back to a new message when that is not possible.
    ``photo`` is an optional local image path; the text becomes its caption (and any
    overflow is sent right after as ordinary messages).
    """

    text: str
    inline: list[list[Btn]] | None = None
    reply_keyboard: list[list[str]] | None = None
    remove_keyboard: bool = False
    edit_message: bool = False
    preview: bool = False
    photo: str | None = None

    def inline_buttons(self) -> list[Btn]:
        return [button for row in (self.inline or []) for button in row]


class InboundKind(str, Enum):
    TEXT = "text"
    CALLBACK = "callback"
    MEMBER = "member"
    OTHER = "other"


@dataclass(frozen=True)
class InboundEvent:
    """A normalised inbound update, regardless of channel."""

    user_id: int
    chat_id: int
    display_name: str | None = None
    kind: InboundKind = InboundKind.TEXT
    text: str | None = None
    action: str | None = None
    message_id: int | None = None
    callback_query_id: str | None = None
    update_id: int | None = None
    is_group: bool = False
    is_bot_mentioned: bool = False
    member_status: str | None = None
    timestamp: int | None = None

    @property
    def is_command(self) -> bool:
        return bool(self.text) and self.text.lstrip().startswith("/")

    @property
    def command(self) -> str | None:
        """The bare command word (without a leading slash or ``@bot`` suffix)."""
        if not self.is_command:
            return None
        token = (self.text or "").strip().split()[0]
        token = token[1:]
        return token.split("@", 1)[0].lower() or None

    @property
    def command_args(self) -> list[str]:
        if not self.is_command:
            return []
        return (self.text or "").strip().split()[1:]

    def is_self_service(self) -> bool:
        """In a group we only ever answer commands and explicit bot mentions."""
        if not self.is_group:
            return True
        return self.is_command or self.is_bot_mentioned


class Channel(ABC):
    """A messaging transport. Implementations parse inbound and send Reply objects."""

    name: str

    @abstractmethod
    def verify_secret(self, header: str | None) -> bool:
        """Validate the webhook ``X-Telegram-Bot-Api-Secret-Token`` header."""

    @abstractmethod
    def parse_updates(self, payload: dict[str, Any]) -> list[InboundEvent]:
        """Extract normalised events from a Telegram webhook payload (may be empty)."""

    @abstractmethod
    async def send(
        self,
        chat_id: int,
        reply: Reply,
        *,
        message_id: int | None = None,
        callback_query_id: str | None = None,
    ) -> None:
        """Render and deliver a Reply to ``chat_id``."""

    @abstractmethod
    async def answer_callback(self, callback_query_id: str, text: str | None = None) -> None:
        """Acknowledge a callback query (clears the client spinner). Best effort."""

    @abstractmethod
    async def aclose(self) -> None:
        """Release any held resources."""
