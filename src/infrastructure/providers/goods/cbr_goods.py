from __future__ import annotations

import csv
import io
from decimal import Decimal
from typing import ClassVar

from bs4 import BeautifulSoup
from bs4.element import Tag

from src.domain.entities import Instrument, Price
from src.domain.exceptions import DataValidationError, ProviderUnavailableError
from src.infrastructure.providers.base import BaseProvider


class CbrGoodsProvider(BaseProvider):
    _URL: ClassVar[str] = "https://www.cbr.ru/scripts/xml_metall.asp"
    _STOOQ_URL: ClassVar[str] = "https://stooq.com/q/l/"
    _STOOQ_FALLBACK_MAP: ClassVar[dict[str, str]] = {
        "GOLD": "GC.F",
    }

    @property
    def name(self: CbrGoodsProvider) -> str:
        return "cbr"

    async def _do_fetch(
        self: CbrGoodsProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        try:
            xml_data = await self._http.get_text(self._URL)
            records = self._parse_xml_records(xml_data)
            return self._build_from_cbr_records(supported, records)
        except ProviderUnavailableError:
            return await self._fetch_fallback_stooq(supported)

    def _build_from_cbr_records(
        self: CbrGoodsProvider,
        supported: list[Instrument],
        records: list[Tag],
    ) -> dict[str, Price]:
        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            record = self._match_record(records, ticker)
            if record is None:
                continue

            buy_tag = record.find("Buy")
            sell_tag = record.find("Sell")
            buy = self._parse_decimal(buy_tag.text if buy_tag else "0")
            sell = self._parse_decimal(sell_tag.text if sell_tag else "0")
            average = (buy + sell) / Decimal("2")
            value = self._validate_price(instrument.symbol, average)

            result[instrument.symbol] = self._build_price(
                instrument,
                value,
                buy=buy,
                sell=sell,
            )

        return result

    async def _fetch_fallback_stooq(
        self: CbrGoodsProvider,
        supported: list[Instrument],
    ) -> dict[str, Price]:
        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            stooq_symbol = self._STOOQ_FALLBACK_MAP.get(ticker.strip().upper())
            if stooq_symbol is None:
                continue

            csv_text = await self._http.get_text(
                self._STOOQ_URL,
                params={
                    "s": stooq_symbol,
                    "f": "sd2t2ohlcv",
                    "h": "",
                    "e": "csv",
                },
            )
            close_value = self._extract_stooq_close(csv_text)
            if close_value is None:
                continue

            try:
                value = self._validate_price(instrument.symbol, close_value)
            except DataValidationError:
                continue

            result[instrument.symbol] = self._build_price(instrument, value)
        return result

    def _extract_stooq_close(self: CbrGoodsProvider, csv_text: str) -> str | None:
        reader = csv.DictReader(io.StringIO(csv_text))
        row = next(reader, None)
        if row is None:
            return None
        return row.get("Close")

    def _parse_xml_records(
        self: CbrGoodsProvider,
        xml_data: str,
    ) -> list[Tag]:
        soup = BeautifulSoup(xml_data, "html.parser")
        records = soup.find_all("record")
        if soup.find() is None or not records:
            raise ProviderUnavailableError(
                self.name,
                "invalid XML response",
            )
        return records

    def _match_record(
        self: CbrGoodsProvider,
        records: list[Tag],
        ticker: str,
    ) -> Tag | None:
        upper_ticker = ticker.strip().upper()
        for record in records:
            code = (
                (record.attrs.get("Code") or record.attrs.get("code") or "")
                .strip()
                .upper()
            )
            metal_tag = record.find("metal")
            name_tag = record.find("name")
            metal = (metal_tag.text if metal_tag else "").strip().upper()
            name = (name_tag.text if name_tag else "").strip().upper()
            if upper_ticker in {code, metal, name}:
                return record
        return None

    def _parse_decimal(self: CbrGoodsProvider, value: str) -> Decimal:
        normalized = value.replace(",", ".").strip()
        return self._validate_price("*", normalized)
