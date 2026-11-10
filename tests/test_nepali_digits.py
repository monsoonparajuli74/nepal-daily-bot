from __future__ import annotations

from decimal import Decimal

import pytest

from app.utils.nepali_digits import (
    AmountError,
    format_npr,
    group_digits,
    parse_amount,
    to_devanagari_digits,
    to_latin_digits,
)


def test_devanagari_round_trip():
    text = "2083"
    assert to_latin_digits(to_devanagari_digits(text)) == text


def test_grouping_indian_style():
    assert group_digits(1234567) == "12,34,567"
    assert group_digits(1000) == "1,000"
    assert group_digits(500) == "500"


def test_group_digits_with_decimals():
    assert group_digits(Decimal("1234.5"), decimals=2) == "1,234.50"


def test_parse_amount_accepts_devanagari():
    assert parse_amount("१,०००") == Decimal("1000")


@pytest.mark.parametrize("value", ["", "abc", "0", "-5", "1.234", "999999999999"])
def test_parse_amount_rejects_bad_input(value):
    with pytest.raises(AmountError):
        parse_amount(value)


def test_format_npr_prefix():
    assert format_npr(Decimal("248800")).startswith("रू ")
