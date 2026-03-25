from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from src.domain.entities import CollectionRun, Price, ProviderResult
from src.domain.value_objects import DataCategory
from src.infrastructure.database import SQLitePriceRepository


@pytest.fixture
async def repository(tmp_path: pytest.TempPathFactory) -> SQLitePriceRepository:
    db_path = tmp_path / "test_finance_bot.db"
    repo = SQLitePriceRepository(str(db_path))
    await repo.initialize()
    yield repo
    await repo.close()


def make_price(
    *,
    symbol: str,
    value: str,
    category: DataCategory,
    source: str,
    collected_at: datetime,
) -> Price:
    return Price(
        symbol=symbol,
        display_name=symbol,
        value=Decimal(value),
        category=category,
        source=source,
        collected_at=collected_at,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_initialize_creates_tables(repository: SQLitePriceRepository) -> None:
    connection = await repository._ensure_connection()
    cursor = await connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    rows = await cursor.fetchall()
    table_names = {str(row[0]) for row in rows}

    assert "prices" in table_names
    assert "collection_runs" in table_names


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_prices_single(repository: SQLitePriceRepository) -> None:
    price = make_price(
        symbol="BTC",
        value="87147.84",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )

    await repository.save_prices([price], run_id=1)

    connection = await repository._ensure_connection()
    cursor = await connection.execute("SELECT COUNT(*) FROM prices")
    row = await cursor.fetchone()

    assert row is not None
    assert int(row[0]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_prices_batch(repository: SQLitePriceRepository) -> None:
    first = make_price(
        symbol="BTC",
        value="87147.84",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )
    second = make_price(
        symbol="ETH",
        value="3120.11",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )

    await repository.save_prices([first, second], run_id=1)

    connection = await repository._ensure_connection()
    cursor = await connection.execute("SELECT COUNT(*) FROM prices")
    row = await cursor.fetchone()

    assert row is not None
    assert int(row[0]) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_prices_duplicate_ignored(repository: SQLitePriceRepository) -> None:
    price = make_price(
        symbol="BTC",
        value="87147.84",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )

    await repository.save_prices([price], run_id=1)
    await repository.save_prices([price], run_id=2)

    connection = await repository._ensure_connection()
    cursor = await connection.execute("SELECT COUNT(*) FROM prices")
    row = await cursor.fetchone()

    assert row is not None
    assert int(row[0]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_previous_price_found(repository: SQLitePriceRepository) -> None:
    older = make_price(
        symbol="BTC",
        value="86000.00",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 24, 8, 0, tzinfo=UTC),
    )
    newer = make_price(
        symbol="BTC",
        value="87147.84",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )

    await repository.save_prices([older, newer], run_id=1)

    previous = await repository.get_previous_price(
        symbol="BTC",
        category=DataCategory.CRYPTO,
        before_date=date(2026, 3, 25),
    )

    assert previous is not None
    assert previous.value == Decimal("86000.00")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_previous_price_not_found(repository: SQLitePriceRepository) -> None:
    price = make_price(
        symbol="BTC",
        value="87147.84",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )

    await repository.save_prices([price], run_id=1)

    previous = await repository.get_previous_price(
        symbol="BTC",
        category=DataCategory.CRYPTO,
        before_date=date(2026, 3, 25),
    )

    assert previous is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decimal_roundtrip(repository: SQLitePriceRepository) -> None:
    price = make_price(
        symbol="BTC",
        value="87147.84",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )

    await repository.save_prices([price], run_id=1)

    previous = await repository.get_previous_price(
        symbol="BTC",
        category=DataCategory.CRYPTO,
        before_date=date(2026, 3, 26),
    )

    assert previous is not None
    assert previous.value == Decimal("87147.84")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_last_known_prices_dedup(repository: SQLitePriceRepository) -> None:
    old_btc = make_price(
        symbol="BTC",
        value="86000.00",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 24, 8, 0, tzinfo=UTC),
    )
    new_btc = make_price(
        symbol="BTC",
        value="87147.84",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )
    eth = make_price(
        symbol="ETH",
        value="3000.00",
        category=DataCategory.CRYPTO,
        source="coingecko",
        collected_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
    )

    await repository.save_prices([old_btc, new_btc, eth], run_id=1)

    latest = await repository.get_last_known_prices(DataCategory.CRYPTO)

    assert set(latest.keys()) == {"BTC", "ETH"}
    assert latest["BTC"].value == Decimal("87147.84")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_collection_run_returns_id(
    repository: SQLitePriceRepository,
) -> None:
    run = CollectionRun(
        started_at=datetime(2026, 3, 25, 8, 0, tzinfo=UTC),
        prices_collected=1,
        provider_results=[
            ProviderResult(
                provider_name="coingecko",
                category=DataCategory.CRYPTO,
                status="SUCCESS",
            )
        ],
    )

    run_id = await repository.save_collection_run(run)

    assert run_id > 0
