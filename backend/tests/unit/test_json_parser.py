"""
Unit tests for JSON metadata parser.

Tests parsing of JSON metadata documents from CEH catalogue.
"""

import json
import pytest

from src.services.parsers.json_parser import JSONMetadataParser
from src.services.parsers.metadata_parser import MetadataParserError


SAMPLE_JSON = {
    "fileIdentifier": "be0bdc0e-bc2e-4f1d-b524-2c02798dd893",
    "title": "Sample Dataset",
    "abstract": "This is a sample dataset abstract.",
    "topicCategory": ["geoscientificInformation"],
    "keywords": ["soil", "ecology"],
    "lineage": "Data collected via field surveys.",
    "supplementalInformation": "Additional notes here.",
}


@pytest.fixture
def parser():
    """Create a JSON parser instance."""
    return JSONMetadataParser()


# ============================================================================
# BASIC PARSING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_json_parser_extracts_all_fields(parser):
    """Test that JSON parser extracts all required fields."""
    dataset = await parser.parse(json.dumps(SAMPLE_JSON))

    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    assert dataset.title == "Sample Dataset"
    assert "sample dataset abstract" in dataset.abstract.lower()
    assert "geoscientificInformation" in dataset.topic_category
    assert "soil" in dataset.keywords
    assert dataset.lineage is not None
    assert dataset.supplemental_info is not None


@pytest.mark.asyncio
async def test_json_parser_handles_missing_fields(parser):
    """Test graceful handling of missing fields."""
    minimal = {
        "fileIdentifier": "id-1",
        "title": "Minimal Dataset",
    }
    dataset = await parser.parse(json.dumps(minimal))

    assert dataset.file_identifier == "id-1"
    assert dataset.title == "Minimal Dataset"
    assert dataset.abstract == ""
    assert dataset.topic_category == []
    assert dataset.keywords == []
    assert dataset.lineage is None


@pytest.mark.asyncio
async def test_json_parser_with_nested_metadata_object(parser):
    """Test parsing JSON with nested metadata object."""
    json_data = {
        "metadata": {
            "fileIdentifier": "nested-id",
            "title": "Nested Dataset",
            "abstract": "Nested abstract"
        },
        "keywords": ["test"]
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert dataset.file_identifier == "nested-id"
    assert dataset.title == "Nested Dataset"


@pytest.mark.asyncio
async def test_json_parser_with_alternative_field_names(parser):
    """Test parsing JSON with alternative field names (id, identifier)."""
    json_data = {
        "id": "alt-id-001",
        "title": "Alternative Fields",
        "abstract": "Test with alternative field names"
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert dataset.file_identifier == "alt-id-001"
    assert dataset.title == "Alternative Fields"


# ============================================================================
# MISSING/NULL FIELD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_json_parser_with_null_values(parser):
    """Test parsing JSON with null values."""
    json_data = {
        "fileIdentifier": "test-id",
        "title": "Test",
        "abstract": None,
        "keywords": None
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert dataset.file_identifier == "test-id"
    assert dataset.abstract == ""
    assert dataset.keywords == []


@pytest.mark.asyncio
async def test_json_parser_with_empty_strings(parser):
    """Test parsing JSON with empty strings."""
    json_data = {
        "fileIdentifier": "  ",
        "title": "Test",
        "abstract": "",
        "keywords": ["", "  ", "valid"]
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert dataset.file_identifier == "unknown"
    assert dataset.abstract == ""
    assert "valid" in dataset.keywords
    assert "" not in dataset.keywords


@pytest.mark.asyncio
async def test_json_parser_with_whitespace_padding(parser):
    """Test parsing JSON with whitespace padding."""
    json_data = {
        "fileIdentifier": "  whitespace-id  ",
        "title": "  Padded Title  ",
        "abstract": "  Abstract with spaces  ",
        "keywords": ["  keyword1  ", "keyword2"]
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert dataset.file_identifier == "whitespace-id"
    assert dataset.title == "Padded Title"
    assert dataset.abstract == "Abstract with spaces"
    assert "keyword1" in dataset.keywords


# ============================================================================
# KEYWORD/TOPIC TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_json_parser_with_array_keywords(parser):
    """Test parsing JSON with array of keywords."""
    json_data = {
        "fileIdentifier": "id-001",
        "title": "Keywords Test",
        "keywords": ["soil", "water", "ecosystem"]
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert len(dataset.keywords) >= 3
    assert "soil" in dataset.keywords
    assert "water" in dataset.keywords


@pytest.mark.asyncio
async def test_json_parser_with_string_keyword(parser):
    """Test parsing JSON with single string keyword."""
    json_data = {
        "fileIdentifier": "id-001",
        "title": "Test",
        "keywords": "single-keyword"
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert "single-keyword" in dataset.keywords


@pytest.mark.asyncio
async def test_json_parser_with_topic_category(parser):
    """Test parsing JSON with topic categories."""
    json_data = {
        "fileIdentifier": "id-001",
        "title": "Test",
        "topicCategory": ["geoscientificInformation", "biota"]
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert "geoscientificInformation" in dataset.topic_category


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_json_parser_invalid_json_format(parser):
    """Test parsing invalid JSON raises error."""
    invalid_json = '{"incomplete": json'
    
    with pytest.raises(MetadataParserError):
        await parser.parse(invalid_json)


@pytest.mark.asyncio
async def test_json_parser_empty_string(parser):
    """Test parsing empty string raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("")


@pytest.mark.asyncio
async def test_json_parser_not_json_string(parser):
    """Test parsing non-JSON string raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("this is not json")


@pytest.mark.asyncio
async def test_json_parser_json_array_instead_of_object(parser):
    """Test parsing JSON array (not object) is handled."""
    json_array = json.dumps([{"title": "Item1"}, {"title": "Item2"}])
    
    with pytest.raises(MetadataParserError):
        await parser.parse(json_array)


# ============================================================================
# UNICODE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_json_parser_with_unicode_characters(parser):
    """Test parsing JSON with unicode characters."""
    json_data = {
        "fileIdentifier": "unicode-test",
        "title": "Tïtlé wîth ünïcödé",
        "abstract": "Àbstrâct with émojis 🌍 📊",
        "keywords": ["Frënch", "Español", "Português"]
    }
    
    dataset = await parser.parse(json.dumps(json_data, ensure_ascii=False))
    
    assert "ünïcödé" in dataset.title
    assert "🌍" in dataset.abstract or "Àbstrâct" in dataset.abstract


# ============================================================================
# LARGE DOCUMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_json_parser_large_keywords_list(parser):
    """Test parsing JSON with large keywords list."""
    keywords = [f"keyword-{i}" for i in range(100)]
    json_data = {
        "fileIdentifier": "large-keywords",
        "title": "Large Keywords Test",
        "keywords": keywords
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert len(dataset.keywords) >= 100


@pytest.mark.asyncio
async def test_json_parser_large_abstract(parser):
    """Test parsing JSON with large abstract text."""
    large_abstract = "Abstract. " * 5000  # ~50KB
    json_data = {
        "fileIdentifier": "large-abstract",
        "title": "Large Abstract Test",
        "abstract": large_abstract
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert len(dataset.abstract) > 45000


# ============================================================================
# SPECIAL VALUE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_json_parser_numeric_identifier(parser):
    """Test parsing JSON with numeric identifier."""
    json_data = {
        "fileIdentifier": 12345,
        "title": "Test",
        "abstract": "Description"
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert dataset.file_identifier == "12345"


@pytest.mark.asyncio
async def test_json_parser_with_extra_fields(parser):
    """Test parsing JSON with extra unknown fields is ignored."""
    json_data = {
        "fileIdentifier": "id-001",
        "title": "Test",
        "abstract": "Description",
        "unknownField1": "value1",
        "unknownField2": {"nested": "value"},
        "unknownField3": [1, 2, 3]
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert dataset.file_identifier == "id-001"
    assert dataset.title == "Test"


@pytest.mark.asyncio
async def test_json_parser_rich_lineage(parser):
    """Test parsing JSON with rich lineage information."""
    json_data = {
        "fileIdentifier": "lineage-test",
        "title": "Lineage Test",
        "lineage": "Data collected from field surveys 2020-2023. Processed by GIS team.",
        "abstract": "Test dataset"
    }
    
    dataset = await parser.parse(json.dumps(json_data))
    
    assert "field surveys" in dataset.lineage
    assert "GIS team" in dataset.lineage


@pytest.mark.asyncio
async def test_json_parser_rejects_invalid_json():
    """Test that invalid JSON raises error."""
    parser = JSONMetadataParser()
    with pytest.raises(MetadataParserError):
        await parser.parse("{invalid json}")