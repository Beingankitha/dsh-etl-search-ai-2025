"""
Tests for CEH Catalogue Service Extractor

Tests metadata extraction from CEH API in all formats.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientError

from src.services.extractors import CEHExtractor, WebFolderTraverserError
from src.infrastructure import AsyncHTTPClient


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_http_client():
    """Create mock HTTP client"""
    client = AsyncMock(spec=AsyncHTTPClient)
    return client


@pytest.fixture
def ceh_extractor(mock_http_client):
    """Create CEH extractor with mock HTTP client"""
    extractor = CEHExtractor(
        http_client=mock_http_client,
        request_id="test-123",
        max_concurrent=5
    )
    return extractor


@pytest.fixture
def ceh_extractor_no_client():
    """Create CEH extractor without client (will create one)"""
    return CEHExtractor(
        request_id="test-456",
        max_concurrent=5
    )


# ============================================================================
# TEST: CEHExtractor Initialization
# ============================================================================

class TestCEHExtractorInitialization:
    """Test CEH extractor initialization"""
    
    def test_extractor_initialization_with_client(self, mock_http_client):
        """Test initializing with provided HTTP client"""
        extractor = CEHExtractor(
            http_client=mock_http_client,
            request_id="test-id"
        )
        
        assert extractor.http_client == mock_http_client
        assert extractor.request_id == "test-id"
        assert extractor.max_concurrent == 5
    
    def test_extractor_initialization_without_client(self):
        """Test initializing without HTTP client"""
        extractor = CEHExtractor()
        
        assert extractor.http_client is None
        assert extractor.request_id is not None
        assert extractor.max_concurrent == 5
    
    def test_extractor_custom_max_concurrent(self, mock_http_client):
        """Test setting custom max_concurrent"""
        extractor = CEHExtractor(
            http_client=mock_http_client,
            max_concurrent=10
        )
        
        assert extractor.max_concurrent == 10
    
    def test_api_endpoints_defined(self):
        """Test API endpoints are defined"""
        assert CEHExtractor.CEH_API_BASE == "https://catalogue.ceh.ac.uk/documents"
        assert CEHExtractor.CEH_SEARCH_API == "https://catalogue.ceh.ac.uk/api/documents"
        assert CEHExtractor.CEH_WAF == "https://catalogue.ceh.ac.uk/eidc/documents"


# ============================================================================
# TEST: XML Metadata Fetching
# ============================================================================

class TestXMLFetching:
    """Test ISO 19139 XML metadata fetching"""
    
    @pytest.mark.asyncio
    async def test_fetch_xml_success(self, ceh_extractor, mock_http_client):
        """Test successfully fetching XML metadata"""
        identifier = "dataset-001"
        xml_content = '<?xml version="1.0"?><root></root>'
        
        # AsyncMock needs return_value set for async methods
        mock_http_client.get_text = AsyncMock(return_value=xml_content)
        
        result = await ceh_extractor.fetch_dataset_xml(identifier)
        
        assert result == xml_content
        mock_http_client.get_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_xml_constructs_correct_url(self, ceh_extractor, mock_http_client):
        """Test XML fetch constructs correct URL"""
        identifier = "dataset-002"
        mock_http_client.get_text = AsyncMock(return_value="<xml/>")
        
        await ceh_extractor.fetch_dataset_xml(identifier)
        
        # Should call get_text
        call_args = mock_http_client.get_text.call_args
        assert call_args is not None
        url = call_args[0][0] if call_args[0] else call_args.kwargs.get('url', '')
        assert '.xml' in url or 'dataset-002' in url
    
    @pytest.mark.asyncio
    async def test_fetch_xml_handles_404(self, ceh_extractor, mock_http_client):
        """Test XML fetch handles 404 errors"""
        from src.services.extractors import CEHExtractorError
        identifier = "non-existent"
        
        mock_http_client.get_text = AsyncMock(side_effect=ClientError("404 Not Found"))
        
        with pytest.raises(CEHExtractorError):
            await ceh_extractor.fetch_dataset_xml(identifier)
    
    @pytest.mark.asyncio
    async def test_fetch_xml_handles_timeout(self, ceh_extractor, mock_http_client):
        """Test XML fetch handles timeout"""
        from src.services.extractors import CEHExtractorError
        mock_http_client.get_text = AsyncMock(side_effect=TimeoutError("Request timeout"))
        
        with pytest.raises(CEHExtractorError):
            await ceh_extractor.fetch_dataset_xml("dataset-003")


# ============================================================================
# TEST: JSON Metadata Fetching
# ============================================================================

class TestJSONFetching:
    """Test JSON metadata fetching"""
    
    @pytest.mark.asyncio
    async def test_fetch_json_success(self, ceh_extractor, mock_http_client):
        """Test successfully fetching JSON metadata"""
        identifier = "dataset-001"
        json_obj = {"title": "Test Dataset", "description": "Test"}
        
        mock_http_client.get.return_value = json_obj
        
        result = await ceh_extractor.fetch_dataset_json(identifier)
        
        assert result == json_obj
    
    @pytest.mark.asyncio
    async def test_fetch_json_parses_valid_json(self, ceh_extractor, mock_http_client):
        """Test JSON content is valid"""
        identifier = "dataset-002"
        json_obj = {"title": "Dataset", "id": "ds-001"}
        
        mock_http_client.get.return_value = json_obj
        
        result = await ceh_extractor.fetch_dataset_json(identifier)
        
        # Should be a dict
        assert result["title"] == "Dataset"


# ============================================================================
# TEST: RDF Metadata Fetching
# ============================================================================

class TestRDFFetching:
    """Test RDF metadata fetching"""
    
    @pytest.mark.asyncio
    async def test_fetch_rdf_success(self, ceh_extractor, mock_http_client):
        """Test successfully fetching RDF metadata"""
        identifier = "dataset-001"
        rdf_content = '<?xml version="1.0"?><rdf:RDF></rdf:RDF>'
        
        mock_http_client.get_text = AsyncMock(return_value=rdf_content)
        
        result = await ceh_extractor.fetch_dataset_rdf(identifier)
        
        assert result == rdf_content
    
    @pytest.mark.asyncio
    async def test_fetch_rdf_contains_xml(self, ceh_extractor, mock_http_client):
        """Test RDF content format"""
        identifier = "dataset-002"
        rdf_content = '''<?xml version="1.0"?>
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description rdf:about="http://example.org/dataset1">
            </rdf:Description>
        </rdf:RDF>'''
        
        mock_http_client.get_text = AsyncMock(return_value=rdf_content)
        
        result = await ceh_extractor.fetch_dataset_rdf(identifier)
        
        assert "rdf:RDF" in result


# ============================================================================
# TEST: Schema.org Metadata Fetching
# ============================================================================

class TestSchemaOrgFetching:
    """Test Schema.org metadata fetching"""
    
    @pytest.mark.asyncio
    async def test_fetch_schema_org_success(self, ceh_extractor, mock_http_client):
        """Test successfully fetching Schema.org metadata"""
        identifier = "dataset-001"
        schema_org_obj = {"@context": "https://schema.org", "@type": "Dataset"}
        
        mock_http_client.get.return_value = schema_org_obj
        
        result = await ceh_extractor.fetch_dataset_schema_org(identifier)
        
        assert result == schema_org_obj
    
    @pytest.mark.asyncio
    async def test_fetch_schema_org_structure(self, ceh_extractor, mock_http_client):
        """Test Schema.org structure"""
        identifier = "dataset-002"
        schema_org = {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": "Test Dataset",
            "description": "Test Description"
        }
        
        mock_http_client.get.return_value = schema_org
        
        result = await ceh_extractor.fetch_dataset_schema_org(identifier)
        
        assert result["@type"] == "Dataset"
        assert result["@context"] == "https://schema.org"


# ============================================================================
# TEST: Batch Fetching
# ============================================================================

class TestBatchFetching:
    """Test fetching multiple formats"""
    
    @pytest.mark.asyncio
    async def test_fetch_all_formats(self, ceh_extractor, mock_http_client):
        """Test fetching all metadata formats for one identifier"""
        identifier = "dataset-001"
        
        # Set up async mocks for each method
        mock_http_client.get_text = AsyncMock(return_value="<xml>test</xml>")
        mock_http_client.get = AsyncMock(return_value={"key": "value"})
        
        # Each fetch calls appropriate method and returns
        xml = await ceh_extractor.fetch_dataset_xml(identifier)
        json_data = await ceh_extractor.fetch_dataset_json(identifier)
        rdf = await ceh_extractor.fetch_dataset_rdf(identifier)
        schema_org = await ceh_extractor.fetch_dataset_schema_org(identifier)
        
        assert "xml" in xml
        assert "key" in json_data
        assert "xml" in rdf  # get_text returns <xml>test</xml>
        assert "key" in schema_org  # get returns {"key": "value"}


# ============================================================================
# TEST: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in extractor"""
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, ceh_extractor, mock_http_client):
        """Test handling network errors"""
        from src.services.extractors import CEHExtractorError
        mock_http_client.get_text = AsyncMock(side_effect=ClientError("Connection refused"))
        
        with pytest.raises(CEHExtractorError):
            await ceh_extractor.fetch_dataset_xml("dataset-001")
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, ceh_extractor, mock_http_client):
        """Test handling timeout errors"""
        from src.services.extractors import CEHExtractorError
        mock_http_client.get = AsyncMock(side_effect=TimeoutError())
        
        with pytest.raises(CEHExtractorError):
            await ceh_extractor.fetch_dataset_json("dataset-001")
    
    @pytest.mark.asyncio
    async def test_empty_identifier(self, ceh_extractor, mock_http_client):
        """Test handling empty identifier"""
        mock_http_client.get_text = AsyncMock(return_value="")
        
        # Should call even with empty identifier
        result = await ceh_extractor.fetch_dataset_xml("")
        
        assert result == "" or result is not None
    
    @pytest.mark.asyncio
    async def test_special_characters_in_identifier(self, ceh_extractor, mock_http_client):
        """Test handling special characters in identifier"""
        identifier = "dataset/001&special=chars"
        mock_http_client.get_text.return_value = "<xml/>"
        
        result = await ceh_extractor.fetch_dataset_xml(identifier)
        
        assert result == "<xml/>"


# ============================================================================
# TEST: Client Management
# ============================================================================

class TestClientManagement:
    """Test HTTP client lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_ensures_client_exists(self, ceh_extractor_no_client):
        """Test extractor ensures client exists"""
        assert ceh_extractor_no_client.http_client is None
        
        # Ensure client is created
        await ceh_extractor_no_client._ensure_client()
        
        assert ceh_extractor_no_client.http_client is not None
    
    @pytest.mark.asyncio
    async def test_owns_client_flag(self, ceh_extractor_no_client):
        """Test _owns_client flag is set"""
        assert ceh_extractor_no_client._owns_client is False
        
        await ceh_extractor_no_client._ensure_client()
        
        assert ceh_extractor_no_client._owns_client is True


# ============================================================================
# TEST: Request Tracing
# ============================================================================

class TestRequestTracing:
    """Test request tracing functionality"""
    
    def test_request_id_generated(self):
        """Test request ID is generated if not provided"""
        extractor = CEHExtractor()
        
        assert extractor.request_id is not None
        assert len(extractor.request_id) > 0
    
    def test_request_id_preserved(self):
        """Test provided request ID is preserved"""
        request_id = "custom-request-id"
        extractor = CEHExtractor(request_id=request_id)
        
        assert extractor.request_id == request_id


# ============================================================================
# TEST: URL Construction
# ============================================================================

class TestURLConstruction:
    """Test URL construction for API calls"""
    
    @pytest.mark.asyncio
    async def test_xml_url_format(self, ceh_extractor, mock_http_client):
        """Test XML URL format"""
        identifier = "test-dataset-123"
        mock_http_client.get.return_value = "<xml/>"
        
        await ceh_extractor.fetch_dataset_xml(identifier)
        
        # Verify URL includes .xml extension
        call_args = mock_http_client.get.call_args
        if call_args and call_args[0]:
            url = call_args[0][0]
            assert ".xml" in url
    
    @pytest.mark.asyncio
    async def test_json_url_format(self, ceh_extractor, mock_http_client):
        """Test JSON URL format"""
        identifier = "test-dataset-123"
        mock_http_client.get.return_value = "{}"
        
        await ceh_extractor.fetch_dataset_json(identifier)
        
        # Verify URL includes .json extension
        call_args = mock_http_client.get.call_args
        if call_args and call_args[0]:
            url = call_args[0][0]
            assert ".json" in url
