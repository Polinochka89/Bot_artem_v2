from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.value_objects.data_category import DataCategory


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    display_name: str
    category: DataCategory
    emoji: str
    ticker_map: dict[str, str] = field(default_factory=dict)

    def get_ticker(self: Instrument, provider_name: str) -> str | None:
        return self.ticker_map.get(provider_name)
