"""
Comprehensive tests for ETL Service.

Tests the complete ETL pipeline end-to-end.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.etl.etl_service import ETLService
from src.repositories import UnitOfWork
from src.models import DatasetEntity, MetadataDocument


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_identifiers_file():
    """Create temporary identifiers file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("# Test dataset identifiers\n")
        f.write("test-id-001\n")
        f.write("\n")
        f.write("test-id-002\n")
        f.write("# Another comment\n")
        f.write("test-id-003\n")
        temp_path = f.name
    
    yield Path(temp_path)
    
    import os
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_unit_of_work():
    """Mock UnitOfWork"""
    mock_uow = MagicMock(spec=UnitOfWork)
    mock_uow.datasets = MagicMock()
    mock_uow.metadata_documents = MagicMock()
    mock_uow.supporting_documents = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=None)
    mock_uow.commit = MagicMock()
    return mock_uow


@pytest.fixture
def etl_service_with_mocks(temp_identifiers_file, mock_unit_of_work):
    """ETL Service with all external dependencies mocked"""
    service = ETLService(
        identifiers_file=temp_identifiers_file,
        unit_of_work=mock_unit_of_work,
        batch_size=2,
        max_concurrent_downloads=3,
        dry_run=False,
        enable_supporting_docs=False
    )
    
    # Mock extractors and parsers
    service.ceh_extractor = AsyncMock()
    
    # Mock the cached fetcher that wraps the extractor
    service.cached_fetcher = MagicMock()
    service.cached_fetcher.fetch_xml = AsyncMock(return_value="<xml>...</xml>")
    service.cached_fetcher.fetch_json = AsyncMock(return_value='{"key": "value"}')
    service.cached_fetcher.fetch_rdf = AsyncMock(return_value="<rdf>...</rdf>")
    service.cached_fetcher.fetch_schema_org = AsyncMock(return_value=None)
    service.cached_fetcher.clear_fetch_cache_status = MagicMock()
    service.cached_fetcher.fetch_cache_status = {}
    
    # Create regular mocks for parsers with async parse methods
    service.iso_parser = MagicMock()
    service.iso_parser.parse = AsyncMock()
    service.json_parser = MagicMock()
    service.json_parser.parse = AsyncMock()
    service.rdf_parser = MagicMock()
    service.rdf_parser.parse = AsyncMock()
    service.schema_org_parser = MagicMock()
    service.schema_org_parser.parse = AsyncMock()
    
    return service


# ============================================================================
# TEST: ETL Service Initialization
# ============================================================================

class TestETLServiceInitialization:
    """Test ETL Service initialization"""
    
    def test_service_initialization(self, temp_identifiers_file, mock_unit_of_work):
        """Test service initializes with correct parameters"""
        service = ETLService(
            identifiers_file=temp_identifiers_file,
            unit_of_work=mock_unit_of_work,
            batch_size=10,
            max_concurrent_downloads=5,
            dry_run=True,
            enable_supporting_docs=False
        )
        
        assert service.batch_size == 10
        assert service.max_concurrent_downloads == 5
        assert service.dry_run is True
        assert service.enable_supporting_docs is False
        assert service.identifiers_file == temp_identifiers_file
    
    def test_service_creates_report_structure(self, temp_identifiers_file, mock_unit_of_work):
        """Test service initializes report structure"""
        service = ETLService(
            identifiers_file=temp_identifiers_file,
            unit_of_work=mock_unit_of_work
        )
        
        assert 'total_identifiers' in service.report
        assert 'successful' in service.report
        assert 'failed' in service.report
        assert service.report['total_identifiers'] == 0
        assert service.report['successful'] == 0


# ============================================================================
# TEST: Identifier Reading
# ============================================================================

class TestIdentifierReading:
    """Test identifier file reading"""
    
    def test_read_all_identifiers(self, etl_service_with_mocks):
        """Test reading all identifiers"""
        identifiers = etl_service_with_mocks._read_identifiers()
        
        assert len(identifiers) == 3
        assert 'test-id-001' in identifiers
        assert 'test-id-002' in identifiers
        assert 'test-id-003' in identifiers
    
    def test_read_identifiers_with_limit(self, etl_service_with_mocks):
        """Test reading with limit"""
        identifiers = etl_service_with_mocks._read_identifiers(limit=2)
        
        assert len(identifiers) == 2
    
    def test_read_identifiers_skips_comments(self, etl_service_with_mocks):
        """Test that comments are skipped"""
        identifiers = etl_service_with_mocks._read_identifiers()
        
        assert not any('#' in id for id in identifiers)
    
    def test_read_identifiers_skips_empty_lines(self, etl_service_with_mocks):
        """Test that empty lines are skipped"""
        identifiers = etl_service_with_mocks._read_identifiers()
        
        assert all(id.strip() for id in identifiers)


# ============================================================================
# TEST: Extract Phase
# ============================================================================

class TestExtractPhase:
    """Test metadata extraction phase"""
    
    @pytest.mark.asyncio
    async def test_extract_phase_all_success(self, etl_service_with_mocks):
        """Test successful extraction for all identifiers"""
        identifiers = ['id-001', 'id-002']
        
        # Mock successful extractions using cached fetcher
        etl_service_with_mocks.cached_fetcher.fetch_xml = AsyncMock(return_value='<xml/>')
        etl_service_with_mocks.cached_fetcher.fetch_json = AsyncMock(return_value='{}')
        etl_service_with_mocks.cached_fetcher.fetch_rdf = AsyncMock(return_value='<rdf/>')
        etl_service_with_mocks.cached_fetcher.fetch_schema_org = AsyncMock(return_value='{}')
        
        result = await etl_service_with_mocks._extract_phase(identifiers)
        
        assert len(result) == 2
        assert 'id-001' in result
        assert 'id-002' in result
        assert result['id-001']['xml'] == '<xml/>'
    
    @pytest.mark.asyncio
    async def test_fetch_metadata_for_single_identifier(self, etl_service_with_mocks):
        """Test fetching metadata for single identifier"""
        identifier = 'test-id'
        
        etl_service_with_mocks.cached_fetcher.fetch_xml = AsyncMock(return_value='<xml/>')
        etl_service_with_mocks.cached_fetcher.fetch_json = AsyncMock(return_value='{}')
        etl_service_with_mocks.cached_fetcher.fetch_rdf = AsyncMock(return_value='<rdf/>')
        etl_service_with_mocks.cached_fetcher.fetch_schema_org = AsyncMock(return_value='{}')
        
        result = await etl_service_with_mocks._fetch_metadata_for_identifier(identifier)
        
        assert result['identifier'] == identifier
        assert result['xml'] is not None
        assert result['json'] is not None


# ============================================================================
# TEST: Parse Metadata with Fallback
# ============================================================================

class TestParseMetadataWithFallback:
    """Test metadata parsing with fallback strategy"""
    
    @pytest.mark.asyncio
    async def test_parse_xml_first(self, etl_service_with_mocks):
        """Test XML is tried first"""
        metadata = {
            'xml': '<xml>data</xml>',
            'json': '{}',
            'rdf': '<rdf/>',
            'schema_org': '{}'
        }
        
        mock_dataset = MagicMock(spec=DatasetEntity)
        etl_service_with_mocks.iso_parser.parse = AsyncMock(return_value=mock_dataset)
        
        result = await etl_service_with_mocks._parse_metadata_with_fallback('id-001', metadata)
        
        assert result is not None
        etl_service_with_mocks.iso_parser.parse.assert_called_once()
        etl_service_with_mocks.json_parser.parse.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fallback_to_json_when_xml_fails(self, etl_service_with_mocks):
        """Test fallback to JSON when XML parsing fails"""
        metadata = {
            'xml': '<invalid>',
            'json': '{"valid": "json"}',
            'rdf': None,
            'schema_org': None
        }
        
        # XML fails
        etl_service_with_mocks.iso_parser.parse = AsyncMock(side_effect=Exception("Parse error"))
        
        # JSON succeeds
        mock_dataset = MagicMock(spec=DatasetEntity)
        etl_service_with_mocks.json_parser.parse = AsyncMock(return_value=mock_dataset)
        
        result = await etl_service_with_mocks._parse_metadata_with_fallback('id-001', metadata)
        
        assert result is not None
        etl_service_with_mocks.iso_parser.parse.assert_called_once()
        etl_service_with_mocks.json_parser.parse.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_returns_none_when_all_formats_fail(self, etl_service_with_mocks):
        """Test returns None when all parsers fail"""
        metadata = {
            'xml': '<invalid>',
            'json': '{invalid}',
            'rdf': '<invalid>',
            'schema_org': '{invalid}'
        }
        
        # All parsers fail
        etl_service_with_mocks.iso_parser.parse.side_effect = Exception("Error")
        etl_service_with_mocks.json_parser.parse.side_effect = Exception("Error")
        etl_service_with_mocks.rdf_parser.parse.side_effect = Exception("Error")
        etl_service_with_mocks.schema_org_parser.parse.side_effect = Exception("Error")
        
        result = await etl_service_with_mocks._parse_metadata_with_fallback('id-001', metadata)
        
        assert result is None


# ============================================================================
# TEST: Load to Database
# ============================================================================

class TestLoadToDatabase:
    """Test loading data to database"""
    
    @pytest.mark.asyncio
    async def test_load_dataset_to_database(self, etl_service_with_mocks, mock_unit_of_work):
        """Test dataset loading"""
        dataset = MagicMock(spec=DatasetEntity)
        dataset.file_identifier = 'id-001'
        dataset.id = 1
        
        metadata = {
            'xml': '<xml>data</xml>',
            'json': '{"data": "json"}'
        }
        
        # Setup mock for upsert_by_identifier
        etl_service_with_mocks.unit_of_work.datasets.upsert_by_identifier = MagicMock(return_value=dataset)
        etl_service_with_mocks.unit_of_work.metadata_documents.get_by_dataset_and_type = MagicMock(return_value=None)
        etl_service_with_mocks.unit_of_work.metadata_documents.insert = MagicMock()
        etl_service_with_mocks.unit_of_work.commit = MagicMock()
        
        await etl_service_with_mocks._load_dataset_to_database('id-001', dataset, metadata)
        
        etl_service_with_mocks.unit_of_work.datasets.upsert_by_identifier.assert_called_once()
        etl_service_with_mocks.unit_of_work.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dry_run_skips_database_write(self, etl_service_with_mocks):
        """Test dry-run mode skips database writes"""
        etl_service_with_mocks.dry_run = True
        
        dataset = MagicMock(spec=DatasetEntity)
        metadata = {'xml': '<xml/>'}
        
        await etl_service_with_mocks._load_dataset_to_database('id-001', dataset, metadata)
        
        etl_service_with_mocks.unit_of_work.datasets.upsert.assert_not_called()


# ============================================================================
# TEST: Full Pipeline
# ============================================================================

class TestFullPipeline:
    """Test complete ETL pipeline"""
    
    @pytest.mark.asyncio
    async def test_run_pipeline_success(self, etl_service_with_mocks):
        """Test successful pipeline run"""
        # Mock all components
        etl_service_with_mocks.ceh_extractor.fetch_dataset_xml = AsyncMock(return_value='<xml/>')
        etl_service_with_mocks.ceh_extractor.fetch_dataset_json = AsyncMock(return_value='{}')
        etl_service_with_mocks.ceh_extractor.fetch_dataset_rdf = AsyncMock(return_value=None)
        etl_service_with_mocks.ceh_extractor.fetch_dataset_schema_org = AsyncMock(return_value=None)
        
        mock_dataset = MagicMock(spec=DatasetEntity)
        mock_dataset.file_identifier = None
        etl_service_with_mocks.iso_parser.parse = AsyncMock(return_value=mock_dataset)
        
        result = await etl_service_with_mocks.run_pipeline(limit=2)
        
        assert result['total_identifiers'] == 2
        assert 'successful' in result
        assert 'failed' in result
        assert 'duration' in result
    
    @pytest.mark.asyncio
    async def test_run_pipeline_tracks_duration(self, etl_service_with_mocks):
        """Test pipeline tracks execution duration"""
        etl_service_with_mocks.ceh_extractor.fetch_dataset_xml = AsyncMock(return_value='<xml/>')
        etl_service_with_mocks.ceh_extractor.fetch_dataset_json = AsyncMock(return_value=None)
        etl_service_with_mocks.ceh_extractor.fetch_dataset_rdf = AsyncMock(return_value=None)
        etl_service_with_mocks.ceh_extractor.fetch_dataset_schema_org = AsyncMock(return_value=None)
        
        mock_dataset = MagicMock(spec=DatasetEntity)
        etl_service_with_mocks.iso_parser.parse = AsyncMock(return_value=mock_dataset)
        
        result = await etl_service_with_mocks.run_pipeline(limit=1)
        
        assert result['duration'] > 0