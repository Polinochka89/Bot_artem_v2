from __future__ import annotations

from src.infrastructure.providers.stocks.alpha_vantage_stocks import (
    AlphaVantageStocksProvider,
)


class AlphaVantageGoodsProvider(AlphaVantageStocksProvider):
    @property
    def name(self: AlphaVantageGoodsProvider) -> str:
        return "alphavantage_goods"
