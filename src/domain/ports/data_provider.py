from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities import Instrument, Price


class IDataProvider(ABC):
    @property
    @abstractmethod
    def name(self: IDataProvider) -> str:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self: IDataProvider, instruments: list[Instrument]
    ) -> dict[str, Price]:
        raise NotImplementedError

    async def health_check(self: IDataProvider) -> bool:
        try:
            await self.fetch([])
        except Exception:
            return False
        return True
