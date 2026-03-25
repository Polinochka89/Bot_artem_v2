from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src.domain.entities import Instrument
from src.domain.value_objects import DataCategory
from src.infrastructure.http import HttpClient
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.providers.crypto import (
    CoinCapProvider,
    CoinGeckoProvider,
    CoinMarketCapProvider,
    CryptoCompareProvider,
)
from src.infrastructure.providers.currency import (
    AlphaVantageForexProvider,
    CbrCurrencyProvider,
    CurrencyLayerProvider,
    ExchangeRateProvider,
    FixerProvider,
    TwelveDataForexProvider,
)
from src.infrastructure.providers.goods import (
    AlphaVantageGoodsProvider,
    CbrGoodsProvider,
    StooqGoodsProvider,
    TwelveDataGoodsProvider,
    YahooGoodsProvider,
)
from src.infrastructure.providers.indices import (
    AlphaVantageIndicesProvider,
    MoexIndicesProvider,
    StooqIndicesProvider,
    TwelveDataIndicesProvider,
    YahooIndicesProvider,
)
from src.infrastructure.providers.stocks import (
    AlphaVantageStocksProvider,
    MoexStocksProvider,
    TinkoffProvider,
    TwelveDataStocksProvider,
)
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


@dataclass(frozen=True, slots=True)
class ProviderCheckCase:
    name: str
    provider: BaseProvider
    instruments: list[Instrument]
    missing_credentials_reason: str | None = None
    require_buy_sell: bool = False


@dataclass(frozen=True, slots=True)
class ProviderCheckResult:
    provider: str
    status: str
    count: int
    sample: str
    error: str


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


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
            continue
        key, value = cleaned.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _read_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _table(results: list[ProviderCheckResult]) -> str:
    headers = ["provider", "status", "count", "sample", "error"]
    rows = [
        [
            result.provider,
            result.status,
            str(result.count),
            result.sample,
            result.error,
        ]
        for result in results
    ]

    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def render_row(values: list[str]) -> str:
        cells = [value.ljust(widths[idx]) for idx, value in enumerate(values)]
        return " | ".join(cells)

    separator = "-+-".join("-" * width for width in widths)
    output_lines = [render_row(headers), separator]
    output_lines.extend(render_row(row) for row in rows)
    return "\n".join(output_lines)


def _sample_symbol_values(captured: dict[str, object] | Mapping[str, object]) -> str:
    items: list[str] = []
    for symbol, price in list(captured.items())[:6]:
        value = getattr(price, "value", None)
        items.append(f"{symbol}={value}")
    return ", ".join(items)


async def _run_case(case: ProviderCheckCase) -> ProviderCheckResult:
    if case.missing_credentials_reason is not None:
        return ProviderCheckResult(
            provider=case.name,
            status="SKIP",
            count=0,
            sample="",
            error=case.missing_credentials_reason,
        )

    try:
        result = await case.provider.fetch(case.instruments)
        if case.require_buy_sell and result:
            missing_buy_sell = [
                symbol
                for symbol, price in result.items()
                if price.buy is None or price.sell is None
            ]
            if missing_buy_sell:
                return ProviderCheckResult(
                    provider=case.name,
                    status="ERROR",
                    count=len(result),
                    sample=_sample_symbol_values(result),
                    error="missing buy/sell for: " + ",".join(missing_buy_sell),
                )

        return ProviderCheckResult(
            provider=case.name,
            status="OK" if result else "EMPTY",
            count=len(result),
            sample=_sample_symbol_values(result),
            error="",
        )
    except Exception as error:
        return ProviderCheckResult(
            provider=case.name,
            status="ERROR",
            count=0,
            sample="",
            error=str(error),
        )


async def main() -> int:
    _load_env_file(Path(".env"))

    http = HttpClient(timeout=20)
    retry = RetryPolicy(max_attempts=2, base_delay=0.2, max_delay=1.0, jitter=0.2)

    exchangerate_key = _read_env("EXCHANGERATE_API_KEY")
    tinkoff_token = _read_env("TINKOFF_TOKEN", "TINKOFF_API_TOKEN")
    coinmarketcap_key = _read_env("COINMARKETCAP_API_KEY")
    fixer_key = _read_env("FIXER_API_KEY")
    currencylayer_key = _read_env("CURRENCYLAYER_API_KEY")
    alphavantage_key = _read_env("ALPHAVANTAGE_API_KEY")
    twelvedata_key = _read_env("TWELVE_DATA_API_KEY")

    cases: list[ProviderCheckCase] = [
        ProviderCheckCase(
            name="coingecko",
            provider=CoinGeckoProvider(http, CircuitBreaker("coingecko", 2, 5), retry),
            instruments=[
                _instrument("BTC", DataCategory.CRYPTO, "coingecko", "bitcoin"),
                _instrument("ETH", DataCategory.CRYPTO, "coingecko", "ethereum"),
                _instrument("XRP", DataCategory.CRYPTO, "coingecko", "ripple"),
                _instrument("SOL", DataCategory.CRYPTO, "coingecko", "solana"),
                _instrument(
                    "TON",
                    DataCategory.CRYPTO,
                    "coingecko",
                    "the-open-network",
                ),
            ],
        ),
        ProviderCheckCase(
            name="coincap",
            provider=CoinCapProvider(http, CircuitBreaker("coincap", 2, 5), retry),
            instruments=[
                _instrument("BTC", DataCategory.CRYPTO, "coincap", "bitcoin"),
                _instrument("ETH", DataCategory.CRYPTO, "coincap", "ethereum"),
                _instrument("XRP", DataCategory.CRYPTO, "coincap", "xrp"),
                _instrument("SOL", DataCategory.CRYPTO, "coincap", "solana"),
                _instrument("TON", DataCategory.CRYPTO, "coincap", "toncoin"),
            ],
        ),
        ProviderCheckCase(
            name="cryptocompare",
            provider=CryptoCompareProvider(
                http,
                CircuitBreaker("cryptocompare", 2, 5),
                retry,
            ),
            instruments=[
                _instrument("BTC", DataCategory.CRYPTO, "cryptocompare", "BTC"),
                _instrument("ETH", DataCategory.CRYPTO, "cryptocompare", "ETH"),
                _instrument("XRP", DataCategory.CRYPTO, "cryptocompare", "XRP"),
                _instrument("SOL", DataCategory.CRYPTO, "cryptocompare", "SOL"),
                _instrument("TON", DataCategory.CRYPTO, "cryptocompare", "TON"),
            ],
        ),
        ProviderCheckCase(
            name="coinmarketcap",
            provider=CoinMarketCapProvider(
                http,
                CircuitBreaker("coinmarketcap", 2, 5),
                retry,
                coinmarketcap_key,
            ),
            instruments=[
                _instrument("BTC", DataCategory.CRYPTO, "coinmarketcap", "BTC"),
                _instrument("ETH", DataCategory.CRYPTO, "coinmarketcap", "ETH"),
                _instrument("XRP", DataCategory.CRYPTO, "coinmarketcap", "XRP"),
                _instrument("SOL", DataCategory.CRYPTO, "coinmarketcap", "SOL"),
                _instrument("TON", DataCategory.CRYPTO, "coinmarketcap", "TON"),
            ],
            missing_credentials_reason=(
                None if coinmarketcap_key else "missing COINMARKETCAP_API_KEY"
            ),
        ),
        ProviderCheckCase(
            name="cbr_currency",
            provider=CbrCurrencyProvider(http, CircuitBreaker("cbr", 2, 5), retry),
            instruments=[
                _instrument("USD", DataCategory.CURRENCY, "cbr", "USD"),
                _instrument("EUR", DataCategory.CURRENCY, "cbr", "EUR"),
                _instrument("CNY", DataCategory.CURRENCY, "cbr", "CNY"),
            ],
        ),
        ProviderCheckCase(
            name="exchangerate",
            provider=ExchangeRateProvider(
                http,
                CircuitBreaker("exchangerate", 2, 5),
                retry,
                exchangerate_key,
            ),
            instruments=[
                _instrument("USD", DataCategory.CURRENCY, "exchangerate", "USD"),
                _instrument("EUR", DataCategory.CURRENCY, "exchangerate", "EUR"),
                _instrument("CNY", DataCategory.CURRENCY, "exchangerate", "CNY"),
            ],
            missing_credentials_reason=(
                None if exchangerate_key else "missing EXCHANGERATE_API_KEY"
            ),
        ),
        ProviderCheckCase(
            name="fixer",
            provider=FixerProvider(
                http,
                CircuitBreaker("fixer", 2, 5),
                retry,
                fixer_key,
            ),
            instruments=[
                _instrument("USD", DataCategory.CURRENCY, "fixer", "USD"),
                _instrument("EUR", DataCategory.CURRENCY, "fixer", "EUR"),
                _instrument("CNY", DataCategory.CURRENCY, "fixer", "CNY"),
            ],
            missing_credentials_reason=(None if fixer_key else "missing FIXER_API_KEY"),
        ),
        ProviderCheckCase(
            name="currencylayer",
            provider=CurrencyLayerProvider(
                http,
                CircuitBreaker("currencylayer", 2, 5),
                retry,
                currencylayer_key,
            ),
            instruments=[
                _instrument("USD", DataCategory.CURRENCY, "currencylayer", "USD"),
                _instrument("EUR", DataCategory.CURRENCY, "currencylayer", "EUR"),
                _instrument("CNY", DataCategory.CURRENCY, "currencylayer", "CNY"),
            ],
            missing_credentials_reason=(
                None if currencylayer_key else "missing CURRENCYLAYER_API_KEY"
            ),
        ),
        ProviderCheckCase(
            name="alphavantage_forex",
            provider=AlphaVantageForexProvider(
                http,
                CircuitBreaker("alphavantage_forex", 2, 5),
                retry,
                alphavantage_key,
            ),
            instruments=[
                _instrument("USD", DataCategory.CURRENCY, "alphavantage_forex", "USD"),
                _instrument("EUR", DataCategory.CURRENCY, "alphavantage_forex", "EUR"),
                _instrument("CNY", DataCategory.CURRENCY, "alphavantage_forex", "CNY"),
            ],
            missing_credentials_reason=(
                None if alphavantage_key else "missing ALPHAVANTAGE_API_KEY"
            ),
            require_buy_sell=True,
        ),
        ProviderCheckCase(
            name="twelvedata_forex",
            provider=TwelveDataForexProvider(
                http,
                CircuitBreaker("twelvedata_forex", 2, 5),
                retry,
                twelvedata_key,
            ),
            instruments=[
                _instrument("USD", DataCategory.CURRENCY, "twelvedata_forex", "USDRUB"),
                _instrument("EUR", DataCategory.CURRENCY, "twelvedata_forex", "EURRUB"),
                _instrument("CNY", DataCategory.CURRENCY, "twelvedata_forex", "CNYRUB"),
            ],
            missing_credentials_reason=(
                None if twelvedata_key else "missing TWELVE_DATA_API_KEY"
            ),
            require_buy_sell=True,
        ),
        ProviderCheckCase(
            name="cbr_goods",
            provider=CbrGoodsProvider(http, CircuitBreaker("cbr", 2, 5), retry),
            instruments=[_instrument("GOLD", DataCategory.GOODS, "cbr", "GOLD")],
        ),
        ProviderCheckCase(
            name="yahoo_goods",
            provider=YahooGoodsProvider(http, CircuitBreaker("yahoo", 2, 5), retry),
            instruments=[
                _instrument("GOLD", DataCategory.GOODS, "yahoo_goods", "GC=F"),
                _instrument("OIL", DataCategory.GOODS, "yahoo_goods", "BZ=F"),
            ],
        ),
        ProviderCheckCase(
            name="alphavantage_goods",
            provider=AlphaVantageGoodsProvider(
                http, CircuitBreaker("alphavantage", 2, 5), retry, alphavantage_key
            ),
            instruments=[
                _instrument("GOLD", DataCategory.GOODS, "alphavantage_goods", "GLD"),
                _instrument("OIL", DataCategory.GOODS, "alphavantage_goods", "BNO"),
            ],
            missing_credentials_reason=(
                None if alphavantage_key else "missing ALPHAVANTAGE_API_KEY"
            ),
        ),
        ProviderCheckCase(
            name="twelvedata_goods",
            provider=TwelveDataGoodsProvider(
                http, CircuitBreaker("twelvedata", 2, 5), retry, twelvedata_key
            ),
            instruments=[
                _instrument("GOLD", DataCategory.GOODS, "twelvedata_goods", "XAU/USD"),
                _instrument("OIL", DataCategory.GOODS, "twelvedata_goods", "BNO"),
            ],
            missing_credentials_reason=(
                None if twelvedata_key else "missing TWELVE_DATA_API_KEY"
            ),
        ),
        ProviderCheckCase(
            name="stooq_goods",
            provider=StooqGoodsProvider(http, CircuitBreaker("stooq", 2, 5), retry),
            instruments=[
                _instrument("GOLD", DataCategory.GOODS, "stooq", "GC.F"),
                _instrument("OIL", DataCategory.GOODS, "stooq", "CB.F"),
            ],
        ),
        ProviderCheckCase(
            name="moex_stocks",
            provider=MoexStocksProvider(http, CircuitBreaker("moex", 2, 5), retry),
            instruments=[
                _instrument("SBER", DataCategory.STOCKS, "moex", "SBER"),
                _instrument("LKOH", DataCategory.STOCKS, "moex", "LKOH"),
                _instrument("ROSN", DataCategory.STOCKS, "moex", "ROSN"),
            ],
        ),
        ProviderCheckCase(
            name="tinkoff",
            provider=TinkoffProvider(
                http,
                CircuitBreaker("tinkoff", 2, 5),
                retry,
                tinkoff_token,
            ),
            instruments=[
                _instrument("SBER", DataCategory.STOCKS, "tinkoff", "BBG004730N88"),
                _instrument("LKOH", DataCategory.STOCKS, "tinkoff", "BBG004731032"),
                _instrument("ROSN", DataCategory.STOCKS, "tinkoff", "BBG004731354"),
            ],
            missing_credentials_reason=(
                None if tinkoff_token else "missing TINKOFF_TOKEN or TINKOFF_API_TOKEN"
            ),
        ),
        ProviderCheckCase(
            name="alphavantage_stocks",
            provider=AlphaVantageStocksProvider(
                http,
                CircuitBreaker("alphavantage", 2, 5),
                retry,
                alphavantage_key,
            ),
            instruments=[
                _instrument("SBER", DataCategory.STOCKS, "alphavantage", "SBER.ME"),
                _instrument("LKOH", DataCategory.STOCKS, "alphavantage", "LKOH.ME"),
                _instrument("ROSN", DataCategory.STOCKS, "alphavantage", "ROSN.ME"),
            ],
            missing_credentials_reason=(
                None if alphavantage_key else "missing ALPHAVANTAGE_API_KEY"
            ),
        ),
        ProviderCheckCase(
            name="twelvedata_stocks",
            provider=TwelveDataStocksProvider(
                http,
                CircuitBreaker("twelvedata", 2, 5),
                retry,
                twelvedata_key,
            ),
            instruments=[
                _instrument("SBER", DataCategory.STOCKS, "twelvedata", "SBER.ME"),
                _instrument("LKOH", DataCategory.STOCKS, "twelvedata", "LKOH.ME"),
                _instrument("ROSN", DataCategory.STOCKS, "twelvedata", "ROSN.ME"),
            ],
            missing_credentials_reason=(
                None if twelvedata_key else "missing TWELVE_DATA_API_KEY"
            ),
        ),
        ProviderCheckCase(
            name="moex_indices",
            provider=MoexIndicesProvider(
                http,
                CircuitBreaker("moex_indices", 2, 5),
                retry,
            ),
            instruments=[
                _instrument("IMOEX", DataCategory.INDICES, "moex_indices", "IMOEX")
            ],
        ),
        ProviderCheckCase(
            name="yahoo_indices",
            provider=YahooIndicesProvider(http, CircuitBreaker("yahoo", 2, 5), retry),
            instruments=[
                _instrument("SPX", DataCategory.INDICES, "yahoo_indices", "^GSPC"),
                _instrument("SSEC", DataCategory.INDICES, "yahoo_indices", "000001.SS"),
                _instrument(
                    "STOXX50", DataCategory.INDICES, "yahoo_indices", "^STOXX50E"
                ),
            ],
        ),
        ProviderCheckCase(
            name="stooq_indices",
            provider=StooqIndicesProvider(http, CircuitBreaker("stooq", 2, 5), retry),
            instruments=[_instrument("SPX", DataCategory.INDICES, "stooq", "^SPX")],
        ),
        ProviderCheckCase(
            name="alphavantage_indices",
            provider=AlphaVantageIndicesProvider(
                http,
                CircuitBreaker("alphavantage_indices", 2, 5),
                retry,
                alphavantage_key,
            ),
            instruments=[
                _instrument(
                    "SPX",
                    DataCategory.INDICES,
                    "alphavantage_indices",
                    "SPY",
                )
            ],
            missing_credentials_reason=(
                None if alphavantage_key else "missing ALPHAVANTAGE_API_KEY"
            ),
        ),
        ProviderCheckCase(
            name="twelvedata_indices",
            provider=TwelveDataIndicesProvider(
                http,
                CircuitBreaker("twelvedata_indices", 2, 5),
                retry,
                twelvedata_key,
            ),
            instruments=[
                _instrument(
                    "SPX",
                    DataCategory.INDICES,
                    "twelvedata_indices",
                    "SPY",
                ),
                _instrument(
                    "SSEC",
                    DataCategory.INDICES,
                    "twelvedata_indices",
                    "000001.SS",
                ),
                _instrument(
                    "STOXX50",
                    DataCategory.INDICES,
                    "twelvedata_indices",
                    "STOXX50",
                ),
            ],
            missing_credentials_reason=(
                None if twelvedata_key else "missing TWELVE_DATA_API_KEY"
            ),
        ),
    ]

    await http.start()
    try:
        results: list[ProviderCheckResult] = []
        for case in cases:
            results.append(await _run_case(case))
    finally:
        await http.stop()

    print(_table(results))

    has_errors = any(item.status == "ERROR" for item in results)
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
