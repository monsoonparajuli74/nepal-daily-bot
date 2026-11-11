"""Router: maps callback action ids and free text to handlers.

Telegram deliverable routes are namespaced action ids (``nav:home``, ``hs:s:leo``,
``fx:cc:AED``) carried as ``callback_data``. Free text covers the persistent keyboard
labels, typed words and ``/`` commands (optionally with an argument). Unknown input falls
back to the home menu with a short hint. Handlers are idempotent; duplicates are filtered
upstream by update dedupe.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from app.bot import actions, state, textcmd
from app.bot.context import BotContext
from app.bot.handlers import (
    admin,
    calendar,
    forex,
    fuel,
    horoscope,
    language,
    lifecycle,
    metals,
    news,
    share,
    veg,
    weather,
)
from app.bot.handlers.common import send_help, send_home
from app.bot.i18n import SIGN_NAMES
from app.bot.labels import resolve_label
from app.data.config_loader import city_list

logger = logging.getLogger(__name__)

Handler = Callable[[BotContext, str | None], Awaitable[None]]

EXACT_ROUTES: dict[str, Handler] = {
    actions.HOME: lambda ctx, param: send_home(ctx),
    actions.HELP: lambda ctx, param: send_help(ctx),
    actions.STOP: lifecycle.stop,
    actions.DELETEDATA: lifecycle.deletedata,
    actions.SUBSCRIBE: lifecycle.subscribe,
    actions.UNSUBSCRIBE: lifecycle.unsubscribe,
    actions.LANG_TOGGLE: language.toggle,
    actions.LANG_EN: language.set_en,
    actions.LANG_NE: language.set_ne,
    actions.HOROSCOPE_MENU: horoscope.menu,
    actions.HOROSCOPE_CHANGE: horoscope.change,
    actions.FOREX_RATES: forex.rates,
    actions.FOREX_CALC: forex.calc,
    actions.FOREX_MORE: forex.calc_more,
    actions.FOREX_TYPE_ANOTHER: forex.type_another,
    actions.FOREX_AGAIN: forex.calc_again,
    actions.VEG_MENU: veg.menu,
    actions.VEG_ESSENTIALS: veg.essentials,
    actions.VEG_GREENS: veg.greens,
    actions.VEG_VEGETABLES: veg.vegetables,
    actions.VEG_FRUITS: veg.fruits,
    actions.VEG_TRENDS: veg.trends,
    actions.VEG_MORE: veg.more,
    actions.WX_MENU: weather.menu,
    actions.WX_MORE: weather.more,
    actions.NEWS_LATEST: news.latest,
    "nw:l": news.latest,
    actions.CAL_TODAY: calendar.today,
    actions.METALS_TODAY: metals.today,
    actions.FUEL_TODAY: fuel.today,
}

PREFIX_ROUTES: tuple[tuple[str, Handler], ...] = (
    ("hs:s:", horoscope.sign),
    ("hs:p:", horoscope.period),
    ("hs:save:", horoscope.save),
    ("fx:cc:", forex.calc_currency),
    ("fx:ca:", forex.calc_amount),
    ("wx:c:", weather.city),
    ("nw:l", news.latest),
    ("share:", share.share),
)


async def route_action(ctx: BotContext, action: str) -> None:
    action = (action or "").strip()
    await _maybe_clear_state(ctx, action)

    handler = EXACT_ROUTES.get(action)
    if handler is not None:
        await handler(ctx, None)
        return

    for prefix, prefix_handler in PREFIX_ROUTES:
        if action.startswith(prefix):
            await prefix_handler(ctx, action[len(prefix) :])
            return

    await send_home(ctx, hint=True)


async def route_text(ctx: BotContext, text: str) -> None:
    """Free text: calculator amount, a label/typed command, or a slash command."""
    text = _strip_mention(ctx, text)

    row = await state.get_state(ctx.session, ctx.tg_id)
    if row is not None and row.state == state.STATE_AWAITING_AMOUNT:
        await forex.handle_input(ctx, text)
        return

    command = textcmd.command_name(text)
    if command is not None:
        await route_command(ctx, command, textcmd.command_args(text))
        return

    action = resolve_label(text) or textcmd.resolve_plain(text)
    if action is not None:
        await route_action(ctx, action)
        return

    await send_home(ctx, hint=True)


async def route_command(ctx: BotContext, name: str, args: list[str]) -> None:
    """Slash command, optionally with an argument (``/horoscope leo``)."""
    if name == "stats":
        await admin.stats(ctx, args[0] if args else None)
        return
    if name in {"horoscope", "rashifal"}:
        slug = args[0].strip().lower() if args else ""
        if slug in SIGN_NAMES:
            await horoscope.sign(ctx, slug)
        else:
            await horoscope.menu(ctx)
        return
    if name in {"weather", "mausam"}:
        key = args[0].strip().lower() if args else ""
        if key in city_list():
            await weather.city(ctx, key)
        else:
            await weather.menu(ctx)
        return

    action = textcmd.SLASH_COMMANDS.get(name)
    if action is None:
        await send_home(ctx, hint=True)
        return
    await route_action(ctx, action)


def _strip_mention(ctx: BotContext, text: str) -> str:
    username = ctx.settings.bot_username
    if username:
        text = text.replace(f"@{username}", " ").replace(f"@{username.lower()}", " ")
    return text.strip()


async def _maybe_clear_state(ctx: BotContext, action: str) -> None:
    """Navigating away from the calculator cancels it (typing-friendly)."""
    row = await state.get_state(ctx.session, ctx.tg_id)
    if row is None or row.state != state.STATE_AWAITING_AMOUNT:
        return
    if action.startswith("fx:"):
        return
    await state.clear_state(ctx.session, ctx.tg_id)
