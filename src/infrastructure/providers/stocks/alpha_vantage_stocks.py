from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class AlphaVantageStocksProvider(BaseProvider):
    _URL = "https://www.alphavantage.co/query"

    def __init__(
        self: AlphaVantageStocksProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        api_key: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._api_key = api_key

    @property
    def name(self: AlphaVantageStocksProvider) -> str:
        return "alphavantage"

    async def _do_fetch(
        self: AlphaVantageStocksProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key is missing")

        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            payload = await self._http.get_json(
                self._URL,
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": ticker,
                    "apikey": self._api_key,
                },
            )
            quote = self._parse_payload(payload)
            if quote is None:
                continue

            value = self._validate_price(instrument.symbol, quote.get("05. price"))
            change_pct = self._parse_change(quote.get("10. change percent"))
            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                change_pct=change_pct,
            )

        return result

    def _parse_payload(
        self: AlphaVantageStocksProvider,
        payload: JsonValue,
    ) -> Mapping[str, object] | None:
        if not isinstance(payload, Mapping):
            raise DataValidationError(self.name, "*", "payload is not an object")

        if (
            "Note" in payload
            or "Information" in payload
            or "Error Message" in payload
        ):
            return None

        quote = payload.get("Global Quote")
        if not isinstance(quote, Mapping):
            return None
        return quote

    def _parse_change(
        self: AlphaVantageStocksProvider,
        value: object,
    ) -> Decimal | None:
        if value is None:
            return None
        normalized = str(value).replace("%", "").strip()
        if not normalized:
            return None
        return Decimal(normalized)
