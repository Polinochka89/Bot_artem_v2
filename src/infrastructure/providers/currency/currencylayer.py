from __future__ import annotations

from collections.abc import Mapping

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class CurrencyLayerProvider(BaseProvider):
    _URL = "http://api.currencylayer.com/live"

    def __init__(
        self: CurrencyLayerProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        api_key: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._api_key = api_key

    @property
    def name(self: CurrencyLayerProvider) -> str:
        return "currencylayer"

    async def _do_fetch(
        self: CurrencyLayerProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key is missing")

        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        payload = await self._http.get_json(
            self._URL,
            params={"access_key": self._api_key},
        )
        quotes = self._parse_payload(payload)

        usd_rub = self._validate_price("RUB", quotes.get("USDRUB"))
        result: dict[str, Price] = {}

        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            target = ticker.strip().upper()
            if target == "USD":
                divisor: object = 1
            else:
                divisor = quotes.get(f"USD{target}")

            if divisor is None:
                continue

            target_rate = self._validate_price(instrument.symbol, divisor)
            rub_per_target = usd_rub / target_rate
            value = self._validate_price(instrument.symbol, rub_per_target)
            result[instrument.symbol] = self._build_price(instrument, value)

        return result

    def _parse_payload(
        self: CurrencyLayerProvider,
        payload: JsonValue,
    ) -> Mapping[str, object]:
        if not isinstance(payload, Mapping):
            raise DataValidationError(self.name, "*", "payload is not an object")

        success = payload.get("success")
        if success is False:
            error = payload.get("error")
            message = str(error) if error is not None else "CurrencyLayer API error"
            raise ProviderUnavailableError(self.name, message)

        quotes = payload.get("quotes")
        if not isinstance(quotes, Mapping):
            raise DataValidationError(self.name, "*", "missing quotes field")
        return quotes
