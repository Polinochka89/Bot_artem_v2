from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider


class CryptoCompareProvider(BaseProvider):
    _URL = "https://min-api.cryptocompare.com/data/pricemultifull"

    @property
    def name(self: CryptoCompareProvider) -> str:
        return "cryptocompare"

    async def _do_fetch(
        self: CryptoCompareProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        tickers = [instrument.get_ticker(self.name) for instrument in supported]
        valid_tickers = [ticker for ticker in tickers if ticker is not None]
        if not valid_tickers:
            return {}

        payload = await self._http.get_json(
            self._URL,
            params={"fsyms": ",".join(valid_tickers), "tsyms": "USD"},
        )
        raw_by_symbol = self._parse_payload(payload)

        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            raw_symbol = raw_by_symbol.get(ticker.upper())
            if not isinstance(raw_symbol, Mapping):
                continue

            usd = raw_symbol.get("USD")
            if not isinstance(usd, Mapping):
                continue

            value = self._validate_price(instrument.symbol, usd.get("PRICE"))
            change_raw = usd.get("CHANGEPCT24HOUR")
            change_pct = None if change_raw is None else Decimal(str(change_raw))
            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                change_pct=change_pct,
            )

        return result

    def _parse_payload(
        self: CryptoCompareProvider,
        payload: JsonValue,
    ) -> Mapping[str, object]:
        if not isinstance(payload, Mapping):
            raise DataValidationError(self.name, "*", "payload is not an object")

        raw = payload.get("RAW")
        if not isinstance(raw, Mapping):
            raise DataValidationError(self.name, "*", "missing RAW field")
        return raw
