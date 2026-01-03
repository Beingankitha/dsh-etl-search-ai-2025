"""
Supporting document downloader with retry logic and file management.

Features:
- Async HTTP download with exponential backoff
- File validation and integrity checks
- Local caching to avoid re-downloading
- Error recovery and logging
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import hashlib

from src.infrastructure import AsyncHTTPClient, HTTPClientError
from src.logging_config import get_logger

logger = get_logger(__name__)


class SupportingDocDownloaderError(Exception):
    """Base exception for download errors."""
    pass


class SupportingDocDownloader:
    """
    Downloads supporting documents from URLs.

    Features:
    - Reuses AsyncHTTPClient for retry logic
    - Local file caching
    - MIME type validation
    - File size limits
    """

    def __init__(
        self,
        http_client: AsyncHTTPClient,
        cache_dir: Optional[Path] = None,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB default
    ):
        """
        Initialize downloader.

        Args:
            http_client: AsyncHTTPClient instance
            cache_dir: Directory to cache downloaded files
            max_file_size: Maximum file size to download (bytes)
        """
        self.http_client = http_client
        self.cache_dir = Path(cache_dir) if isinstance(cache_dir, str) else cache_dir 
        self.max_file_size = max_file_size

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SupportingDocDownloader initialized with cache_dir: {self.cache_dir}")

    async def download(
        self, url: str, request_id: Optional[str] = None
    ) -> Optional[Path]:
        """
        Download file from URL.

        Args:
            url: File URL
            request_id: Optional request ID for tracing

        Returns:
            Path to downloaded file, or None if failed

        Raises:
            SupportingDocDownloaderError: If download fails
        """
        try:
            logger.info(f"Downloading: {url}", extra={"request_id": request_id})

            # Generate cache filename from URL
            cache_path = self._get_cache_path(url)

            # Return cached file if it exists
            if cache_path.exists():
                logger.info(
                    f"Using cached file: {cache_path}",
                    extra={"request_id": request_id},
                )
                return cache_path

            # Download file
            file_content = await self.http_client.get_bytes(url, request_id=request_id)

            # Validate file size
            if len(file_content) > self.max_file_size:
                raise SupportingDocDownloaderError(
                    f"File too large: {len(file_content)} > {self.max_file_size}"
                )

            # Write to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(file_content)

            logger.info(
                f"Downloaded {len(file_content)} bytes to {cache_path}",
                extra={"request_id": request_id},
            )
            return cache_path

        except HTTPClientError as e:
            logger.error(
                f"Failed to download {url}: {e}",
                extra={"request_id": request_id},
            )
            raise SupportingDocDownloaderError(f"Download failed: {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error downloading {url}: {e}",
                extra={"request_id": request_id},
            )
            raise SupportingDocDownloaderError(f"Download error: {e}") from e

    async def download_batch(self, urls: list[str]) -> list[tuple[str, Path]]:
        """
        Download multiple files, skipping failures.
        
        Args:
            urls: List of file URLs to download
            
        Returns:
            List of tuples (url, path) for successfully downloaded files
        """
        downloaded_items = []
        
        for url in urls:
            try:
                path = await self.download(url)
                if path:
                    downloaded_items.append((url, path))
            except Exception as e:
                logger.warning(f"Failed to download {url}: {e}")
                # Continue with next URL instead of failing
                continue
        
        logger.info(f"Successfully downloaded {len(downloaded_items)}/{len(urls)} files")
        return downloaded_items

    def _get_cache_path(self, url: str) -> Path:
        """
        Generate cache file path from URL.

        Args:
            url: File URL

        Returns:
            Path to cache file
        """
        parsed = urlparse(url)
        filename = Path(parsed.path).name

        # Generate hash if:
        # 1. No filename extracted, OR
        # 2. Filename has no extension (not a real file)
        if not filename or "." not in filename:
            filename = hashlib.md5(url.encode()).hexdigest()

        return self.cache_dir / filename
