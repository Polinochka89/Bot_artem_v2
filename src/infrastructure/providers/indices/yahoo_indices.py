from __future__ import annotations

from src.infrastructure.providers.goods.yahoo_goods import YahooBaseProvider


class YahooIndicesProvider(YahooBaseProvider):
    @property
    def name(self: YahooIndicesProvider) -> str:
        return "yahoo_indices"
