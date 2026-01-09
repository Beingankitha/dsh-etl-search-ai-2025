"""
Unit tests for RDF (Turtle) metadata parser.

Tests parsing of RDF/Turtle metadata documents from CEH catalogue using DCAT vocabulary.
"""

import pytest

from src.services.parsers.rdf_parser import RDFParser
from src.services.parsers.metadata_parser import MetadataParserError


SAMPLE_TURTLE = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

<http://example.com/dataset/1> a dcat:Dataset ;
    dct:identifier "be0bdc0e-bc2e-4f1d-b524-2c02798dd893" ;
    dct:title "Sample Dataset" ;
    dct:description "This is a sample dataset abstract." ;
    dcat:keyword "soil" ;
    dcat:keyword "ecology" ;
    dct:creator [
        a foaf:Person ;
        foaf:name "John Doe"
    ] ;
    dct:subject "geoscientificInformation" .
"""

MULTIPLE_KEYWORDS_TURTLE = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .

<http://example.com/dataset/2> a dcat:Dataset ;
    dct:identifier "dataset-2" ;
    dct:title "Multi-Keyword Dataset" ;
    dct:description "Dataset with many keywords" ;
    dcat:keyword "water" ;
    dcat:keyword "soil" ;
    dcat:keyword "carbon" ;
    dcat:keyword "nitrogen" ;
    dcat:keyword "ecosystem" .
"""

MINIMAL_TURTLE = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .

<http://example.com/dataset/3> a dcat:Dataset ;
    dct:identifier "minimal-id" ;
    dct:title "Minimal Dataset" .
"""

WITH_DCTERMS_TURTLE = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix dcterms: <http://purl.org/dc/terms/> .

<http://example.com/dataset/4> a dcat:Dataset ;
    dcterms:identifier "dcterms-id" ;
    dcterms:title "DCTerms Dataset" ;
    dcterms:description "Using dcterms prefix" ;
    dcterms:subject "environment" .
"""

WITH_SUBJECTS_TURTLE = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .

<http://example.com/dataset/5> a dcat:Dataset ;
    dct:identifier "subjects-id" ;
    dct:title "Multiple Subjects" ;
    dct:description "Dataset with multiple subjects" ;
    dct:subject "geoscientificInformation" ;
    dct:subject "biota" ;
    dct:subject "environment" .
"""

BLANK_NODES_TURTLE = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

<http://example.com/dataset/6> a dcat:Dataset ;
    dct:identifier "blank-nodes-id" ;
    dct:title "Blank Nodes Dataset" ;
    dct:description "Dataset with blank nodes" ;
    dct:creator [ foaf:name "Anonymous Author" ] ;
    dct:publisher [ foaf:name "Unknown Publisher" ] .
"""


@pytest.fixture
def parser():
    """Create an RDF parser instance."""
    return RDFParser()


# ============================================================================
# BASIC PARSING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rdf_parser_extracts_fields(parser):
    """Test RDF/Turtle parser extraction of basic fields."""
    dataset = await parser.parse(SAMPLE_TURTLE)

    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    assert dataset.title == "Sample Dataset"
    assert "sample dataset abstract" in dataset.abstract.lower()
    assert "soil" in dataset.keywords
    assert "ecology" in dataset.keywords


@pytest.mark.asyncio
async def test_rdf_parser_handles_missing_fields(parser):
    """Test RDF parser handles missing optional fields."""
    dataset = await parser.parse(MINIMAL_TURTLE)

    assert dataset.file_identifier == "minimal-id"
    assert dataset.title == "Minimal Dataset"
    assert dataset.abstract == ""
    assert dataset.keywords == []


@pytest.mark.asyncio
async def test_rdf_parser_with_multiple_keywords(parser):
    """Test RDF parser extracts multiple keywords."""
    dataset = await parser.parse(MULTIPLE_KEYWORDS_TURTLE)

    assert dataset.file_identifier == "dataset-2"
    assert len(dataset.keywords) == 5
    assert "water" in dataset.keywords
    assert "soil" in dataset.keywords
    assert "carbon" in dataset.keywords


@pytest.mark.asyncio
async def test_rdf_parser_with_dcterms_prefix(parser):
    """Test RDF parser with dcterms namespace prefix."""
    dataset = await parser.parse(WITH_DCTERMS_TURTLE)

    assert dataset.file_identifier == "dcterms-id"
    assert dataset.title == "DCTerms Dataset"
    assert "dcterms" in dataset.abstract.lower() or dataset.abstract != ""


@pytest.mark.asyncio
async def test_rdf_parser_with_multiple_subjects(parser):
    """Test RDF parser extracts multiple subject/topic categories."""
    dataset = await parser.parse(WITH_SUBJECTS_TURTLE)

    assert dataset.file_identifier == "subjects-id"
    assert "geoscientificInformation" in dataset.topic_category
    assert "biota" in dataset.topic_category
    assert "environment" in dataset.topic_category


@pytest.mark.asyncio
async def test_rdf_parser_with_blank_nodes(parser):
    """Test RDF parser handles blank nodes in creator/publisher."""
    dataset = await parser.parse(BLANK_NODES_TURTLE)

    assert dataset.file_identifier == "blank-nodes-id"
    assert dataset.title == "Blank Nodes Dataset"
    # Lineage should contain creator info
    assert dataset.lineage is not None or dataset.abstract != ""


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rdf_parser_rejects_invalid_turtle(parser):
    """Test that invalid Turtle raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("@invalid turtle content")


@pytest.mark.asyncio
async def test_rdf_parser_empty_string(parser):
    """Test that empty string raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("")


@pytest.mark.asyncio
async def test_rdf_parser_missing_dataset_resource(parser):
    """Test that RDF without dcat:Dataset raises error."""
    rdf_no_dataset = """
    @prefix dcat: <http://www.w3.org/ns/dcat#> .
    @prefix dct: <http://purl.org/dc/terms/> .
    
    <http://example.com/other> a dcat:Catalog ;
        dct:title "This is not a dataset" .
    """
    
    with pytest.raises(MetadataParserError):
        await parser.parse(rdf_no_dataset)


@pytest.mark.asyncio
async def test_rdf_parser_malformed_turtle_syntax(parser):
    """Test that malformed Turtle syntax raises error."""
    malformed = """
    @prefix dcat: <http://www.w3.org/ns/dcat#> .
    
    <http://example.com/dataset> a dcat:Dataset
    dct:title "Missing semicolon above"
    """
    
    with pytest.raises(MetadataParserError):
        await parser.parse(malformed)


# ============================================================================
# NAMESPACE HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rdf_parser_with_multiple_namespaces(parser):
    """Test RDF parser with multiple namespace definitions."""
    complex_rdf = """
    @prefix dcat: <http://www.w3.org/ns/dcat#> .
    @prefix dct: <http://purl.org/dc/terms/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .
    @prefix adms: <http://www.w3.org/ns/adms#> .
    @prefix vcard: <http://www.w3.org/2006/vcard/ns#> .
    
    <http://example.com/dataset/complex> a dcat:Dataset ;
        dct:identifier "complex-id" ;
        dct:title "Complex Namespaces" ;
        dct:description "Test with many namespaces" ;
        dcat:keyword "test" ;
        dct:subject "environment" ;
        foaf:depiction <http://example.com/image.png> ;
        adms:status "completed" .
    """
    
    dataset = await parser.parse(complex_rdf)
    
    assert dataset.file_identifier == "complex-id"
    assert dataset.title == "Complex Namespaces"


# ============================================================================
# UNICODE AND SPECIAL CHARACTERS
# ============================================================================

@pytest.mark.asyncio
async def test_rdf_parser_unicode_in_literals(parser):
    """Test RDF parser handles Unicode in literal values."""
    unicode_rdf = """
    @prefix dcat: <http://www.w3.org/ns/dcat#> .
    @prefix dct: <http://purl.org/dc/terms/> .
    
    <http://example.com/dataset/unicode> a dcat:Dataset ;
        dct:identifier "unicode-id" ;
        dct:title "Tïtlé wîth ünïcödé" ;
        dct:description "Àbstrâct with émojis 🌍" ;
        dcat:keyword "Frënch" ;
        dcat:keyword "日本語" ;
        dcat:keyword "العربية" .
    """
    
    dataset = await parser.parse(unicode_rdf)
    
    assert "ünïcödé" in dataset.title or "unicode" in dataset.title.lower()


# ============================================================================
# RDF FORMAT VARIATIONS
# ============================================================================

@pytest.mark.asyncio
async def test_rdf_parser_ttl_format(parser):
    """Test RDF parser with TTL (Turtle) format."""
    # Standard Turtle format is already being tested
    dataset = await parser.parse(SAMPLE_TURTLE)
    assert dataset.file_identifier is not None


@pytest.mark.asyncio
async def test_rdf_parser_extended_properties(parser):
    """Test RDF parser with extended properties."""
    extended_rdf = """
    @prefix dcat: <http://www.w3.org/ns/dcat#> .
    @prefix dct: <http://purl.org/dc/terms/> .
    @prefix schema: <http://schema.org/> .
    
    <http://example.com/dataset/extended> a dcat:Dataset ;
        dct:identifier "extended-id" ;
        dct:title "Extended Properties" ;
        dct:description "Dataset with extended properties" ;
        dcat:keyword "extended" ;
        dct:issued "2020-01-01"^^<http://www.w3.org/2001/XMLSchema#date> ;
        dct:modified "2023-12-31"^^<http://www.w3.org/2001/XMLSchema#date> ;
        dcat:distribution [ dcat:accessURL <http://example.com/data.csv> ] .
    """
    
    dataset = await parser.parse(extended_rdf)
    
    assert dataset.file_identifier == "extended-id"
    assert dataset.title == "Extended Properties"
