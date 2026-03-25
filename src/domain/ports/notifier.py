from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities import CollectionRun


class INotifier(ABC):
    @abstractmethod
    async def send_report(self: INotifier, text: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_log_message(self: INotifier, run: CollectionRun) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_log_file(self: INotifier, filepath: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_alert(self: INotifier, text: str) -> None:
        raise NotImplementedError
