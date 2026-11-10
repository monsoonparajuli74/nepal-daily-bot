"""An aiogram ``BaseSession`` backed by httpx.

aiogram's default session uses aiohttp; the rest of this codebase (and its tests) already
speak httpx/respx. This thin adapter lets us keep aiogram as the Bot API client and type
layer while every request still goes through a single ``httpx.AsyncClient`` — which respx
can intercept in tests.

JSON methods are posted as JSON; methods carrying an ``InputFile`` (profile and welcome
photos) fall back to ``multipart/form-data`` with ``attach://`` references resolved.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod


class HttpxSession(BaseSession):
    def __init__(self, client: httpx.AsyncClient | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client = client
        self._owns_client = client is None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
        self._client = None

    def _serialise(self, bot, method: TelegramMethod) -> tuple[dict[str, Any], dict[str, Any]]:
        files: dict[str, Any] = {}
        payload: dict[str, Any] = {}
        for key, value in method.model_dump(warnings=False).items():
            prepared = self.prepare_value(value, bot=bot, files=files, _dumps_json=False)
            if prepared is None:
                continue
            payload[key] = prepared
        return payload, files

    @staticmethod
    def _form(payload: dict[str, Any]) -> dict[str, str]:
        """Flatten a payload for multipart/form-data (Telegram accepts JSON strings)."""
        form: dict[str, str] = {}
        for key, value in payload.items():
            if isinstance(value, bool):
                form[key] = "true" if value else "false"
            elif isinstance(value, (dict, list)):
                form[key] = json.dumps(value)
            else:
                form[key] = str(value)
        return form

    def _request_timeout(self, method: TelegramMethod, timeout: int | None) -> float | None:
        if timeout is not None:
            return timeout
        # Long-polling getUpdates must be allowed to outlive the global HTTP timeout.
        if getattr(method, "__api_method__", None) == "getUpdates":
            poll = int(getattr(method, "timeout", 0) or 0)
            return max(float(self.timeout or 0), float(poll + 15))
        return self.timeout

    async def make_request(self, bot, method: TelegramMethod, timeout: int | None = None):  # type: ignore[override]
        url = self.api.api_url(token=bot.token, method=method.__api_method__)
        payload, files = self._serialise(bot, method)
        request_timeout = self._request_timeout(method, timeout)
        if files:
            upload: dict[str, tuple[str, bytes]] = {}
            for key, input_file in files.items():
                data = b"".join([chunk async for chunk in input_file.read(bot)])
                upload[key] = (getattr(input_file, "filename", None) or "file", data)
            response = await self.client.post(
                url,
                data=self._form(payload),
                files=upload,
                timeout=request_timeout,
            )
        else:
            response = await self.client.post(
                url,
                json=payload,
                timeout=request_timeout,
            )
        parsed = self.check_response(
            bot=bot,
            method=method,
            status_code=response.status_code,
            content=response.text,
        )
        return parsed.result

    async def stream_content(  # type: ignore[override]
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:  # pragma: no cover - unused
        response = await self.client.get(url, headers=headers or {}, timeout=timeout)
        response.raise_for_status()
        yield response.content
