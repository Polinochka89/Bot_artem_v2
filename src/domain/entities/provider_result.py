from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.domain.value_objects.data_category import DataCategory

ProviderStatus = Literal["SUCCESS", "PARTIAL", "FAIL", "OPEN", "SKIP"]


@dataclass(slots=True)
class ProviderResult:
    provider_name: str
    category: DataCategory
    status: ProviderStatus
    symbols_ok: list[str] = field(default_factory=list)
    symbols_fail: list[str] = field(default_factory=list)
    error: str | None = None
    duration_ms: int | None = None
