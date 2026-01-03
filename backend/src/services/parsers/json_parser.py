"""
JSON metadata parser for CEH catalogue datasets.

Parses expanded JSON documents that model relationships between metadata resources.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from src.logging_config import get_logger
from src.models import Dataset
from .metadata_parser import MetadataParser, MetadataParserError

logger = get_logger(__name__)


class JSONMetadataParser(MetadataParser):
    """
    Parses JSON metadata documents from CEH catalogue.

    JSON format provides expanded document modeling and relationships between:
    - Metadata documents (ISO, JSON-LD, RDF)
    - Supporting documents
    - Download/fileAccess links
    """

    async def parse(self, content: str) -> Dataset:
        """
        Parse JSON metadata into Dataset.

        Args:
            content: JSON string

        Returns:
            Parsed Dataset

        Raises:
            MetadataParserError: If parsing fails
        """
        try:
            logger.info("Parsing JSON metadata")
            data = json.loads(content)
            return self._extract_dataset(data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            raise MetadataParserError(f"Invalid JSON: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse JSON metadata: {e}")
            raise MetadataParserError(f"Parse error: {e}") from e

    def _extract_dataset(self, data: dict[str, Any]) -> Dataset:
        """
        Extract Dataset fields from JSON object.

        Args:
            data: JSON data as dict

        Returns:
            Dataset object
        """
        # Handle both direct fields and nested structures
        file_identifier = self._extract_file_identifier(data)
        title = self._extract_title(data)
        abstract = self._extract_abstract(data)
        topic_category = self._extract_topic_category(data)
        keywords = self._extract_keywords(data)
        lineage = self._extract_lineage(data)
        supplemental_info = self._extract_supplemental_info(data)

        return Dataset(
            file_identifier=file_identifier or "unknown",
            title=title or "Unknown Title",
            abstract=abstract or "",
            topic_category=topic_category,
            keywords=keywords,
            lineage=lineage,
            supplemental_info=supplemental_info,
        )

    def _extract_file_identifier(self, data: dict) -> Optional[str]:
        """Extract file identifier from JSON."""
        # Try multiple possible paths
        paths = [
            data.get("fileIdentifier"),
            data.get("id"),
            data.get("identifier"),
            data.get("metadata", {}).get("fileIdentifier"),
        ]
        for value in paths:
            sanitized = self._sanitize_string(value)
            if sanitized:
                return sanitized
        return None

    def _extract_title(self, data: dict) -> Optional[str]:
        """Extract title from JSON."""
        paths = [
            data.get("title"),
            data.get("name"),
            data.get("metadata", {}).get("title"),
        ]
        for value in paths:
            sanitized = self._sanitize_string(value)
            if sanitized:
                return sanitized
        return None

    def _extract_abstract(self, data: dict) -> Optional[str]:
        """Extract abstract from JSON."""
        paths = [
            data.get("abstract"),
            data.get("description"),
            data.get("summary"),
            data.get("metadata", {}).get("abstract"),
        ]
        for value in paths:
            sanitized = self._sanitize_string(value)
            if sanitized:
                return sanitized
        return None

    def _extract_topic_category(self, data: dict) -> list[str]:
        """Extract topic categories from JSON."""
        categories = data.get("topicCategory", data.get("topics", []))
        return self._extract_list(categories)

    def _extract_keywords(self, data: dict) -> list[str]:
        """Extract keywords from JSON."""
        keywords = data.get("keywords", data.get("tags", []))
        return self._extract_list(keywords)

    def _extract_lineage(self, data: dict) -> Optional[str]:
        """Extract lineage from JSON."""
        lineage = data.get("lineage") or data.get("provenance")
        return self._sanitize_string(lineage)

    def _extract_supplemental_info(self, data: dict) -> Optional[str]:
        """Extract supplemental information from JSON."""
        info = data.get("supplementalInformation") or data.get("notes")
        return self._sanitize_string(info)