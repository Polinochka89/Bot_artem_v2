from __future__ import annotations

from enum import StrEnum, auto


class DataCategory(StrEnum):
    CRYPTO = auto()
    CURRENCY = auto()
    GOODS = auto()
    STOCKS = auto()
    INDICES = auto()
