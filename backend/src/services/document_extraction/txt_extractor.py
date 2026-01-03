"""
Plain text document extractor.

Handles:
- Plain text files (.txt)
- Encoding detection (UTF-8, UTF-16, etc.)
- Large file handling
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.logging_config import get_logger
from .document_extractor import DocumentExtractor, DocumentExtractorError

logger = get_logger(__name__)


class TXTExtractor(DocumentExtractor):
    """
    Extracts text from plain text files.

    Features:
    - Automatic encoding detection
    - Graceful fallback to latin-1
    - Large file support
    """

    SUPPORTED_MIMES = ["text/plain"]

    async def extract(self, file_path: str | Path) -> str:
        """
        Extract text from plain text file.

        Args:
            file_path: Path to TXT file

        Returns:
            File content (normalized)

        Raises:
            DocumentExtractorError: If file invalid or unreadable
        """
        try:
            path = self._validate_file(file_path)
            logger.info(f"Extracting TXT: {path}")

            # Try UTF-8, then UTF-16, then latin-1
            encodings = ["utf-8", "utf-16", "latin-1"]
            text = None

            for encoding in encodings:
                try:
                    with open(path, "r", encoding=encoding) as f:
                        text = f.read()
                    logger.info(f"Read {path} with encoding {encoding}")
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if text is None:
                raise DocumentExtractorError(f"Could not decode {path} with any encoding")

            if not text.strip():
                raise DocumentExtractorError(f"File is empty: {path}")

            sanitized = self._sanitize_text(text)
            return sanitized

        except DocumentExtractorError:
            raise
        except Exception as e:
            logger.error(f"TXT extraction failed: {e}")
            raise DocumentExtractorError(f"Failed to extract TXT: {e}") from e