from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError
from src.domain.value_objects import DataCategory
from src.infrastructure.providers.base import BaseProvider


class DummyProvider(BaseProvider):
    @property
    def name(self: DummyProvider) -> str:
        return "dummy"

    async def _do_fetch(
        self: DummyProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        supported = self._supported_instruments(instruments)
        return {
            instrument.symbol: self._build_price(instrument, Decimal("1"))
            for instrument in supported
        }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_returns_only_supported(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    provider = DummyProvider(fake_http_client, fake_cb, fake_retry)
    supported = make_instrument("BTC", DataCategory.CRYPTO, {"dummy": "btc"})
    unsupported = make_instrument("ETH", DataCategory.CRYPTO, {"other": "eth"})

    result = await provider.fetch([supported, unsupported])

    assert set(result.keys()) == {"BTC"}


@pytest.mark.unit
def test_validate_price_raises_for_invalid_value(
    fake_http_client,
    fake_cb,
    fake_retry,
) -> None:
    provider = DummyProvider(fake_http_client, fake_cb, fake_retry)

    with pytest.raises(DataValidationError):
        provider._validate_price("BTC", "NaN")
