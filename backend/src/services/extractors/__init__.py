"""
Data Extractors Module - Data Source Extraction and Discovery

This module provides utilities for extracting data from various sources, particularly
from web-based data repositories and archive files.

Classes:
    - CEHExtractor: Fetches dataset metadata from CEH (Centre for Ecology & Hydrology) API
    - WebFolderTraverser: Traverses web folders to discover available files
    - ZipExtractor: Extracts and explores contents of ZIP archives

Features:
    - CEHExtractor:
        * Fetches metadata in multiple formats (XML, JSON, RDF, Schema.org)
        * Handles API rate limiting and retries
        * Supports multiple file identifiers in batch
        * Generates request IDs for tracking
    
    - WebFolderTraverser:
        * Discovers files in web-accessible directories
        * Identifies file types by extension
        * Handles directory listings (HTML parsing)
        * Filters by file type patterns
    
    - ZipExtractor:
        * Extracts ZIP file contents in-memory
        * Filters extracted files by patterns
        * Preserves directory structure

Usage:
    from src.services.extractors import CEHExtractor, WebFolderTraverser, ZipExtractor
    
    # Extract from CEH API
    ceh = CEHExtractor()
    xml_data = await ceh.fetch_dataset_xml("dataset-id-123")
    json_data = await ceh.fetch_dataset_json("dataset-id-123")
    
    # Traverse web folders
    traverser = WebFolderTraverser()
    files = await traverser.discover_files("https://data.example.com/datasets/")
    
    # Extract ZIP archives
    zip_extractor = ZipExtractor()
    contents = await zip_extractor.extract_zip(zip_bytes)

API Endpoints (CEH):
    - XML: https://catalogue.ceh.ac.uk/documents/{id}.xml
    - JSON: https://catalogue.ceh.ac.uk/documents/{id}.json
    - RDF: https://catalogue.ceh.ac.uk/documents/{id}.rdf
    - Schema.org: https://catalogue.ceh.ac.uk/documents/{id}.schema.org.json

Error Handling:
    - CEHExtractorError for API failures
    - Network timeouts handled with retries
    - Invalid file formats detected and reported
"""

from .ceh_extractor import CEHExtractor, CEHExtractorError
from .web_folder_traverser import WebFolderTraverser, WebFolderTraverserError
from .zip_extractor import ZipExtractor, ZipExtractorError
from .dataset_file_extractor import DatasetFileExtractor, DatasetFileExtractionError

__all__ = [
    # CEH API extractor
    "CEHExtractor",
    "CEHExtractorError",
    # Web traversal
    "WebFolderTraverser",
    "WebFolderTraverserError",
    # ZIP handling
    "ZipExtractor",
    "ZipExtractorError",
    # Dataset file extraction
    "DatasetFileExtractor",
    "DatasetFileExtractionError",
]
