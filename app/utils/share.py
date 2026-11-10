"""Share helpers for Telegram.

Telegram can open its chat picker with prefilled text via
``https://t.me/share/url?url=<link>&text=<text>``. The ``url`` is the bot's deep link so the
forwarded block always carries a "get this free" call to action.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

SHARE_CAPTION = "📲 Get daily rates free on Sajilo Nepal"

#: Telegram share picker.
SHARE_URL = "https://t.me/share/url"


def bot_link(bot_username: str) -> str:
    """Return ``https://t.me/<username>`` for the bot, or "" when unset."""
    username = (bot_username or "").strip().lstrip("@")
    return f"https://t.me/{username}" if username else ""


def share_text(compact: str, bot_username: str) -> str:
    """The block prefixed into the recipient picker."""
    link = bot_link(bot_username)
    caption = f"{SHARE_CAPTION}: {link}" if link else SHARE_CAPTION
    return f"{compact}\n\n{caption}"


def share_url(compact: str, bot_username: str, start: str = "share") -> str:
    """A t.me/share/url link that opens the picker with the block prefilled."""
    link = bot_link(bot_username)
    if link:
        link = f"{link}?start={quote(start, safe='')}"
    query = urlencode({"url": link, "text": share_text(compact, bot_username)})
    return f"{SHARE_URL}?{query}"
