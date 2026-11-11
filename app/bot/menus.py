"""Telegram affordance builders: inline keyboard grids and the persistent home keyboard.

Telegram lets us restore the original 3x3 home grid (a persistent reply keyboard) and a
12-sign zodiac grid (an inline keyboard), so most of the compact WhatsApp workarounds are
gone. Every builder returns a channel-agnostic :class:`Reply`.
"""

from __future__ import annotations

from collections.abc import Callable

from app.bot import actions
from app.bot.i18n import sign_label
from app.bot.labels import home_keyboard
from app.channels.base import Btn, Reply
from app.data.config_loader import city_list
from app.data.sources.forex import flag

TextFn = Callable[[str], str]

SIGNS: tuple[str, ...] = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)

WEATHER_ORDER: tuple[str, ...] = (
    "kathmandu",
    "pokhara",
    "chitwan",
    "biratnagar",
    "janakpur",
    "birgunj",
    "butwal",
    "nepalgunj",
    "dhangadhi",
)
WEATHER_MORE_ORDER: tuple[str, ...] = (
    "itahari",
    "bharatpur",
    "hetauda",
    "bhairahawa",
    "surkhet",
    "dadeldhura",
    "tulsipur",
    "gorkha",
    "illam",
    "birendranagar",
    "nepalgunj",
    "dhangadhi",
)


def _rows(buttons: list[Btn], per_row: int) -> list[list[Btn]]:
    return [buttons[i : i + per_row] for i in range(0, len(buttons), per_row)]


def home_reply(t: TextFn, *, text: str | None = None, photo: str | None = None) -> Reply:
    return Reply(
        text=text if text is not None else t("home_menu_title"),
        reply_keyboard=home_keyboard(t),
        photo=photo,
    )


def share_btn(t: TextFn, key: str) -> Btn:
    """A callback button; the key references the stashed block in handlers.share."""
    return Btn(text=t("btn_share"), action=actions.share(key))


def back_btn(t: TextFn, action: str = actions.HOME) -> Btn:
    return Btn(text=t("btn_back"), action=action)


def _mark(active: bool, label: str) -> str:
    """Highlight the reading period the user is currently looking at."""
    return f"• {label}" if active else label


def zodiac_menu(t: TextFn, language: str = "en") -> Reply:
    buttons = [
        Btn(text=sign_label(slug, language), action=actions.horoscope_sign(slug)) for slug in SIGNS
    ]
    rows = _rows(buttons, 3)
    rows.append([back_btn(t)])
    return Reply(text=t("horo_pick_sign"), inline=rows, edit_message=True)


def horoscope_buttons(
    t: TextFn,
    sign: str,
    *,
    can_save: bool,
    share_key: str,
    period: str = "d",
) -> list[list[Btn]]:
    periods = [
        Btn(
            text=_mark(period == "d", t("horo_period_today")),
            action=actions.horoscope_sign(sign),
        ),
        Btn(
            text=_mark(period == "w", t("horo_period_week")),
            action=actions.horoscope_period("w", sign),
        ),
        Btn(
            text=_mark(period == "m", t("horo_period_month")),
            action=actions.horoscope_period("m", sign),
        ),
        Btn(
            text=_mark(period == "y", t("horo_period_year")),
            action=actions.horoscope_period("y", sign),
        ),
    ]
    first = (
        Btn(text=t("btn_save_default"), action=actions.horoscope_save(sign))
        if can_save
        else Btn(text=t("horo_change_sign"), action=actions.horoscope_change())
    )
    return [_rows(periods, 2)[0], _rows(periods, 2)[1], [first, share_btn(t, share_key)], [back_btn(t, actions.horoscope_change())]]


def forex_buttons(t: TextFn, share_key: str) -> list[list[Btn]]:
    return [
        [Btn(text=t("btn_calculator_short"), action=actions.FOREX_CALC), share_btn(t, share_key)],
    ]


def currency_grid(t: TextFn, codes: list[str], *, more: bool = False) -> Reply:
    buttons = [
        Btn(text=f"{flag(code)} {code}", action=actions.forex_currency(code))
        for code in codes
    ]
    rows = _rows(buttons, 3)
    if more:
        rows.append([Btn(text=t("btn_more_currencies"), action=actions.FOREX_MORE)])
    rows.append([back_btn(t, actions.FOREX_RATES)])
    return Reply(text=t("fx_calc_pick"), inline=rows, edit_message=True)


def amount_picker(t: TextFn, currency: str, quick: list[int]) -> Reply:
    amounts = [Btn(text=f"{n:,}", action=actions.forex_amount(n)) for n in quick]
    rows = _rows(amounts, 3)
    rows.append([Btn(text=t("btn_type_another"), action=actions.FOREX_TYPE_ANOTHER)])
    rows.append([back_btn(t, actions.FOREX_CALC)])
    prompt = f"{t('calc_prompt', currency=currency)}\n\n{t('calc_type_hint')}"
    return Reply(text=prompt, inline=rows, edit_message=True)


def conversion_buttons(t: TextFn, currency: str, share_key: str) -> list[list[Btn]]:
    return [
        [Btn(text=t("btn_convert_again"), action=actions.forex_currency(currency)), share_btn(t, share_key)],
        [back_btn(t, actions.FOREX_RATES)],
    ]


def veg_menu(t: TextFn) -> Reply:
    return Reply(
        text=t("veg_pick"),
        inline=[
            [
                Btn(text=t("btn_essentials"), action=actions.VEG_ESSENTIALS),
                Btn(text=t("btn_veg_list"), action=actions.VEG_VEGETABLES),
            ],
            [
                Btn(text=t("btn_fruit_list"), action=actions.VEG_FRUITS),
                Btn(text=t("btn_greens"), action=actions.VEG_GREENS),
            ],
            [
                Btn(text=t("btn_trends"), action=actions.VEG_TRENDS),
                Btn(text=t("btn_more_veg"), action=actions.VEG_MORE),
            ],
            [back_btn(t)],
        ],
        edit_message=True,
    )


def result_buttons(
    t: TextFn,
    *,
    back_action: str | None = None,
    share_key: str | None = None,
) -> list[list[Btn]]:
    row: list[Btn] = []
    if back_action:
        row.append(back_btn(t, back_action))
    if share_key:
        row.append(share_btn(t, share_key))
    return [row] if row else []


def weather_city_grid(t: TextFn, more: bool = False) -> Reply:
    cities = city_list()
    if more:
        order = [key for key in WEATHER_MORE_ORDER if key not in WEATHER_ORDER]
    else:
        order = WEATHER_ORDER
    keys = [key for key in order if key in cities]
    if not keys and not more:
        keys = [key for key in WEATHER_ORDER if key in cities] or list(cities)
    buttons = [Btn(text=t(f"city_{key}"), action=actions.weather_city(key)) for key in keys]
    rows = _rows(buttons, 3)
    nav_row = []
    if not more and any((c in WEATHER_MORE_ORDER and c not in WEATHER_ORDER and c in cities) for c in (WEATHER_MORE_ORDER)):
        nav_row.append(Btn(text=t("btn_more"), action=actions.WX_MORE))
    nav_row.append(back_btn(t, actions.WX_MENU))
    rows.append(nav_row)
    return Reply(text=t("wx_pick"), inline=rows, edit_message=True)


def news_buttons(t: TextFn, links: list[dict[str, str]]) -> list[list[Btn]]:
    rows: list[list[Btn]] = []
    for index, item in enumerate(links, start=1):
        if not item.get("link"):
            continue
        label = item["title"].strip()
        if len(label) > 46:
            label = label[:45].rstrip() + "..."
        rows.append([Btn(text=f"{index}. {label}", url=item["link"])])
    rows.append([Btn(text=t("btn_refresh"), action=actions.NEWS_LATEST)])
    return rows
