from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from src.domain.value_objects.data_category import DataCategory


@dataclass(frozen=True, slots=True)
class Price:
    symbol: str
    display_name: str
    value: Decimal
    category: DataCategory
    source: str
    collected_at: datetime
    buy: Decimal | None = None
    sell: Decimal | None = None
    change_pct: Decimal | None = None
    emoji: str = ""

    def with_change(self: Price, pct: Decimal) -> Price:
        return replace(self, change_pct=pct)

    @property
    def is_valid(self: Price) -> bool:
        return (
            not self.value.is_nan() and not self.value.is_infinite() and self.value > 0
        )
