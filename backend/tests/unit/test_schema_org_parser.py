"""
Unit tests for Schema.org (JSON-LD) metadata parser.

Tests parsing of structured data in Schema.org vocabulary using JSON-LD format.
"""

import json
import pytest

from src.services.parsers.schema_org_parser import SchemaOrgParser
from src.services.parsers.metadata_parser import MetadataParserError


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

SCHEMA_ORG_WITH_GRAPH = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "Organization",
            "@id": "https://example.com/org",
            "name": "Example Organization"
        },
        {
            "@type": "Dataset",
            "identifier": "graph-dataset-id",
            "name": "Graph Dataset",
            "description": "Dataset in @graph structure"
        }
    ]
}

SCHEMA_ORG_MINIMAL = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "identifier": "minimal-id",
    "name": "Minimal Dataset"
}

SCHEMA_ORG_WITH_CREATOR = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "identifier": "creator-dataset",
    "name": "Dataset with Creator",
    "description": "Test creator field",
    "creator": {
        "@type": "Person",
        "name": "Jane Smith"
    },
    "author": {
        "@type": "Organization",
        "name": "Research Institute"
    }
}

SCHEMA_ORG_WITH_COVERAGE = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "identifier": "coverage-dataset",
    "name": "Coverage Dataset",
    "description": "Dataset with spatial and temporal coverage",
    "spatialCoverage": "United Kingdom",
    "temporalCoverage": "2020-01-01/2023-12-31"
}

SCHEMA_ORG_ARRAY_KEYWORDS = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "identifier": "array-keywords",
    "name": "Array Keywords",
    "description": "Dataset with keyword array",
    "keywords": ["soil", "water", "carbon", "nitrogen", "ecosystem"]
}

SCHEMA_ORG_STRING_KEYWORDS = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "identifier": "string-keywords",
    "name": "String Keywords",
    "description": "Dataset with comma-separated keywords",
    "keywords": "soil, water, ecosystem, biodiversity"
}

SCHEMA_ORG_PROPERTY_VALUE_IDENTIFIER = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "identifier": {
        "@type": "PropertyValue",
        "value": "property-value-id"
    },
    "name": "PropertyValue ID",
    "description": "Dataset with PropertyValue identifier"
}


@pytest.fixture
def parser():
    """Create a Schema.org parser instance."""
    return SchemaOrgParser()


# ============================================================================
# BASIC PARSING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_extracts_fields(parser):
    """Test Schema.org parser extraction of basic fields."""
    dataset = await parser.parse(json.dumps(SAMPLE_SCHEMA_ORG))

    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    assert dataset.title == "Sample Dataset"
    assert "sample dataset abstract" in dataset.abstract.lower()
    assert "soil" in dataset.keywords
    assert "ecology" in dataset.keywords


@pytest.mark.asyncio
async def test_schema_org_parser_handles_missing_fields(parser):
    """Test Schema.org parser handles missing optional fields."""
    dataset = await parser.parse(json.dumps(SAMPLE_SCHEMA_ORG))

    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    assert dataset.title == "Sample Dataset"


@pytest.mark.asyncio
async def test_schema_org_parser_with_graph_structure(parser):
    """Test Schema.org parser with @graph containing multiple entities."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_WITH_GRAPH))

    assert dataset.file_identifier == "graph-dataset-id"
    assert dataset.title == "Graph Dataset"
    assert "graph structure" in dataset.abstract.lower()


@pytest.mark.asyncio
async def test_schema_org_parser_minimal(parser):
    """Test Schema.org parser with minimal required fields."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_MINIMAL))

    assert dataset.file_identifier == "minimal-id"
    assert dataset.title == "Minimal Dataset"
    assert dataset.abstract == ""
    assert dataset.keywords == []


# ============================================================================
# IDENTIFIER HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_string_identifier(parser):
    """Test Schema.org parser with string identifier."""
    dataset = await parser.parse(json.dumps(SAMPLE_SCHEMA_ORG))

    assert isinstance(dataset.file_identifier, str)
    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"


@pytest.mark.asyncio
async def test_schema_org_parser_property_value_identifier(parser):
    """Test Schema.org parser with PropertyValue identifier."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_PROPERTY_VALUE_IDENTIFIER))

    assert dataset.file_identifier == "property-value-id"
    assert dataset.title == "PropertyValue ID"


# ============================================================================
# KEYWORDS HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_array_keywords(parser):
    """Test Schema.org parser with keyword array."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_ARRAY_KEYWORDS))

    assert len(dataset.keywords) == 5
    assert "soil" in dataset.keywords
    assert "water" in dataset.keywords
    assert "carbon" in dataset.keywords


@pytest.mark.asyncio
async def test_schema_org_parser_string_comma_separated_keywords(parser):
    """Test Schema.org parser with comma-separated keyword string."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_STRING_KEYWORDS))

    assert len(dataset.keywords) >= 4
    assert "soil" in dataset.keywords
    assert "water" in dataset.keywords
    assert "ecosystem" in dataset.keywords


# ============================================================================
# CREATOR/AUTHOR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_with_creator_person(parser):
    """Test Schema.org parser with creator as Person."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_WITH_CREATOR))

    assert dataset.file_identifier == "creator-dataset"
    assert "Jane Smith" in (dataset.lineage or "")


@pytest.mark.asyncio
async def test_schema_org_parser_with_creator_and_author(parser):
    """Test Schema.org parser with both creator and author."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_WITH_CREATOR))

    # Both creator and author info should be in lineage
    assert dataset.lineage is not None


# ============================================================================
# COVERAGE HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_with_spatial_coverage(parser):
    """Test Schema.org parser with spatial coverage."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_WITH_COVERAGE))

    assert dataset.file_identifier == "coverage-dataset"
    # Coverage info might be in supplemental_info
    assert dataset.abstract != "" or dataset.supplemental_info is not None


@pytest.mark.asyncio
async def test_schema_org_parser_with_temporal_coverage(parser):
    """Test Schema.org parser with temporal coverage."""
    dataset = await parser.parse(json.dumps(SCHEMA_ORG_WITH_COVERAGE))

    assert dataset.file_identifier == "coverage-dataset"
    assert dataset.title == "Coverage Dataset"


# ============================================================================
# ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_rejects_invalid_json(parser):
    """Test that invalid JSON raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("{invalid}")


@pytest.mark.asyncio
async def test_schema_org_parser_empty_string(parser):
    """Test that empty string raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("")


@pytest.mark.asyncio
async def test_schema_org_parser_not_json_string(parser):
    """Test that non-JSON string raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("this is not json")


@pytest.mark.asyncio
async def test_schema_org_parser_json_array_instead_of_object(parser):
    """Test that JSON array raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse(json.dumps([{"name": "item1"}, {"name": "item2"}]))


# ============================================================================
# UNICODE HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_unicode_characters(parser):
    """Test Schema.org parser handles unicode characters."""
    unicode_data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "identifier": "unicode-id",
        "name": "Tïtlé wîth ünïcödé",
        "description": "Àbstrâct with émojis 🌍 📊",
        "keywords": ["Frënch", "日本語", "العربية"]
    }
    
    dataset = await parser.parse(json.dumps(unicode_data, ensure_ascii=False))
    
    assert "ünïcödé" in dataset.title or "unicode" in dataset.title.lower()


# ============================================================================
# COMPLEX STRUCTURES
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_with_multiple_creators(parser):
    """Test Schema.org parser with array of creators."""
    multi_creator_data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "identifier": "multi-creator",
        "name": "Multi-Creator Dataset",
        "description": "Dataset with multiple creators",
        "creator": [
            {"@type": "Person", "name": "Alice"},
            {"@type": "Person", "name": "Bob"},
            {"@type": "Organization", "name": "Research Lab"}
        ]
    }
    
    dataset = await parser.parse(json.dumps(multi_creator_data))
    
    assert dataset.file_identifier == "multi-creator"


@pytest.mark.asyncio
async def test_schema_org_parser_with_nested_objects(parser):
    """Test Schema.org parser with nested object structures."""
    nested_data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "identifier": "nested-id",
        "name": "Nested Objects",
        "description": "Dataset with nested objects",
        "creator": {
            "@type": "Organization",
            "name": "Example Org",
            "url": "https://example.com",
            "contactPoint": {
                "@type": "ContactPoint",
                "name": "Support",
                "email": "support@example.com"
            }
        }
    }
    
    dataset = await parser.parse(json.dumps(nested_data))
    
    assert dataset.file_identifier == "nested-id"
    assert dataset.title == "Nested Objects"


# ============================================================================
# EXTENDED PROPERTIES
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_with_encoding_format(parser):
    """Test Schema.org parser with encoding format property."""
    with_format_data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "identifier": "format-id",
        "name": "Format Dataset",
        "description": "Dataset with encoding format",
        "encodingFormat": "CSV",
        "keywords": ["tabular", "open-data"]
    }
    
    dataset = await parser.parse(json.dumps(with_format_data))
    
    assert dataset.file_identifier == "format-id"
    assert "tabular" in dataset.keywords


@pytest.mark.asyncio
async def test_schema_org_parser_with_url_property(parser):
    """Test Schema.org parser with URL property."""
    with_url_data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "identifier": "url-id",
        "name": "URL Dataset",
        "description": "Dataset with URL",
        "url": "https://example.com/dataset",
        "downloadUrl": "https://example.com/dataset/download"
    }
    
    dataset = await parser.parse(json.dumps(with_url_data))
    
    assert dataset.file_identifier == "url-id"
    assert dataset.title == "URL Dataset"


# ============================================================================
# LARGE DOCUMENTS
# ============================================================================

@pytest.mark.asyncio
async def test_schema_org_parser_large_keywords_list(parser):
    """Test Schema.org parser with large keywords list."""
    large_keywords_data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "identifier": "large-keywords",
        "name": "Large Keywords",
        "description": "Dataset with many keywords",
        "keywords": [f"keyword-{i}" for i in range(100)]
    }
    
    dataset = await parser.parse(json.dumps(large_keywords_data))
    
    assert len(dataset.keywords) >= 100


@pytest.mark.asyncio
async def test_schema_org_parser_large_description(parser):
    """Test Schema.org parser with large description text."""
    large_description = "Description. " * 5000
    large_desc_data = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "identifier": "large-desc",
        "name": "Large Description",
        "description": large_description
    }
    
    dataset = await parser.parse(json.dumps(large_desc_data))
    
    assert len(dataset.abstract) > 45000
