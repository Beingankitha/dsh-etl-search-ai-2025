"""
Dataset File Extraction Service

Handles discovery, download, and extraction of dataset files from ZIP archives.

Features:
- URL discovery from metadata (JSON/XML/RDF)
- ZIP file downloading with async HTTP client
- In-memory extraction (no disk space required)
- File metadata storage in database
- Error handling and recovery
"""

from __future__ import annotations

import logging
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from mimetypes import guess_type

from src.logging_config import get_logger
from src.infrastructure import AsyncHTTPClient
from src.services.extractors.zip_extractor import ZipExtractor
from src.services.supporting_documents import SupportingDocDiscoverer
from src.models.database_models import DataFile
from src.repositories import DataFileRepository
from src.config import settings

logger = get_logger(__name__)


class DatasetFileExtractionError(Exception):
    """Base exception for dataset file extraction errors."""
    pass


class DatasetFileExtractor:
    """
    Extracts dataset files from metadata and manages storage.
    
    Features:
    - URL discovery from JSON/XML/RDF metadata
    - ZIP file downloading and extraction
    - File metadata tracking
    - Batch processing with concurrency control
    - Error recovery and logging
    """

    # File extensions to include in extraction
    DATA_FILE_EXTENSIONS = {
        # Geospatial
        ".tif", ".tiff", ".geotiff", ".img", ".hdf", ".nc",  # Raster
        ".shp", ".shx", ".dbf", ".prj", ".cpg",  # Shapefile
        ".gpkg",  # GeoPackage
        
        # Data formats
        ".csv", ".tsv", ".xlsx", ".xls",  # Spreadsheets
        ".json", ".xml", ".sql",  # Structured data
        ".parquet", ".h5",  # Binary data
        
        # Documents
        ".txt", ".md", ".pdf",  # Documents
        ".rst",  # reStructuredText
        ".doc", ".docx",  # Microsoft Word documents
        ".ppt", ".pptx",  # Microsoft PowerPoint
        ".odt", ".odp",  # OpenDocument formats
        
        # Code
        ".py", ".r", ".m", ".sql",  # Analysis code
        
        # Archives
        ".zip", ".tar", ".gz", ".tar.gz",  # Nested archives
    }

    def __init__(
        self,
        http_client: Optional[AsyncHTTPClient] = None,
        file_repository: Optional[DataFileRepository] = None,
        max_concurrent: int = 3,
    ):
        """
        Initialize dataset file extractor.

        Args:
            http_client: AsyncHTTPClient for downloads
            file_repository: Repository for storing file metadata
            max_concurrent: Maximum concurrent downloads
        """
        self.http_client = http_client
        self.file_repository = file_repository
        self.max_concurrent = max_concurrent
        self.zip_extractor = ZipExtractor()
        self.doc_discoverer = SupportingDocDiscoverer()
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

    async def extract_and_load(
        self,
        identifier: str,
        dataset_id: int,
        metadata_docs: Dict[str, str],
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract files from dataset and load metadata to database.

        Args:
            identifier: Dataset file identifier
            dataset_id: Database ID of dataset
            metadata_docs: Dictionary with 'json', 'xml', 'rdf' content
            dry_run: If True, don't save to database

        Returns:
            Dictionary with extraction statistics
        """
        await self._ensure_client()

        stats = {
            "identifier": identifier,
            "dataset_id": dataset_id,
            "download_urls_found": 0,
            "fileaccess_urls_found": 0,
            "files_extracted": 0,
            "files_stored": 0,
            "errors": [],
        }

        try:
            # Step 1: Discover download and fileaccess URLs
            logger.info(f"[{identifier}] Discovering data download URLs")
            
            # Use existing discoverer which already separates download/fileaccess URLs
            discoverer = SupportingDocDiscoverer()
            
            # Discover from JSON first
            if metadata_docs.get("json"):
                try:
                    json_urls = await discoverer.discover_from_json(
                        metadata_docs["json"]
                    )
                    download_urls = json_urls.download_urls
                    fileaccess_urls = json_urls.fileaccess_urls
                except Exception as e:
                    logger.warning(f"[{identifier}] JSON discovery failed: {e}")
                    download_urls = []
                    fileaccess_urls = []
            else:
                download_urls = []
                fileaccess_urls = []

            # Try XML if JSON didn't find URLs
            if not download_urls and metadata_docs.get("xml"):
                try:
                    xml_urls = await discoverer.discover_from_iso_xml(
                        metadata_docs["xml"]
                    )
                    download_urls = xml_urls.download_urls
                    fileaccess_urls = xml_urls.fileaccess_urls or fileaccess_urls
                except Exception as e:
                    logger.warning(f"[{identifier}] XML discovery failed: {e}")

            stats["download_urls_found"] = len(download_urls)
            stats["fileaccess_urls_found"] = len(fileaccess_urls)

            logger.info(
                f"[{identifier}] Found {len(download_urls)} download URLs, "
                f"{len(fileaccess_urls)} fileaccess URLs"
            )

            # Step 2: Process download URLs (ZIP files)
            if download_urls:
                try:
                    extracted = await self._process_zip_downloads(
                        identifier,
                        dataset_id,
                        download_urls,
                        dry_run,
                    )
                    stats["files_extracted"] += extracted["extracted"]
                    stats["files_stored"] += extracted["stored"]
                    if extracted.get("errors"):
                        stats["errors"].extend(extracted["errors"])
                except Exception as e:
                    logger.error(f"[{identifier}] ZIP processing failed: {e}")
                    stats["errors"].append(f"ZIP processing: {str(e)}")

            # Step 3: Process fileaccess URLs (web folders) - NOT YET IMPLEMENTED
            # These are URLs ending with / that might be directory listings
            # But many are just websites (like eidc.ac.uk) not actual web folders
            if fileaccess_urls:
                logger.debug(
                    f"[{identifier}] Found {len(fileaccess_urls)} fileaccess URLs "
                    "(directory traversal requires validation - skipped)"
                )

            logger.info(
                f"[{identifier}] Data file extraction complete: "
                f"{stats['files_extracted']} extracted, "
                f"{stats['files_stored']} stored"
            )

            return stats

        except Exception as e:
            logger.error(f"[{identifier}] Extract and load failed: {e}")
            stats["errors"].append(f"Fatal error: {str(e)}")
            raise DatasetFileExtractionError(
                f"Failed to extract dataset files: {e}"
            ) from e

    async def _process_zip_downloads(
        self,
        identifier: str,
        dataset_id: int,
        download_urls: List[str],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """
        Download and extract ZIP files.

        Args:
            identifier: Dataset identifier
            dataset_id: Database dataset ID
            download_urls: List of download URLs
            dry_run: If True, don't save to database

        Returns:
            Dictionary with extraction statistics
        """
        stats = {
            "extracted": 0,
            "stored": 0,
            "errors": [],
        }

        for url_idx, url in enumerate(download_urls, 1):
            try:
                logger.debug(
                    f"[{identifier}] Processing ZIP {url_idx}/{len(download_urls)}: {url}"
                )

                # Download ZIP file
                try:
                    zip_bytes = await self.http_client.get_bytes(url)
                    logger.debug(f"[{identifier}] Downloaded {len(zip_bytes)} bytes")
                except Exception as e:
                    logger.warning(f"[{identifier}] Failed to download {url}: {e}")
                    stats["errors"].append(f"Download failed: {str(e)}")
                    continue

                # Extract ZIP contents in-memory
                try:
                    files = await self.zip_extractor.extract_in_memory(
                        zip_bytes,
                        file_filter=self._is_data_file,
                    )
                    logger.info(
                        f"[{identifier}] Extracted {len(files)} files from ZIP"
                    )
                    stats["extracted"] += len(files)
                except Exception as e:
                    logger.warning(f"[{identifier}] ZIP extraction failed: {e}")
                    stats["errors"].append(f"Extraction failed: {str(e)}")
                    continue

                # Store file metadata in database
                if not dry_run and files:
                    try:
                        stored = await self._store_file_metadata(
                            identifier,
                            dataset_id,
                            files,
                        )
                        stats["stored"] += stored
                    except Exception as e:
                        logger.warning(f"[{identifier}] Failed to store files: {e}")
                        stats["errors"].append(f"Storage failed: {str(e)}")

            except Exception as e:
                logger.error(f"[{identifier}] ZIP processing error: {e}")
                stats["errors"].append(f"ZIP processing: {str(e)}")
                continue

        return stats

    async def _store_file_metadata(
        self,
        identifier: str,
        dataset_id: int,
        files: Dict[str, bytes],
    ) -> int:
        """
        Store file metadata in database.

        Args:
            identifier: Dataset identifier
            dataset_id: Database dataset ID
            files: Dictionary mapping filename to content

        Returns:
            Number of files stored
        """
        if not self.file_repository:
            logger.warning("[%s] File repository not available", identifier)
            return 0

        stored = 0
        for filename, content in files.items():
            try:
                # Determine MIME type
                mime_type, _ = guess_type(filename)
                if not mime_type:
                    # Default based on extension
                    ext = Path(filename).suffix.lower()
                    mime_type = {
                        ".tif": "image/tiff",
                        ".tiff": "image/tiff",
                        ".geotiff": "image/tiff",
                        ".csv": "text/csv",
                        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ".json": "application/json",
                        ".xml": "application/xml",
                        ".txt": "text/plain",
                    }.get(ext, "application/octet-stream")

                # Create DataFile record
                data_file = DataFile(
                    dataset_id=dataset_id,
                    filename=Path(filename).name,  # Just the filename, not full path
                    file_path=None,  # We're not storing to disk
                    file_size=len(content),
                    mime_type=mime_type,
                )

                # Store in database
                self.file_repository.insert(data_file)
                stored += 1
                logger.debug(
                    f"[{identifier}] Stored: {filename} "
                    f"({len(content)} bytes, {mime_type})"
                )

            except Exception as e:
                logger.warning(
                    f"[{identifier}] Failed to store {filename}: {e}"
                )
                continue

        return stored

    @staticmethod
    def _is_data_file(file_path: str) -> bool:
        """
        Check if file should be included in extraction.

        Args:
            file_path: File path from ZIP

        Returns:
            True if file should be extracted
        """
        # Skip hidden files and metadata
        if "__MACOSX" in file_path or file_path.startswith("."):
            return False

        # Skip common archive/installer files
        if file_path.endswith((".exe", ".msi", ".dmg", ".app")):
            return False

        # Check extension
        ext = Path(file_path).suffix.lower()
        return ext in DatasetFileExtractor.DATA_FILE_EXTENSIONS

    async def cleanup(self):
        """Cleanup resources."""
        if self._owns_client and self.http_client:
            await self.http_client.__aexit__(None, None, None)
