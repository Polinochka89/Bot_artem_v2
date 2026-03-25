from __future__ import annotations

from src.infrastructure.providers.stocks.twelve_data_stocks import (
    TwelveDataStocksProvider,
)


class TwelveDataIndicesProvider(TwelveDataStocksProvider):
    @property
    def name(self: TwelveDataIndicesProvider) -> str:
        return "twelvedata_indices"
