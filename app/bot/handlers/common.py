"""Home screen, welcome, unknown input, help and shared helpers."""

from __future__ import annotations

from pathlib import Path

from app.bot import menus
from app.bot.context import BotContext
from app.channels.base import Reply
from app.data.cache import latest_snapshot, payload_of

#: Bundled Nepal-themed artwork (see ``scripts/make_art.py``).
ASSETS = Path(__file__).resolve().parents[2] / "assets"
WELCOME_PHOTO = ASSETS / "welcome.png"


def welcome_menu(ctx: BotContext) -> Reply:
    text = f"{ctx.t('welcome_body')}\n\n{ctx.t('home_menu_title')}"
    body = f"<b>Sajilo Nepal</b>\n{ctx.t('welcome_body')}\n\n<b>{ctx.t('home_menu_title')}</b>"
    return menus.home_reply(
        ctx.t,
        text=body,
        photo=str(WELCOME_PHOTO) if WELCOME_PHOTO.exists() else None,
    )


async def send_home(ctx: BotContext, *, hint: bool = False, text: str | None = None) -> None:
    if hint and text is None:
        body = f"{ctx.t('unknown_hint')}\n\n<b>{ctx.t('home_menu_title')}</b>"
    elif text is not None:
        body = text
    else:
        body = f"<b>{ctx.t('home_menu_title')}</b>"
    await ctx.send(menus.home_reply(ctx.t, text=body))


async def send_error(ctx: BotContext) -> None:
    await ctx.reply(
        f"<b>{ctx.t('error_generic')}</b>",
        inline=[[menus.back_btn(ctx.t)]],
    )


async def send_help(ctx: BotContext) -> None:
    await ctx.reply(f"<b>{ctx.t('home_menu_title')}</b>\n\n{ctx.t('help_text')}", inline=[[menus.back_btn(ctx.t)]])


async def source_payload(ctx: BotContext, source: str):
    """Return (payload, snapshot_row) for the newest successful snapshot."""
    row = await latest_snapshot(ctx.session, source, ok_only=True)
    return payload_of(row), row
