"""Opt-out, data deletion and digest opt-in lifecycle.

``stop`` marks the user inactive; we still answer (the user just messaged us) so they know
it worked. Any later inbound message reactivates them. ``deletedata`` erases everything.
"""

from __future__ import annotations

from sqlalchemy import delete

from app.bot import state
from app.bot.context import BotContext
from app.bot.handlers.common import send_home
from app.bot.users import mark_inactive, set_digest_opt_in
from app.data.models import Event


async def stop(ctx: BotContext, param: str | None = None) -> None:
    await mark_inactive(ctx.session, ctx.tg_id)
    await ctx.track("opt_out")
    await ctx.reply(ctx.t("stopped_notice"), remove_keyboard=True)


async def start(ctx: BotContext, param: str | None = None) -> None:
    await send_home(ctx)


async def deletedata(ctx: BotContext, param: str | None = None) -> None:
    await ctx.track("delete_data")
    await state.clear_state(ctx.session, ctx.tg_id)
    await ctx.session.execute(delete(Event).where(Event.tg_user_id_hash == ctx.user_hash()))
    await ctx.session.delete(ctx.user)
    await ctx.session.flush()
    await ctx.reply(ctx.t("deletedata_done"), remove_keyboard=True)


async def subscribe(ctx: BotContext, param: str | None = None) -> None:
    if not ctx.settings.feature_daily_digest:
        await ctx.reply(ctx.t("digest_disabled"))
        return
    await set_digest_opt_in(ctx.session, ctx.tg_id, True)
    await ctx.track("digest_subscribe")
    await ctx.reply(ctx.t("digest_subscribed"))


async def unsubscribe(ctx: BotContext, param: str | None = None) -> None:
    await set_digest_opt_in(ctx.session, ctx.tg_id, False)
    await ctx.track("digest_unsubscribe")
    await ctx.reply(ctx.t("digest_unsubscribed"))
