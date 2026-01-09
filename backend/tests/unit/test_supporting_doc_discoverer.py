import json
import pytest



from src.services.supporting_documents.supporting_doc_discoverer import (
    SupportingDocDiscoverer,
    SupportingDocDiscoveryError,
)


SAMPLE_JSON = {
    "supportingDocuments": [
        {"url": "https://example.com/document.pdf"},
        {"url": "https://example.com/data.zip"},
        {"url": "https://example.com/folder/"},
    ]
}


@pytest.mark.asyncio
async def test_discover_urls_from_json():
    """Test URL discovery from JSON."""
    discoverer = SupportingDocDiscoverer()
    result = await discoverer.discover_from_json(json.dumps(SAMPLE_JSON))

    assert len(result.supporting_docs) == 1  # PDF
    assert len(result.download_urls) == 1  # ZIP
    # Folder URLs (ending with /) are NOT automatically classified as fileaccess_urls
    # They must have "fileaccess" or "/directory/" in the URL
    # So the folder/ URL is skipped entirely
    assert len(result.fileaccess_urls) == 0


@pytest.mark.asyncio
async def test_discover_rejects_invalid_json():
    """Test error handling for invalid JSON."""
    discoverer = SupportingDocDiscoverer()
    with pytest.raises(SupportingDocDiscoveryError):
        await discoverer.discover_from_json("{invalid json}")