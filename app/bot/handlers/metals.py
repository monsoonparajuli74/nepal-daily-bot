"""Gold & silver daily rates."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from app.bot import menus
from app.bot.context import BotContext
from app.bot.formatters import metals_signal, updated_line
from app.bot.handlers import share
from app.bot.handlers.common import send_error
from app.data.cache import latest_snapshot, previous_ok_snapshot
from app.utils import nepali_digits as nd

logger = logging.getLogger(__name__)


async def today(ctx: BotContext, param: str | None = None) -> None:
    row = await latest_snapshot(ctx.session, "metals", ok_only=True)
    if row is None:
        await send_error(ctx, module="metals")
        return
    payload = row.payload or {}
    values = payload.get("today") or {}
    if not values:
        await send_error(ctx, module="metals")
        return
    previous = await previous_ok_snapshot(ctx.session, "metals")
    previous_values = (previous.payload or {}).get("today", {}) if previous else {}

    ctx.track("view", module="metals")
    lines = [f"<b>{ctx.t('metals_title')}</b>", ""]
    lines.extend(_metal_line(ctx, values, previous_values, "gold_tola", "metals_hallmark", "metals_per_tola"))
    if values.get("tejabi_tola") is not None:
        lines.append(
            _single_line(
                ctx,
                "metals_tejabi",
                values.get("tejabi_tola"),
                previous_values.get("tejabi_tola"),
                "metals_per_tola",
            )
        )
    if values.get("gold_10g") is not None:
        lines.append(
            _metal_line(ctx, values, previous_values, "gold_10g", "metals_hallmark", "metals_per_10g")[0]
        )
    lines.extend(_metal_line(ctx, values, previous_values, "silver_tola", "metals_silver", "metals_per_tola"))
    if payload.get("effective"):
        lines.append(f"<i>{ctx.t('metals_effective', date=str(payload['effective'])[:10])}</i>")
    lines.append("")
    lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
    body = "\n".join(lines)

    gold = values.get("gold_tola")
    compact = f"💰 Gold {ctx.t('metals_per_tola')}: रू {gold}"
    await ctx.reply(body, inline=menus.result_buttons(ctx.t, share_key=share.stash("metals", compact)))


def _metal_line(ctx: BotContext, values, previous, key, label_key, unit_key) -> list[str]:
    return [_single_line(ctx, label_key, values.get(key), previous.get(key), unit_key)]


def _single_line(ctx: BotContext, label_key, current, previous, unit_key) -> str:
    label = ctx.t(label_key)
    unit = ctx.t(unit_key)
    value = _dec(current)
    if value is None:
        return f"{label} ({unit}): -"
    delta = None
    prev_value = _dec(previous)
    if prev_value is not None:
        delta = value - prev_value
    symbol = metals_signal(delta)
    change = ""
    if delta is not None and delta != 0:
        sign = "+" if delta > 0 else "-"
        change = f" ({sign}{nd.format_number(abs(delta))})"
    return f"• <b>{label}</b> <i>({unit})</i>\n  रू {nd.format_number(value)}{change} {symbol}"


def _dec(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("1"))
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        return None
