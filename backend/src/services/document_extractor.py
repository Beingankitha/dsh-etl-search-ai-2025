"""
Abstract document text extractor hierarchy.

Supports multiple document formats: PDF, DOCX, TXT, RTF.
Uses OOP strategy pattern for extensibility.

Example:
    extractor = PDFExtractor()
    text = await extractor.extract("report.pdf")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.logging_config import get_logger

logger = get_logger(__name__)


class DocumentExtractorError(Exception):
    """Base exception for document extraction errors."""

    pass


class DocumentExtractor(ABC):
    """
    Abstract base class for extracting text from documents.

    Subclasses implement format-specific extraction logic.
    Each extractor handles:
    - File validation (magic bytes, extension)
    - Error recovery (corrupted files, encoding issues)
    - Text normalization (whitespace, encoding)
    """

    # Supported MIME types per extractor
    SUPPORTED_MIMES: list[str] = []

    @abstractmethod
    async def extract(self, file_path: str | Path) -> str:
        """
        Extract text from document.

        Args:
            file_path: Path to document file

        Returns:
            Extracted text (cleaned, normalized)

        Raises:
            DocumentExtractorError: If extraction fails
        """
        pass

    def _sanitize_text(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize extracted text.

        Args:
            text: Raw extracted text
            max_length: Optional max characters

        Returns:
            Cleaned text with normalized whitespace
        """
        # Normalize whitespace
        sanitized = " ".join(text.split())

        # Limit length if specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        return sanitized

    def _validate_file(self, file_path: str | Path) -> Path:
        """
        Validate file exists and is readable.

        Args:
            file_path: Path to check

        Returns:
            Validated Path object

        Raises:
            DocumentExtractorError: If file invalid
        """
        path = Path(file_path)

        if not path.exists():
            raise DocumentExtractorError(f"File not found: {path}")

        if not path.is_file():
            raise DocumentExtractorError(f"Not a file: {path}")

        if not path.stat().st_size > 0:
            raise DocumentExtractorError(f"File is empty: {path}")

        return path