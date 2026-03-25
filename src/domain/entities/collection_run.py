from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.provider_result import ProviderResult


@dataclass(slots=True)
class CollectionRun:
    started_at: datetime
    finished_at: datetime | None = None
    provider_results: list[ProviderResult] = field(default_factory=list)
    prices_collected: int = 0

    @property
    def duration_ms(self: CollectionRun) -> int:
        if self.finished_at is None:
            return 0
        return int((self.finished_at - self.started_at).total_seconds() * 1000)

    @property
    def has_any_data(self: CollectionRun) -> bool:
        return self.prices_collected > 0
