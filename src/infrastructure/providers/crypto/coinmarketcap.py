from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class CoinMarketCapProvider(BaseProvider):
    _URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

    def __init__(
        self: CoinMarketCapProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        api_key: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._api_key = api_key

    @property
    def name(self: CoinMarketCapProvider) -> str:
        return "coinmarketcap"

    async def _do_fetch(
        self: CoinMarketCapProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key is missing")

        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        tickers = [instrument.get_ticker(self.name) for instrument in supported]
        valid_tickers = [ticker for ticker in tickers if ticker is not None]
        if not valid_tickers:
            return {}

        payload = await self._http.get_json(
            self._URL,
            params={"symbol": ",".join(valid_tickers)},
            headers={"X-CMC_PRO_API_KEY": self._api_key},
        )
        data = self._parse_payload(payload)

        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            entry = data.get(ticker.upper())
            quote = self._extract_usd_quote(entry)
            if quote is None:
                continue

            value = self._validate_price(instrument.symbol, quote.get("price"))
            change_raw = quote.get("percent_change_24h")
            change_pct = None if change_raw is None else Decimal(str(change_raw))
            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                change_pct=change_pct,
            )

        return result

    def _parse_payload(
        self: CoinMarketCapProvider,
        payload: JsonValue,
    ) -> Mapping[str, object]:
        if not isinstance(payload, Mapping):
            raise DataValidationError(self.name, "*", "payload is not an object")

        status = payload.get("status")
        if isinstance(status, Mapping) and status.get("error_code") not in (0, None):
            message = str(status.get("error_message") or "unknown API error")
            raise ProviderUnavailableError(self.name, message)

        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise DataValidationError(self.name, "*", "missing data field")
        return data

    def _extract_usd_quote(
        self: CoinMarketCapProvider,
        entry: object,
    ) -> Mapping[str, object] | None:
        if isinstance(entry, list):
            if not entry:
                return None
            entry = entry[0]
        if not isinstance(entry, Mapping):
            return None

        quote = entry.get("quote")
        if not isinstance(quote, Mapping):
            return None
        usd = quote.get("USD")
        if not isinstance(usd, Mapping):
            return None
        return usd
