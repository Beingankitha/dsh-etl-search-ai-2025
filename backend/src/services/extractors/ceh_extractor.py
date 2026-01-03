"""
CEH Catalogue Service extractor.

Fetches dataset metadata from CEH API using dataset file identifiers.

CEH API Documentation:
- Base Catalogue: https://catalogue.ceh.ac.uk/
- Documents API: https://catalogue.ceh.ac.uk/documents/{file-identifier}.{format}
- Formats: xml (ISO 19139), json, rdf, schema.org.json
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from src.infrastructure import AsyncHTTPClient
from src.logging_config import get_logger
from src.config import settings

logger = get_logger(__name__)


class CEHExtractorError(Exception):
    """Base exception for CEH extractor errors."""
    pass


class CEHExtractor:
    """
    Fetches dataset metadata from CEH Catalogue Service API.

    The CEH API returns ISO 19139 XML metadata for datasets identified by file_identifier.
    
    URL Patterns:
    - XML: https://catalogue.ceh.ac.uk/documents/{file-identifier}.xml
    - JSON: https://catalogue.ceh.ac.uk/documents/{file-identifier}.json
    - RDF: https://catalogue.ceh.ac.uk/documents/{file-identifier}.rdf
    - Schema.org: https://catalogue.ceh.ac.uk/documents/{file-identifier}.schema.org.json
    """

    # CEH API endpoints
    CEH_API_BASE = "https://catalogue.ceh.ac.uk/documents"
    CEH_SEARCH_API = "https://catalogue.ceh.ac.uk/api/documents"
    CEH_WAF = "https://catalogue.ceh.ac.uk/eidc/documents"  # Web Accessible Folder

    def __init__(
        self,
        http_client: Optional[AsyncHTTPClient] = None,
        request_id: Optional[str] = None,
        max_concurrent: int = 5,
    ):
        """
        Initialize CEH Extractor.

        Args:
            http_client: AsyncHTTPClient instance (optional, will create if not provided)
            request_id: Optional request ID for tracing (default: generate UUID)
            max_concurrent: Maximum concurrent requests
        """
        self.http_client = http_client
        self.request_id = request_id or str(uuid.uuid4())
        self.max_concurrent = max_concurrent
        self._owns_client = False

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if not self.http_client:
            self.http_client = AsyncHTTPClient(
                timeout=settings.ceh_api_timeout,
                max_retries=settings.ceh_api_max_retries,
                max_concurrent=self.max_concurrent,
            )
            self._owns_client = True
            await self.http_client.__aenter__()

    async def fetch_dataset_xml(self, file_identifier: str) -> str:
        """
        Fetch ISO 19139 XML metadata for a dataset.

        Args:
            file_identifier: Dataset file identifier (UUID)

        Returns:
            XML metadata as string

        Raises:
            CEHExtractorError: If fetch fails
            
        Example:
            xml = await extractor.fetch_dataset_xml('d4f0f0a0-0f0a-0f0a-0f0a-0f0a0f0a0f0a')
        """
        await self._ensure_client()

        url = f"{self.CEH_API_BASE}/{file_identifier}.xml"
        try:
            logger.info(
                f"Fetching ISO 19139 XML for dataset: {file_identifier}",
                extra={"request_id": self.request_id},
            )
            xml = await self.http_client.get_text(url, request_id=self.request_id)
            logger.info(
                f"Successfully fetched XML for {file_identifier} ({len(xml)} bytes)",
                extra={"request_id": self.request_id},
            )
            return xml
        except Exception as e:
            logger.error(
                f"Failed to fetch XML for {file_identifier}: {e}",
                extra={"request_id": self.request_id},
            )
            logger.debug(f"XML fetch exception type: {type(e).__name__}, message: {str(e)}")
            raise CEHExtractorError(f"Failed to fetch XML for {file_identifier}: {e}") from e

    async def fetch_dataset_json(self, file_identifier: str) -> dict:
        """
        Fetch JSON metadata for a dataset.

        Args:
            file_identifier: Dataset file identifier (UUID)

        Returns:
            JSON metadata as dict

        Raises:
            CEHExtractorError: If fetch fails
        """
        await self._ensure_client()

        url = f"{self.CEH_API_BASE}/{file_identifier}.json"
        try:
            logger.info(
                f"Fetching JSON metadata for dataset: {file_identifier}",
                extra={"request_id": self.request_id},
            )
            data = await self.http_client.get(url, request_id=self.request_id)
            logger.info(
                f"Successfully fetched JSON for {file_identifier}",
                extra={"request_id": self.request_id},
            )
            return data
        except Exception as e:
            logger.error(
                f"Failed to fetch JSON for {file_identifier}: {e}",
                extra={"request_id": self.request_id},
            )
            raise CEHExtractorError(f"Failed to fetch JSON for {file_identifier}: {e}") from e

    async def fetch_dataset_rdf(self, file_identifier: str) -> str:
        """
        Fetch RDF (Turtle) metadata for a dataset.

        Args:
            file_identifier: Dataset file identifier (UUID)

        Returns:
            RDF metadata as string

        Raises:
            CEHExtractorError: If fetch fails
        """
        await self._ensure_client()

        url = f"{self.CEH_API_BASE}/{file_identifier}.rdf"
        try:
            logger.info(
                f"Fetching RDF metadata for dataset: {file_identifier}",
                extra={"request_id": self.request_id},
            )
            rdf = await self.http_client.get_text(url, request_id=self.request_id)
            logger.info(
                f"Successfully fetched RDF for {file_identifier}",
                extra={"request_id": self.request_id},
            )
            return rdf
        except Exception as e:
            logger.error(
                f"Failed to fetch RDF for {file_identifier}: {e}",
                extra={"request_id": self.request_id},
            )
            raise CEHExtractorError(f"Failed to fetch RDF for {file_identifier}: {e}") from e

    async def fetch_dataset_schema_org(self, file_identifier: str) -> dict:
        """
        Fetch Schema.org (JSON-LD) metadata for a dataset.

        Args:
            file_identifier: Dataset file identifier (UUID)

        Returns:
            Schema.org metadata as dict

        Raises:
            CEHExtractorError: If fetch fails
        """
        await self._ensure_client()

        url = f"{self.CEH_API_BASE}/{file_identifier}.schema.org.json"
        try:
            logger.info(
                f"Fetching Schema.org metadata for dataset: {file_identifier}",
                extra={"request_id": self.request_id},
            )
            data = await self.http_client.get(url, request_id=self.request_id)
            logger.info(
                f"Successfully fetched Schema.org for {file_identifier}",
                extra={"request_id": self.request_id},
            )
            return data
        except Exception as e:
            logger.error(
                f"Failed to fetch Schema.org for {file_identifier}: {e}",
                extra={"request_id": self.request_id},
            )
            raise CEHExtractorError(f"Failed to fetch Schema.org for {file_identifier}: {e}") from e

    async def fetch_all_metadata_formats(self, file_identifier: str) -> dict:
        """
        Fetch all metadata formats for a dataset concurrently.

        Args:
            file_identifier: Dataset file identifier

        Returns:
            Dictionary with keys: xml, json, rdf, schema_org
            Values are either content (str/dict) or Exception
        """
        import asyncio
        
        await self._ensure_client()

        logger.info(
            f"Fetching all metadata formats for: {file_identifier}",
            extra={"request_id": self.request_id},
        )

        results = await asyncio.gather(
            self.fetch_dataset_xml(file_identifier),
            self.fetch_dataset_json(file_identifier),
            self.fetch_dataset_rdf(file_identifier),
            self.fetch_dataset_schema_org(file_identifier),
            return_exceptions=True,
        )

        return {
            "file_identifier": file_identifier,
            "xml": results[0] if not isinstance(results[0], Exception) else None,
            "json": results[1] if not isinstance(results[1], Exception) else None,
            "rdf": results[2] if not isinstance(results[2], Exception) else None,
            "schema_org": results[3] if not isinstance(results[3], Exception) else None,
            "errors": [
                (fmt, str(err))
                for fmt, err in zip(["xml", "json", "rdf", "schema_org"], results)
                if isinstance(err, Exception)
            ],
        }

    async def _fetch_optional(self, format_name: str, file_identifier: str) -> Optional[str]:
        """
        Fetch an optional metadata format. Returns None if not available.
        Does not raise exception on 404.
        """
        try:
            if format_name == "json":
                return await self.fetch_dataset_json(file_identifier)
            elif format_name == "rdf":
                return await self.fetch_dataset_rdf(file_identifier)
            elif format_name == "schema_org":
                return await self.fetch_dataset_schema_org(file_identifier)
        except Exception as e:
            # Log but don't fail - this format is optional
            logger.debug(
                f"Optional format {format_name} not available for {file_identifier}: {e}",
                extra={"request_id": self.request_id},
            )
            return None
        
        return None

    # async def close(self):
    #     """Close HTTP client if we own it."""
    #     if self._owns_client and self.http_client:
    #         await self.http_client.__aexit__(None, None, None)

    async def close(self):
        """Close HTTP client session."""
        if self.http_client:
            try:
                await self.http_client.close()
                logger.debug("CEH extractor HTTP client closed")
            except Exception as e:
                logger.warning(f"Error closing CEH extractor HTTP client: {e}")