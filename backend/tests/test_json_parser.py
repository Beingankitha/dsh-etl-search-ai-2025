import json
import pytest

from src.services.parsers.json_parser import JSONMetadataParser, MetadataParserError


SAMPLE_JSON = {
    "fileIdentifier": "be0bdc0e-bc2e-4f1d-b524-2c02798dd893",
    "title": "Sample Dataset",
    "abstract": "This is a sample dataset abstract.",
    "topicCategory": ["geoscientificInformation"],
    "keywords": ["soil", "ecology"],
    "lineage": "Data collected via field surveys.",
    "supplementalInformation": "Additional notes here.",
}


@pytest.mark.asyncio
async def test_json_parser_extracts_all_fields():
    """Test that JSON parser extracts all required fields."""
    parser = JSONMetadataParser()
    dataset = await parser.parse(json.dumps(SAMPLE_JSON))

    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    assert dataset.title == "Sample Dataset"
    assert "sample dataset abstract" in dataset.abstract.lower()
    assert "geoscientificInformation" in dataset.topic_category
    assert "soil" in dataset.keywords
    assert dataset.lineage is not None
    assert dataset.supplemental_info is not None


@pytest.mark.asyncio
async def test_json_parser_handles_missing_fields():
    """Test graceful handling of missing fields."""
    minimal = {
        "fileIdentifier": "id-1",
        "title": "Minimal Dataset",
    }
    parser = JSONMetadataParser()
    dataset = await parser.parse(json.dumps(minimal))

    assert dataset.file_identifier == "id-1"
    assert dataset.title == "Minimal Dataset"
    assert dataset.abstract == ""
    assert dataset.topic_category == []
    assert dataset.keywords == []
    assert dataset.lineage is None


@pytest.mark.asyncio
async def test_json_parser_rejects_invalid_json():
    """Test that invalid JSON raises error."""
    parser = JSONMetadataParser()
    with pytest.raises(MetadataParserError):
        await parser.parse("{invalid json}")