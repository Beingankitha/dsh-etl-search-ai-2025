"""Tests for DatasetFileExtractor."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from src.services.extractors.dataset_file_extractor import (
    DatasetFileExtractor,
    DatasetFileExtractionError
)


@pytest.fixture
def extractor():
    """Create DatasetFileExtractor instance."""
    return DatasetFileExtractor()


def test_supported_extensions():
    """Test that supported file extensions are defined."""
    extractor = DatasetFileExtractor()
    
    assert ".csv" in extractor.DATA_FILE_EXTENSIONS
    assert ".shp" in extractor.DATA_FILE_EXTENSIONS
    assert ".tif" in extractor.DATA_FILE_EXTENSIONS
    assert ".nc" in extractor.DATA_FILE_EXTENSIONS
    assert ".json" in extractor.DATA_FILE_EXTENSIONS
    assert ".xlsx" in extractor.DATA_FILE_EXTENSIONS


def test_initialization_with_defaults():
    """Test extractor initialization with default parameters."""
    extractor = DatasetFileExtractor()
    
    assert extractor is not None
    assert extractor.max_concurrent == 3
    assert hasattr(extractor, 'DATA_FILE_EXTENSIONS')
    assert len(extractor.DATA_FILE_EXTENSIONS) > 0


def test_initialization_with_custom_concurrency():
    """Test extractor initialization with custom concurrency."""
    extractor = DatasetFileExtractor(max_concurrent=5)
    
    assert extractor.max_concurrent == 5


@pytest.mark.asyncio
async def test_extract_and_load_basic():
    """Test basic extract_and_load operation."""
    mock_client = AsyncMock()
    mock_repo = MagicMock()
    
    extractor = DatasetFileExtractor(
        http_client=mock_client,
        file_repository=mock_repo
    )
    
    # Call with minimal metadata
    result = await extractor.extract_and_load(
        identifier="test-001",
        dataset_id=1,
        metadata_docs={"json": "{}", "xml": "<root/>", "rdf": ""}
    )
    
    assert result is not None
    assert result['identifier'] == 'test-001'
    assert result['dataset_id'] == 1


def test_extensions_coverage():
    """Test that critical file extensions are covered."""
    extractor = DatasetFileExtractor()
    extensions = extractor.DATA_FILE_EXTENSIONS
    
    # Geospatial
    assert ".shp" in extensions
    assert ".tif" in extensions
    assert ".gpkg" in extensions
    
    # Data
    assert ".csv" in extensions
    assert ".json" in extensions
    assert ".xlsx" in extensions
    
    # Archives
    assert ".zip" in extensions


def test_extension_lowercase():
    """Test that extensions use lowercase."""
    extractor = DatasetFileExtractor()
    
    for ext in extractor.DATA_FILE_EXTENSIONS:
        assert ext == ext.lower(), f"Extension {ext} should be lowercase"


def test_data_file_extensions_not_empty():
    """Test that DATA_FILE_EXTENSIONS is populated."""
    extractor = DatasetFileExtractor()
    
    assert isinstance(extractor.DATA_FILE_EXTENSIONS, set)
    assert len(extractor.DATA_FILE_EXTENSIONS) >= 20


@pytest.mark.asyncio  
async def test_extract_with_no_client_auto_creates():
    """Test that HTTP client is auto-created if not provided."""
    extractor = DatasetFileExtractor()
    
    assert extractor.http_client is None
    
    await extractor._ensure_client()
    
    assert extractor.http_client is not None


@pytest.mark.asyncio
async def test_context_manager_ensures_client():
    """Test client initialization in context manager."""
    mock_client = AsyncMock()
    extractor = DatasetFileExtractor(http_client=mock_client)
    
    # Ensure client is ready
    await extractor._ensure_client()
    
    assert extractor.http_client == mock_client


def test_extraction_error_exception():
    """Test DatasetFileExtractionError is defined."""
    try:
        raise DatasetFileExtractionError("Test error")
    except DatasetFileExtractionError as e:
        assert str(e) == "Test error"


def test_extractor_has_dependencies():
    """Test that extractor initializes with helper objects."""
    extractor = DatasetFileExtractor()
    
    assert hasattr(extractor, 'zip_extractor')
    assert hasattr(extractor, 'doc_discoverer')
    assert extractor.zip_extractor is not None
    assert extractor.doc_discoverer is not None
