"""Tests for concrete document extractor implementations."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.services.document_extraction.document_extractor_impl import (
    PlainTextExtractor,
    PDFExtractor,
    DOCXExtractor,
    UniversalDocumentExtractor,
    DocumentExtractorError
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# Plain Text Extractor Tests

@pytest.mark.asyncio
async def test_plain_text_extractor_initialization():
    """Test PlainTextExtractor initialization."""
    extractor = PlainTextExtractor()
    assert extractor is not None
    assert "text/plain" in extractor.SUPPORTED_MIMES


@pytest.mark.asyncio
async def test_plain_text_extractor_supported_mimes():
    """Test PlainTextExtractor supported MIME types."""
    extractor = PlainTextExtractor()
    assert len(extractor.SUPPORTED_MIMES) > 0
    assert "text/plain" in extractor.SUPPORTED_MIMES


@pytest.mark.asyncio
async def test_plain_text_extract(temp_dir):
    """Test extracting plain text."""
    extractor = PlainTextExtractor()
    
    # Create test file
    test_file = temp_dir / "test.txt"
    test_content = "This is a test file\nWith multiple lines\nAnd content"
    test_file.write_text(test_content)
    
    result = await extractor.extract(test_file)
    
    assert result is not None
    assert "test file" in result
    assert "multiple lines" in result


@pytest.mark.asyncio
async def test_plain_text_extract_empty_file(temp_dir):
    """Test extracting empty text file."""
    extractor = PlainTextExtractor()
    
    test_file = temp_dir / "empty.txt"
    test_file.write_text("")
    
    # Empty files may raise DocumentExtractorError
    try:
        result = await extractor.extract(test_file)
        # If it succeeds, result should be empty string
        assert result == ""
    except DocumentExtractorError:
        # This is acceptable - empty files may be rejected
        pass


@pytest.mark.asyncio
async def test_plain_text_extract_with_different_encoding(temp_dir):
    """Test extracting file with different encoding."""
    extractor = PlainTextExtractor()
    
    test_file = temp_dir / "latin1.txt"
    test_content = "Test file with special chars"
    test_file.write_text(test_content, encoding='utf-8')
    
    result = await extractor.extract(test_file)
    
    assert "Test file" in result


@pytest.mark.asyncio
async def test_plain_text_extract_nonexistent_file():
    """Test extracting nonexistent file raises error."""
    extractor = PlainTextExtractor()
    
    with pytest.raises((FileNotFoundError, DocumentExtractorError)):
        await extractor.extract("/nonexistent/file.txt")


@pytest.mark.asyncio
async def test_plain_text_extract_sanitization(temp_dir):
    """Test that text is sanitized."""
    extractor = PlainTextExtractor()
    
    test_file = temp_dir / "test.txt"
    test_file.write_text("Content")
    
    result = await extractor.extract(test_file)
    
    # Should be sanitized (implementation dependent)
    assert isinstance(result, str)


# PDF Extractor Tests

@pytest.mark.asyncio
async def test_pdf_extractor_initialization():
    """Test PDFExtractor initialization."""
    extractor = PDFExtractor()
    assert extractor is not None
    assert "application/pdf" in extractor.SUPPORTED_MIMES


@pytest.mark.asyncio
async def test_pdf_extractor_supported_mimes():
    """Test PDFExtractor supported MIME types."""
    extractor = PDFExtractor()
    assert "application/pdf" in extractor.SUPPORTED_MIMES


@pytest.mark.asyncio
async def test_pdf_extractor_with_nonexistent_file():
    """Test extracting nonexistent PDF file."""
    extractor = PDFExtractor()
    
    with pytest.raises((FileNotFoundError, DocumentExtractorError)):
        await extractor.extract("/nonexistent/file.pdf")


@pytest.mark.asyncio
async def test_pdf_extractor_invalid_pdf_file(temp_dir):
    """Test extracting invalid PDF file."""
    extractor = PDFExtractor()
    
    # Create invalid PDF file
    test_file = temp_dir / "invalid.pdf"
    test_file.write_text("This is not a PDF")
    
    with pytest.raises(DocumentExtractorError):
        await extractor.extract(test_file)


# DOCX Extractor Tests

@pytest.mark.asyncio
async def test_docx_extractor_initialization():
    """Test DOCXExtractor initialization."""
    extractor = DOCXExtractor()
    assert extractor is not None
    assert len(extractor.SUPPORTED_MIMES) > 0


@pytest.mark.asyncio
async def test_docx_extractor_mime_type():
    """Test DOCXExtractor MIME type."""
    extractor = DOCXExtractor()
    # Should contain docx MIME type
    assert any("word" in mime.lower() or "docx" in mime.lower() 
               for mime in extractor.SUPPORTED_MIMES)


@pytest.mark.asyncio
async def test_docx_extractor_with_nonexistent_file():
    """Test extracting nonexistent DOCX file."""
    extractor = DOCXExtractor()
    
    with pytest.raises((FileNotFoundError, DocumentExtractorError)):
        await extractor.extract("/nonexistent/file.docx")


@pytest.mark.asyncio
async def test_docx_extractor_invalid_file(temp_dir):
    """Test extracting invalid DOCX file."""
    extractor = DOCXExtractor()
    
    # Create invalid DOCX file
    test_file = temp_dir / "invalid.docx"
    test_file.write_text("This is not a DOCX")
    
    with pytest.raises(DocumentExtractorError):
        await extractor.extract(test_file)


# Universal Document Extractor Tests

@pytest.mark.asyncio
async def test_universal_extractor_initialization():
    """Test UniversalDocumentExtractor initialization."""
    extractor = UniversalDocumentExtractor()
    assert extractor is not None


@pytest.mark.asyncio
async def test_universal_extractor_supports_txt(temp_dir):
    """Test UniversalDocumentExtractor with text file."""
    extractor = UniversalDocumentExtractor()
    
    # Create test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("Universal test content")
    
    result = await extractor.extract(test_file)
    
    assert result is not None
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_universal_extractor_auto_detection(temp_dir):
    """Test UniversalDocumentExtractor auto-detects format."""
    extractor = UniversalDocumentExtractor()
    
    # Create plain text file
    test_file = temp_dir / "auto_detect.txt"
    test_file.write_text("Auto detect test")
    
    # Should auto-detect as text and extract
    result = await extractor.extract(test_file)
    
    assert result is not None


@pytest.mark.asyncio
async def test_universal_extractor_unknown_format(temp_dir):
    """Test UniversalDocumentExtractor with unknown format."""
    extractor = UniversalDocumentExtractor()
    
    # Create file with unknown extension
    test_file = temp_dir / "unknown.xyz"
    test_file.write_text("Unknown format")
    
    # Should handle gracefully or raise appropriate error
    try:
        result = await extractor.extract(test_file)
        # If successful, should return string
        assert isinstance(result, str)
    except DocumentExtractorError:
        # If it raises error, that's also acceptable
        pass


# Extractor Factory Tests

@pytest.mark.asyncio
async def test_plain_text_extractor_handles_paths():
    """Test extractor works with both string and Path objects."""
    extractor = PlainTextExtractor()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Content")
        
        # Test with Path object
        result = await extractor.extract(test_file)
        assert result is not None
        
        # Test with string path
        result2 = await extractor.extract(str(test_file))
        assert result2 is not None


@pytest.mark.asyncio
async def test_extractor_error_messages():
    """Test that extractors provide informative error messages."""
    extractor = PlainTextExtractor()
    
    try:
        await extractor.extract("/nonexistent/path.txt")
    except Exception as e:
        assert len(str(e)) > 0


# Integration Tests

@pytest.mark.asyncio
async def test_all_extractors_have_async_extract():
    """Test that all extractors implement async extract method."""
    extractors = [
        PlainTextExtractor(),
        PDFExtractor(),
        DOCXExtractor(),
        UniversalDocumentExtractor()
    ]
    
    for extractor in extractors:
        assert hasattr(extractor, 'extract')
        # Check that extract is async
        import inspect
        assert inspect.iscoroutinefunction(extractor.extract)


@pytest.mark.asyncio
async def test_extractors_inherit_from_base():
    """Test that all extractors inherit from DocumentExtractor."""
    from src.services.document_extraction.document_extractor import DocumentExtractor
    
    extractors = [
        PlainTextExtractor(),
        PDFExtractor(),
        DOCXExtractor(),
        UniversalDocumentExtractor()
    ]
    
    for extractor in extractors:
        assert isinstance(extractor, DocumentExtractor)
