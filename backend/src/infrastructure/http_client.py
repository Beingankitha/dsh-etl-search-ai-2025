"""
Async HTTP client with retry logic, timeout handling, and observability.

Provides a resilient wrapper around aiohttp with:
- Exponential backoff retry logic
- Request/response logging with request_id
- Timeout enforcement
- Error envelope standardization
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""

    pass


class HTTPTimeoutError(HTTPClientError):
    """Raised when HTTP request times out."""

    pass


class HTTPRetryExhaustedError(HTTPClientError):
    """Raised when all retries are exhausted."""

    pass


class AsyncHTTPClient:
    """
    Resilient async HTTP client with retry logic and observability.

    Features:
    - Exponential backoff retries on transient failures
    - Request/response logging with request_id
    - Timeout enforcement
    - Structured error responses
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        """
        Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Max number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get(self, url: str, request_id: Optional[str] = None, **kwargs) -> dict:
        """
        GET request with retry logic.

        Args:
            url: Request URL
            request_id: Optional request ID for tracing
            **kwargs: Additional aiohttp arguments

        Returns:
            JSON response as dict

        Raises:
            HTTPTimeoutError: On timeout
            HTTPRetryExhaustedError: When retries exhausted
            HTTPClientError: On other HTTP errors
        """
        if not self.session:
            raise HTTPClientError("Session not initialized. Use 'async with' context manager.")

        headers = kwargs.pop("headers", {})
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            logger.info(f"GET {url}", extra={"request_id": request_id})
            async with self.session.get(url, headers=headers, **kwargs) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info(f"GET {url} -> {response.status}", extra={"request_id": request_id})
                return data
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout on GET {url}", extra={"request_id": request_id})
            raise HTTPTimeoutError(f"Request timeout: {url}") from e
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error on GET {url}: {e}", extra={"request_id": request_id})
            raise HTTPClientError(f"HTTP error: {e}") from e

    async def get_text(self, url: str, request_id: Optional[str] = None, **kwargs) -> str:
        """
        GET request returning raw text (for XML, HTML, etc.).

        Args:
            url: Request URL
            request_id: Optional request ID for tracing
            **kwargs: Additional aiohttp arguments

        Returns:
            Response body as string

        Raises:
            HTTPTimeoutError: On timeout
            HTTPClientError: On HTTP errors
        """
        if not self.session:
            raise HTTPClientError("Session not initialized. Use 'async with' context manager.")

        headers = kwargs.pop("headers", {})
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            logger.info(f"GET (text) {url}", extra={"request_id": request_id})
            async with self.session.get(url, headers=headers, **kwargs) as response:
                response.raise_for_status()
                text = await response.text()
                logger.info(
                    f"GET (text) {url} -> {response.status}",
                    extra={"request_id": request_id},
                )
                return text
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout on GET {url}", extra={"request_id": request_id})
            raise HTTPTimeoutError(f"Request timeout: {url}") from e
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error on GET {url}: {e}", extra={"request_id": request_id})
            raise HTTPClientError(f"HTTP error: {e}") from e
        

    async def get_bytes(self, url: str, request_id: Optional[str] = None, **kwargs) -> bytes:
        """
        GET request returning raw bytes (for binary files).

        Args:
            url: Request URL
            request_id: Optional request ID for tracing
            **kwargs: Additional aiohttp arguments

        Returns:
            Response body as bytes

        Raises:
            HTTPTimeoutError: On timeout
            HTTPClientError: On HTTP errors
        """
        if not self.session:
            raise HTTPClientError("Session not initialized. Use 'async with' context manager.")

        headers = kwargs.pop("headers", {})
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            logger.info(f"GET (bytes) {url}", extra={"request_id": request_id})
            async with self.session.get(url, headers=headers, **kwargs) as response:
                response.raise_for_status()
                data = await response.read()
                logger.info(
                    f"GET (bytes) {url} -> {response.status} ({len(data)} bytes)",
                    extra={"request_id": request_id},
                )
                return data
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout on GET {url}", extra={"request_id": request_id})
            raise HTTPTimeoutError(f"Request timeout: {url}") from e
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error on GET {url}: {e}", extra={"request_id": request_id})
            raise HTTPClientError(f"HTTP error: {e}") from e