from __future__ import annotations

import xml.etree.ElementTree
from decimal import Decimal

from src.domain.entities import Instrument, Price
from src.domain.exceptions import ProviderUnavailableError
from src.infrastructure.providers.base import BaseProvider


class CbrCurrencyProvider(BaseProvider):
    _URL = "https://www.cbr.ru/scripts/XML_daily.asp"

    @property
    def name(self: CbrCurrencyProvider) -> str:
        return "cbr"

    async def _do_fetch(
        self: CbrCurrencyProvider,
        instruments: list[Instrument],
    ) -> dict[str, Price]:
        supported = self._supported_instruments(instruments)
        if not supported:
            return {}

        xml_data = await self._http.get_text(self._URL)
        root = self._parse_xml(xml_data)

        by_code: dict[str, xml.etree.ElementTree.Element] = {}
        for element in root.findall("Valute"):
            code = element.findtext("CharCode")
            if code:
                by_code[code.strip().upper()] = element

        result: dict[str, Price] = {}
        for instrument in supported:
            ticker = instrument.get_ticker(self.name)
            if ticker is None:
                continue

            node = by_code.get(ticker.strip().upper())
            if node is None:
                continue

            nominal = self._parse_decimal(node.findtext("Nominal", default="1"))
            value = self._parse_decimal(node.findtext("Value", default="0"))
            rub_per_unit = self._validate_price(instrument.symbol, value / nominal)

            result[instrument.symbol] = self._build_price(instrument, rub_per_unit)

        return result

    def _parse_xml(
        self: CbrCurrencyProvider,
        xml_data: str,
    ) -> xml.etree.ElementTree.Element:
        try:
            return xml.etree.ElementTree.fromstring(xml_data)  # noqa: S314
        except xml.etree.ElementTree.ParseError as error:
            raise ProviderUnavailableError(
                self.name,
                f"invalid XML response: {error}",
            ) from error

    def _parse_decimal(self: CbrCurrencyProvider, value: str) -> Decimal:
        normalized = value.replace(",", ".").strip()
        return self._validate_price("*", normalized)
