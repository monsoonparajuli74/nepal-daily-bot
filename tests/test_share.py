"""Share/deep-link helpers build valid t.me URLs."""

from __future__ import annotations

from app.bot.handlers import share
from app.utils.share import bot_link, share_text, share_url


def test_bot_link_strips_at_sign():
    assert bot_link("@everyday_bot") == "https://t.me/everyday_bot"
    assert bot_link("") == ""


def test_share_text_includes_bot_link():
    text = share_text("body", "everyday_bot")
    assert "body" in text
    assert "https://t.me/everyday_bot" in text


def test_share_url_points_at_telegram_share_picker():
    url = share_url("body", "everyday_bot")
    assert url.startswith("https://t.me/share/url?")
    assert "everyday_bot" in url


def test_stash_roundtrip_and_unique_keys():
    first_key = share.stash("weather", "Kathmandu 25C")
    second_key = share.stash("weather", "Kathmandu 25C")
    assert first_key != second_key
    assert share._take(first_key) == ("weather", "Kathmandu 25C")
    assert share._take(second_key) == ("weather", "Kathmandu 25C")


def test_stash_unknown_or_expired_key_falls_back_to_generic():
    assert share._take("no-such-key") == ("", "")
