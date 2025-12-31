"""
ZIP file extractor with in-memory support and error handling.

Features:
- In-memory extraction (no disk space required)
- Integrity validation
- Selective file extraction
- Error recovery
"""

from __future__ import annotations

import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional, Callable

from src.logging_config import get_logger

logger = get_logger(__name__)


class ZipExtractorError(Exception):
    """Base exception for ZIP extraction errors."""
    pass


class ZipExtractor:
    """
    Extracts ZIP archives with error handling.

    Features:
    - In-memory extraction
    - File filtering by type
    - Progress tracking
    - Corrupted file recovery
    """

    # Supported document extensions
    DOCUMENT_EXTENSIONS = {
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".xml",
        ".json",
        ".csv",
    }

    async def extract_in_memory(
        self, zip_bytes: bytes, file_filter: Optional[Callable[[str], bool]] = None
    ) -> dict[str, bytes]:
        """
        Extract ZIP archive in-memory.

        Args:
            zip_bytes: ZIP file content as bytes
            file_filter: Optional function to filter files (path: str -> bool)

        Returns:
            Dictionary mapping file paths to content

        Raises:
            ZipExtractorError: If ZIP invalid or extraction fails
        """
        try:
            logger.info(f"Extracting ZIP ({len(zip_bytes)} bytes)")

            with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                # Validate ZIP
                bad_file = zf.testzip()
                if bad_file:
                    logger.warning(f"Corrupted file in ZIP: {bad_file}")
                    # Continue anyway, extract what we can

                files = {}
                for file_info in zf.filelist:
                    # Skip directories
                    if file_info.is_dir():
                        continue

                    file_path = file_info.filename

                    # Apply filter if provided
                    if file_filter and not file_filter(file_path):
                        continue

                    try:
                        content = zf.read(file_path)
                        files[file_path] = content
                        logger.debug(f"Extracted: {file_path} ({len(content)} bytes)")
                    except Exception as e:
                        logger.warning(f"Failed to extract {file_path}: {e}")
                        # Continue on individual file failures
                        continue

                logger.info(f"Extracted {len(files)} files from ZIP")
                return files

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file: {e}")
            raise ZipExtractorError(f"Invalid ZIP: {e}") from e
        except Exception as e:
            logger.error(f"ZIP extraction failed: {e}")
            raise ZipExtractorError(f"Extraction failed: {e}") from e

    async def extract_to_disk(
        self,
        zip_bytes: bytes,
        output_dir: Path,
        file_filter: Optional[Callable[[str], bool]] = None,
    ) -> Path:
        """
        Extract ZIP archive to disk.

        Args:
            zip_bytes: ZIP file content as bytes
            output_dir: Directory to extract to
            file_filter: Optional function to filter files

        Returns:
            Path to output directory

        Raises:
            ZipExtractorError: If extraction fails
        """
        try:
            logger.info(f"Extracting ZIP to {output_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                for file_info in zf.filelist:
                    if file_info.is_dir():
                        continue

                    file_path = file_info.filename

                    if file_filter and not file_filter(file_path):
                        continue

                    try:
                        zf.extract(file_info, output_dir)
                        logger.debug(f"Extracted: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to extract {file_path}: {e}")
                        continue

            logger.info(f"Extraction complete: {output_dir}")
            return output_dir

        except Exception as e:
            logger.error(f"ZIP extraction to disk failed: {e}")
            raise ZipExtractorError(f"Extraction failed: {e}") from e

    @staticmethod
    def _is_document(file_path: str) -> bool:
        """Check if file is a document we care about."""
        return Path(file_path).suffix.lower() in ZipExtractor.DOCUMENT_EXTENSIONS