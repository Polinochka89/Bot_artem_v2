from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import ClassVar

from pydantic import ValidationError

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider
from src.infrastructure.providers.crypto.schemas import CoinCapResponse


class CoinCapProvider(BaseProvider):
    _URL: ClassVar[str] = "https://api.coincap.io/v2/assets"
    _FALLBACK_URL: ClassVar[str] = "https://api.coinpaprika.com/v1/tickers/{coin_id}"
    _COINPAPRIKA_ID_MAP: ClassVar[dict[str, str]] = {
        "bitcoin": "btc-bitcoin",
        "ethereum": "eth-ethereum",
    }

    @property
    def name(self: CoinCapProvider) -> str:
        return "coincap"

    async def _do_fetch(
        self: CoinCapProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        ids = [instrument.get_ticker(self.name) for instrument in supported]
        valid_ids = [ticker for ticker in ids if ticker is not None]
        if not valid_ids:
            return {}

        try:
            payload = await self._http.get_json(
                self._URL,
                params={"ids": ",".join(valid_ids)},
            )
            parsed = self._parse_payload(payload)

            by_id = {item.id: item for item in parsed.data}
            result: dict[str, Price] = {}

            for instrument in supported:
                ticker = instrument.get_ticker(self.name)
                if ticker is None:
                    continue

                asset = by_id.get(ticker)
                if asset is None:
                    continue

                value = self._validate_price(instrument.symbol, asset.price_usd)
                change_pct = self._parse_change(asset.change_percent_24hr)
                result[instrument.symbol] = self._build_price(
                    instrument,
                    value,
                    change_pct=change_pct,
                )

            return result
        except ProviderUnavailableError:
            return await self._fetch_fallback_coinpaprika(supported)

    async def _fetch_fallback_coinpaprika(
        self: CoinCapProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        result: dict[str, Price] = {}
        for instrument in instruments:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            coin_id = self._coinpaprika_id(ticker)
            if coin_id is None:
                continue

            payload = await self._http.get_json(
                self._FALLBACK_URL.format(coin_id=coin_id)
            )
            value, change_pct = self._parse_coinpaprika_payload(
                instrument.symbol,
                payload,
            )
            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                change_pct=change_pct,
            )
        return result

    def _coinpaprika_id(self: CoinCapProvider, ticker: str) -> str | None:
        normalized = ticker.strip().lower()
        return self._COINPAPRIKA_ID_MAP.get(normalized)

    def _parse_coinpaprika_payload(
        self: CoinCapProvider,
        symbol: str,
        payload: JsonValue,
    ) -> tuple[Decimal, Decimal | None]:
        if not isinstance(payload, Mapping):
            raise DataValidationError(
                self.name,
                symbol,
                "fallback payload is not an object",
            )

        quotes = payload.get("quotes")
        if not isinstance(quotes, Mapping):
            raise DataValidationError(
                self.name,
                symbol,
                "fallback payload has no quotes",
            )
        usd = quotes.get("USD")
        if not isinstance(usd, Mapping):
            raise DataValidationError(
                self.name,
                symbol,
                "fallback payload has no USD quote",
            )

        price_raw = usd.get("price")
        value = self._validate_price(symbol, price_raw)

        change_raw = usd.get("percent_change_24h")
        change_pct = None if change_raw is None else Decimal(str(change_raw))
        return value, change_pct

    def _parse_payload(self: CoinCapProvider, payload: JsonValue) -> CoinCapResponse:
        if not isinstance(payload, dict):
            raise DataValidationError(self.name, "*", "payload is not an object")
        try:
            return CoinCapResponse.model_validate(payload)
        except ValidationError as error:
            raise ProviderUnavailableError(
                self.name,
                f"invalid payload schema: {error}",
            ) from error

    def _parse_change(self: CoinCapProvider, value: str | None) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError) as error:
            raise DataValidationError(
                self.name,
                "*",
                "invalid changePercent24Hr",
            ) from error
