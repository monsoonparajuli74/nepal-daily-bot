"""Premium UX pieces: art captions, the 2x6 zodiac grid, period buttons and matching."""

from __future__ import annotations

from pathlib import Path

from aiogram.methods import SendMessage, SendPhoto

from app.bot import actions, menus
from app.bot.handlers.veg import _find
from app.bot.i18n import make_translator
from app.channels.base import Btn, Reply
from app.channels.telegram.renderer import render
from app.data.sources.news import _interleave
from app.data.sources.veg import parse_vegetable_payload

T = make_translator("en")


def test_zodiac_grid_is_three_columns_by_four_rows():
    reply = menus.zodiac_menu(T, "en")
    sign_rows = reply.inline[:-1]
    assert len(sign_rows) == 4
    assert all(len(row) == 3 for row in sign_rows)
    assert sum(len(row) for row in sign_rows) == 12
    assert "मेष" in menus.zodiac_menu(T, "ne").inline[0][0].text


def test_horoscope_buttons_offer_all_periods_and_highlight_current():
    rows = menus.horoscope_buttons(
        T,
        "leo",
        can_save=True,
        share_url="https://t.me/share/url?url=x",
        period="m",
    )
    actions_row = [btn.action for row in rows[:2] for btn in row]
    assert actions_row == ["hs:s:leo", "hs:p:w:leo", "hs:p:m:leo", "hs:p:y:leo"]
    assert rows[1][0].text.startswith("• ")
    assert not rows[0][1].text.startswith("• ")


def test_photo_caption_overflow_becomes_follow_up_messages(tmp_path: Path):
    image = tmp_path / "welcome.png"
    image.write_bytes(b"not-a-real-png")
    long_text = "intro line\n\n" + ("a long paragraph. " * 200)
    methods = render(
        Reply(
            text=long_text,
            photo=str(image),
            inline=[[Btn(text="Back", action=actions.HOME)]],
        ),
        7,
    )
    assert isinstance(methods[0], SendPhoto)
    assert methods[0].caption is not None and len(methods[0].caption) <= 1024
    assert all(isinstance(m, SendMessage) for m in methods[1:])
    assert methods[-1].reply_markup is not None
    assert methods[0].reply_markup is None


def test_short_photo_caption_keeps_the_keyboard_on_the_photo(tmp_path: Path):
    image = tmp_path / "welcome.png"
    image.write_bytes(b"x")
    methods = render(
        Reply(text="Namaste", photo=str(image), inline=[[Btn(text="Back", action=actions.HOME)]]),
        7,
    )
    assert len(methods) == 1
    assert methods[0].reply_markup is not None


def test_vegetable_matching_prefers_specific_variants():
    items = parse_vegetable_payload(
        {
            "prices": [
                {"commodityname": "Tomato Big(Indian)", "commodityunit": "KG", "minprice": "1", "avgprice": "1"},
                {"commodityname": "Tomato Small(Local)", "commodityunit": "KG", "minprice": "2", "avgprice": "2"},
                {"commodityname": "Cauli Local", "commodityunit": "KG", "minprice": "3", "avgprice": "3"},
                {"commodityname": "Garlic Green", "commodityunit": "KG", "minprice": "4", "avgprice": "4"},
                {"commodityname": "Garlic Dry Nepali", "commodityunit": "KG", "minprice": "5", "avgprice": "5"},
                {"commodityname": "Brd Leaf Mustard", "commodityunit": "KG", "minprice": "6", "avgprice": "6"},
                {"commodityname": "Mustard Leaf", "commodityunit": "KG", "minprice": "7", "avgprice": "7"},
            ]
        }
    )
    assert _find(items, {"match": ["tomato small local", "tomato"]})["name"] == "Tomato Small(Local)"
    assert _find(items, {"match": ["cauli", "cauliflower"]})["name"] == "Cauli Local"
    assert _find(items, {"match": ["garlic dry", "garlic"]})["name"] == "Garlic Dry Nepali"
    assert _find(items, {"match": ["brd leaf", "broad leaf"]})["name"] == "Brd Leaf Mustard"
    assert _find(items, {"match": ["mustard leaf"]})["name"] == "Mustard Leaf"
    assert _find(items, {"match": ["fenugreek"]}) is None


def test_news_interleaves_feeds_for_variety():
    group_a = [{"title": "a1"}, {"title": "a2"}]
    group_b = [{"title": "b1"}]
    assert [item["title"] for item in _interleave([group_a, group_b])] == ["a1", "b1", "a2"]
