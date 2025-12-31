"""
PDF document text extractor using pypdf library.

Handles:
- Single and multi-page PDFs
- Text extraction with metadata preservation
- Error handling for corrupted PDFs
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

from src.logging_config import get_logger
from src.services.document_extractor import DocumentExtractor, DocumentExtractorError

logger = get_logger(__name__)


class PDFExtractor(DocumentExtractor):
    """
    Extracts text from PDF documents.

    Features:
    - Multi-page support
    - Handles corrupted PDFs gracefully
    - Preserves basic structure (newlines between pages)
    """

    SUPPORTED_MIMES = ["application/pdf"]

    async def extract(self, file_path: str | Path, max_pages: Optional[int] = None) -> str:
        """
        Extract text from PDF.

        Args:
            file_path: Path to PDF file
            max_pages: Optional limit on pages to extract

        Returns:
            Extracted text with page breaks

        Raises:
            DocumentExtractorError: If PDF invalid or extraction fails
        """
        try:
            path = self._validate_file(file_path)
            logger.info(f"Extracting PDF: {path}")

            reader = PdfReader(path)
            pages_to_extract = min(len(reader.pages), max_pages or len(reader.pages))

            text_parts = []
            for i in range(pages_to_extract):
                try:
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Failed to extract page {i + 1}: {e}")
                    # Continue on individual page failures
                    continue

            if not text_parts:
                raise DocumentExtractorError(f"No text extracted from {path}")

            combined = "\n\n--- Page Break ---\n\n".join(text_parts)
            sanitized = self._sanitize_text(combined)

            logger.info(f"Extracted {len(text_parts)} pages from PDF: {path}")
            return sanitized

        except DocumentExtractorError:
            raise
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise DocumentExtractorError(f"Failed to extract PDF: {e}") from e