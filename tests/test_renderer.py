"""Renderer: Reply -> Bot API method objects, including Telegram's limits."""

from __future__ import annotations

import pytest
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.channels.base import Btn, Reply
from app.channels.telegram.renderer import inline_markup, render, reply_markup, split_text


def test_btn_requires_exactly_one_target():
    with pytest.raises(ValueError):
        Btn(text="x")
    with pytest.raises(ValueError):
        Btn(text="x", action="a", url="https://e.test")


def test_render_plain_text_is_one_sendmessage():
    methods = render(Reply(text="hello"), 1)
    assert len(methods) == 1
    assert isinstance(methods[0], SendMessage)
    assert methods[0].chat_id == 1 and methods[0].text == "hello"


def test_render_inline_url_and_callback_buttons():
    reply = Reply(
        text="pick",
        inline=[[Btn(text="Open", url="https://e.test"), Btn(text="Do", action="nav:home")]],
    )
    markup = inline_markup(reply)
    assert isinstance(markup, InlineKeyboardMarkup)
    row = markup.inline_keyboard[0]
    assert row[0].url == "https://e.test" and row[0].callback_data is None
    assert row[1].callback_data == "nav:home"


def test_render_reply_keyboard_is_persistent_grid():
    reply = Reply(text="home", reply_keyboard=[["A", "B", "C"], ["D", "E", "F"]])
    markup = reply_markup(reply)
    assert isinstance(markup, ReplyKeyboardMarkup)
    assert markup.is_persistent is True
    assert [[b.text for b in row] for row in markup.keyboard] == [["A", "B", "C"], ["D", "E", "F"]]


def test_callback_data_is_clipped_to_64_bytes():
    reply = Reply(text="x", inline=[[Btn(text="big", action="fx:cc:" + "A" * 80)]])
    markup = inline_markup(reply)
    encoded = markup.inline_keyboard[0][0].callback_data.encode("utf-8")
    assert len(encoded) <= 64


def test_split_text_keeps_chunks_under_limit():
    chunks = split_text(("para\n\n" * 1000), limit=100)
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert len(chunks) > 1


def test_render_edit_when_message_id_present():
    methods = render(Reply(text="x", edit_message=True), 1, message_id=99)
    assert isinstance(methods[0], EditMessageText)
    assert methods[0].message_id == 99


def test_render_skips_empty_reply():
    assert render(Reply(text=""), 1) == []
