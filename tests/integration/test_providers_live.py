from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest

from src.domain.entities import Instrument, Price
from src.domain.value_objects import DataCategory
from src.infrastructure.http import HttpClient
from src.infrastructure.providers import BaseProvider
from src.infrastructure.providers.crypto import (
    CoinCapProvider,
    CoinGeckoProvider,
    CoinMarketCapProvider,
    CryptoCompareProvider,
)
from src.infrastructure.providers.currency import (
    CbrCurrencyProvider,
    CurrencyLayerProvider,
    ExchangeRateProvider,
    FixerProvider,
)
from src.infrastructure.providers.goods import CbrGoodsProvider, StooqGoodsProvider
from src.infrastructure.providers.indices import (
    AlphaVantageIndicesProvider,
    MoexIndicesProvider,
    StooqIndicesProvider,
    TwelveDataIndicesProvider,
)
from src.infrastructure.providers.stocks import (
    AlphaVantageStocksProvider,
    MoexStocksProvider,
    TinkoffProvider,
    TwelveDataStocksProvider,
)
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_PROVIDER_TESTS") != "1",
        reason="Set RUN_LIVE_PROVIDER_TESTS=1 to run live provider integration tests",
    ),
]


def _instrument(
    symbol: str,
    category: DataCategory,
    provider_name: str,
    ticker: str,
) -> Instrument:
    return Instrument(
        symbol=symbol,
        display_name=symbol,
        category=category,
        emoji="",
        ticker_map={provider_name: ticker},
    )


def _assert_live_payload(
    result: dict[str, Price],
    instruments: list[Instrument],
) -> None:
    assert result
    expected_symbols = {item.symbol for item in instruments}
    assert set(result.keys()).issubset(expected_symbols)
    assert all(price.is_valid for price in result.values())


def _read_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


@pytest.fixture
async def live_http_client() -> AsyncGenerator[HttpClient, None]:
    client = HttpClient(timeout=20)
    await client.start()
    try:
        yield client
    finally:
        await client.stop()


@pytest.fixture
def live_retry_policy() -> RetryPolicy:
    return RetryPolicy(max_attempts=2, base_delay=0.2, max_delay=1.0, jitter=0.2)


def _live_cb(provider_name: str) -> CircuitBreaker:
    return CircuitBreaker(
        provider_name=provider_name,
        failure_threshold=2,
        recovery_timeout=5,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "instruments"),
    [
        (
            "coingecko",
            [_instrument("BTC", DataCategory.CRYPTO, "coingecko", "bitcoin")],
        ),
        (
            "coincap",
            [_instrument("BTC", DataCategory.CRYPTO, "coincap", "bitcoin")],
        ),
        (
            "cryptocompare",
            [_instrument("BTC", DataCategory.CRYPTO, "cryptocompare", "BTC")],
        ),
        (
            "cbr_currency",
            [_instrument("USD", DataCategory.CURRENCY, "cbr", "USD")],
        ),
        (
            "cbr_goods",
            [_instrument("GOLD", DataCategory.GOODS, "cbr", "GOLD")],
        ),
        (
            "stooq_goods",
            [_instrument("GOLD", DataCategory.GOODS, "stooq", "GC.F")],
        ),
        (
            "moex_stocks",
            [_instrument("SBER", DataCategory.STOCKS, "moex", "SBER")],
        ),
        (
            "moex_indices",
            [_instrument("IMOEX", DataCategory.INDICES, "moex_indices", "IMOEX")],
        ),
        (
            "stooq_indices",
            [_instrument("SPX", DataCategory.INDICES, "stooq", "^SPX")],
        ),
    ],
)
async def test_live_providers_without_secrets(
    provider: str,
    instruments: list[Instrument],
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    adapter: BaseProvider
    match provider:
        case "coingecko":
            adapter = CoinGeckoProvider(
                live_http_client,
                _live_cb("coingecko"),
                live_retry_policy,
            )
        case "coincap":
            adapter = CoinCapProvider(
                live_http_client,
                _live_cb("coincap"),
                live_retry_policy,
            )
        case "cryptocompare":
            adapter = CryptoCompareProvider(
                live_http_client,
                _live_cb("cryptocompare"),
                live_retry_policy,
            )
        case "cbr_currency":
            adapter = CbrCurrencyProvider(
                live_http_client,
                _live_cb("cbr"),
                live_retry_policy,
            )
        case "cbr_goods":
            adapter = CbrGoodsProvider(
                live_http_client,
                _live_cb("cbr"),
                live_retry_policy,
            )
        case "stooq_goods":
            adapter = StooqGoodsProvider(
                live_http_client,
                _live_cb("stooq"),
                live_retry_policy,
            )
        case "moex_stocks":
            adapter = MoexStocksProvider(
                live_http_client,
                _live_cb("moex"),
                live_retry_policy,
            )
        case "moex_indices":
            adapter = MoexIndicesProvider(
                live_http_client,
                _live_cb("moex_indices"),
                live_retry_policy,
            )
        case "stooq_indices":
            adapter = StooqIndicesProvider(
                live_http_client,
                _live_cb("stooq"),
                live_retry_policy,
            )
        case _:
            raise AssertionError(f"Unknown provider: {provider}")

    result = await adapter.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_exchangerate_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    api_key = _read_env("EXCHANGERATE_API_KEY")
    if not api_key:
        pytest.skip("EXCHANGERATE_API_KEY is not set")

    provider = ExchangeRateProvider(
        live_http_client,
        _live_cb("exchangerate"),
        live_retry_policy,
        api_key,
    )
    instruments = [_instrument("USD", DataCategory.CURRENCY, "exchangerate", "USD")]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_coinmarketcap_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    api_key = _read_env("COINMARKETCAP_API_KEY")
    if not api_key:
        pytest.skip("COINMARKETCAP_API_KEY is not set")

    provider = CoinMarketCapProvider(
        live_http_client,
        _live_cb("coinmarketcap"),
        live_retry_policy,
        api_key,
    )
    instruments = [_instrument("BTC", DataCategory.CRYPTO, "coinmarketcap", "BTC")]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_tinkoff_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    token = _read_env("TINKOFF_TOKEN", "TINKOFF_API_TOKEN")
    if not token:
        pytest.skip("TINKOFF_TOKEN or TINKOFF_API_TOKEN is not set")

    provider = TinkoffProvider(
        live_http_client,
        _live_cb("tinkoff"),
        live_retry_policy,
        token,
    )
    instruments = [
        _instrument("SBER", DataCategory.STOCKS, "tinkoff", "BBG004730N88"),
    ]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_fixer_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    api_key = _read_env("FIXER_API_KEY")
    if not api_key:
        pytest.skip("FIXER_API_KEY is not set")

    provider = FixerProvider(
        live_http_client,
        _live_cb("fixer"),
        live_retry_policy,
        api_key,
    )
    instruments = [_instrument("USD", DataCategory.CURRENCY, "fixer", "USD")]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_currencylayer_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    api_key = _read_env("CURRENCYLAYER_API_KEY")
    if not api_key:
        pytest.skip("CURRENCYLAYER_API_KEY is not set")

    provider = CurrencyLayerProvider(
        live_http_client,
        _live_cb("currencylayer"),
        live_retry_policy,
        api_key,
    )
    instruments = [
        _instrument("USD", DataCategory.CURRENCY, "currencylayer", "USD"),
    ]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_alphavantage_stocks_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    api_key = _read_env("ALPHAVANTAGE_API_KEY")
    if not api_key:
        pytest.skip("ALPHAVANTAGE_API_KEY is not set")

    provider = AlphaVantageStocksProvider(
        live_http_client,
        _live_cb("alphavantage"),
        live_retry_policy,
        api_key,
    )
    instruments = [_instrument("AAPL", DataCategory.STOCKS, "alphavantage", "AAPL")]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_twelvedata_stocks_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    api_key = _read_env("TWELVE_DATA_API_KEY")
    if not api_key:
        pytest.skip("TWELVE_DATA_API_KEY is not set")

    provider = TwelveDataStocksProvider(
        live_http_client,
        _live_cb("twelvedata"),
        live_retry_policy,
        api_key,
    )
    instruments = [_instrument("AAPL", DataCategory.STOCKS, "twelvedata", "AAPL")]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_alphavantage_indices_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    api_key = _read_env("ALPHAVANTAGE_API_KEY")
    if not api_key:
        pytest.skip("ALPHAVANTAGE_API_KEY is not set")

    provider = AlphaVantageIndicesProvider(
        live_http_client,
        _live_cb("alphavantage_indices"),
        live_retry_policy,
        api_key,
    )
    instruments = [
        _instrument("SPX", DataCategory.INDICES, "alphavantage_indices", "SPY"),
    ]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)


@pytest.mark.asyncio
async def test_live_twelvedata_indices_provider(
    live_http_client: HttpClient,
    live_retry_policy: RetryPolicy,
) -> None:
    api_key = _read_env("TWELVE_DATA_API_KEY")
    if not api_key:
        pytest.skip("TWELVE_DATA_API_KEY is not set")

    provider = TwelveDataIndicesProvider(
        live_http_client,
        _live_cb("twelvedata_indices"),
        live_retry_policy,
        api_key,
    )
    instruments = [
        _instrument("SPX", DataCategory.INDICES, "twelvedata_indices", "SPY"),
    ]

    result = await provider.fetch(instruments)
    _assert_live_payload(result, instruments)
