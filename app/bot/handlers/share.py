"""Share flow: a callback button, then Telegram's own chat picker.

The Share button is a normal callback (not a URL button) so the tap can be counted. The
block to share is stashed in memory for a short while — never in the database — and the
follow-up offers the t.me/share/url picker, which opens without a confirmation prompt
because t.me is an internal Telegram domain. Recipients land on the bot via
``start=share_<module>`` for acquisition attribution.
"""

from __future__ import annotations

import secrets
import time

from app.bot import menus
from app.bot.context import BotContext
from app.channels.base import Btn
from app.utils.share import share_url

#: key -> (module, compact, stored_at). Bounded and short-lived on purpose.
_STASH: dict[str, tuple[str, str, float]] = {}
_STASH_LIMIT = 256
_STASH_TTL_SECONDS = 1800.0


def stash(module: str, compact: str) -> str:
    """Remember the block to share and return the callback key that references it."""
    now = time.monotonic()
    for key, entry in list(_STASH.items()):
        if now - entry[2] > _STASH_TTL_SECONDS:
            _STASH.pop(key, None)
    while len(_STASH) >= _STASH_LIMIT:
        _STASH.pop(next(iter(_STASH)))
    key = secrets.token_hex(4)
    _STASH[key] = (module, compact, now)
    return key


def _take(key: str) -> tuple[str, str]:
    entry = _STASH.get(key)
    if entry is None:
        return "", ""
    if time.monotonic() - entry[2] > _STASH_TTL_SECONDS:
        _STASH.pop(key, None)
        return "", ""
    return entry[0], entry[1]


async def share(ctx: BotContext, param: str | None = None) -> None:
    module, compact = _take((param or "").strip())
    ctx.track("share_tap", module=module or None)
    if not compact:
        compact = "📲 Sajilo Nepal"
    start = f"share_{module}" if module else "share"
    url = share_url(compact, ctx.settings.bot_username, start=start)
    await ctx.reply(
        ctx.t("share_prompt"),
        inline=[[Btn(text=ctx.t("btn_share"), url=url), menus.back_btn(ctx.t)]],
    )
