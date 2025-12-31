"""
Web folder traverser for discovering files via HTTP directory listings.

Handles:
- HTML directory index parsing
- Apache/Nginx/Windows directory listings
- Recursive file discovery
- URL normalization
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from src.infrastructure.http_client import AsyncHTTPClient, HTTPClientError
from src.logging_config import get_logger

logger = get_logger(__name__)


class WebFolderTraverserError(Exception):
    """Base exception for web traversal errors."""
    pass


class WebFolderTraverser:
    """
    Discovers and traverses web-accessible folders.

    Supports:
    - Apache directory listings
    - Nginx directory listings
    - Windows IIS directory listings
    - Custom HTML patterns
    """

    def __init__(self, http_client: AsyncHTTPClient):
        """
        Initialize traverser.

        Args:
            http_client: AsyncHTTPClient instance
        """
        self.http_client = http_client
        self.visited = set()

    async def discover_files(
        self,
        folder_url: str,
        request_id: Optional[str] = None,
        recursive: bool = True,
        max_depth: int = 3,
    ) -> list[str]:
        """
        Discover files in web folder.

        Args:
            folder_url: Root folder URL
            request_id: Optional request ID for tracing
            recursive: Whether to traverse subdirectories
            max_depth: Maximum recursion depth

        Returns:
            List of discovered file URLs

        Raises:
            WebFolderTraverserError: If traversal fails
        """
        try:
            self.visited = set()
            files = await self._traverse(
                folder_url, request_id, recursive, max_depth, depth=0
            )
            logger.info(
                f"Discovered {len(files)} files in {folder_url}",
                extra={"request_id": request_id},
            )
            return files
        except Exception as e:
            logger.error(
                f"Web folder traversal failed for {folder_url}: {e}",
                extra={"request_id": request_id},
            )
            raise WebFolderTraverserError(f"Traversal failed: {e}") from e

    async def _traverse(
        self,
        folder_url: str,
        request_id: Optional[str],
        recursive: bool,
        max_depth: int,
        depth: int,
    ) -> list[str]:
        """
        Recursive folder traversal.

        Args:
            folder_url: Current folder URL
            request_id: Request ID for tracing
            recursive: Whether to recurse
            max_depth: Maximum depth
            depth: Current depth

        Returns:
            List of file URLs discovered
        """
        # Prevent infinite loops
        if depth > max_depth or folder_url in self.visited:
            return []

        self.visited.add(folder_url)

        try:
            html = await self.http_client.get_text(folder_url, request_id=request_id)
            links = self._extract_links(html, folder_url)

            files = []
            folders = []

            for link in links:
                if self._is_file(link):
                    files.append(link)
                elif self._is_folder(link) and recursive:
                    folders.append(link)

            # Recursively traverse folders
            if recursive and folders:
                for folder_url_next in folders:
                    sub_files = await self._traverse(
                        folder_url_next, request_id, recursive, max_depth, depth + 1
                    )
                    files.extend(sub_files)

            return files

        except HTTPClientError as e:
            logger.warning(f"Failed to access {folder_url}: {e}")
            return []

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """
        Extract links from HTML directory listing.

        Args:
            html: HTML content
            base_url: Base URL for relative links

        Returns:
            List of discovered URLs
        """
        links = []

        # Pattern 1: href="filename.ext" (Apache, Nginx)
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html):
            href = match.group(1)
            if href and not href.startswith(("?", "#")):
                link = urljoin(base_url, href)
                links.append(link)

        # Pattern 2: <a href=filename> (older HTML)
        for match in re.finditer(r"<a\s+href=([^\s>]+)", html, re.IGNORECASE):
            href = match.group(1)
            link = urljoin(base_url, href)
            links.append(link)

        # Remove duplicates and invalid URLs
        links = list(set(links))
        links = [l for l in links if l.startswith(("http://", "https://"))]

        return links

    @staticmethod
    def _is_file(url: str) -> bool:
        """Check if URL is likely a file."""
        path = urlparse(url).path.lower()
        file_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".txt",
            ".csv",
            ".zip",
            ".tar",
            ".gz",
            ".xml",
            ".json",
        }
        return any(path.endswith(ext) for ext in file_extensions)

    @staticmethod
    def _is_folder(url: str) -> bool:
        """Check if URL is likely a folder."""
        path = urlparse(url).path
        # Folders typically end with / and don't have a file extension
        return path.endswith("/") and "." not in path.split("/")[-1]