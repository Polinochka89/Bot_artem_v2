from __future__ import annotations

from src.infrastructure.providers.goods.yahoo_goods import YahooBaseProvider


class YahooStocksProvider(YahooBaseProvider):
    @property
    def name(self: YahooStocksProvider) -> str:
        return "yahoo_stocks"
