"""
CEH Catalogue Service extractor.

Fetches dataset metadata from CEH API using dataset file identifiers.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.infrastructure.http_client import AsyncHTTPClient
from src.logging_config import get_logger

logger = get_logger(__name__)


class CEHExtractorError(Exception):
    """Base exception for CEH extractor errors."""

    pass


class CEHExtractor:
    """
    Fetches dataset metadata from CEH Catalogue Service API.

    The CEH API returns ISO 19139 XML metadata for datasets identified by file_identifier.
    """

    # CEH API endpoints (example; adjust for actual CEH service)
    CEH_API_BASE = "https://catalogue.ceh.ac.uk/documents"
    CEH_SEARCH_API = "https://catalogue.ceh.ac.uk/api/documents"

    def __init__(self, http_client: AsyncHTTPClient, request_id: Optional[str] = None):
        """
        Initialize extractor.

        Args:
            http_client: AsyncHTTPClient instance (should be used with context manager)
            request_id: Optional request ID for tracing
        """
        self.http_client = http_client
        self.request_id = request_id

    async def fetch_dataset_xml(self, file_identifier: str) -> str:
        """
        Fetch ISO 19139 XML metadata for a dataset.

        Args:
            file_identifier: Dataset file identifier (UUID)

        Returns:
            XML metadata as string

        Raises:
            CEHExtractorError: If fetch fails
        """
        url = f"{self.CEH_API_BASE}/{file_identifier}.xml"
        try:
            logger.info(
                f"Fetching dataset XML: {file_identifier}",
                extra={"request_id": self.request_id},
            )
            xml = await self.http_client.get_text(url, request_id=self.request_id)
            logger.info(
                f"Fetched dataset XML: {file_identifier}",
                extra={"request_id": self.request_id},
            )
            return xml
        except Exception as e:
            logger.error(
                f"Failed to fetch dataset XML {file_identifier}: {e}",
                extra={"request_id": self.request_id},
            )
            raise CEHExtractorError(f"Failed to fetch {file_identifier}: {e}") from e

    async def fetch_dataset_list(self, limit: int = 100, offset: int = 0) -> list[str]:
        """
        Fetch list of dataset file identifiers from CEH API.

        Args:
            limit: Max results per request
            offset: Pagination offset

        Returns:
            List of file identifiers

        Raises:
            CEHExtractorError: If fetch fails
        """
        url = f"{self.CEH_SEARCH_API}?limit={limit}&offset={offset}"
        try:
            logger.info(
                f"Fetching dataset list (limit={limit}, offset={offset})",
                extra={"request_id": self.request_id},
            )
            response = await self.http_client.get(url, request_id=self.request_id)

            # Extract file identifiers from response
            # (adjust based on actual CEH API response format)
            identifiers = [doc.get("fileIdentifier") for doc in response.get("documents", [])]
            logger.info(
                f"Fetched {len(identifiers)} dataset identifiers",
                extra={"request_id": self.request_id},
            )
            return identifiers
        except Exception as e:
            logger.error(
                f"Failed to fetch dataset list: {e}",
                extra={"request_id": self.request_id},
            )
            raise CEHExtractorError(f"Failed to fetch dataset list: {e}") from e