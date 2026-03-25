from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities import CollectionRun, ProviderResult
from src.domain.value_objects import DataCategory

pytestmark = pytest.mark.unit


def test_provider_result_defaults_are_initialized() -> None:
    result = ProviderResult(
        provider_name="coingecko",
        category=DataCategory.CRYPTO,
        status="SUCCESS",
    )

    assert result.symbols_ok == []
    assert result.symbols_fail == []
    assert result.error is None
    assert result.duration_ms is None


def test_collection_run_duration_returns_zero_without_finish() -> None:
    run = CollectionRun(started_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC))
    assert run.duration_ms == 0


def test_collection_run_duration_is_calculated_in_milliseconds() -> None:
    started_at = datetime(2026, 3, 25, 8, 0, tzinfo=UTC)
    finished_at = started_at + timedelta(seconds=1, milliseconds=234)
    run = CollectionRun(started_at=started_at, finished_at=finished_at)

    assert run.duration_ms == 1234


def test_collection_run_has_any_data_flag() -> None:
    run = CollectionRun(
        started_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
        prices_collected=2,
    )

    assert run.has_any_data is True
