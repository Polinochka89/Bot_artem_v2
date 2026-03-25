from __future__ import annotations

import asyncio
from time import monotonic

import pytest

from src.domain.exceptions import CircuitOpenError
from src.infrastructure.reliability import CircuitBreaker, CircuitState


@pytest.mark.unit
@pytest.mark.asyncio
async def test_closed_allows_requests() -> None:
    breaker = CircuitBreaker("provider", failure_threshold=2, recovery_timeout=1)

    async def factory() -> str:
        return "ok"

    result = await breaker.call(factory)

    assert result == "ok"
    assert breaker.get_status()["state"] == CircuitState.CLOSED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_opens_after_threshold() -> None:
    breaker = CircuitBreaker("provider", failure_threshold=2, recovery_timeout=1)

    async def factory() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await breaker.call(factory)
    with pytest.raises(RuntimeError):
        await breaker.call(factory)

    assert breaker.get_status()["state"] == CircuitState.OPEN.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_open_blocks_requests() -> None:
    breaker = CircuitBreaker("provider", failure_threshold=1, recovery_timeout=60)

    async def failed() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await breaker.call(failed)

    called = False

    async def success() -> str:
        nonlocal called
        called = True
        return "ok"

    with pytest.raises(CircuitOpenError):
        await breaker.call(success)

    assert called is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_half_open_after_timeout() -> None:
    breaker = CircuitBreaker("provider", failure_threshold=1, recovery_timeout=1)

    async def failed() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await breaker.call(failed)

    breaker._opened_at = monotonic() - 2

    async def success() -> str:
        return "ok"

    result = await breaker.call(success)

    assert result == "ok"
    assert breaker.get_status()["state"] == CircuitState.CLOSED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_half_open_success_closes() -> None:
    breaker = CircuitBreaker("provider", failure_threshold=1, recovery_timeout=1)

    async def failed() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await breaker.call(failed)

    breaker._opened_at = monotonic() - 2

    async def success() -> str:
        return "ok"

    await breaker.call(success)

    status = breaker.get_status()
    assert status["state"] == CircuitState.CLOSED.value
    assert status["failures"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_half_open_failure_reopens() -> None:
    breaker = CircuitBreaker("provider", failure_threshold=1, recovery_timeout=1)

    async def failed() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await breaker.call(failed)

    breaker._opened_at = monotonic() - 2

    with pytest.raises(RuntimeError):
        await breaker.call(failed)

    assert breaker.get_status()["state"] == CircuitState.OPEN.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_calls_safe() -> None:
    breaker = CircuitBreaker("provider", failure_threshold=1, recovery_timeout=1)
    breaker._state = CircuitState.HALF_OPEN
    breaker._half_open_in_flight = False

    async def slow_success() -> str:
        await asyncio.sleep(0.02)
        return "ok"

    results = await asyncio.gather(
        breaker.call(slow_success),
        breaker.call(slow_success),
        return_exceptions=True,
    )

    successful = [result for result in results if result == "ok"]
    errors = [result for result in results if isinstance(result, CircuitOpenError)]

    assert len(successful) == 1
    assert len(errors) == 1
