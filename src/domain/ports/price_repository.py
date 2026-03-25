from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities import CollectionRun, Price
from src.domain.value_objects import DataCategory


class IPriceRepository(ABC):
    @abstractmethod
    async def save_prices(
        self: IPriceRepository, prices: list[Price], run_id: int
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_previous_price(
        self: IPriceRepository,
        symbol: str,
        category: DataCategory,
        before_date: date,
    ) -> Price | None:
        raise NotImplementedError

    @abstractmethod
    async def save_collection_run(
        self: IPriceRepository, run: CollectionRun
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_last_known_prices(
        self: IPriceRepository, category: DataCategory
    ) -> dict[str, Price]:
        raise NotImplementedError

    @abstractmethod
    async def initialize(self: IPriceRepository) -> None:
        raise NotImplementedError
