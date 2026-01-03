"""
Supporting Documents Module - Discovery and Management of Related Documents

This module handles the discovery and download of supporting documents that are
referenced in dataset metadata. These might include reports, technical documentation,
data dictionaries, and other related files.

Classes:
    - SupportingDocDiscoverer: Discovers supporting document URLs from metadata
    - SupportingDocDownloader: Downloads and caches supporting documents
    - SupportingDocURLs: Container for categorized document URLs

Features:
    - SupportingDocDiscoverer:
        * Extracts URLs from ISO 19139 XML (gmd:onlineResource)
        * Parses JSON metadata arrays
        * Extracts from Schema.org distributions
        * Queries RDF graphs for document links
        * Supports multi-format metadata input
    
    - SupportingDocDownloader:
        * Async HTTP downloads with retry logic
        * File caching to avoid re-downloading
        * Configurable max file size limits
        * Content-type validation
        * Automatic cache directory creation
        * Request ID tracking for audit trails

Usage:
    from src.services.supporting_documents import (
        SupportingDocDiscoverer,
        SupportingDocDownloader
    )
    
    # Discover supporting document URLs
    discoverer = SupportingDocDiscoverer()
    doc_urls = discoverer.discover_from_xml(xml_content)
    doc_urls = discoverer.discover_from_json(json_content)
    
    # Download supporting documents
    downloader = SupportingDocDownloader()
    file_path = await downloader.download_file(
        url="https://example.com/dataset-report.pdf",
        request_id="abc-123"
    )
    
    # Batch download
    downloader = SupportingDocDownloader(cache_dir=Path("data/docs"))
    for url in doc_urls.data_documents:
        try:
            path = await downloader.download_file(url)
            print(f"Downloaded: {path}")
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")

Cache Structure:
    data/
    └── supporting_docs/
        ├── {hash}.pdf
        ├── {hash}.txt
        └── {hash}.xml

Document Categories (SupportingDocURLs):
    - data_documents: Primary data files
    - metadata_documents: Metadata/schema files
    - technical_docs: Technical documentation
    - other_documents: Miscellaneous related files

Error Handling:
    - Network timeouts with exponential backoff retry
    - File size validation (configurable limit)
    - Content-type verification
    - Graceful handling of 404 and other HTTP errors
"""

from .supporting_doc_discoverer import (
    SupportingDocDiscoverer,
    SupportingDocURLs,
    SupportingDocDiscoveryError,
)
from .supporting_doc_downloader import (
    SupportingDocDownloader,
    SupportingDocDownloaderError,
)

__all__ = [
    # Discovery
    "SupportingDocDiscoverer",
    "SupportingDocURLs",
    "SupportingDocDiscoveryError",
    # Download
    "SupportingDocDownloader",
    "SupportingDocDownloaderError",
]
