"""Language selection (persists the choice and re-renders the home menu)."""

from __future__ import annotations

from app.bot.context import BotContext
from app.bot.handlers.common import send_home
from app.bot.users import set_language, toggle_language


async def toggle(ctx: BotContext, param: str | None = None) -> None:
    user = await toggle_language(ctx.session, ctx.user)
    ctx.set_language(user.language)
    ctx.track("language_change")
    await send_home(ctx, text=f"{ctx.t('language_set')}\n{ctx.t('home_menu_title')}")


async def set_en(ctx: BotContext, param: str | None = None) -> None:
    await _apply(ctx, "en")


async def set_ne(ctx: BotContext, param: str | None = None) -> None:
    await _apply(ctx, "ne")


async def _apply(ctx: BotContext, language: str) -> None:
    user = await set_language(ctx.session, ctx.user, language)
    ctx.set_language(user.language)
    ctx.track("language_change")
    await send_home(ctx, text=f"{ctx.t('language_set')}\n{ctx.t('home_menu_title')}")
