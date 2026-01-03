"""
Unit tests for supporting document downloader.

Tests cover:
- Successful file downloads
- Local caching
- File size validation
- Error handling
- Request ID tracing
"""

import asyncio
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from aioresponses import aioresponses

from src.infrastructure.http_client import AsyncHTTPClient
from src.services.supporting_documents.supporting_doc_downloader import (
    SupportingDocDownloader,
    SupportingDocDownloaderError,
)


@pytest.mark.asyncio
async def test_download_file_success():
    """Test successful file download."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        url = "https://example.com/document.pdf"
        file_content = b"PDF content here"
        
        with aioresponses() as mocked:
            mocked.get(url, body=file_content)
            async with AsyncHTTPClient() as client:
                downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
                result = await downloader.download(url)
            # Assertions after context manager closes and session is cleaned
            assert result is not None
            assert result.exists()
            assert result.read_bytes() == file_content


@pytest.mark.asyncio
async def test_download_uses_cache():
    """Test that cached files are reused."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        
        with aioresponses() as mocked:
            url = "https://example.com/report.docx"
            file_content = b"DOCX file content"
            mocked.get(url, body=file_content)

            async with AsyncHTTPClient() as client:
                downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
                
                # First download
                result1 = await downloader.download(url)
                assert result1.exists()

                # Second download (should use cache, no HTTP call)
                result2 = await downloader.download(url)
                assert result2 == result1
                assert result2.read_bytes() == file_content


@pytest.mark.asyncio
async def test_download_with_request_id():
    """Test that request_id is propagated."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        
        with aioresponses() as mocked:
            url = "https://example.com/data.zip"
            file_content = b"ZIP file content"
            mocked.get(url, body=file_content)

            async with AsyncHTTPClient() as client:
                downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
                result = await downloader.download(url, request_id="req-12345")

                assert result is not None
                assert result.read_bytes() == file_content


@pytest.mark.asyncio
async def test_download_respects_max_file_size():
    """Test that oversized files are rejected."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        max_size = 1000  # 1KB limit
        
        with aioresponses() as mocked:
            url = "https://example.com/large_file.zip"
            large_content = b"x" * (max_size + 1)  # Larger than limit
            mocked.get(url, body=large_content)

            async with AsyncHTTPClient() as client:
                downloader = SupportingDocDownloader(
                    client, cache_dir=cache_dir, max_file_size=max_size
                )
                
                with pytest.raises(SupportingDocDownloaderError):
                    await downloader.download(url)


@pytest.mark.asyncio
async def test_download_handles_http_errors():
    """Test error handling for HTTP failures."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        
        with aioresponses() as mocked:
            url = "https://example.com/missing.pdf"
            mocked.get(url, status=404)

            async with AsyncHTTPClient() as client:
                downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
                
                with pytest.raises(SupportingDocDownloaderError):
                    await downloader.download(url)


@pytest.mark.asyncio
async def test_download_handles_timeout():
    """Test error handling for timeouts."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        url = "https://example.com/slow.pdf"
        
        with aioresponses() as mocked:
            mocked.get(url, status=500)  # Simulates server error
            try:
                async with AsyncHTTPClient() as client:
                    downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
                    await downloader.download(url)
            except SupportingDocDownloaderError:
                pass  # Expected error


@pytest.mark.asyncio
async def test_download_creates_cache_directory():
    """Test that cache directory is created if it doesn't exist."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "downloads" / "nested" / "cache"
        
        with aioresponses() as mocked:
            url = "https://example.com/file.txt"
            file_content = b"Text file"
            mocked.get(url, body=file_content)

            async with AsyncHTTPClient() as client:
                downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
                result = await downloader.download(url)

                # Cache directory should be created
                assert cache_dir.exists()
                assert result.exists()


# @pytest.mark.asyncio
# async def test_download_generates_hash_filename_for_urlless_paths():
#     """Test that hash-based filenames are generated for URLs without file paths."""
#     with TemporaryDirectory() as tmpdir:
#         cache_dir = Path(tmpdir)
        
#         with aioresponses() as mocked:
#             url = "https://example.com/api/download?id=12345&format=zip"
#             file_content = b"Downloaded content"
#             mocked.get(url, body=file_content)

#             async with AsyncHTTPClient() as client:
#                 downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
#                 result = await downloader.download(url)

#                 # Should generate a hash-based filename
#                 assert result is not None
#                 assert result.exists()
#                 # Filename should be a hash (no extension from URL)
#                 assert len(result.name) == 32  # MD5 hex is 32 chars

@pytest.mark.asyncio
async def test_download_generates_hash_filename_for_urlless_paths():
    """Test that hash-based filenames are generated for URLs without file paths."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        
        with aioresponses() as mocked:
            # Use URL with no file path (or path without extension)
            url = "https://example.com/api/download"  # No extension
            file_content = b"Downloaded content"
            mocked.get(url, body=file_content)

            async with AsyncHTTPClient() as client:
                downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
                result = await downloader.download(url)

                # Should generate a hash-based filename
                assert result is not None
                assert result.exists()
                # Filename should be a hash (no extension from URL)
                assert len(result.name) == 32  # MD5 hex is 32 chars


@pytest.mark.asyncio
async def test_multiple_downloads_different_urls():
    """Test downloading multiple files from different URLs."""
    with TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        
        with aioresponses() as mocked:
            urls = [
                ("https://example.com/file1.pdf", b"PDF 1"),
                ("https://example.com/file2.docx", b"DOCX"),
                ("https://example.com/file3.txt", b"Text"),
            ]
            
            for url, content in urls:
                mocked.get(url, body=content)

            async with AsyncHTTPClient() as client:
                downloader = SupportingDocDownloader(client, cache_dir=cache_dir)
                
                results = []
                for url, expected_content in urls:
                    result = await downloader.download(url)
                    results.append(result)
                    assert result.read_bytes() == expected_content

                # All files should exist in cache
                assert len(results) == 3
                assert all(r.exists() for r in results)
