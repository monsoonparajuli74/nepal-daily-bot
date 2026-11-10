"""Devanagari <-> Latin digit helpers and Nepali/Indian number grouping."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

DEVANAGARI_DIGITS = "०१२३४५६७८९"
LATIN_DIGITS = "0123456789"
_DEV_TO_LATIN = str.maketrans(DEVANAGARI_DIGITS, LATIN_DIGITS)
_LATIN_TO_DEV = str.maketrans(LATIN_DIGITS, DEVANAGARI_DIGITS)


def to_latin_digits(text: str) -> str:
    """Convert Devanagari digits to ASCII digits."""
    return text.translate(_DEV_TO_LATIN)


def to_devanagari_digits(text: str) -> str:
    """Convert ASCII digits in a string to Devanagari digits."""
    return text.translate(_LATIN_TO_DEV)


def strip_separators(text: str) -> str:
    """Remove spaces, commas and non-breaking spaces commonly used as thousands separators."""
    return text.replace(",", "").replace("\u00a0", "").replace(" ", "").strip()


class AmountError(ValueError):
    """Raised when typed input cannot be parsed into a valid positive money amount."""


#: Maximum accepted remittance amount, guards against absurd input / overflow.
MAX_AMOUNT = Decimal("10000000")


def parse_amount(raw: str) -> Decimal:
    """Parse a user-typed amount.

    Accepts Latin or Devanagari digits, optional commas/spaces, up to 2 decimals.
    """
    if raw is None:
        raise AmountError("empty")
    normalised = strip_separators(to_latin_digits(str(raw)))
    if not normalised:
        raise AmountError("empty")
    if normalised.count(".") > 1:
        raise AmountError("too_many_dots")
    try:
        value = Decimal(normalised)
    except InvalidOperation as exc:  # noqa: TRY003
        raise AmountError("not_a_number") from exc
    if not value.is_finite():
        raise AmountError("not_finite")
    if value <= 0:
        raise AmountError("not_positive")
    if value > MAX_AMOUNT:
        raise AmountError("too_large")
    if -value.as_tuple().exponent > 2:
        raise AmountError("too_many_decimals")
    return value


def group_digits(value: Decimal | int, decimals: int | None = None) -> str:
    """Format a number using the South Asian grouping (e.g. 1234567 -> 12,34,567).

    Mirrors lakh/crore grouping used across Nepal and India. Prices stay in Latin digits.
    """
    if isinstance(value, Decimal):
        quantised = value.quantize(Decimal(1)) if decimals is None else value
        sign = "-" if quantised < 0 else ""
        quantised = abs(quantised)
        if decimals is not None:
            text = f"{quantised:.{decimals}f}"
            int_part, _, frac_part = text.partition(".")
        else:
            # Drop trailing zeros from source values like 200.00 -> 200
            text = format(quantised.normalize(), "f")
            int_part, _, frac_part = text.partition(".")
            if "." in text and decimals is None:
                frac_part = text.split(".", 1)[1]
    else:
        sign = "-" if value < 0 else ""
        int_part = str(abs(int(value)))
        frac_part = ""

    grouped = _group_int(int_part)
    result = grouped
    if frac_part:
        result = f"{grouped}.{frac_part}"
    return sign + result


def _group_int(digits: str) -> str:
    if len(digits) <= 3:
        return digits
    last3 = digits[-3:]
    rest = digits[:-3]
    chunks: list[str] = []
    while len(rest) > 2:
        chunks.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        chunks.insert(0, rest)
    return ",".join([*chunks, last3])


#: Backwards-friendly alias used by the handlers when they only need grouping.
format_number = group_digits


def format_npr(value: Decimal | int, *, unit: bool = False, decimals: int | None = None) -> str:
    """Format a rupee amount with the रू prefix and Nepali digit grouping."""
    body = group_digits(value, decimals=decimals)
    prefix = "रू " if not unit else "रू "
    return f"{prefix}{body}"


def format_decimal(value: Decimal | int, decimals: int = 2) -> str:
    """Plain fixed-point string without grouping (used for rates)."""
    if isinstance(value, Decimal):
        return f"{value:.{decimals}f}".rstrip("0").rstrip(".") or "0"
    return str(value)
