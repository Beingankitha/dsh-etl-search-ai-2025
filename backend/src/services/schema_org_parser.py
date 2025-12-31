"""
Schema.org (JSON-LD) metadata parser for CEH datasets.

Parses structured data in Schema.org vocabulary using JSON-LD format.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from src.logging_config import get_logger
from src.models import Dataset
from src.services.metadata_parser import MetadataParser, MetadataParserError

logger = get_logger(__name__)


class SchemaOrgParser(MetadataParser):
    """
    Parses Schema.org (JSON-LD) metadata documents.

    Schema.org provides structured, semantic markup for datasets using:
    - @context: "https://schema.org"
    - @type: "Dataset"
    - Standard properties: name, description, keywords, etc.
    """

    async def parse(self, content: str) -> Dataset:
        """
        Parse Schema.org JSON-LD into Dataset.

        Args:
            content: JSON-LD string

        Returns:
            Parsed Dataset

        Raises:
            MetadataParserError: If parsing fails
        """
        try:
            logger.info("Parsing Schema.org JSON-LD metadata")
            data = json.loads(content)
            return self._extract_dataset(data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON-LD: {e}")
            raise MetadataParserError(f"Invalid JSON-LD: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse Schema.org metadata: {e}")
            raise MetadataParserError(f"Parse error: {e}") from e

    def _extract_dataset(self, data: dict[str, Any]) -> Dataset:
        """
        Extract Dataset fields from JSON-LD object.

        Args:
            data: JSON-LD data as dict

        Returns:
            Dataset object
        """
        # Handle @graph (multiple entities) or direct Dataset
        dataset_obj = data
        if isinstance(data.get("@graph"), list):
            # Find Dataset in graph
            for item in data["@graph"]:
                if item.get("@type") == "Dataset" or "Dataset" in item.get("@type", []):
                    dataset_obj = item
                    break

        file_identifier = self._extract_identifier(dataset_obj)
        title = self._extract_title(dataset_obj)
        abstract = self._extract_description(dataset_obj)
        topic_category = self._extract_keywords(dataset_obj)  # Schema.org uses keywords, not topicCategory
        keywords = self._extract_keywords(dataset_obj)
        lineage = self._extract_lineage(dataset_obj)
        supplemental_info = self._extract_supplemental_info(dataset_obj)

        return Dataset(
            file_identifier=file_identifier or "unknown",
            title=title or "Unknown Title",
            abstract=abstract or "",
            topic_category=topic_category,
            keywords=keywords,
            lineage=lineage,
            supplemental_info=supplemental_info,
        )

    def _extract_identifier(self, data: dict) -> Optional[str]:
        """Extract identifier from Schema.org Dataset."""
        # Schema.org uses identifier (string or PropertyValue)
        identifier = data.get("identifier")
        if isinstance(identifier, dict):
            return self._sanitize_string(identifier.get("value"))
        return self._sanitize_string(identifier)

    def _extract_title(self, data: dict) -> Optional[str]:
        """Extract name (title) from Schema.org Dataset."""
        name = data.get("name")
        return self._sanitize_string(name)

    def _extract_description(self, data: dict) -> Optional[str]:
        """Extract description from Schema.org Dataset."""
        description = data.get("description")
        return self._sanitize_string(description)

    def _extract_keywords(self, data: dict) -> list[str]:
        """Extract keywords from Schema.org Dataset."""
        keywords = data.get("keywords", [])
        # Keywords can be string (comma-separated) or array
        if isinstance(keywords, str):
            return [k.strip() for k in keywords.split(",") if k.strip()]
        return self._extract_list(keywords)

    def _extract_lineage(self, data: dict) -> Optional[str]:
        """Extract lineage/provenance from Schema.org Dataset."""
        # Schema.org uses creator, author, spatialCoverage, temporalCoverage
        lineage_parts = []

        creator = data.get("creator")
        if creator:
            if isinstance(creator, dict):
                creator_name = creator.get("name", str(creator))
            else:
                creator_name = str(creator)
            lineage_parts.append(f"Created by: {creator_name}")

        author = data.get("author")
        if author and author != creator:
            if isinstance(author, dict):
                author_name = author.get("name", str(author))
            else:
                author_name = str(author)
            lineage_parts.append(f"Author: {author_name}")

        return "; ".join(lineage_parts) if lineage_parts else None

    def _extract_supplemental_info(self, data: dict) -> Optional[str]:
        """Extract supplemental information from Schema.org Dataset."""
        # Schema.org uses spatialCoverage, temporalCoverage, encodingFormat, url
        info_parts = []

        spatial = data.get("spatialCoverage")
        if spatial:
            info_parts.append(f"Spatial coverage: {spatial}")

        temporal = data.get("temporalCoverage")
        if temporal:
            info_parts.append(f"Temporal coverage: {temporal}")

        url = data.get("url")
        if url:
            info_parts.append(f"URL: {url}")

        return "; ".join(info_parts) if info_parts else None