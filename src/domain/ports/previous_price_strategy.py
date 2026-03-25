from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.domain.value_objects import DataCategory


class IPreviousPriceStrategy(ABC):
    @abstractmethod
    def get_reference_date(
        self: IPreviousPriceStrategy, category: DataCategory, today: date
    ) -> date:
        raise NotImplementedError
