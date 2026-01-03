"""
Abstract metadata parser hierarchy.

Supports multiple metadata formats: ISO 19139 XML, JSON, Schema.org JSON-LD, RDF Turtle.
Uses OOP principles for extensibility and testability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from src.logging_config import get_logger
from src.models import Dataset

logger = get_logger(__name__)


class MetadataParserError(Exception):
    """Base exception for parser errors."""

    pass


class MetadataParser(ABC):
    """
    Abstract base class for metadata parsers.

    Subclasses implement format-specific parsing logic.
    """

    @abstractmethod
    async def parse(self, content: str) -> Dataset:
        """
        Parse metadata content into a Dataset object.

        Args:
            content: Raw metadata content (XML, JSON, etc.)

        Returns:
            Parsed Dataset

        Raises:
            MetadataParserError: If parsing fails
        """
        pass

    def _sanitize_string(self, value: Optional[str]) -> Optional[str]:
        """
        Sanitize and normalize string values.

        Args:
            value: Input string

        Returns:
            Trimmed string or None if empty
        """
        if value is None:
            return None
        sanitized = str(value).strip()
        return sanitized if sanitized else None

    def _extract_list(self, items: Any) -> list[str]:
        """
        Extract list of strings from various input formats.

        Args:
            items: Single item, list, or None

        Returns:
            List of strings
        """
        if items is None:
            return []
        if isinstance(items, str):
            return [self._sanitize_string(items)] if items.strip() else []
        if isinstance(items, list):
            return [
                self._sanitize_string(item) for item in items if self._sanitize_string(item)
            ]
        return []