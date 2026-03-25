from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.providers.crypto.schemas import CoinGeckoPriceData


class CoinGeckoProvider(BaseProvider):
    _URL = "https://api.coingecko.com/api/v3/simple/price"

    @property
    def name(self: CoinGeckoProvider) -> str:
        return "coingecko"

    async def _do_fetch(
        self: CoinGeckoProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        ids = [instrument.get_ticker(self.name) for instrument in supported]
        valid_ids = [ticker for ticker in ids if ticker is not None]
        if not valid_ids:
            return {}

        payload = await self._http.get_json(
            self._URL,
            params={
                "ids": ",".join(valid_ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
        )

        parsed = self._parse_payload(payload)
        result: dict[str, Price] = {}

        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            ticker_data = parsed.get(ticker)
            if ticker_data is None:
                continue

            value = self._validate_price(instrument.symbol, ticker_data.usd)
            change_pct = (
                Decimal(str(ticker_data.usd_24h_change))
                if ticker_data.usd_24h_change is not None
                else None
            )
            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                change_pct=change_pct,
            )

        return result

    def _parse_payload(
        self: CoinGeckoProvider,
        payload: JsonValue,
    ) -> Mapping[str, CoinGeckoPriceData]:
        if not isinstance(payload, dict):
            raise DataValidationError(self.name, "*", "payload is not an object")

        adapter = TypeAdapter(dict[str, CoinGeckoPriceData])
        try:
            return adapter.validate_python(payload)
        except ValidationError as error:
            raise ProviderUnavailableError(
                self.name,
                f"invalid payload schema: {error}",
            ) from error
