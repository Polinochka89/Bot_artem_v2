import pytest

from src.domain.entities import ProviderResult
from src.domain.exceptions import (
    AllProvidersFailedError,
    CircuitOpenError,
    ConfigurationError,
    DataValidationError,
    FinanceBotError,
    ProviderUnavailableError,
    ReportSendError,
)
from src.domain.value_objects import DataCategory

pytestmark = pytest.mark.unit


def test_domain_exceptions_inherit_from_base_error() -> None:
    assert issubclass(ProviderUnavailableError, FinanceBotError)
    assert issubclass(DataValidationError, FinanceBotError)
    assert issubclass(AllProvidersFailedError, FinanceBotError)
    assert issubclass(CircuitOpenError, FinanceBotError)
    assert issubclass(ReportSendError, FinanceBotError)
    assert issubclass(ConfigurationError, FinanceBotError)


def test_provider_unavailable_error_contains_context() -> None:
    error = ProviderUnavailableError(name="coingecko", reason="timeout")
    assert "coingecko" in str(error)
    assert "timeout" in str(error)


def test_all_providers_failed_error_stores_results_and_category() -> None:
    results = [
        ProviderResult(
            provider_name="coingecko",
            category=DataCategory.CRYPTO,
            status="FAIL",
            error="timeout",
        )
    ]
    error = AllProvidersFailedError(category=DataCategory.CRYPTO, results=results)

    assert error.category == DataCategory.CRYPTO
    assert error.results == results
