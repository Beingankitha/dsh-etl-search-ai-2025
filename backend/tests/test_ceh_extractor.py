import pytest
from aioresponses import aioresponses

from src.infrastructure.http_client import AsyncHTTPClient
from src.services.ceh_extractor import CEHExtractor, CEHExtractorError


@pytest.mark.asyncio
async def test_fetch_dataset_xml():
    """Test fetching dataset XML by identifier."""
    file_id = "be0bdc0e-bc2e-4f1d-b524-2c02798dd893"
    xml_content = """<?xml version="1.0"?>
    <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd">
        <gmd:fileIdentifier>
            <gco:CharacterString>be0bdc0e-bc2e-4f1d-b524-2c02798dd893</gco:CharacterString>
        </gmd:fileIdentifier>
    </gmd:MD_Metadata>"""

    with aioresponses() as mocked:
        url = f"https://catalogue.ceh.ac.uk/documents/{file_id}.xml"
        mocked.get(url, body=xml_content)

        async with AsyncHTTPClient() as client:
            extractor = CEHExtractor(client)
            result = await extractor.fetch_dataset_xml(file_id)
            assert file_id in result


@pytest.mark.asyncio
async def test_fetch_dataset_list():
    """Test fetching dataset list."""
    with aioresponses() as mocked:
        url = "https://catalogue.ceh.ac.uk/api/documents?limit=100&offset=0"
        mocked.get(
            url,
            payload={
                "documents": [
                    {"fileIdentifier": "id-1"},
                    {"fileIdentifier": "id-2"},
                ]
            },
        )

        async with AsyncHTTPClient() as client:
            extractor = CEHExtractor(client)
            result = await extractor.fetch_dataset_list()
            assert len(result) == 2
            assert "id-1" in result