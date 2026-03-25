from __future__ import annotations

import asyncio
import csv
import io
import secrets
from collections.abc import Mapping

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.providers.base import BaseProvider


class StooqIndicesProvider(BaseProvider):
    _URL = "https://stooq.com/q/l/"

    @property
    def name(self: StooqIndicesProvider) -> str:
        return "stooq"

    async def _do_fetch(
        self: StooqIndicesProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        await self._throttle_request()

        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            text = await self._http.get_text(
                self._URL,
                params={
                    "s": ticker,
                    "f": "sd2t2ohlcv",
                    "h": "",
                    "e": "csv",
                },
            )
            rows = self._parse_csv(text)

            row = rows.get(ticker.upper())
            if row is None:
                continue

            close_value = row.get("Close")
            if close_value is None:
                continue

            try:
                value = self._validate_price(instrument.symbol, close_value)
            except DataValidationError:
                continue
            result[instrument.symbol] = self._build_price(instrument, value)

        return result

    async def _throttle_request(self: StooqIndicesProvider) -> None:
        delay_seed = secrets.randbelow(1_000_000) / 1_000_000
        delay = 0.5 + delay_seed
        await asyncio.sleep(delay)

    def _parse_csv(
        self: StooqIndicesProvider,
        text: str,
    ) -> Mapping[str, dict[str, str]]:
        if text.lstrip().startswith("<"):
            raise ProviderUnavailableError(self.name, "HTML response instead of CSV")

        reader = csv.DictReader(io.StringIO(text))
        by_symbol: dict[str, dict[str, str]] = {}
        for row in reader:
            symbol = row.get("Symbol")
            if not symbol:
                continue
            by_symbol[symbol.upper()] = row
        return by_symbol
