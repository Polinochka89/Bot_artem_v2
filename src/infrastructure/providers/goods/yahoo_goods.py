from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar

from src.domain.entities import Instrument, Price
from src.infrastructure.http.client import JsonValue
from src.infrastructure.providers.base import BaseProvider


class YahooBaseProvider(BaseProvider):
    _URL: ClassVar[str] = "https://query1.finance.yahoo.com/v8/finance/chart/"

    async def _do_fetch(
        self: YahooBaseProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        headers = {"User-Agent": "Mozilla/5.0"}
        result: dict[str, Price] = {}

        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            try:
                payload = await self._http.get_json(
                    self._URL + ticker,
                    headers=headers,
                )
                value = self._parse_payload(payload)
                if value is None:
                    continue

                valid_value = self._validate_price(instrument.symbol, value)
                result[instrument.symbol] = self._build_price(
                    instrument,
                    valid_value,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Yahoo error: %s", e)
                continue

        return result

    def _parse_payload(
        self: YahooBaseProvider,
        payload: JsonValue,
    ) -> float | None:
        if not isinstance(payload, Mapping):
            return None

        chart = payload.get("chart")
        if not isinstance(chart, Mapping):
            return None

        result_list = chart.get("result")
        if not isinstance(result_list, list) or not result_list:
            return None

        result_item = result_list[0]
        if not isinstance(result_item, Mapping):
            return None

        meta = result_item.get("meta")
        if not isinstance(meta, Mapping):
            return None

        price = meta.get("regularMarketPrice")
        if price is None:
            return None

        return float(price)


class YahooGoodsProvider(YahooBaseProvider):
    @property
    def name(self: YahooGoodsProvider) -> str:
        return "yahoo_goods"
