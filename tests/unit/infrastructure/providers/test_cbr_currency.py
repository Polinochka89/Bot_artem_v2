from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.value_objects import DataCategory
from src.infrastructure.providers.currency import CbrCurrencyProvider


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cbr_currency_parses_xml(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    fake_http_client.text_payload = """
    <ValCurs Date=\"25.03.2026\" name=\"Foreign Currency Market\">
        <Valute ID=\"R01235\">
            <CharCode>USD</CharCode>
            <Nominal>1</Nominal>
            <Value>81,1400</Value>
        </Valute>
        <Valute ID=\"R01239\">
            <CharCode>EUR</CharCode>
            <Nominal>1</Nominal>
            <Value>89,1000</Value>
        </Valute>
    </ValCurs>
    """

    provider = CbrCurrencyProvider(fake_http_client, fake_cb, fake_retry)
    instruments = [
        make_instrument("USD", DataCategory.CURRENCY, {"cbr": "USD"}),
        make_instrument("EUR", DataCategory.CURRENCY, {"cbr": "EUR"}),
    ]

    result = await provider._do_fetch(instruments)

    assert result["USD"].value == Decimal("81.1400")
    assert result["EUR"].value == Decimal("89.1000")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cbr_currency_returns_partial(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    fake_http_client.text_payload = """
    <ValCurs Date=\"25.03.2026\" name=\"Foreign Currency Market\">
        <Valute ID=\"R01235\">
            <CharCode>USD</CharCode>
            <Nominal>1</Nominal>
            <Value>81,1400</Value>
        </Valute>
    </ValCurs>
    """

    provider = CbrCurrencyProvider(fake_http_client, fake_cb, fake_retry)
    instruments = [
        make_instrument("USD", DataCategory.CURRENCY, {"cbr": "USD"}),
        make_instrument("EUR", DataCategory.CURRENCY, {"cbr": "EUR"}),
    ]

    result = await provider._do_fetch(instruments)

    assert set(result.keys()) == {"USD"}
