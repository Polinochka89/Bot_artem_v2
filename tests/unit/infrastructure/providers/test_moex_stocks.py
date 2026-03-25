from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.value_objects import DataCategory
from src.infrastructure.providers.stocks import MoexStocksProvider


@pytest.mark.unit
@pytest.mark.asyncio
async def test_moex_stocks_parses_iss_payload(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    fake_http_client.json_payload = {
        "marketdata": {
            "columns": ["SECID", "LAST"],
            "data": [["SBER", 300.01], ["GAZP", 174.2]],
        }
    }

    provider = MoexStocksProvider(fake_http_client, fake_cb, fake_retry)
    instruments = [
        make_instrument("SBER", DataCategory.STOCKS, {"moex": "SBER"}),
        make_instrument("GAZP", DataCategory.STOCKS, {"moex": "GAZP"}),
    ]

    result = await provider._do_fetch(instruments)

    assert result["SBER"].value == Decimal("300.01")
    assert result["GAZP"].value == Decimal("174.2")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_moex_stocks_ignores_missing_symbol(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    fake_http_client.json_payload = {
        "marketdata": {
            "columns": ["SECID", "LAST"],
            "data": [["SBER", 300.01]],
        }
    }

    provider = MoexStocksProvider(fake_http_client, fake_cb, fake_retry)
    instruments = [
        make_instrument("SBER", DataCategory.STOCKS, {"moex": "SBER"}),
        make_instrument("GAZP", DataCategory.STOCKS, {"moex": "GAZP"}),
    ]

    result = await provider._do_fetch(instruments)

    assert set(result.keys()) == {"SBER"}
