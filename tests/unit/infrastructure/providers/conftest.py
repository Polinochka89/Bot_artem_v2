from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

from src.domain.entities import Instrument, Price
from src.domain.value_objects import DataCategory


class FakeHttpClient:
    def __init__(self: FakeHttpClient) -> None:
        self.json_payload: object | None = None
        self.text_payload: str = ""

    async def get_json(
        self: FakeHttpClient,
        url: str,
        params: Mapping[str, str | int | float] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> object:
        del url, params, headers
        if self.json_payload is None:
            raise RuntimeError("json payload is not set")
        return self.json_payload

    async def get_text(
        self: FakeHttpClient,
        url: str,
        params: Mapping[str, str | int | float] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        del url, params, headers
        return self.text_payload


class FakeCircuitBreaker:
    async def call(self: FakeCircuitBreaker, coro_factory):
        return await coro_factory()


class FakeRetryPolicy:
    async def execute(self: FakeRetryPolicy, coro_factory):
        return await coro_factory()


@pytest.fixture
def fake_http_client() -> FakeHttpClient:
    return FakeHttpClient()


@pytest.fixture
def fake_cb() -> FakeCircuitBreaker:
    return FakeCircuitBreaker()


@pytest.fixture
def fake_retry() -> FakeRetryPolicy:
    return FakeRetryPolicy()


@pytest.fixture
def make_instrument():
    def factory(
        symbol: str,
        category: DataCategory,
        ticker_map: dict[str, str],
    ) -> Instrument:
        return Instrument(
            symbol=symbol,
            display_name=symbol,
            category=category,
            emoji="",
            ticker_map=ticker_map,
        )

    return factory


@pytest.fixture
def make_price():
    def factory(symbol: str, category: DataCategory, source: str) -> Price:
        return Price(
            symbol=symbol,
            display_name=symbol,
            value=1,
            category=category,
            source=source,
            collected_at=datetime.now(UTC),
        )

    return factory
