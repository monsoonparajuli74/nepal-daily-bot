"""Kalimati vegetable market: essentials, leafy greens and trends."""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

from app.bot import actions, menus
from app.bot.context import BotContext
from app.bot.formatters import consumer_signal, updated_line
from app.bot.handlers.common import send_error
from app.data.cache import latest_snapshot, previous_ok_snapshot
from app.data.config_loader import load_vegetables
from app.utils import nepali_digits as nd

logger = logging.getLogger(__name__)


async def menu(ctx: BotContext, param: str | None = None) -> None:
    await ctx.track("veg_menu")
    await ctx.send(menus.veg_menu(ctx.t))


async def essentials(ctx: BotContext, param: str | None = None) -> None:
    config = load_vegetables(ctx.settings.data_dir)
    entries = config.get("essentials", [])
    await _render_selection(ctx, entries, "veg_essentials_title", "veg_essentials")


async def vegetables(ctx: BotContext, param: str | None = None) -> None:
    config = load_vegetables(ctx.settings.data_dir)
    entries = config.get("vegetables", [])
    await _render_selection(ctx, entries, "veg_vegetables_title", "veg_vegetables")


async def fruits(ctx: BotContext, param: str | None = None) -> None:
    config = load_vegetables(ctx.settings.data_dir)
    entries = config.get("fruits", [])
    await _render_selection(ctx, entries, "veg_fruits_title", "veg_fruits")


async def greens(ctx: BotContext, param: str | None = None) -> None:
    config = load_vegetables(ctx.settings.data_dir)
    entries = config.get("greens", [])
    await _render_selection(ctx, entries, "veg_greens_title", "veg_greens")


async def _render_selection(ctx: BotContext, entries: list[dict], title_key: str, event: str) -> None:
    row = await latest_snapshot(ctx.session, "vegetables", ok_only=True)
    if row is None:
        await send_error(ctx)
        return
    items = (row.payload or {}).get("items") or []
    if not items:
        await send_error(ctx)
        return

    await ctx.track(event)
    lines = [f"{ctx.t('veg_title')}", ctx.t(title_key), ""]
    found = 0
    for entry in entries:
        item = _find(items, entry)
        if item is None:
            continue
        found += 1
        label = entry.get("ne") if ctx.language == "ne" else entry.get("en")
        unit = item.get("unit") or "kg"
        minimum = nd.format_number(_dec(item.get("min"))) if _dec(item.get("min")) is not None else "-"
        maximum = nd.format_number(_dec(item.get("max"))) if _dec(item.get("max")) is not None else "-"
        min_disp = nd.to_devanagari_digits(minimum) if ctx.language == "ne" else minimum
        max_disp = nd.to_devanagari_digits(maximum) if ctx.language == "ne" else maximum
        if ctx.language == "ne":
            unit_disp = "के.जी." if unit == "kg" else unit
        else:
            unit_disp = unit
        lines.append(f"{label}: रू {min_disp} - रू {max_disp} /{unit_disp}")
    if found == 0:
        lines.append(ctx.t("veg_no_items"))
    lines.append("")
    lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
    body = "\n".join(lines)

    compact = f"🥦 Kalimati vegetable prices ({ctx.t(title_key)})"
    rows = [[menus.Btn(text=ctx.t("btn_more_veg"), action=actions.VEG_MORE)]]
    rows.extend(
        menus.result_buttons(ctx.t, back_action=actions.VEG_MENU, share_url=ctx.share_url(compact))
    )
    await ctx.reply(body, inline=rows)


async def more(ctx: BotContext, param: str | None = None) -> None:
    """A longer list of vegetables beyond the essentials + greens shortcuts."""
    row = await latest_snapshot(ctx.session, "vegetables", ok_only=True)
    if row is None:
        await send_error(ctx)
        return
    items = (row.payload or {}).get("items") or []
    if not items:
        await send_error(ctx)
        return

    config = load_vegetables(ctx.settings.data_dir)
    entries = _all_entries(config)
    used = set()
    for entry in entries:
        item = _find(items, entry)
        if item is not None:
            used.add(_item_key(item))

    extras: list[tuple[str, dict]] = []
    seen: set[str] = set()
    for item in items:
        name = str(item.get("name") or "").strip()
        key = _item_key(item)
        if not name or key in used or key in seen:
            continue
        seen.add(key)
        extras.append((name, item))
    extras.sort(key=lambda pair: pair[0].lower())

    await ctx.track("veg_more")
    lines = [ctx.t("veg_title"), ctx.t("veg_more_title"), ""]
    shown = 0
    for name, item in extras[:20]:
        unit = item.get("unit") or "kg"
        minimum = nd.format_number(_dec(item.get("min"))) if _dec(item.get("min")) is not None else "-"
        maximum = nd.format_number(_dec(item.get("max"))) if _dec(item.get("max")) is not None else "-"
        min_disp = nd.to_devanagari_digits(minimum) if ctx.language == "ne" else minimum
        max_disp = nd.to_devanagari_digits(maximum) if ctx.language == "ne" else maximum
        if ctx.language == "ne":
            unit_disp = "के.जी." if unit == "kg" else unit
        else:
            unit_disp = unit
        disp_name = name
        lines.append(f"{disp_name}: रू {min_disp} - रू {max_disp} /{unit_disp}")
        shown += 1
    if shown == 0:
        lines.append(ctx.t("veg_no_items"))
    lines.append("")
    lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
    body = "\n".join(lines)

    compact = "🥦 Kalimati vegetable prices (more vegetables)"
    await ctx.reply(
        body,
        inline=menus.result_buttons(ctx.t, back_action=actions.VEG_MENU, share_url=ctx.share_url(compact)),
    )


def _all_entries(config: dict) -> list[dict]:
    entries: list[dict] = []
    for section in ("essentials", "vegetables", "fruits", "greens"):
        entries.extend(config.get(section, []))
    return entries


def _item_key(item: dict) -> str:
    return _normalise_name(item.get("name"))


def _ranges(items: list[dict], entries: list[dict], language: str) -> list[str]:
    """Biggest min-max spreads today, used when there is nothing to compare against."""
    rows: list[tuple[Decimal, str]] = []
    for entry in entries:
        item = _find(items, entry)
        if item is None:
            continue
        minimum = _dec(item.get("min"))
        maximum = _dec(item.get("max"))
        if minimum is None or maximum is None or minimum <= 0:
            continue
        spread = (maximum - minimum) / minimum * 100
        label = entry.get("ne") if language == "ne" else entry.get("en")
        unit = item.get("unit") or "kg"
        rows.append(
            (
                spread,
                f"{label}: रू {nd.format_number(minimum)} - रू {nd.format_number(maximum)} /{unit}",
            )
        )
    rows.sort(key=lambda row: row[0], reverse=True)
    return [text for _spread, text in rows[:5]]


async def trends(ctx: BotContext, param: str | None = None) -> None:
    row = await latest_snapshot(ctx.session, "vegetables", ok_only=True)
    if row is None:
        await send_error(ctx)
        return
    today_items = (row.payload or {}).get("items") or []
    previous = await previous_ok_snapshot(ctx.session, "vegetables")
    yesterday_items = (previous.payload or {}).get("items", []) if previous else []

    await ctx.track("veg_trends")
    lines = [ctx.t("veg_title"), ctx.t("veg_trends_title"), ""]

    if not yesterday_items:
        lines.append(ctx.t("veg_no_compare"))
        lines.append("")
        lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
        compact = "🥦 Kalimati vegetable price trends"
        await ctx.reply(
            "\n".join(lines),
            inline=menus.result_buttons(ctx.t, back_action=actions.VEG_MENU, share_url=ctx.share_url(compact)),
        )
        return

    config = load_vegetables(ctx.settings.data_dir)
    entries = config.get("essentials", []) + config.get("greens", [])
    previous_lookup = _index_by_key(yesterday_items, entries)

    movers: list[tuple[str, Decimal, Decimal, Decimal]] = []
    for entry in entries:
        item = _find(today_items, entry)
        if item is None:
            continue
        key = entry.get("key")
        prev = previous_lookup.get(key)
        if prev is None:
            continue
        today_avg = _dec(item.get("avg"))
        prev_avg = _dec(prev.get("avg"))
        if today_avg is None or prev_avg is None or prev_avg == 0:
            continue
        delta = today_avg - prev_avg
        if delta == 0:
            continue
        percent = (delta / prev_avg) * 100
        label = entry.get("ne") if ctx.language == "ne" else entry.get("en")
        movers.append((label, delta, percent, today_avg))

    ups = sorted([m for m in movers if m[1] > 0], key=lambda m: m[1], reverse=True)[:5]
    downs = sorted([m for m in movers if m[1] < 0], key=lambda m: m[1])[:5]

    if not ups and not downs:
        lines.append(ctx.t("veg_range_note"))
        lines.extend(_ranges(today_items, entries, ctx.language))
    else:
        for label, _delta, percent, _avg in ups:
            lines.append(f"{label}: +{percent.quantize(Decimal('0.1'))}% {consumer_signal(Decimal(1))}")
        for label, _delta, percent, _avg in downs:
            lines.append(f"{label}: {percent.quantize(Decimal('0.1'))}% {consumer_signal(Decimal(-1))}")

    lines.append("")
    lines.append(updated_line(ctx.language, row.fetched_at, row.checked_at))
    compact = "🥦 Kalimati vegetable price trends"
    await ctx.reply(
        "\n".join(lines),
        inline=menus.result_buttons(ctx.t, back_action=actions.VEG_MENU, share_url=ctx.share_url(compact)),
    )


_NAME_NOISE = re.compile(r"[^a-z0-9]+")


def _normalise_name(value: object) -> str:
    return _NAME_NOISE.sub(" ", str(value or "").lower()).strip()


def _find(items: list[dict], entry: dict) -> dict | None:
    """First entry pattern (in priority order) that appears in an item name."""
    for pattern in entry.get("match") or []:
        if isinstance(pattern, (list, tuple)):
            needle = " ".join(str(word).lower() for word in pattern).strip()
        else:
            needle = " ".join(str(pattern).lower().split())
        if not needle:
            continue
        for item in items:
            if needle in _normalise_name(item.get("name")):
                return item
    return None


def _index_by_key(items: list[dict], entries: list[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for entry in entries:
        item = _find(items, entry)
        if item is not None:
            lookup[entry.get("key")] = item
    return lookup


def _dec(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        return None
