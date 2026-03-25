from __future__ import annotations

from decimal import Decimal

from pydantic import ValidationError

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.providers.currency.schemas import ExchangeRateResponse
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class ExchangeRateProvider(BaseProvider):
    _URL_TEMPLATE = "https://v6.exchangerate-api.com/v6/{api_key}/latest/RUB"

    def __init__(
        self: ExchangeRateProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        api_key: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._api_key = api_key

    @property
    def name(self: ExchangeRateProvider) -> str:
        return "exchangerate"

    async def _do_fetch(
        self: ExchangeRateProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key is missing")

        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        payload = await self._http.get_json(
            self._URL_TEMPLATE.format(api_key=self._api_key)
        )
        parsed = self._parse_payload(payload)
        if parsed.result.lower() != "success":
            raise ProviderUnavailableError(self.name, "unsuccessful API response")

        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            rate = parsed.conversion_rates.get(ticker)
            if rate is None:
                continue

            value = self._to_rub_price(instrument.symbol, rate)
            result[instrument.symbol] = self._build_price(instrument, value)

        return result

    def _parse_payload(
        self: ExchangeRateProvider,
        payload: JsonValue,
    ) -> ExchangeRateResponse:
        if not isinstance(payload, dict):
            raise DataValidationError(self.name, "*", "payload is not an object")
        try:
            return ExchangeRateResponse.model_validate(payload)
        except ValidationError as error:
            raise ProviderUnavailableError(
                self.name,
                f"invalid payload schema: {error}",
            ) from error

    def _to_rub_price(self: ExchangeRateProvider, symbol: str, quote: float) -> Decimal:
        normalized = self._validate_price(symbol, quote)
        if normalized == 0:
            raise DataValidationError(self.name, symbol, "zero conversion rate")
        return Decimal("1") / normalized
