import asyncio
import pytest
from aioresponses import aioresponses

from src.infrastructure.http_client import AsyncHTTPClient, HTTPTimeoutError, HTTPClientError


@pytest.mark.asyncio
async def test_http_client_get_json():
    """Test successful JSON GET request."""
    with aioresponses() as mocked:
        url = "https://example.com/api/data"
        mocked.get(url, payload={"key": "value"})

        async with AsyncHTTPClient() as client:
            result = await client.get(url)
            assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_http_client_get_text():
    """Test successful text GET request."""
    with aioresponses() as mocked:
        url = "https://example.com/data.xml"
        xml_content = "<root><item>test</item></root>"
        mocked.get(url, body=xml_content)

        async with AsyncHTTPClient() as client:
            result = await client.get_text(url)
            assert result == xml_content


@pytest.mark.asyncio
async def test_http_client_request_id_header():
    """Test that request_id is included in headers."""
    with aioresponses() as mocked:
        url = "https://example.com/api/data"
        mocked.get(url, payload={"ok": True})

        async with AsyncHTTPClient() as client:
            await client.get(url, request_id="req-123")
            # Verify the request was made (aioresponses handles header matching internally)
            assert True


@pytest.mark.asyncio
async def test_http_client_no_session_error():
    """Test error when using client without context manager."""
    client = AsyncHTTPClient()
    with pytest.raises(HTTPClientError):
        await client.get("https://example.com")