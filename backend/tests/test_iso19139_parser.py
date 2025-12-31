import pytest

from src.services.iso19139_parser import ISO19139Parser, MetadataParserError


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


@pytest.mark.asyncio
async def test_iso19139_parser_extracts_all_fields():
    """Test that ISO19139 parser extracts all required fields."""
    parser = ISO19139Parser()
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
async def test_iso19139_parser_handles_missing_optional_fields():
    """Test graceful handling of missing optional fields."""
    minimal_xml = """<?xml version="1.0"?>
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

    parser = ISO19139Parser()
    dataset = await parser.parse(minimal_xml)

    assert dataset.file_identifier == "id-123"
    assert dataset.title == "Minimal Dataset"
    assert dataset.abstract == ""
    assert dataset.topic_category == []
    assert dataset.keywords == []
    assert dataset.lineage is None
    assert dataset.supplemental_info is None


@pytest.mark.asyncio
async def test_iso19139_parser_rejects_invalid_xml():
    """Test that invalid XML raises MetadataParserError."""
    parser = ISO19139Parser()
    with pytest.raises(MetadataParserError):
        await parser.parse("<invalid>unclosed tag")