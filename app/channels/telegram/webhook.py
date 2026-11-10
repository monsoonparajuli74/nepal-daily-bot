"""Telegram inbound transports: the FastAPI webhook route and a long-polling loop.

Both feed the same :class:`Processor`, so behaviour is identical in production (webhook) and
local development (polling, which needs no public URL).
"""

from __future__ import annotations

import asyncio
import logging

from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import GetUpdates
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.channels.telegram.client import TelegramChannel
from app.channels.telegram.commands import ALLOWED_UPDATES
from app.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter()

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> JSONResponse:
    channel: TelegramChannel = request.app.state.channel
    processor = request.app.state.processor

    if not channel.verify_secret(request.headers.get(SECRET_HEADER)):
        raise HTTPException(status_code=403, detail="invalid secret")

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 - malformed body
        logger.warning("webhook_body_invalid")
        return JSONResponse({"ok": True})

    for event in channel.parse_updates(payload):
        await processor.handle(event)
    return JSONResponse({"ok": True})


async def poll_forever(channel: TelegramChannel, processor, settings: Settings) -> None:
    """Long-poll ``getUpdates`` and dispatch, with backoff on transient errors."""
    bot = channel.bot
    offset: int | None = None
    backoff = 1.0
    logger.info("polling_started", extra={"timeout": settings.telegram_poll_timeout})

    while True:
        try:
            updates = await bot(
                GetUpdates(offset=offset, timeout=settings.telegram_poll_timeout, allowed_updates=ALLOWED_UPDATES)
            )
            backoff = 1.0
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            continue
        except asyncio.CancelledError:  # pragma: no cover - shutdown
            return
        except Exception as exc:  # noqa: BLE001 - polling must never die silently
            logger.warning(
                "polling_transient_error",
                extra={"error": str(exc), "kind": type(exc).__name__, "backoff": backoff},
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
            continue

        for update in updates:
            offset = update.update_id + 1
            event = channel.event_from_update(update)
            if event is None:
                continue
            try:
                await processor.handle(event)
            except Exception:  # noqa: BLE001 - one update must not stop polling
                logger.exception("poll_dispatch_failed")
