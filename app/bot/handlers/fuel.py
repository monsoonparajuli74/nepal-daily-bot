"""Fuel prices for Kathmandu."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from app.bot import menus
from app.bot.context import BotContext
from app.bot.formatters import consumer_signal, updated_line
from app.bot.handlers.common import send_error
from app.data.cache import latest_snapshot, previous_ok_snapshot
from app.utils import nepali_digits as nd

logger = logging.getLogger(__name__)

PRODUCTS = (
    ("petrol", "fuel_petrol"),
    ("diesel", "fuel_diesel"),
    ("kerosene", "fuel_kerosene"),
    ("lpg", "fuel_lpg"),
)


async def today(ctx: BotContext, param: str | None = None) -> None:
    row = await latest_snapshot(ctx.session, "fuel", ok_only=True)
    if row is None:
        await send_error(ctx)
        return
    payload = row.payload or {}
    prices = payload.get("prices") or {}
    if not prices:
        await send_error(ctx)
        return
    previous = await previous_ok_snapshot(ctx.session, "fuel")
    previous_prices = (previous.payload or {}).get("prices", {}) if previous else {}

    await ctx.track("fuel_view")
    lines = [f"<b>{ctx.t('fuel_title')}</b>", ""]
    for key, label_key in PRODUCTS:
        label = ctx.t(label_key)
        suffix = ctx.t("fuel_per_litre") if key != "lpg" else ""
        current = _dec(prices.get(key))
        if current is None:
            lines.append(f"• <b>{label}</b>: —")
            continue
        previous_value = _dec(previous_prices.get(key))
        delta = (current - previous_value) if previous_value is not None else None
        symbol = consumer_signal(delta)
        change = ""
        if delta is not None and delta != 0:
            sign = "+" if delta > 0 else "-"
            change = f" ({sign}{nd.format_number(abs(delta))})"
        lines.append(f"• <b>{label}</b>\n  रू {nd.format_number(current)}{suffix}{change} {symbol}")
    if payload.get("effective"):
        lines.append(f"<i>{ctx.t('fuel_effective', date=str(payload['effective']))}</i>")
    lines.append("")
    lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
    body = "\n".join(lines)

    compact = f"⛽ Fuel (Kathmandu): Petrol रू {prices.get('petrol')}/L, Diesel रू {prices.get('diesel')}/L"
    await ctx.reply(body, inline=menus.result_buttons(ctx.t, share_url=ctx.share_url(compact)))


def _dec(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        return None
