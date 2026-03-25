from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum
from time import monotonic
from typing import TypeVar

from src.domain.exceptions import CircuitOpenError

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self: CircuitBreaker,
        provider_name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
    ) -> None:
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be > 0")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")

        self._provider_name = provider_name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_in_flight = False

        self._lock = asyncio.Lock()

    async def call(self: CircuitBreaker, coro_factory: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            self._before_call_locked()

        try:
            result = await coro_factory()
        except Exception:
            await self._on_failure()
            raise

        await self._on_success()
        return result

    def get_status(self: CircuitBreaker) -> dict[str, str | int | float | bool | None]:
        opened_for_seconds: float | None = None
        if self._opened_at is not None:
            opened_for_seconds = monotonic() - self._opened_at

        return {
            "provider_name": self._provider_name,
            "state": self._state.value,
            "failures": self._failure_count,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout,
            "opened_for_seconds": opened_for_seconds,
            "half_open_in_flight": self._half_open_in_flight,
        }

    def _before_call_locked(self: CircuitBreaker) -> None:
        if self._state == CircuitState.OPEN:
            if self._opened_at is None:
                self._opened_at = monotonic()

            elapsed = monotonic() - self._opened_at
            if elapsed >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_in_flight = False
            else:
                raise CircuitOpenError(self._provider_name)

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_in_flight:
                raise CircuitOpenError(self._provider_name)
            self._half_open_in_flight = True

    async def _on_success(self: CircuitBreaker) -> None:
        async with self._lock:
            self._failure_count = 0
            self._opened_at = None
            self._state = CircuitState.CLOSED
            self._half_open_in_flight = False

    async def _on_failure(self: CircuitBreaker) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = monotonic()
                self._half_open_in_flight = False
                return

            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = monotonic()
                self._half_open_in_flight = False
