"""Turn-failure logging: traceback location without leaking bot tokens."""

from __future__ import annotations

from app.bot.processor import _redact_secrets, _traceback_location, _traceback_text


def test_redacts_bot_tokens_from_error_text():
    token = "123456789:" + "A" * 35
    message = f"POST https://api.telegram.org/bot{token}/sendMessage failed ({token})"

    redacted = _redact_secrets(message)

    assert token not in redacted
    assert redacted.count("<redacted>") == 2


def test_traceback_location_points_at_the_raise_site():
    def boom():
        raise RuntimeError("bad turn")

    try:
        boom()
    except RuntimeError as exc:
        location = _traceback_location(exc)
        text = _traceback_text(exc)

    assert "boom" in location
    assert "bad turn" in text
