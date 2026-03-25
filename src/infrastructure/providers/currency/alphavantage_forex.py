from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class AlphaVantageForexProvider(BaseProvider):
    _URL = "https://www.alphavantage.co/query"

    def __init__(
        self: AlphaVantageForexProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        api_key: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._api_key = api_key

    @property
    def name(self: AlphaVantageForexProvider) -> str:
        return "alphavantage_forex"

    async def _do_fetch(
        self: AlphaVantageForexProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key is missing")

        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        result: dict[str, Price] = {}
        for instrument in supported:
            quote_ccy = instrument.get_ticker(self.name)
            if quote_ccy is None:
                continue

            payload = await self._http.get_json(
                self._URL,
                params={
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": quote_ccy,
                    "to_currency": "RUB",
                    "apikey": self._api_key,
                },
            )
            quote = self._parse_payload(payload)
            if quote is None:
                continue

            rate = self._validate_price(
                instrument.symbol,
                quote.get("5. Exchange Rate"),
            )
            bid = self._validate_price(instrument.symbol, quote.get("8. Bid Price"))
            ask = self._validate_price(instrument.symbol, quote.get("9. Ask Price"))
            value = (bid + ask) / Decimal("2") if bid and ask else rate

            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                buy=bid,
                sell=ask,
            )

        return result

    def _parse_payload(
        self: AlphaVantageForexProvider,
        payload: JsonValue,
    ) -> Mapping[str, object] | None:
        if not isinstance(payload, Mapping):
            raise DataValidationError(self.name, "*", "payload is not an object")

        if "Note" in payload or "Information" in payload or "Error Message" in payload:
            return None

        quote = payload.get("Realtime Currency Exchange Rate")
        if not isinstance(quote, Mapping):
            return None
        return quote
