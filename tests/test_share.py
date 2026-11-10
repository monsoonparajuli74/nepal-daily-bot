"""Share/deep-link helpers build valid t.me URLs."""

from __future__ import annotations

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
