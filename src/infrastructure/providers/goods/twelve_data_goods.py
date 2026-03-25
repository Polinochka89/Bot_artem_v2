from __future__ import annotations

from src.infrastructure.providers.stocks.twelve_data_stocks import (
    TwelveDataStocksProvider,
)


class TwelveDataGoodsProvider(TwelveDataStocksProvider):
    @property
    def name(self: TwelveDataGoodsProvider) -> str:
        return "twelvedata_goods"
