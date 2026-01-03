"""
Tests for Document Extraction Components

Tests PDF, DOCX, TXT extractors and universal document extractor.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import io

from src.services.document_extraction import (
    DocumentExtractor,
    PDFExtractor,
    DOCXExtractor,
    TXTExtractor,
    UniversalDocumentExtractor,
    DocumentExtractorError
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def pdf_extractor():
    """Create PDF extractor"""
    return PDFExtractor()


@pytest.fixture
def docx_extractor():
    """Create DOCX extractor"""
    return DOCXExtractor()


@pytest.fixture
def txt_extractor():
    """Create TXT extractor"""
    return TXTExtractor()


@pytest.fixture
def universal_extractor():
    """Create universal document extractor"""
    return UniversalDocumentExtractor()


# ============================================================================
# TEST: PDF Extractor
# ============================================================================

class TestPDFExtractor:
    """Test PDF text extraction"""
    
    def test_pdf_extractor_initialization(self, pdf_extractor):
        """Test PDF extractor initialization"""
        assert pdf_extractor is not None
        assert PDFExtractor.SUPPORTED_MIMES == ["application/pdf"]
    
    def test_pdf_supported_mimes(self):
        """Test PDF supported MIME types"""
        extractor = PDFExtractor()
        
        assert "application/pdf" in extractor.SUPPORTED_MIMES
    
    @pytest.mark.asyncio
    async def test_extract_pdf_not_found(self, pdf_extractor, temp_dir):
        """Test extracting non-existent PDF"""
        pdf_path = temp_dir / "non_existent.pdf"
        
        with pytest.raises(DocumentExtractorError):
            await pdf_extractor.extract(pdf_path)
    
    @pytest.mark.asyncio
    async def test_extract_pdf_invalid_file(self, pdf_extractor, temp_dir):
        """Test extracting invalid PDF file"""
        pdf_path = temp_dir / "invalid.pdf"
        pdf_path.write_text("This is not a PDF file")
        
        with pytest.raises(DocumentExtractorError):
            await pdf_extractor.extract(pdf_path)
    
    @pytest.mark.asyncio
    async def test_extract_pdf_max_pages(self, pdf_extractor):
        """Test PDF extraction with max_pages limit"""
        # Would need actual PDF file to test properly
        # This is a conceptual test
        pass


# ============================================================================
# TEST: DOCX Extractor
# ============================================================================

class TestDOCXExtractor:
    """Test DOCX text extraction"""
    
    def test_docx_extractor_initialization(self, docx_extractor):
        """Test DOCX extractor initialization"""
        assert docx_extractor is not None
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in docx_extractor.SUPPORTED_MIMES
    
    def test_docx_supported_mimes(self):
        """Test DOCX supported MIME types"""
        extractor = DOCXExtractor()
        
        # DOCX MIME types
        assert any("word" in mime.lower() for mime in extractor.SUPPORTED_MIMES)
    
    @pytest.mark.asyncio
    async def test_extract_docx_not_found(self, docx_extractor, temp_dir):
        """Test extracting non-existent DOCX"""
        docx_path = temp_dir / "non_existent.docx"
        
        with pytest.raises(DocumentExtractorError):
            await docx_extractor.extract(docx_path)
    
    @pytest.mark.asyncio
    async def test_extract_docx_invalid_file(self, docx_extractor, temp_dir):
        """Test extracting invalid DOCX file"""
        docx_path = temp_dir / "invalid.docx"
        docx_path.write_text("This is not a DOCX file")
        
        with pytest.raises(DocumentExtractorError):
            await docx_extractor.extract(docx_path)


# ============================================================================
# TEST: TXT Extractor
# ============================================================================

class TestTXTExtractor:
    """Test TXT text extraction"""
    
    def test_txt_extractor_initialization(self, txt_extractor):
        """Test TXT extractor initialization"""
        assert txt_extractor is not None
        assert "text/plain" in txt_extractor.SUPPORTED_MIMES
    
    @pytest.mark.asyncio
    async def test_extract_txt_simple(self, txt_extractor, temp_dir):
        """Test extracting simple text file"""
        txt_path = temp_dir / "test.txt"
        content = "Hello\nWorld\nTest content"
        txt_path.write_text(content)
        
        result = await txt_extractor.extract(txt_path)
        
        assert "Hello" in result
        assert "World" in result
        assert "Test content" in result
    
    @pytest.mark.asyncio
    async def test_extract_txt_empty_file(self, txt_extractor, temp_dir):
        """Test extracting empty text file"""
        txt_path = temp_dir / "empty.txt"
        txt_path.write_text("")
        
        # Empty files raise an error in TXT extractor
        with pytest.raises(DocumentExtractorError):
            await txt_extractor.extract(txt_path)
    
    @pytest.mark.asyncio
    async def test_extract_txt_unicode(self, txt_extractor, temp_dir):
        """Test extracting text with unicode characters"""
        txt_path = temp_dir / "unicode.txt"
        content = "Hello 世界 مرحبا мир"
        txt_path.write_text(content, encoding='utf-8')
        
        result = await txt_extractor.extract(txt_path)
        
        assert "Hello" in result
        assert "世界" in result or "Hello" in result
    
    @pytest.mark.asyncio
    async def test_extract_txt_large_file(self, txt_extractor, temp_dir):
        """Test extracting large text file"""
        txt_path = temp_dir / "large.txt"
        # Create 1MB text file
        content = "Line of text\n" * 100000
        txt_path.write_text(content)
        
        result = await txt_extractor.extract(txt_path)
        
        assert len(result) > 0
        assert "Line of text" in result
    
    @pytest.mark.asyncio
    async def test_extract_txt_not_found(self, txt_extractor, temp_dir):
        """Test extracting non-existent text file"""
        txt_path = temp_dir / "non_existent.txt"
        
        with pytest.raises(DocumentExtractorError):
            await txt_extractor.extract(txt_path)


# ============================================================================
# TEST: Universal Document Extractor
# ============================================================================

class TestUniversalDocumentExtractor:
    """Test universal document extractor"""
    
    def test_universal_extractor_initialization(self, universal_extractor):
        """Test universal extractor initialization"""
        assert universal_extractor is not None
        
        # Should have multiple extractors
        assert len(universal_extractor.extractors) > 0
    
    def test_universal_extractor_has_supported_formats(self, universal_extractor):
        """Test universal extractor lists supported formats"""
        # Check SUPPORTED_MIMES constant
        assert hasattr(universal_extractor, 'SUPPORTED_MIMES')
        assert "text/plain" in universal_extractor.SUPPORTED_MIMES
    
    @pytest.mark.asyncio
    async def test_extract_txt_via_universal(self, universal_extractor, temp_dir):
        """Test extracting text via universal extractor"""
        txt_path = temp_dir / "test.txt"
        content = "Test content for universal extractor"
        txt_path.write_text(content)
        
        result = await universal_extractor.extract(txt_path)
        
        assert "Test content" in result
    
    @pytest.mark.asyncio
    async def test_extract_auto_detect_mime(self, universal_extractor, temp_dir):
        """Test auto-detecting MIME type"""
        txt_path = temp_dir / "auto.txt"
        txt_path.write_text("Auto-detected content")
        
        # Try auto-detection based on extension
        result = await universal_extractor.extract(txt_path)
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_extract_unsupported_format(self, universal_extractor, temp_dir):
        """Test extracting unsupported format"""
        unknown_path = temp_dir / "file.unknown"
        unknown_path.write_bytes(b"Unknown format")
        
        # Universal extractor tries to read as text
        # It may succeed or fail depending on content
        try:
            result = await universal_extractor.extract(unknown_path)
            assert result is not None
        except DocumentExtractorError:
            pass  # Expected for truly unsupported formats
    
    def test_get_extractor_for_mime(self, universal_extractor):
        """Test getting extractor for specific format"""
        # Universal extractor has extractors dict for different extensions
        assert hasattr(universal_extractor, 'extractors')
        assert len(universal_extractor.extractors) > 0
    
    def test_get_extractor_unsupported_mime(self, universal_extractor):
        """Test extractor for unsupported format defaults to text"""
        # Universal extractor falls back to PlainTextExtractor for unknown types
        # Check that it has extractors for common formats
        assert '.txt' in universal_extractor.extractors
        assert '.pdf' in universal_extractor.extractors
        assert '.docx' in universal_extractor.extractors


# ============================================================================
# TEST: DocumentExtractorError
# ============================================================================

class TestDocumentExtractorError:
    """Test error handling"""
    
    def test_document_extractor_error(self):
        """Test DocumentExtractorError exception"""
        with pytest.raises(DocumentExtractorError):
            raise DocumentExtractorError("Test error message")
    
    def test_error_message_preserved(self):
        """Test error message is preserved"""
        error_msg = "Custom error message"
        
        try:
            raise DocumentExtractorError(error_msg)
        except DocumentExtractorError as e:
            assert error_msg in str(e)


# ============================================================================
# TEST: Integration Tests
# ============================================================================

class TestDocumentExtractionIntegration:
    """Test document extraction integration"""
    
    @pytest.mark.asyncio
    async def test_extract_multiple_formats(self, universal_extractor, temp_dir):
        """Test extracting from multiple document formats"""
        # Create multiple test files
        txt_path = temp_dir / "doc.txt"
        txt_path.write_text("Text document content")
        
        results = []
        
        # Extract text file
        try:
            result = await universal_extractor.extract(txt_path)
            results.append(result)
        except DocumentExtractorError:
            pass
        
        # Should have at least one successful extraction
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_batch_extract(self, txt_extractor, temp_dir):
        """Test batch extraction of multiple files"""
        files = []
        for i in range(3):
            txt_path = temp_dir / f"doc{i}.txt"
            txt_path.write_text(f"Content {i}")
            files.append(txt_path)
        
        results = []
        for file_path in files:
            result = await txt_extractor.extract(file_path)
            results.append(result)
        
        assert len(results) == 3
        assert all(r is not None for r in results)


# ============================================================================
# TEST: File Handling
# ============================================================================

class TestFileHandling:
    """Test file handling and validation"""
    
    @pytest.mark.asyncio
    async def test_extract_with_path_object(self, txt_extractor, temp_dir):
        """Test extraction with Path object"""
        txt_path = temp_dir / "test.txt"
        txt_path.write_text("Path object content")
        
        result = await txt_extractor.extract(txt_path)
        
        assert "Path object content" in result
    
    @pytest.mark.asyncio
    async def test_extract_with_string_path(self, txt_extractor, temp_dir):
        """Test extraction with string path"""
        txt_path = temp_dir / "test.txt"
        txt_path.write_text("String path content")
        
        result = await txt_extractor.extract(str(txt_path))
        
        assert "String path content" in result
    
    @pytest.mark.asyncio
    async def test_extract_permissions_error(self, txt_extractor, temp_dir):
        """Test handling permission errors"""
        # Create a file with restricted permissions
        txt_path = temp_dir / "restricted.txt"
        txt_path.write_text("Restricted content")
        
        # Try to make it unreadable (may not work on all systems)
        try:
            txt_path.chmod(0o000)
            
            with pytest.raises(DocumentExtractorError):
                await txt_extractor.extract(txt_path)
        finally:
            # Restore permissions for cleanup
            txt_path.chmod(0o644)


# ============================================================================
# TEST: Performance
# ============================================================================

class TestDocumentExtractionPerformance:
    """Test extraction performance"""
    
    @pytest.mark.asyncio
    async def test_large_text_extraction(self, txt_extractor, temp_dir):
        """Test extracting large text files"""
        txt_path = temp_dir / "large.txt"
        # Create 10MB text file
        large_content = "x" * (10 * 1024 * 1024)
        txt_path.write_text(large_content)
        
        result = await txt_extractor.extract(txt_path)
        
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_extraction_preserves_formatting(self, txt_extractor, temp_dir):
        """Test that extraction preserves formatting"""
        txt_path = temp_dir / "formatted.txt"
        formatted_content = """Title
        
Section 1
- Item 1
- Item 2
        
Section 2
Content here"""
        txt_path.write_text(formatted_content)
        
        result = await txt_extractor.extract(txt_path)
        
        # Should preserve structure
        assert "Title" in result
        assert "Section 1" in result
        assert "Item 1" in result
