from dataclasses import FrozenInstanceError

import pytest

from src.domain.entities import Instrument
from src.domain.value_objects import DataCategory

pytestmark = pytest.mark.unit


def _make_instrument() -> Instrument:
    return Instrument(
        symbol="BTC",
        display_name="Bitcoin",
        category=DataCategory.CRYPTO,
        emoji="₿",
        ticker_map={"coingecko": "bitcoin", "coincap": "bitcoin"},
    )


def test_get_ticker_returns_ticker_for_known_provider() -> None:
    instrument = _make_instrument()
    assert instrument.get_ticker("coingecko") == "bitcoin"


def test_get_ticker_returns_none_for_unknown_provider() -> None:
    instrument = _make_instrument()
    assert instrument.get_ticker("unknown") is None


def test_instrument_is_frozen() -> None:
    instrument = _make_instrument()
    with pytest.raises(FrozenInstanceError):
        instrument.symbol = "ETH"
