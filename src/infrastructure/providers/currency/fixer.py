from __future__ import annotations

from collections.abc import Mapping

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class FixerProvider(BaseProvider):
    _URL = "http://data.fixer.io/api/latest"

    def __init__(
        self: FixerProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        api_key: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._api_key = api_key

    @property
    def name(self: FixerProvider) -> str:
        return "fixer"

    async def _do_fetch(
        self: FixerProvider,
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
        rates = self._parse_payload(payload)

        rub_per_eur = self._validate_price("RUB", rates.get("RUB"))
        result: dict[str, Price] = {}

        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            target = ticker.strip().upper()
            target_per_eur = rates.get(target)
            if target_per_eur is None:
                continue

            target_rate = self._validate_price(instrument.symbol, target_per_eur)
            rub_per_target = rub_per_eur / target_rate
            value = self._validate_price(instrument.symbol, rub_per_target)
            result[instrument.symbol] = self._build_price(instrument, value)

        return result

    def _parse_payload(
        self: FixerProvider,
        payload: JsonValue,
    ) -> Mapping[str, object]:
        if not isinstance(payload, Mapping):
            raise DataValidationError(self.name, "*", "payload is not an object")

        success = payload.get("success")
        if success is False:
            error = payload.get("error")
            message = str(error) if error is not None else "Fixer API error"
            raise ProviderUnavailableError(self.name, message)

        rates = payload.get("rates")
        if not isinstance(rates, Mapping):
            raise DataValidationError(self.name, "*", "missing rates field")
        return rates
