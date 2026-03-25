from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from json import JSONDecodeError
from typing import Any, cast
from urllib.parse import urlparse

from aiohttp import (
    ClientError,
    ClientResponse,
    ClientSession,
    ClientTimeout,
    TCPConnector,
)

from src.domain.exceptions import ProviderUnavailableError

logger = logging.getLogger(__name__)

JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class HttpClient:
    def __init__(
        self: HttpClient,
        timeout: int,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self._timeout = ClientTimeout(total=float(timeout))
        self._extra_headers = dict(extra_headers or {})
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    async def start(self: HttpClient) -> None:
        async with self._lock:
            if self._session is not None and not self._session.closed:
                return

            self._session = ClientSession(
                timeout=self._timeout,
                headers=self._merge_headers(headers=None),
                connector=TCPConnector(enable_cleanup_closed=True),
            )

    async def stop(self: HttpClient) -> None:
        async with self._lock:
            if self._session is None:
                return

            if not self._session.closed:
                await self._session.close()
            self._session = None

    async def get_json(
        self: HttpClient,
        url: str,
        params: Mapping[str, str | int | float] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> JsonValue:
        session = self._ensure_session()
        provider_name = self._provider_name(url)
        merged_headers = self._merge_headers(headers)

        logger.debug("GET JSON %s", url)
        try:
            async with session.get(
                url,
                params=params,
                headers=merged_headers,
            ) as response:
                self._raise_on_bad_status(response, provider_name)
                try:
                    payload = await response.json(content_type=None)
                    return cast(JsonValue, payload)
                except (JSONDecodeError, ValueError) as error:
                    raise ProviderUnavailableError(
                        provider_name,
                        f"invalid JSON response: {error}",
                    ) from error
        except TimeoutError as error:
            raise ProviderUnavailableError(provider_name, "timeout") from error
        except ClientError as error:
            raise ProviderUnavailableError(provider_name, str(error)) from error

    async def get_text(
        self: HttpClient,
        url: str,
        params: Mapping[str, str | int | float] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        session = self._ensure_session()
        provider_name = self._provider_name(url)
        merged_headers = self._merge_headers(headers)

        logger.debug("GET TEXT %s", url)
        try:
            async with session.get(
                url,
                params=params,
                headers=merged_headers,
            ) as response:
                self._raise_on_bad_status(response, provider_name)
                return await response.text()
        except TimeoutError as error:
            raise ProviderUnavailableError(provider_name, "timeout") from error
        except ClientError as error:
            raise ProviderUnavailableError(provider_name, str(error)) from error

    async def post_json(
        self: HttpClient,
        url: str,
        body: JsonValue,
        headers: Mapping[str, str] | None = None,
    ) -> JsonValue:
        session = self._ensure_session()
        provider_name = self._provider_name(url)
        merged_headers = self._merge_headers(headers)

        logger.debug("POST JSON %s", url)
        try:
            async with session.post(
                url,
                json=body,
                headers=merged_headers,
            ) as response:
                self._raise_on_bad_status(response, provider_name)
                try:
                    payload = await response.json(content_type=None)
                    return cast(JsonValue, payload)
                except (JSONDecodeError, ValueError) as error:
                    raise ProviderUnavailableError(
                        provider_name,
                        f"invalid JSON response: {error}",
                    ) from error
        except TimeoutError as error:
            raise ProviderUnavailableError(provider_name, "timeout") from error
        except ClientError as error:
            raise ProviderUnavailableError(provider_name, str(error)) from error

    def _merge_headers(
        self: HttpClient, headers: Mapping[str, str] | None
    ) -> dict[str, str]:
        merged: dict[str, str] = {"User-Agent": "FinanceBot/2.0"}
        merged.update(self._extra_headers)
        if headers is not None:
            merged.update(dict(headers))
        return merged

    def _raise_on_bad_status(
        self: HttpClient,
        response: ClientResponse,
        provider_name: str,
    ) -> None:
        if response.status >= 400:
            raise ProviderUnavailableError(
                provider_name,
                f"HTTP status {response.status}",
            )

    def _ensure_session(self: HttpClient) -> ClientSession:
        if self._session is None or self._session.closed:
            raise RuntimeError("HttpClient session is not started")
        return self._session

    def _provider_name(self: HttpClient, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or "unknown"
