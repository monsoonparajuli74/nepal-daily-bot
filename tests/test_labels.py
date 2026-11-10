"""Home keyboard labels route back to actions in either language."""

from __future__ import annotations

from app.bot import actions
from app.bot.i18n import make_translator
from app.bot.labels import home_keyboard, resolve_label


def test_home_keyboard_is_three_by_three():
    keyboard = home_keyboard(make_translator("en"))
    assert len(keyboard) == 3
    assert all(len(row) == 3 for row in keyboard)


def test_labels_resolve_in_both_languages():
    for language in ("en", "ne"):
        t = make_translator(language)
        assert resolve_label(t("btn_horoscope")) == actions.HOROSCOPE_MENU
        assert resolve_label(t("btn_language")) == actions.LANG_TOGGLE


def test_label_resolution_ignores_emoji_and_case():
    label = make_translator("en")("btn_weather")
    assert resolve_label(f"  {label.upper()}  ") == actions.WX_MENU


def test_unknown_label_returns_none():
    assert resolve_label("nonsense") is None
