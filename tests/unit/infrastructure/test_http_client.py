from __future__ import annotations

from collections.abc import Mapping

import pytest

from src.domain.exceptions import ProviderUnavailableError
from src.infrastructure.http import HttpClient


class FakeResponse:
    def __init__(
        self: FakeResponse,
        *,
        status: int,
        json_data: object | None = None,
        text_data: str = "",
        json_error: Exception | None = None,
    ) -> None:
        self.status = status
        self._json_data = json_data
        self._text_data = text_data
        self._json_error = json_error

    async def __aenter__(self: FakeResponse) -> FakeResponse:
        return self

    async def __aexit__(
        self: FakeResponse,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        return None

    async def json(self: FakeResponse, content_type: str | None = None) -> object:
        del content_type
        if self._json_error is not None:
            raise self._json_error
        return self._json_data

    async def text(self: FakeResponse) -> str:
        return self._text_data


class FakeSession:
    def __init__(
        self: FakeSession,
        *,
        response: FakeResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.closed = False
        self.last_headers: Mapping[str, str] | None = None

    def get(
        self: FakeSession,
        url: str,
        params: Mapping[str, str | int | float] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> FakeResponse:
        del url, params
        self.last_headers = headers
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise RuntimeError("response is not configured")
        return self._response

    async def close(self: FakeSession) -> None:
        self.closed = True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_json_success() -> None:
    client = HttpClient(timeout=10)
    fake = FakeSession(response=FakeResponse(status=200, json_data={"ok": True}))
    client._session = fake  # type: ignore[assignment]

    result = await client.get_json("https://api.test.local/resource")

    assert result == {"ok": True}
    assert fake.last_headers is not None
    assert fake.last_headers["User-Agent"] == "FinanceBot/2.0"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_json_bad_status() -> None:
    client = HttpClient(timeout=10)
    client._session = FakeSession(response=FakeResponse(status=500))  # type: ignore[assignment]

    with pytest.raises(ProviderUnavailableError, match="HTTP status 500"):
        await client.get_json("https://api.test.local/resource")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_json_timeout() -> None:
    client = HttpClient(timeout=10)
    client._session = FakeSession(error=TimeoutError())  # type: ignore[assignment]

    with pytest.raises(ProviderUnavailableError, match="timeout"):
        await client.get_json("https://api.test.local/resource")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_json_malformed_payload() -> None:
    client = HttpClient(timeout=10)
    malformed = FakeResponse(status=200, json_error=ValueError("invalid json"))
    client._session = FakeSession(response=malformed)  # type: ignore[assignment]

    with pytest.raises(ProviderUnavailableError, match="invalid JSON response"):
        await client.get_json("https://api.test.local/resource")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_text_success() -> None:
    client = HttpClient(timeout=10)
    client._session = FakeSession(  # type: ignore[assignment]
        response=FakeResponse(status=200, text_data="hello")
    )

    result = await client.get_text("https://api.test.local/resource")

    assert result == "hello"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stop_is_idempotent() -> None:
    client = HttpClient(timeout=10)
    fake = FakeSession(response=FakeResponse(status=200))
    client._session = fake  # type: ignore[assignment]

    await client.stop()
    await client.stop()

    assert fake.closed is True
