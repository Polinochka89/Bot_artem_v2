from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class RetryPolicy:
    def __init__(
        self: RetryPolicy,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        jitter: float = 0.5,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be > 0")
        if base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if max_delay <= 0:
            raise ValueError("max_delay must be > 0")
        if jitter < 0:
            raise ValueError("jitter must be >= 0")

        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._jitter = jitter
        self._retryable_exceptions = retryable_exceptions

    async def execute(
        self: RetryPolicy, coro_factory: Callable[[], Awaitable[T]]
    ) -> T:
        last_error: Exception | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                return await coro_factory()
            except self._retryable_exceptions as error:
                last_error = error
                if attempt == self._max_attempts:
                    break

                delay = self._compute_delay(attempt)
                logger.warning(
                    "Attempt %s/%s failed: %s. Retry in %.2fs",
                    attempt,
                    self._max_attempts,
                    error,
                    delay,
                )
                await asyncio.sleep(delay)

        if last_error is None:
            raise RuntimeError("RetryPolicy failed without captured error")
        raise last_error

    def _compute_delay(self: RetryPolicy, attempt: int) -> float:
        exponential = min(self._base_delay * (2 ** (attempt - 1)), self._max_delay)
        if self._jitter == 0:
            jitter_value = 0.0
        else:
            jitter_seed = int(secrets.randbelow(1_000_000))
            jitter_ratio = jitter_seed / 1_000_000
            jitter_value = self._jitter * jitter_ratio
        return float(exponential + jitter_value)
