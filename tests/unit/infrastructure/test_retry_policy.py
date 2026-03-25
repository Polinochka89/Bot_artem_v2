from __future__ import annotations

import asyncio

import pytest

from src.infrastructure.reliability import RetryPolicy


@pytest.mark.unit
@pytest.mark.asyncio
async def test_success_first_attempt() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay=1.0, jitter=0.0)
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await policy.execute(factory)

    assert result == "ok"
    assert calls == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retries_on_failure_then_success() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay=0.01, jitter=0.0)
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("temporary")
        return "ok"

    result = await policy.execute(factory)

    assert result == "ok"
    assert calls == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_after_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay=0.0, jitter=0.0)

    async def factory() -> str:
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        await policy.execute(factory)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exponential_backoff() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=10.0, jitter=0.0)
    recorded_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded_delays.append(delay)

    original_sleep = asyncio.sleep
    asyncio.sleep = fake_sleep

    try:

        async def factory() -> str:
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            await policy.execute(factory)
    finally:
        asyncio.sleep = original_sleep

    assert recorded_delays == [1.0, 2.0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_retryable_exception_is_raised_immediately() -> None:
    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        jitter=0.0,
        retryable_exceptions=(RuntimeError,),
    )
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError, match="not retryable"):
        await policy.execute(factory)

    assert calls == 1
