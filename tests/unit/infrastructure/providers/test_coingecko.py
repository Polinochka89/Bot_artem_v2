from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.value_objects import DataCategory
from src.infrastructure.providers.crypto import CoinGeckoProvider


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coingecko_parses_payload(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    fake_http_client.json_payload = {
        "bitcoin": {"usd": 87147.84, "usd_24h_change": 2.29},
        "ethereum": {"usd": 3120.11, "usd_24h_change": -0.15},
    }

    provider = CoinGeckoProvider(fake_http_client, fake_cb, fake_retry)
    instruments = [
        make_instrument("BTC", DataCategory.CRYPTO, {"coingecko": "bitcoin"}),
        make_instrument("ETH", DataCategory.CRYPTO, {"coingecko": "ethereum"}),
    ]

    result = await provider._do_fetch(instruments)

    assert set(result.keys()) == {"BTC", "ETH"}
    assert result["BTC"].value == Decimal("87147.84")
    assert result["BTC"].change_pct == Decimal("2.29")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_coingecko_partial_success(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    fake_http_client.json_payload = {
        "bitcoin": {"usd": 87147.84},
    }

    provider = CoinGeckoProvider(fake_http_client, fake_cb, fake_retry)
    instruments = [
        make_instrument("BTC", DataCategory.CRYPTO, {"coingecko": "bitcoin"}),
        make_instrument("ETH", DataCategory.CRYPTO, {"coingecko": "ethereum"}),
    ]

    result = await provider._do_fetch(instruments)

    assert set(result.keys()) == {"BTC"}
