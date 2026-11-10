"""Telegram Bot API channel: inbound update parsing, rendering and delivery.

Uses aiogram's ``Bot`` (with our httpx-backed session) as the API client. Sends go through a
tiny per-chat queue so multi-part replies arrive in order while different chats are handled
concurrently.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Update

from app.channels.base import Channel, InboundEvent, InboundKind, Reply
from app.channels.telegram.renderer import PARSE_MODE, render
from app.channels.telegram.session import HttpxSession
from app.config import Settings

logger = logging.getLogger(__name__)

MEMBER_LEFT = {"kicked", "left"}
MEMBER_JOINED = {"member", "administrator", "creator"}
GROUP_CHAT_TYPES = {"group", "supergroup"}

BlockedCallback = Callable[[int], Awaitable[None]]


class TelegramChannel(Channel):
    name = "telegram"

    def __init__(
        self,
        settings: Settings,
        *,
        bot: Bot | None = None,
        http_client=None,
        on_blocked: BlockedCallback | None = None,
    ) -> None:
        self.settings = settings
        self.on_blocked = on_blocked
        if bot is not None:
            self._bot = bot
            self._owns_bot = False
        else:
            session = HttpxSession(client=http_client, timeout=settings.http_timeout_seconds)
            self._bot = Bot(
                token=settings.telegram_bot_token,
                session=session,
                default=DefaultBotProperties(parse_mode=PARSE_MODE),
            )
            self._owns_bot = True
        self._queues: dict[int, asyncio.Queue] = {}
        self._workers: dict[int, asyncio.Task] = {}

    @property
    def bot(self) -> Bot:
        return self._bot

    # ---- Channel protocol ----

    def verify_secret(self, header: str | None) -> bool:
        secret = self.settings.telegram_webhook_secret
        if not secret:
            # No secret configured: accept (local dev / tests). Production must set one.
            return True
        if not header:
            return False
        return hmac.compare_digest(header, secret)

    def parse_updates(self, payload: dict[str, Any]) -> list[InboundEvent]:
        try:
            update = Update.model_validate(payload)
        except Exception:  # noqa: BLE001 - malformed/unknown update
            logger.warning("telegram_update_malformed")
            return []
        event = self.event_from_update(update)
        return [event] if event is not None else []

    def event_from_update(self, update: Update) -> InboundEvent | None:
        if update.message is not None:
            return self._from_message(update)
        if update.callback_query is not None:
            return self._from_callback(update)
        if update.my_chat_member is not None:
            return self._from_member(update)
        return None

    def _from_message(self, update: Update) -> InboundEvent | None:
        message = update.message
        chat = message.chat
        user = message.from_user or chat
        is_group = chat.type in GROUP_CHAT_TYPES
        if message.text is not None:
            kind = InboundKind.TEXT
            text: str | None = message.text
        else:
            kind = InboundKind.OTHER
            text = None
        return InboundEvent(
            user_id=user.id,
            chat_id=chat.id,
            display_name=getattr(user, "full_name", None),
            kind=kind,
            text=text,
            message_id=message.message_id,
            update_id=update.update_id,
            is_group=is_group,
            is_bot_mentioned=self._mentions_bot(message.text),
            timestamp=int(message.date.timestamp()) if message.date else None,
        )

    def _from_callback(self, update: Update) -> InboundEvent | None:
        query = update.callback_query
        if query is None or query.from_user is None:
            return None
        chat = query.message.chat if query.message is not None else None
        chat_id = chat.id if chat is not None else query.from_user.id
        is_group = bool(chat is not None and chat.type in GROUP_CHAT_TYPES)
        return InboundEvent(
            user_id=query.from_user.id,
            chat_id=chat_id,
            display_name=getattr(query.from_user, "full_name", None),
            kind=InboundKind.CALLBACK,
            action=query.data,
            message_id=query.message.message_id if query.message is not None else None,
            callback_query_id=query.id,
            update_id=update.update_id,
            is_group=is_group,
        )

    def _from_member(self, update: Update) -> InboundEvent | None:
        change = update.my_chat_member
        if change is None:
            return None
        status = getattr(change.new_chat_member, "status", None)
        member_status = "left" if status in MEMBER_LEFT else "member" if status in MEMBER_JOINED else "other"
        return InboundEvent(
            user_id=change.from_user.id,
            chat_id=change.chat.id,
            display_name=getattr(change.from_user, "full_name", None),
            kind=InboundKind.MEMBER,
            update_id=update.update_id,
            is_group=change.chat.type in GROUP_CHAT_TYPES,
            member_status=member_status,
        )

    def _mentions_bot(self, text: str | None) -> bool:
        username = self.settings.bot_username
        if not text or not username:
            return False
        return f"@{username.lower()}" in text.lower()

    async def send(
        self,
        chat_id: int,
        reply: Reply,
        *,
        message_id: int | None = None,
        callback_query_id: str | None = None,
    ) -> None:
        methods = render(reply, chat_id, message_id=message_id)
        if not methods:
            return
        await self._enqueue(chat_id, methods)

    async def answer_callback(self, callback_query_id: str, text: str | None = None) -> None:
        from aiogram.methods import AnswerCallbackQuery

        try:
            await self._bot(AnswerCallbackQuery(callback_query_id=callback_query_id, text=text))
        except Exception:  # noqa: BLE001 - acknowledging is best effort
            logger.debug("answer_callback_failed")

    async def aclose(self) -> None:
        for task in self._workers.values():
            task.cancel()
        self._workers.clear()
        self._queues.clear()
        if self._owns_bot:
            await self._bot.session.close()

    # ---- Per-chat ordering queue ----

    async def _enqueue(self, chat_id: int, methods: list) -> None:
        queue = self._queues.get(chat_id)
        if queue is None:
            queue = asyncio.Queue()
            self._queues[chat_id] = queue
            self._workers[chat_id] = asyncio.create_task(self._drain(chat_id, queue))
        done = asyncio.get_event_loop().create_future()
        await queue.put((methods, done))
        await done

    async def _drain(self, chat_id: int, queue: asyncio.Queue) -> None:
        try:
            while True:
                methods, done = await queue.get()
                try:
                    for method in methods:
                        await self._execute(method)
                    if not done.done():
                        done.set_result(True)
                except Exception as exc:  # noqa: BLE001 - never let the worker die
                    logger.exception("telegram_send_failed", extra={"chat": chat_id})
                    if not done.done():
                        done.set_exception(exc)
                finally:
                    queue.task_done()
        except asyncio.CancelledError:  # pragma: no cover - shutdown
            return

    async def _execute(self, method, *, attempt: int = 0) -> None:
        try:
            await self._bot(method)
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            await self._execute(method, attempt=attempt)
        except TelegramForbiddenError:
            chat_id = getattr(method, "chat_id", None)
            logger.warning("telegram_forbidden", extra={"chat": chat_id})
            await self._handle_blocked(chat_id)
        except TelegramBadRequest as exc:
            if isinstance(method, EditMessageText):
                await self._handle_edit_failure(method, exc)
                return
            logger.warning("telegram_bad_request", extra={"error": str(exc)})
        except (TelegramServerError, TelegramNetworkError) as exc:
            if attempt < 3:
                await asyncio.sleep(2**attempt)
                await self._execute(method, attempt=attempt + 1)
            else:
                logger.error("telegram_send_giving_up", extra={"error": str(exc)})

    async def _handle_edit_failure(self, method: EditMessageText, exc: TelegramBadRequest) -> None:
        if "not modified" in str(exc).lower():
            return
        logger.info("telegram_edit_fallback")
        fallback = SendMessage(
            chat_id=method.chat_id,
            text=method.text,
            parse_mode=method.parse_mode or PARSE_MODE,
            link_preview_options=method.link_preview_options,
            reply_markup=method.reply_markup,
        )
        await self._execute(fallback)

    async def _handle_blocked(self, chat_id: int | None) -> None:
        if chat_id is None or self.on_blocked is None:
            return
        try:
            await self.on_blocked(int(chat_id))
        except Exception:  # noqa: BLE001 - deactivation must never break the worker
            logger.exception("blocked_callback_failed")
