import pytest

from src.services.parsers.rdf_parser import RDFParser, MetadataParserError


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


@pytest.mark.asyncio
async def test_rdf_parser_extracts_fields():
    """Test RDF/Turtle parser extraction."""
    parser = RDFParser()
    dataset = await parser.parse(SAMPLE_TURTLE)

    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    assert dataset.title == "Sample Dataset"
    assert "sample dataset abstract" in dataset.abstract.lower()
    assert "soil" in dataset.keywords
    assert "ecology" in dataset.keywords
    assert "John Doe" in (dataset.lineage or "")


@pytest.mark.asyncio
async def test_rdf_parser_rejects_invalid_turtle():
    """Test that invalid Turtle raises error."""
    parser = RDFParser()
    with pytest.raises(MetadataParserError):
        await parser.parse("@invalid turtle content")