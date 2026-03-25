from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class TwelveDataStocksProvider(BaseProvider):
    _URL = "https://api.twelvedata.com/quote"

    def __init__(
        self: TwelveDataStocksProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        api_key: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._api_key = api_key

    @property
    def name(self: TwelveDataStocksProvider) -> str:
        return "twelvedata"

    async def _do_fetch(
        self: TwelveDataStocksProvider,
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
                params={"symbol": ticker, "apikey": self._api_key},
            )
            quote = self._parse_payload(payload)
            if quote is None:
                continue

            value = self._validate_price(instrument.symbol, quote.get("close"))
            change_raw = quote.get("percent_change")
            change_pct = None if change_raw is None else Decimal(str(change_raw))
            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                change_pct=change_pct,
            )

        return result

    def _parse_payload(
        self: TwelveDataStocksProvider,
        payload: JsonValue,
    ) -> Mapping[str, object] | None:
        if not isinstance(payload, Mapping):
            raise DataValidationError(self.name, "*", "payload is not an object")

        status = payload.get("status")
        if isinstance(status, str) and status.lower() == "error":
            return None

        return payload
