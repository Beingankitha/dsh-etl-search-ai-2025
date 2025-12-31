import pytest
import zipfile
from io import BytesIO

from src.services.zip_extractor import ZipExtractor, ZipExtractorError


@pytest.mark.asyncio
async def test_extract_zip_in_memory():
    """Test in-memory ZIP extraction."""
    # Create test ZIP
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("file1.txt", "Content 1")
        zf.writestr("file2.txt", "Content 2")
    zip_bytes = zip_buffer.getvalue()

    extractor = ZipExtractor()
    result = await extractor.extract_in_memory(zip_bytes)

    assert len(result) == 2
    assert result["file1.txt"] == b"Content 1"
    assert result["file2.txt"] == b"Content 2"


@pytest.mark.asyncio
async def test_extract_zip_with_filter():
    """Test ZIP extraction with file filtering."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("report.pdf", "PDF Content")
        zf.writestr("image.jpg", "JPG Content")
    zip_bytes = zip_buffer.getvalue()

    extractor = ZipExtractor()

    # Filter to only PDFs
    def pdf_filter(path: str) -> bool:
        return path.endswith(".pdf")

    result = await extractor.extract_in_memory(zip_bytes, file_filter=pdf_filter)

    assert len(result) == 1
    assert "report.pdf" in result


@pytest.mark.asyncio
async def test_extract_rejects_invalid_zip():
    """Test error handling for invalid ZIP."""
    extractor = ZipExtractor()
    with pytest.raises(ZipExtractorError):
        await extractor.extract_in_memory(b"not a zip file")