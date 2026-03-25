from __future__ import annotations

from collections.abc import Mapping

from pydantic import TypeAdapter, ValidationError

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider


class MoexStocksProvider(BaseProvider):
    _URL = "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"
    _PRICE_FIELDS = (
        "LAST",
        "LCURRENTPRICE",
        "MARKETPRICE",
        "LEGALCLOSEPRICE",
        "PREVPRICE",
    )

    @property
    def name(self: MoexStocksProvider) -> str:
        return "moex"

    async def _do_fetch(
        self: MoexStocksProvider,
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
            params={
                "iss.meta": "off",
                "securities": ",".join(valid_tickers),
            },
        )
        rows_by_secid = self._parse_payload(payload)

        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue
            row = rows_by_secid.get(ticker)
            if row is None:
                continue

            raw_price = self._extract_price(row)
            if raw_price is None:
                continue

            value = self._validate_price(instrument.symbol, raw_price)
            result[instrument.symbol] = self._build_price(instrument, value)

        return result

    def _parse_payload(
        self: MoexStocksProvider,
        payload: JsonValue,
    ) -> Mapping[str, Mapping[str, object]]:
        if not isinstance(payload, dict):
            raise DataValidationError(self.name, "*", "payload is not an object")

        adapter = TypeAdapter(dict[str, object])
        try:
            normalized = adapter.validate_python(payload)
        except ValidationError as error:
            raise ProviderUnavailableError(
                self.name,
                f"invalid payload schema: {error}",
            ) from error

        marketdata = normalized.get("marketdata")
        if not isinstance(marketdata, dict):
            raise ProviderUnavailableError(self.name, "missing marketdata")

        columns = marketdata.get("columns")
        data = marketdata.get("data")
        if not isinstance(columns, list) or not isinstance(data, list):
            raise ProviderUnavailableError(self.name, "invalid marketdata format")

        if "SECID" not in columns:
            raise ProviderUnavailableError(self.name, "SECID column is missing")

        secid_index = columns.index("SECID")
        rows_by_secid: dict[str, Mapping[str, object]] = {}
        for row in data:
            if not isinstance(row, list) or len(row) != len(columns):
                continue
            secid = row[secid_index]
            if not isinstance(secid, str):
                continue
            rows_by_secid[secid] = dict(zip(columns, row, strict=True))

        return rows_by_secid

    def _extract_price(
        self: MoexStocksProvider,
        row: Mapping[str, object],
    ) -> object | None:
        for field in self._PRICE_FIELDS:
            value = row.get(field)
            if value is None:
                continue
            return value
        return None
