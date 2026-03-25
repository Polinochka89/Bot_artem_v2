from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.domain.entities import Price
from src.domain.value_objects import DataCategory

pytestmark = pytest.mark.unit


def _make_price(value: Decimal) -> Price:
    return Price(
        symbol="BTC",
        display_name="Bitcoin",
        value=value,
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, tzinfo=UTC),
        emoji="₿",
    )


def test_price_is_valid_for_positive_decimal() -> None:
    assert _make_price(Decimal("87147.84")).is_valid is True


def test_price_is_invalid_for_zero_value() -> None:
    assert _make_price(Decimal("0")).is_valid is False


def test_price_is_invalid_for_negative_value() -> None:
    assert _make_price(Decimal("-1")).is_valid is False


def test_price_is_invalid_for_nan() -> None:
    assert _make_price(Decimal("NaN")).is_valid is False


def test_price_is_invalid_for_infinity() -> None:
    assert _make_price(Decimal("Infinity")).is_valid is False


def test_with_change_returns_new_instance_and_keeps_original_immutable() -> None:
    original = _make_price(Decimal("100"))
    updated = original.with_change(Decimal("1.250"))

    assert updated is not original
    assert updated.change_pct == Decimal("1.250")
    assert original.change_pct is None


def test_price_is_frozen() -> None:
    price = _make_price(Decimal("100"))
    with pytest.raises(FrozenInstanceError):
        price.symbol = "ETH"
