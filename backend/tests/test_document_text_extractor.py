import pytest
from pathlib import Path

from src.services.txt_extractor import TXTExtractor
from src.services.document_extractor import DocumentExtractorError


@pytest.mark.asyncio
async def test_txt_extractor_reads_plain_text():
    """Test TXT extractor with plain text file."""
    extractor = TXTExtractor()

    # Create temporary test file
    test_file = Path("/tmp/test_doc.txt")
    test_content = "This is a test document.\nWith multiple lines.\n"
    test_file.write_text(test_content)

    try:
        result = await extractor.extract(test_file)
        assert "test document" in result.lower()
        assert "multiple lines" in result.lower()
    finally:
        test_file.unlink()


@pytest.mark.asyncio
async def test_txt_extractor_handles_missing_file():
    """Test error handling for missing files."""
    extractor = TXTExtractor()
    with pytest.raises(DocumentExtractorError):
        await extractor.extract("/nonexistent/file.txt")


@pytest.mark.asyncio
async def test_txt_extractor_handles_empty_file():
    """Test error handling for empty files."""
    extractor = TXTExtractor()

    test_file = Path("/tmp/empty.txt")
    test_file.write_text("")

    try:
        with pytest.raises(DocumentExtractorError):
            await extractor.extract(test_file)
    finally:
        test_file.unlink()