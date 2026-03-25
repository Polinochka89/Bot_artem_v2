from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import aiosqlite

from src.domain.entities import CollectionRun, Price
from src.domain.ports import IPriceRepository
from src.domain.value_objects import DataCategory
from src.infrastructure.database.schemas import (
    CREATE_COLLECTION_RUNS_TABLE,
    CREATE_PRICES_LOOKUP_INDEX,
    CREATE_PRICES_TABLE,
    PRAGMA_STATEMENTS,
)


class SQLitePriceRepository(IPriceRepository):
    def __init__(
        self: SQLitePriceRepository,
        db_path: str = "data/finance_bot.db",
    ) -> None:
        self._db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self: SQLitePriceRepository) -> None:
        connection = await self._ensure_connection()

        for pragma in PRAGMA_STATEMENTS:
            await connection.execute(pragma)

        await connection.execute(CREATE_COLLECTION_RUNS_TABLE)
        await connection.execute(CREATE_PRICES_TABLE)
        await connection.execute(CREATE_PRICES_LOOKUP_INDEX)
        await connection.commit()

    async def save_prices(
        self: SQLitePriceRepository,
        prices: list[Price],
        run_id: int,
    ) -> None:
        if not prices:
            return

        connection = await self._ensure_connection()
        rows = [self._price_to_row(price=price, run_id=run_id) for price in prices]

        await connection.executemany(
            """
            INSERT OR IGNORE INTO prices (
                run_id, symbol, category, value, buy, sell, source,
                display_name, emoji, collected_at, date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        await connection.commit()

    async def get_previous_price(
        self: SQLitePriceRepository,
        symbol: str,
        category: DataCategory,
        before_date: date,
    ) -> Price | None:
        connection = await self._ensure_connection()
        cursor = await connection.execute(
            """
            SELECT symbol, display_name, value, category, source,
                   collected_at, buy, sell, emoji
            FROM prices
            WHERE symbol = ?
              AND category = ?
              AND date < ?
            ORDER BY collected_at DESC
            LIMIT 1
            """,
            (symbol, str(category), before_date.isoformat()),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_price(row)

    async def save_collection_run(
        self: SQLitePriceRepository,
        run: CollectionRun,
    ) -> int:
        connection = await self._ensure_connection()
        has_errors = any(
            result.status in {"FAIL", "OPEN"} or result.error is not None
            for result in run.provider_results
        )

        cursor = await connection.execute(
            """
            INSERT INTO collection_runs (
                started_at,
                finished_at,
                prices_count,
                has_errors
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                run.started_at.isoformat(),
                (run.finished_at.isoformat() if run.finished_at is not None else None),
                run.prices_collected,
                int(has_errors),
            ),
        )
        await connection.commit()

        if cursor.lastrowid is None:
            raise RuntimeError("Failed to obtain run id")
        return int(cursor.lastrowid)

    async def get_last_known_prices(
        self: SQLitePriceRepository, category: DataCategory
    ) -> dict[str, Price]:
        connection = await self._ensure_connection()
        cursor = await connection.execute(
            """
            SELECT p.symbol, p.display_name, p.value, p.category, p.source,
                   p.collected_at, p.buy, p.sell, p.emoji
            FROM prices p
            INNER JOIN (
                SELECT symbol, MAX(collected_at) AS max_ts
                FROM prices
                WHERE category = ?
                GROUP BY symbol
            ) latest ON p.symbol = latest.symbol
                    AND p.collected_at = latest.max_ts
            WHERE p.category = ?
            """,
            (str(category), str(category)),
        )
        rows = await cursor.fetchall()

        result: dict[str, Price] = {}
        for row in rows:
            price = self._row_to_price(row)
            result[price.symbol] = price
        return result

    async def close(self: SQLitePriceRepository) -> None:
        if self._connection is None:
            return

        await self._connection.close()
        self._connection = None

    async def _ensure_connection(self: SQLitePriceRepository) -> aiosqlite.Connection:
        if self._connection is not None:
            return self._connection

        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        return self._connection

    def _price_to_row(
        self: SQLitePriceRepository,
        *,
        price: Price,
        run_id: int,
    ) -> tuple[
        int,
        str,
        str,
        str,
        str | None,
        str | None,
        str,
        str,
        str,
        str,
        str,
    ]:
        return (
            run_id,
            price.symbol,
            str(price.category),
            str(price.value),
            str(price.buy) if price.buy is not None else None,
            str(price.sell) if price.sell is not None else None,
            price.source,
            price.display_name,
            price.emoji,
            price.collected_at.isoformat(),
            price.collected_at.date().isoformat(),
        )

    def _row_to_price(self: SQLitePriceRepository, row: aiosqlite.Row) -> Price:
        return Price(
            symbol=str(row["symbol"]),
            display_name=str(row["display_name"]),
            value=Decimal(str(row["value"])),
            category=DataCategory(str(row["category"])),
            source=str(row["source"]),
            collected_at=datetime.fromisoformat(str(row["collected_at"])),
            buy=Decimal(str(row["buy"])) if row["buy"] is not None else None,
            sell=Decimal(str(row["sell"])) if row["sell"] is not None else None,
            emoji=str(row["emoji"]),
        )
