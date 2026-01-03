import json
import pytest

from src.services.parsers.schema_org_parser import SchemaOrgParser, MetadataParserError


SAMPLE_SCHEMA_ORG = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "identifier": "be0bdc0e-bc2e-4f1d-b524-2c02798dd893",
    "name": "Sample Dataset",
    "description": "This is a sample dataset abstract.",
    "keywords": ["soil", "ecology"],
    "creator": {
        "@type": "Person",
        "name": "John Doe",
    },
    "url": "https://example.com/dataset",
}


@pytest.mark.asyncio
async def test_schema_org_parser_extracts_fields():
    """Test Schema.org parser extraction."""
    parser = SchemaOrgParser()
    dataset = await parser.parse(json.dumps(SAMPLE_SCHEMA_ORG))

    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    assert dataset.title == "Sample Dataset"
    assert "sample dataset abstract" in dataset.abstract.lower()
    assert "soil" in dataset.keywords
    assert "ecology" in dataset.keywords


@pytest.mark.asyncio
async def test_schema_org_parser_rejects_invalid_json():
    """Test that invalid JSON raises error."""
    parser = SchemaOrgParser()
    with pytest.raises(MetadataParserError):
        await parser.parse("{invalid}")