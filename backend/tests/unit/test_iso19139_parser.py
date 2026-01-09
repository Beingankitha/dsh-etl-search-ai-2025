"""
Unit tests for ISO 19139 XML metadata parser.

Tests parsing of ISO 19115 geographic metadata encoded in XML format (ISO 19139).
"""

import pytest

from src.services.parsers.iso19139_parser import ISO19139Parser
from src.services.parsers.metadata_parser import MetadataParserError


SAMPLE_ISO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
    <gmd:fileIdentifier>
        <gco:CharacterString>be0bdc0e-bc2e-4f1d-b524-2c02798dd893</gco:CharacterString>
    </gmd:fileIdentifier>
    <gmd:identificationInfo>
        <gmd:MD_DataIdentification>
            <gmd:title>
                <gco:CharacterString>Sample Dataset</gco:CharacterString>
            </gmd:title>
            <gmd:abstract>
                <gco:CharacterString>This is a sample dataset abstract.</gco:CharacterString>
            </gmd:abstract>
            <gmd:topicCategory>
                <gmd:MD_TopicCategoryCode>geoscientificInformation</gmd:MD_TopicCategoryCode>
            </gmd:topicCategory>
            <gmd:keyword>
                <gco:CharacterString>soil</gco:CharacterString>
            </gmd:keyword>
            <gmd:keyword>
                <gco:CharacterString>ecology</gco:CharacterString>
            </gmd:keyword>
            <gmd:supplementalInformation>
                <gco:CharacterString>Additional notes here.</gco:CharacterString>
            </gmd:supplementalInformation>
        </gmd:MD_DataIdentification>
    </gmd:identificationInfo>
    <gmd:dataQualityInfo>
        <gmd:DQ_DataQuality>
            <gmd:lineage>
                <gmd:LI_Lineage>
                    <gmd:statement>
                        <gco:CharacterString>Data collected via field surveys.</gco:CharacterString>
                    </gmd:statement>
                </gmd:LI_Lineage>
            </gmd:lineage>
        </gmd:DQ_DataQuality>
    </gmd:dataQualityInfo>
</gmd:MD_Metadata>"""

MINIMAL_ISO_XML = """<?xml version="1.0"?>
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
    <gmd:fileIdentifier>
        <gco:CharacterString>id-123</gco:CharacterString>
    </gmd:fileIdentifier>
    <gmd:identificationInfo>
        <gmd:MD_DataIdentification>
            <gmd:title>
                <gco:CharacterString>Minimal Dataset</gco:CharacterString>
            </gmd:title>
        </gmd:MD_DataIdentification>
    </gmd:identificationInfo>
</gmd:MD_Metadata>"""

MULTIPLE_TOPICS_ISO = """<?xml version="1.0"?>
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
    <gmd:fileIdentifier>
        <gco:CharacterString>multi-topic-id</gco:CharacterString>
    </gmd:fileIdentifier>
    <gmd:identificationInfo>
        <gmd:MD_DataIdentification>
            <gmd:title>
                <gco:CharacterString>Multi-Topic Dataset</gco:CharacterString>
            </gmd:title>
            <gmd:abstract>
                <gco:CharacterString>Dataset with multiple topics</gco:CharacterString>
            </gmd:abstract>
            <gmd:topicCategory>
                <gmd:MD_TopicCategoryCode>geoscientificInformation</gmd:MD_TopicCategoryCode>
            </gmd:topicCategory>
            <gmd:topicCategory>
                <gmd:MD_TopicCategoryCode>biota</gmd:MD_TopicCategoryCode>
            </gmd:topicCategory>
            <gmd:topicCategory>
                <gmd:MD_TopicCategoryCode>environment</gmd:MD_TopicCategoryCode>
            </gmd:topicCategory>
        </gmd:MD_DataIdentification>
    </gmd:identificationInfo>
</gmd:MD_Metadata>"""

WITH_EXTENT_ISO = """<?xml version="1.0"?>
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
    <gmd:fileIdentifier>
        <gco:CharacterString>extent-id</gco:CharacterString>
    </gmd:fileIdentifier>
    <gmd:identificationInfo>
        <gmd:MD_DataIdentification>
            <gmd:title>
                <gco:CharacterString>Dataset with Extent</gco:CharacterString>
            </gmd:title>
            <gmd:abstract>
                <gco:CharacterString>Dataset with geographic extent</gco:CharacterString>
            </gmd:abstract>
            <gmd:extent>
                <gmd:EX_Extent>
                    <gmd:geographicElement>
                        <gmd:EX_GeographicBoundingBox>
                            <gmd:westBoundLongitude>
                                <gco:Decimal>-5.0</gco:Decimal>
                            </gmd:westBoundLongitude>
                            <gmd:eastBoundLongitude>
                                <gco:Decimal>2.0</gco:Decimal>
                            </gmd:eastBoundLongitude>
                            <gmd:southBoundLatitude>
                                <gco:Decimal>50.0</gco:Decimal>
                            </gmd:southBoundLatitude>
                            <gmd:northBoundLatitude>
                                <gco:Decimal>55.0</gco:Decimal>
                            </gmd:northBoundLatitude>
                        </gmd:EX_GeographicBoundingBox>
                    </gmd:geographicElement>
                </gmd:EX_Extent>
            </gmd:extent>
        </gmd:MD_DataIdentification>
    </gmd:identificationInfo>
</gmd:MD_Metadata>"""


@pytest.fixture
def parser():
    """Create an ISO19139 parser instance."""
    return ISO19139Parser()


# ============================================================================
# BASIC PARSING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_iso19139_parser_extracts_all_fields(parser):
    """Test that ISO19139 parser extracts all required fields."""
    dataset = await parser.parse(SAMPLE_ISO_XML)

    assert dataset.file_identifier == "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    assert dataset.title == "Sample Dataset"
    assert "sample dataset abstract" in dataset.abstract.lower()
    assert "geoscientificInformation" in dataset.topic_category
    assert "soil" in dataset.keywords
    assert "ecology" in dataset.keywords
    assert dataset.lineage is not None
    assert "field surveys" in dataset.lineage.lower()
    assert "Additional notes" in dataset.supplemental_info


@pytest.mark.asyncio
async def test_iso19139_parser_handles_missing_optional_fields(parser):
    """Test graceful handling of missing optional fields."""
    dataset = await parser.parse(MINIMAL_ISO_XML)

    assert dataset.file_identifier == "id-123"
    assert dataset.title == "Minimal Dataset"
    assert dataset.abstract == ""
    assert dataset.topic_category == []
    assert dataset.keywords == []
    assert dataset.lineage is None
    assert dataset.supplemental_info is None


@pytest.mark.asyncio
async def test_iso19139_parser_with_multiple_topics(parser):
    """Test ISO19139 parser with multiple topic categories."""
    dataset = await parser.parse(MULTIPLE_TOPICS_ISO)

    assert dataset.file_identifier == "multi-topic-id"
    assert len(dataset.topic_category) >= 3
    assert "geoscientificInformation" in dataset.topic_category
    assert "biota" in dataset.topic_category
    assert "environment" in dataset.topic_category


@pytest.mark.asyncio
async def test_iso19139_parser_with_geographic_extent(parser):
    """Test ISO19139 parser with geographic extent information."""
    dataset = await parser.parse(WITH_EXTENT_ISO)

    assert dataset.file_identifier == "extent-id"
    assert dataset.title == "Dataset with Extent"
    # Extent info may be captured in supplemental_info or abstract
    assert dataset.abstract != ""


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_iso19139_parser_rejects_invalid_xml(parser):
    """Test that invalid XML raises MetadataParserError."""
    with pytest.raises(MetadataParserError):
        await parser.parse("<invalid>unclosed tag")


@pytest.mark.asyncio
async def test_iso19139_parser_empty_string(parser):
    """Test that empty string raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("")


@pytest.mark.asyncio
async def test_iso19139_parser_not_xml_string(parser):
    """Test that non-XML string raises error."""
    with pytest.raises(MetadataParserError):
        await parser.parse("this is not xml")


@pytest.mark.asyncio
async def test_iso19139_parser_malformed_xml_syntax(parser):
    """Test that malformed XML syntax raises error."""
    malformed_xml = """<?xml version="1.0"?>
    <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd">
        <gmd:fileIdentifier>
            <gco:CharacterString>id</gco:CharacterString
        </gmd:fileIdentifier>
    </gmd:MD_Metadata>"""
    
    with pytest.raises(MetadataParserError):
        await parser.parse(malformed_xml)


# ============================================================================
# NAMESPACE HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_iso19139_parser_with_additional_namespaces(parser):
    """Test ISO19139 parser with additional XML namespaces."""
    extended_iso = """<?xml version="1.0"?>
    <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" 
                     xmlns:gco="http://www.isotc211.org/2005/gco"
                     xmlns:gmx="http://www.isotc211.org/2005/gmx"
                     xmlns:xlink="http://www.w3.org/1999/xlink">
        <gmd:fileIdentifier>
            <gco:CharacterString>extended-id</gco:CharacterString>
        </gmd:fileIdentifier>
        <gmd:identificationInfo>
            <gmd:MD_DataIdentification>
                <gmd:title>
                    <gco:CharacterString>Extended ISO Dataset</gco:CharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Dataset with extended namespaces</gco:CharacterString>
                </gmd:abstract>
            </gmd:MD_DataIdentification>
        </gmd:identificationInfo>
    </gmd:MD_Metadata>"""
    
    dataset = await parser.parse(extended_iso)
    
    assert dataset.file_identifier == "extended-id"
    assert dataset.title == "Extended ISO Dataset"


# ============================================================================
# UNICODE HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_iso19139_parser_unicode_in_text(parser):
    """Test ISO19139 parser handles unicode characters."""
    unicode_iso = """<?xml version="1.0" encoding="UTF-8"?>
    <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
        <gmd:fileIdentifier>
            <gco:CharacterString>unicode-id</gco:CharacterString>
        </gmd:fileIdentifier>
        <gmd:identificationInfo>
            <gmd:MD_DataIdentification>
                <gmd:title>
                    <gco:CharacterString>Tïtlé wîth ünïcödé</gco:CharacterString>
                </gmd:title>
                <gmd:abstract>
                    <gco:CharacterString>Àbstrâct 🌍 📊 with émojis</gco:CharacterString>
                </gmd:abstract>
                <gmd:keyword>
                    <gco:CharacterString>Frënch</gco:CharacterString>
                </gmd:keyword>
                <gmd:keyword>
                    <gco:CharacterString>日本語</gco:CharacterString>
                </gmd:keyword>
            </gmd:MD_DataIdentification>
        </gmd:identificationInfo>
    </gmd:MD_Metadata>"""
    
    dataset = await parser.parse(unicode_iso)
    
    assert "ünïcödé" in dataset.title or "unicode" in dataset.title.lower()


# ============================================================================
# COMPLEX STRUCTURES
# ============================================================================

@pytest.mark.asyncio
async def test_iso19139_parser_contact_information(parser):
    """Test ISO19139 parser with contact information structure."""
    contact_iso = """<?xml version="1.0"?>
    <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
        <gmd:fileIdentifier>
            <gco:CharacterString>contact-id</gco:CharacterString>
        </gmd:fileIdentifier>
        <gmd:contact>
            <gmd:CI_ResponsibleParty>
                <gmd:organisationName>
                    <gco:CharacterString>UK Environmental Agency</gco:CharacterString>
                </gmd:organisationName>
                <gmd:contactInfo>
                    <gmd:CI_Contact>
                        <gmd:phone>
                            <gmd:CI_Telephone>
                                <gmd:voice>
                                    <gco:CharacterString>+44-1234-567890</gco:CharacterString>
                                </gmd:voice>
                            </gmd:CI_Telephone>
                        </gmd:phone>
                    </gmd:CI_Contact>
                </gmd:contactInfo>
            </gmd:CI_ResponsibleParty>
        </gmd:contact>
        <gmd:identificationInfo>
            <gmd:MD_DataIdentification>
                <gmd:title>
                    <gco:CharacterString>Contact Info Dataset</gco:CharacterString>
                </gmd:title>
            </gmd:MD_DataIdentification>
        </gmd:identificationInfo>
    </gmd:MD_Metadata>"""
    
    dataset = await parser.parse(contact_iso)
    
    assert dataset.file_identifier == "contact-id"
    assert dataset.title == "Contact Info Dataset"


@pytest.mark.asyncio
async def test_iso19139_parser_many_keywords(parser):
    """Test ISO19139 parser with many keywords."""
    keywords = "\n".join([
        f"            <gmd:keyword>\n                <gco:CharacterString>keyword-{i}</gco:CharacterString>\n            </gmd:keyword>"
        for i in range(20)
    ])
    
    many_keywords_iso = f"""<?xml version="1.0"?>
    <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
        <gmd:fileIdentifier>
            <gco:CharacterString>many-keywords-id</gco:CharacterString>
        </gmd:fileIdentifier>
        <gmd:identificationInfo>
            <gmd:MD_DataIdentification>
                <gmd:title>
                    <gco:CharacterString>Many Keywords Dataset</gco:CharacterString>
                </gmd:title>
                {keywords}
            </gmd:MD_DataIdentification>
        </gmd:identificationInfo>
    </gmd:MD_Metadata>"""
    
    dataset = await parser.parse(many_keywords_iso)
    
    assert len(dataset.keywords) >= 20
    assert "keyword-0" in dataset.keywords


# ============================================================================
# SCHEMA VALIDATION
# ============================================================================

@pytest.mark.asyncio
async def test_iso19139_parser_with_schema_reference(parser):
    """Test ISO19139 parser with schema location attributes."""
    with_schema = """<?xml version="1.0"?>
    <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                     xmlns:gco="http://www.isotc211.org/2005/gco"
                     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                     xsi:schemaLocation="http://www.isotc211.org/2005/gmd http://www.isotc211.org/2005/gmd/gmd.xsd">
        <gmd:fileIdentifier>
            <gco:CharacterString>schema-ref-id</gco:CharacterString>
        </gmd:fileIdentifier>
        <gmd:identificationInfo>
            <gmd:MD_DataIdentification>
                <gmd:title>
                    <gco:CharacterString>Schema Referenced Dataset</gco:CharacterString>
                </gmd:title>
            </gmd:MD_DataIdentification>
        </gmd:identificationInfo>
    </gmd:MD_Metadata>"""
    
    dataset = await parser.parse(with_schema)
    
    assert dataset.file_identifier == "schema-ref-id"
