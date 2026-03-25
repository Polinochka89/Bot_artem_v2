from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.exceptions import ProviderUnavailableError
from src.domain.value_objects import DataCategory
from src.infrastructure.providers.indices import StooqIndicesProvider


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stooq_indices_parses_csv(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    fake_http_client.text_payload = (
        "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
        "^WIG,2026-03-25,12:00:00,2800,2900,2790,2872.77,100\n"
    )

    provider = StooqIndicesProvider(fake_http_client, fake_cb, fake_retry)
    provider._throttle_request = _noop_throttle.__get__(provider, StooqIndicesProvider)
    instruments = [
        make_instrument("IMOEX", DataCategory.INDICES, {"stooq": "^WIG"}),
    ]

    result = await provider._do_fetch(instruments)

    assert result["IMOEX"].value == Decimal("2872.77")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stooq_indices_raises_on_html_response(
    fake_http_client,
    fake_cb,
    fake_retry,
    make_instrument,
) -> None:
    fake_http_client.text_payload = "<html>captcha</html>"

    provider = StooqIndicesProvider(fake_http_client, fake_cb, fake_retry)
    provider._throttle_request = _noop_throttle.__get__(provider, StooqIndicesProvider)
    instruments = [
        make_instrument("IMOEX", DataCategory.INDICES, {"stooq": "^WIG"}),
    ]

    with pytest.raises(ProviderUnavailableError):
        await provider._do_fetch(instruments)


async def _noop_throttle(self: StooqIndicesProvider) -> None:
    del self
