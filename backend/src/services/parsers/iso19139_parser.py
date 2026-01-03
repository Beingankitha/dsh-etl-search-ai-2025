"""
ISO 19139 XML metadata parser.

Parses ISO 19115 geographic metadata encoded in XML format.
"""

from __future__ import annotations

import logging
from typing import Optional

from lxml import etree

from src.logging_config import get_logger
from src.models import Dataset
from .metadata_parser import MetadataParser, MetadataParserError

logger = get_logger(__name__)


class ISO19139Parser(MetadataParser):
    """
    Parses ISO 19139 XML metadata documents.

    Extracts key ISO 19115 fields including:
    - file_identifier
    - title
    - abstract
    - topic_category
    - keywords
    - lineage
    - supplemental_information
    """

    # ISO XML namespaces
    NAMESPACES = {
        "gmd": "http://www.isotc211.org/2005/gmd",
        "gco": "http://www.isotc211.org/2005/gco",
        "gmx": "http://www.isotc211.org/2005/gmx",
    }

    async def parse(self, content: str) -> Dataset:
        """
        Parse ISO 19139 XML into Dataset.

        Args:
            content: XML string

        Returns:
            Parsed Dataset

        Raises:
            MetadataParserError: If parsing fails
        """
        try:
            logger.info("Parsing ISO 19139 XML metadata")
            root = etree.fromstring(content.encode("utf-8"))
            return self._extract_dataset(root)
        except etree.XMLSyntaxError as e:
            logger.error(f"XML syntax error: {e}")
            raise MetadataParserError(f"Invalid XML: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse ISO 19139 XML: {e}")
            raise MetadataParserError(f"Parse error: {e}") from e

    def _extract_dataset(self, root: etree._Element) -> Dataset:
        """
        Extract Dataset fields from XML root.

        Args:
            root: XML root element

        Returns:
            Dataset object
        """
        file_identifier = self._extract_file_identifier(root)
        title = self._extract_title(root)
        abstract = self._extract_abstract(root)
        topic_category = self._extract_topic_category(root)
        keywords = self._extract_keywords(root)
        lineage = self._extract_lineage(root)
        supplemental_info = self._extract_supplemental_info(root)

        return Dataset(
            file_identifier=file_identifier or "unknown",
            title=title or "Unknown Title",
            abstract=abstract or "",
            topic_category=topic_category,
            keywords=keywords,
            lineage=lineage,
            supplemental_info=supplemental_info,
        )

    def _extract_file_identifier(self, root: etree._Element) -> Optional[str]:
        """Extract file identifier."""
        xpath = ".//gmd:fileIdentifier/gco:CharacterString/text()"
        result = root.xpath(xpath, namespaces=self.NAMESPACES)
        return self._sanitize_string(result[0]) if result else None

    def _extract_title(self, root: etree._Element) -> Optional[str]:
        """Extract dataset title."""
        xpath = ".//gmd:identificationInfo//gmd:title/gco:CharacterString/text()"
        result = root.xpath(xpath, namespaces=self.NAMESPACES)
        return self._sanitize_string(result[0]) if result else None

    def _extract_abstract(self, root: etree._Element) -> Optional[str]:
        """Extract dataset abstract."""
        xpath = ".//gmd:identificationInfo//gmd:abstract/gco:CharacterString/text()"
        result = root.xpath(xpath, namespaces=self.NAMESPACES)
        return self._sanitize_string(result[0]) if result else None

    def _extract_topic_category(self, root: etree._Element) -> list[str]:
        """Extract topic categories."""
        xpath = ".//gmd:identificationInfo//gmd:topicCategory/gmd:MD_TopicCategoryCode/text()"
        result = root.xpath(xpath, namespaces=self.NAMESPACES)
        return self._extract_list(result)

    def _extract_keywords(self, root: etree._Element) -> list[str]:
        """Extract keywords."""
        xpath = ".//gmd:identificationInfo//gmd:keyword/gco:CharacterString/text()"
        result = root.xpath(xpath, namespaces=self.NAMESPACES)
        return self._extract_list(result)

    def _extract_lineage(self, root: etree._Element) -> Optional[str]:
        """Extract lineage."""
        xpath = ".//gmd:dataQualityInfo//gmd:lineage//gmd:statement/gco:CharacterString/text()"
        result = root.xpath(xpath, namespaces=self.NAMESPACES)
        return self._sanitize_string(result[0]) if result else None

    def _extract_supplemental_info(self, root: etree._Element) -> Optional[str]:
        """Extract supplemental information."""
        xpath = ".//gmd:identificationInfo//gmd:supplementalInformation/gco:CharacterString/text()"
        result = root.xpath(xpath, namespaces=self.NAMESPACES)
        return self._sanitize_string(result[0]) if result else None