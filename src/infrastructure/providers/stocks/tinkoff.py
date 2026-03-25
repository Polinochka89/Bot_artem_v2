from __future__ import annotations

from decimal import Decimal

from pydantic import ValidationError

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.providers.stocks.schemas import TinkoffResponse
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class TinkoffProvider(BaseProvider):
    _URL = (
        "https://invest-public-api.tinkoff.ru/rest/"
        "tinkoff.public.invest.api.contract.v1.MarketDataService/GetLastPrices"
    )

    def __init__(
        self: TinkoffProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        token: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._token = token

    @property
    def name(self: TinkoffProvider) -> str:
        return "tinkoff"

    async def _do_fetch(
        self: TinkoffProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        if not self._token:
            raise ProviderUnavailableError(self.name, "API token is missing")

        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        ids = [instrument.get_ticker(self.name) for instrument in supported]
        valid_ids = [ticker for ticker in ids if ticker is not None]
        if not valid_ids:
            return {}

        payload = await self._http.post_json(
            self._URL,
            body={"instrumentId": valid_ids},
            headers={"Authorization": f"Bearer {self._token}"},
        )

        parsed = self._parse_payload(payload)
        by_id: dict[str, Decimal] = {}
        for item in parsed.last_prices:
            if item.instrument_uid is None and item.figi is None:
                continue
            identifier_for_validation = item.figi or item.instrument_uid or "*"
            units = self._validate_price(identifier_for_validation, item.price.units)
            nanos = Decimal(item.price.nano or 0) / Decimal(1_000_000_000)
            value = units + nanos

            if item.figi is not None:
                by_id[item.figi] = value
            if item.instrument_uid is not None:
                by_id[item.instrument_uid] = value

        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            resolved_value = by_id.get(ticker)
            if resolved_value is None:
                continue
            result[instrument.symbol] = self._build_price(instrument, resolved_value)

        return result

    def _parse_payload(self: TinkoffProvider, payload: JsonValue) -> TinkoffResponse:
        if not isinstance(payload, dict):
            raise DataValidationError(self.name, "*", "payload is not an object")
        try:
            return TinkoffResponse.model_validate(payload)
        except ValidationError as error:
            raise ProviderUnavailableError(
                self.name,
                f"invalid payload schema: {error}",
            ) from error
