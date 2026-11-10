"""Render a channel-agnostic :class:`Reply` into Telegram Bot API method objects.

This is the single place that knows Telegram's limits. It never raises on oversized content
from a handler in production: it clips button labels, drops excess buttons with a warning,
splits long bodies on paragraph boundaries and keeps multi-part sends in order.
"""

from __future__ import annotations

import logging

from aiogram.methods import EditMessageText, SendMessage, SendPhoto
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LinkPreviewOptions,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app.channels.base import (
    CALLBACK_DATA_MAX,
    CAPTION_MAX,
    INLINE_BUTTONS_PER_ROW_MAX,
    INLINE_BUTTONS_TOTAL_MAX,
    TEXT_BODY_MAX,
    Reply,
)

logger = logging.getLogger(__name__)

PARSE_MODE = "HTML"
INPUT_PLACEHOLDER = "Choose an option / विकल्प छान्नुहोस्"


def split_text(text: str, limit: int = TEXT_BODY_MAX) -> list[str]:
    """Split text on paragraph boundaries so no chunk exceeds ``limit`` chars."""
    text = text or ""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(paragraph) > limit:
            chunks.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        current = paragraph
    if current:
        chunks.append(current)
    return chunks or [""]


def _clip_callback(action: str) -> str:
    encoded = action.encode("utf-8")
    if len(encoded) <= CALLBACK_DATA_MAX:
        return action
    logger.warning("callback_data_too_long", extra={"bytes": len(encoded)})
    clipped = encoded[:CALLBACK_DATA_MAX]
    while clipped:
        try:
            return clipped.decode("utf-8")
        except UnicodeDecodeError:
            clipped = clipped[:-1]
    return ""


def inline_markup(reply: Reply) -> InlineKeyboardMarkup | None:
    if not reply.inline:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    total = 0
    for row in reply.inline:
        buttons: list[InlineKeyboardButton] = []
        for button in row[:INLINE_BUTTONS_PER_ROW_MAX]:
            if total >= INLINE_BUTTONS_TOTAL_MAX:
                logger.warning("inline_buttons_truncated")
                break
            if button.url:
                buttons.append(InlineKeyboardButton(text=button.text, url=button.url))
            else:
                buttons.append(
                    InlineKeyboardButton(
                        text=button.text,
                        callback_data=_clip_callback(button.action or ""),
                    )
                )
            total += 1
        if buttons:
            rows.append(buttons)
        if total >= INLINE_BUTTONS_TOTAL_MAX:
            break
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def reply_markup(reply: Reply) -> ReplyKeyboardMarkup | ReplyKeyboardRemove | None:
    if reply.remove_keyboard:
        return ReplyKeyboardRemove()
    if reply.reply_keyboard:
        keyboard = [[KeyboardButton(text=label) for label in row if label] for row in reply.reply_keyboard]
        keyboard = [row for row in keyboard if row]
        if keyboard:
            return ReplyKeyboardMarkup(
                keyboard=keyboard,
                is_persistent=True,
                resize_keyboard=True,
                input_field_placeholder=INPUT_PLACEHOLDER,
            )
    return None


def _markup(reply: Reply):
    inline = inline_markup(reply)
    keyboard = reply_markup(reply)
    if inline is not None and keyboard is not None:
        # Telegram allows only one reply_markup per message; inline wins for flow screens.
        logger.warning("reply_has_inline_and_keyboard")
        return inline
    return inline if inline is not None else keyboard


def _link_preview(reply: Reply) -> LinkPreviewOptions:
    return LinkPreviewOptions(is_disabled=not reply.preview)


def _caption_and_rest(text: str) -> tuple[str, str]:
    """Split a body so the first part fits a Telegram caption (1024 chars)."""
    if len(text) <= CAPTION_MAX:
        return text, ""
    cut = text.rfind("\n\n", 0, CAPTION_MAX)
    if cut <= CAPTION_MAX * 0.5:
        cut = CAPTION_MAX
    return text[:cut], text[cut:].lstrip("\n")


def _render_photo(
    reply: Reply,
    chat_id: int,
    text: str,
    markup,
) -> list[SendPhoto | SendMessage]:
    """Send the artwork with the text as caption, then any overflow as normal messages."""
    caption, rest = _caption_and_rest(text)
    rest_chunks = split_text(rest) if rest.strip() else []
    photo_markup = markup if not rest_chunks else None
    methods: list[SendPhoto | SendMessage] = [
        SendPhoto(
            chat_id=chat_id,
            photo=FSInputFile(reply.photo or ""),
            caption=caption or None,
            parse_mode=PARSE_MODE,
            reply_markup=photo_markup,
        )
    ]
    for index, chunk in enumerate(rest_chunks):
        attach = markup if index == len(rest_chunks) - 1 else None
        methods.append(
            SendMessage(
                chat_id=chat_id,
                text=chunk,
                parse_mode=PARSE_MODE,
                link_preview_options=_link_preview(reply),
                reply_markup=attach,
            )
        )
    return methods


def render(
    reply: Reply,
    chat_id: int,
    *,
    message_id: int | None = None,
) -> list[SendMessage | EditMessageText | SendPhoto]:
    """Convert a Reply into one or more Bot API method objects, in order."""
    text = reply.text or ""
    markup = _markup(reply)
    if not text.strip() and markup is None:
        return []

    if reply.photo:
        return _render_photo(reply, chat_id, text, markup)

    chunks = split_text(text)
    methods: list[SendMessage | EditMessageText] = []
    for index, chunk in enumerate(chunks):
        is_last = index == len(chunks) - 1
        attach = markup if is_last else None
        if index == 0 and reply.edit_message and message_id is not None:
            methods.append(
                EditMessageText(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=chunk,
                    parse_mode=PARSE_MODE,
                    link_preview_options=_link_preview(reply),
                    reply_markup=attach,
                )
            )
        else:
            methods.append(
                SendMessage(
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode=PARSE_MODE,
                    link_preview_options=_link_preview(reply),
                    reply_markup=attach,
                )
            )
    return methods
