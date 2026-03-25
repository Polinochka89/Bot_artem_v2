from __future__ import annotations

from src.infrastructure.providers.stocks.alpha_vantage_stocks import (
    AlphaVantageStocksProvider,
)


class AlphaVantageIndicesProvider(AlphaVantageStocksProvider):
    @property
    def name(self: AlphaVantageIndicesProvider) -> str:
        return "alphavantage_indices"
