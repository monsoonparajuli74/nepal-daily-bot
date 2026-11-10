"""Latest news headlines via RSS. Headlines + source + link only."""

from __future__ import annotations

import logging

from app.bot import actions, menus
from app.bot.context import BotContext
from app.bot.formatters import esc, updated_line
from app.bot.handlers.common import send_error
from app.data.cache import latest_snapshot

logger = logging.getLogger(__name__)

BADGES = ("1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟")


async def latest(ctx: BotContext, param: str | None = None) -> None:
    page = 0
    if param:
        p = str(param).strip()
        # handle cases like "1", "l1", etc
        if p.isdigit():
            page = max(0, int(p))
        elif p and p[0].isdigit():
            # extract leading number
            import re
            m = re.match(r"^(\d+)", p)
            if m:
                page = max(0, int(m.group(1)))
    row = await latest_snapshot(ctx.session, "news", ok_only=True)
    if row is None:
        await send_error(ctx)
        return
    payload = row.payload or {}
    items = payload.get(ctx.language) or payload.get("en") or []
    if not items:
        await send_error(ctx)
        return

    per_page = 5
    start = page * per_page
    end = start + per_page
    page_items = items[start:end]
    if not page_items:
        await send_error(ctx)
        return

    await ctx.track("news_view")
    sources = " · ".join(dict.fromkeys(item.get("source", "") for item in items if item.get("source")))
    lines = [
        f"<b>{esc(ctx.t('news_title'))}</b>",
        f"<i>{esc(sources)}</i>",
        "",
    ]
    for index, item in enumerate(page_items):
        global_idx = start + index + 1
        badge = BADGES[global_idx - 1] if global_idx - 1 < len(BADGES) else f"{global_idx}."
        title = item.get("title", "") or ""
        source = item.get("source", "")
        link = item.get("link", "") or ""
        summary = item.get("summary") or item.get("description") or ""
        summary_clean = " ".join(str(summary).split()) if summary else ""
        display_title = title
        if len(display_title) > 220:
            display_title = display_title[:217].rstrip() + "..."
        lines.append(f"{badge} <b>{esc(display_title)}</b>")
        if source or link:
            if source and link:
                if ctx.language == "ne":
                    lines.append(f"     <i>{esc(source)}</i> · <a href=\"{esc(link)}\">पूरा पढ्नुहोस्</a>")
                else:
                    lines.append(f"     <i>{esc(source)}</i> · <a href=\"{esc(link)}\">Read more</a>")
            elif source:
                lines.append(f"     <i>{esc(source)}</i>")
            elif link:
                if ctx.language == "ne":
                    lines.append(f"     <a href=\"{esc(link)}\">पूरा पढ्नुहोस्</a>")
                else:
                    lines.append(f"     <a href=\"{esc(link)}\">Read more</a>")
        if summary_clean:
            if len(summary_clean) > 320:
                summary_clean = summary_clean[:317].rstrip() + "..."
            lines.append(f"     {esc(summary_clean)}")
        lines.append("")
    lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
    body = "\n".join(lines)

    navigation = []
    if end < len(items):
        navigation.append(menus.Btn(text="More News", action=f"nw:l{page + 1}"))
    navigation.append(menus.Btn(text=ctx.t("btn_back"), action=actions.HOME))
    btns = [navigation]
    btns.append([menus.Btn(text=ctx.t("btn_refresh"), action=f"nw:l{page}")])
    await ctx.reply(body, inline=btns)


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
