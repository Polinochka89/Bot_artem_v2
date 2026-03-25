from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities import ProviderResult
    from src.domain.value_objects import DataCategory


class FinanceBotError(Exception):
    pass


class ProviderUnavailableError(FinanceBotError):
    def __init__(self: ProviderUnavailableError, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason
        super().__init__(f"Provider '{name}' is unavailable: {reason}")


class DataValidationError(FinanceBotError):
    def __init__(
        self: DataValidationError, name: str, symbol: str, reason: str
    ) -> None:
        self.name = name
        self.symbol = symbol
        self.reason = reason
        message = f"Provider '{name}' returned invalid data for '{symbol}': {reason}"
        super().__init__(message)


class AllProvidersFailedError(FinanceBotError):
    def __init__(
        self: AllProvidersFailedError,
        category: DataCategory,
        results: list[ProviderResult],
    ) -> None:
        self.category = category
        self.results = results
        super().__init__(f"All providers failed for category '{category}'")


class CircuitOpenError(FinanceBotError):
    def __init__(self: CircuitOpenError, provider_name: str) -> None:
        self.provider_name = provider_name
        super().__init__(f"Circuit breaker is open for provider '{provider_name}'")


class ReportSendError(FinanceBotError):
    def __init__(self: ReportSendError, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Failed to send report: {reason}")


class ConfigurationError(FinanceBotError):
    def __init__(self: ConfigurationError, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"Configuration error in '{field}': {reason}")


__all__ = [
    "AllProvidersFailedError",
    "CircuitOpenError",
    "ConfigurationError",
    "DataValidationError",
    "FinanceBotError",
    "ProviderUnavailableError",
    "ReportSendError",
]
