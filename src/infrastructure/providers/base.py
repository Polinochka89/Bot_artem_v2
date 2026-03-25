from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError
from src.domain.ports import IDataProvider
from src.infrastructure.http import HttpClient
from src.infrastructure.reliability import CircuitBreaker, RetryPolicy


class BaseProvider(IDataProvider, ABC):
    def __init__(
        self: BaseProvider,
        http: HttpClient,
        circuit_breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
    ) -> None:
        self._http = http
        self._circuit_breaker = circuit_breaker
        self._retry_policy = retry_policy

    async def fetch(
        self: BaseProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        return await self._circuit_breaker.call(
            lambda: self._retry_policy.execute(
                lambda: self._do_fetch(instruments),
            )
        )

    @abstractmethod
    async def _do_fetch(
        self: BaseProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        raise NotImplementedError

    def _supported_instruments(
        self: BaseProvider,
        instruments: list[Instrument],
    ) -> list[Instrument]:
        return [
            instrument
            for instrument in instruments
            if instrument.get_ticker(self.name) is not None
        ]

    def _validate_price(self: BaseProvider, symbol: str, raw_value: object) -> Decimal:
        try:
            value = Decimal(str(raw_value))
        except (InvalidOperation, ValueError, TypeError) as error:
            raise DataValidationError(
                self.name,
                symbol,
                "invalid decimal value",
            ) from error

        if value.is_nan() or value.is_infinite() or value <= 0:
            raise DataValidationError(self.name, symbol, "value must be finite and > 0")

        return value

    def _build_price(
        self: BaseProvider,
        instrument: Instrument,
        value: Decimal,
        *,
        buy: Decimal | None = None,
        sell: Decimal | None = None,
        change_pct: Decimal | None = None,
    ) -> Price:
        return Price(
            symbol=instrument.symbol,
            display_name=instrument.display_name,
            value=value,
            category=instrument.category,
            source=self.name,
            collected_at=datetime.now(UTC),
            buy=buy,
            sell=sell,
            change_pct=change_pct,
            emoji=instrument.emoji,
        )
