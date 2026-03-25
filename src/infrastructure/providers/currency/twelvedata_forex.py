from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http import HttpClient
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class TwelveDataForexProvider(BaseProvider):
    _URL = "https://api.twelvedata.com/quote"

    def __init__(
        self: TwelveDataForexProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        api_key: str | None,
    ) -> None:
        super().__init__(http, circuit_breaker, retry_policy)
        self._api_key = api_key

    @property
    def name(self: TwelveDataForexProvider) -> str:
        return "twelvedata_forex"

    async def _do_fetch(
        self: TwelveDataForexProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key is missing")

        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        result: dict[str, Price] = {}
        for instrument in supported:
            pair = instrument.get_ticker(self.name)
            if pair is None:
                continue

            payload = await self._http.get_json(
                self._URL,
                params={"symbol": pair, "apikey": self._api_key},
            )
            quote = self._parse_payload(payload)
            if quote is None:
                continue

            close = self._validate_price(instrument.symbol, quote.get("close"))
            bid_raw = quote.get("bid")
            ask_raw = quote.get("ask")
            bid = (
                None
                if bid_raw is None
                else self._validate_price(instrument.symbol, bid_raw)
            )
            ask = (
                None
                if ask_raw is None
                else self._validate_price(instrument.symbol, ask_raw)
            )
            value = (
                (bid + ask) / Decimal("2")
                if bid is not None and ask is not None
                else close
            )

            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                buy=bid,
                sell=ask,
            )

        return result

    def _parse_payload(
        self: TwelveDataForexProvider,
        payload: JsonValue,
    ) -> Mapping[str, object] | None:
        if not isinstance(payload, Mapping):
            raise DataValidationError(self.name, "*", "payload is not an object")

        status = payload.get("status")
        if isinstance(status, str) and status.lower() == "error":
            return None

        return payload
