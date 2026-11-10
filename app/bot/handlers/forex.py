"""Forex rates and the remittance calculator."""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.bot import actions, menus, state
from app.bot.context import BotContext
from app.bot.formatters import market_signal, updated_line
from app.bot.handlers.common import send_error
from app.data.cache import previous_ok_snapshot
from app.data.sources.forex import ALL_CURRENCIES, KEY_CURRENCIES, OTHER_CURRENCIES, flag
from app.utils import nepali_digits as nd
from app.utils.nepali_digits import AmountError, parse_amount

logger = logging.getLogger(__name__)

QUICK_PICKS = [500, 1000, 2500, 5000]

#: True = use the NRB buy rate (what the receiving side gets). Matches the product spec.
USE_BUY_RATE = True


async def rates(ctx: BotContext, param: str | None = None) -> None:
    row = await _latest(ctx)
    if row is None:
        await send_error(ctx)
        return
    payload = row.payload or {}
    rates_data = payload.get("rates") or {}
    if not rates_data:
        await send_error(ctx)
        return

    previous = await previous_ok_snapshot(ctx.session, "forex")
    previous_rates = (previous.payload or {}).get("rates", {}) if previous else {}

    await ctx.track("fx_rates")
    lines = [ctx.t("fx_title")]
    lines.extend(_rate_lines(ctx, rates_data, previous_rates, KEY_CURRENCIES))
    lines.append("")
    lines.extend(_rate_lines(ctx, rates_data, previous_rates, OTHER_CURRENCIES))
    lines.append("")
    lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
    lines.append(ctx.t("fx_disclaimer"))
    body = "\n".join(lines)

    compact = f"💵 NRB rates: USD buy रू {_buy_of(rates_data.get('USD'))}"
    await ctx.reply(body, inline=menus.forex_buttons(ctx.t, ctx.share_url(compact)))


def _rate_lines(ctx: BotContext, today: dict, previous: dict, codes) -> list[str]:
    lines: list[str] = []
    for code in codes:
        entry = today.get(code)
        if not entry:
            continue
        unit = int(entry.get("unit", 1))
        label = f"{flag(code)} {code} ({unit})" if unit != 1 else f"{flag(code)} {code}"
        buy = _decimal(entry.get("buy"))
        sell = _decimal(entry.get("sell"))
        delta = None
        prev_entry = previous.get(code)
        if prev_entry:
            prev_buy = _decimal(prev_entry.get("buy"))
            if prev_buy is not None and buy is not None:
                delta = buy - prev_buy
        signal = market_signal(delta)
        buy_text = nd.format_npr(buy, decimals=2) if buy is not None else "-"
        sell_text = nd.format_npr(sell, decimals=2) if sell is not None else "-"
        lines.append(f"{label}: {ctx.t('fx_buy')} {buy_text} | {ctx.t('fx_sell')} {sell_text} {signal}")
    return lines


async def calc(ctx: BotContext, param: str | None = None) -> None:
    await state.clear_state(ctx.session, ctx.tg_id)
    await ctx.send(menus.currency_grid(ctx.t, list(KEY_CURRENCIES), more=True))


async def calc_currency(ctx: BotContext, param: str | None = None) -> None:
    code = (param or "").upper()
    if code not in ALL_CURRENCIES:
        await calc(ctx)
        return
    await _prompt_amount(ctx, code)


async def calc_more(ctx: BotContext, param: str | None = None) -> None:
    await ctx.send(menus.currency_grid(ctx.t, list(OTHER_CURRENCIES)))


async def _prompt_amount(ctx: BotContext, code: str) -> None:
    await state.set_state(ctx.session, ctx.tg_id, state.STATE_AWAITING_AMOUNT, {"currency": code})
    await ctx.send(menus.amount_picker(ctx.t, code, QUICK_PICKS))


async def calc_amount(ctx: BotContext, param: str | None = None) -> None:
    row = await state.get_state(ctx.session, ctx.tg_id)
    context = dict(row.context) if row else {}
    code = context.get("currency")
    if not code:
        await calc(ctx)
        return
    await handle_input(ctx, str(param or ""), code)


async def type_another(ctx: BotContext, param: str | None = None) -> None:
    """The "Type another amount" button - keep the currency, ask for free text."""
    row = await state.get_state(ctx.session, ctx.tg_id)
    context = dict(row.context) if row else {}
    code = context.get("currency")
    if not code:
        await calc(ctx)
        return
    await state.set_state(ctx.session, ctx.tg_id, state.STATE_AWAITING_AMOUNT, {"currency": code})
    await ctx.track("fx_type_another")
    buttons = [[menus.back_btn(ctx.t, actions.FOREX_CALC)]]
    await ctx.reply(ctx.t("calc_type_now", currency=f"{flag(code)} {code}"), inline=buttons)


async def calc_again(ctx: BotContext, param: str | None = None) -> None:
    row = await state.get_state(ctx.session, ctx.tg_id)
    context = dict(row.context) if row else {}
    code = context.get("currency") or "USD"
    await _prompt_amount(ctx, code)


async def handle_input(ctx: BotContext, raw: str, code: str | None = None) -> None:
    """Entry point for free-text amounts (also used by the router)."""
    if code is None:
        row = await state.get_state(ctx.session, ctx.tg_id)
        code = (row.context or {}).get("currency") if row else None
    if not code:
        await calc(ctx)
        return

    try:
        amount = parse_amount(raw)
    except AmountError:
        await ctx.track("calc_invalid")
        await ctx.send(menus.amount_picker(ctx.t, code, QUICK_PICKS))
        await ctx.reply(ctx.t("calc_invalid"))
        return

    rows = await _rate_rows(ctx)
    if rows is None:
        await state.clear_state(ctx.session, ctx.tg_id)
        await send_error(ctx)
        return
    today, _row = rows
    entry = today.get(code)
    if not entry:
        await state.clear_state(ctx.session, ctx.tg_id)
        await send_error(ctx)
        return

    rate = _decimal(entry.get("sell" if not USE_BUY_RATE else "buy"))
    unit = int(entry.get("unit", 1))
    if rate is None:
        await state.clear_state(ctx.session, ctx.tg_id)
        await send_error(ctx)
        return

    total = (amount * rate / Decimal(unit)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    await state.clear_state(ctx.session, ctx.tg_id)
    await ctx.track("calc_complete")

    rate_line = (
        f"1 {code} = रू {nd.group_digits(rate, decimals=2)}"
        if unit == 1
        else f"{unit} {code} = रू {nd.group_digits(rate, decimals=2)}"
    )
    foreign_text = f"{nd.group_digits(amount)} {code}"
    total_text = nd.format_npr(total, decimals=2)

    lines = [
        ctx.t("calc_title"),
        f"{ctx.t('calc_foreign_amount')}: {foreign_text}",
        f"{ctx.t('calc_today_rate')}: {rate_line}",
        f"{ctx.t('calc_total')}: {total_text} NPR",
        "",
        ctx.t("calc_disclaimer"),
    ]
    compact = f"💱 {foreign_text} = {total_text} NPR"
    await ctx.reply("\n".join(lines), inline=menus.conversion_buttons(ctx.t, code, ctx.share_url(compact)))


async def _latest(ctx: BotContext):
    from app.data.cache import latest_snapshot

    return await latest_snapshot(ctx.session, "forex", ok_only=True)


async def _rate_rows(ctx: BotContext):
    row = await _latest(ctx)
    if row is None:
        return None
    return (row.payload or {}).get("rates") or {}, row


def _decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        return None


def _buy_of(entry) -> str:
    if not entry:
        return "-"
    return str(entry.get("buy", "-"))
