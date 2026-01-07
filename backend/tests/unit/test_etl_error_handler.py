"""
Unit tests for ETL CLI and service.

Tests cover:
1. CLI argument parsing
2. ETL pipeline phases (Extract, Transform, Load)
3. Error handling and recovery
4. Batch processing and optimization
5. Database integration
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from src.services.etl.etl_service import ETLService
from src.services.etl.etl_error_handler import (
    ETLErrorHandler,
    RetryConfig,
    RetryStrategy,
    RecoverableError,
    NetworkError,
    ParsingError,
    NonRecoverableError,
    ValidationError
)
from src.services.etl.etl_optimizer import (
    AdaptiveBatchProcessor,
    ConcurrencyOptimizer,
    CachingBatchProcessor,
    PerformanceMetrics
)
from src.repositories.unit_of_work import UnitOfWork
from src.models.database_models import Dataset, MetadataDocument


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_identifiers_file():
    """Create temporary identifiers file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("# Test identifiers\n")
        f.write("identifier-001\n")
        f.write("identifier-002\n")
        f.write("\n")  # Empty line
        f.write("identifier-003\n")
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_unit_of_work():
    """Create mock UnitOfWork instance"""
    mock_uow = AsyncMock(spec=UnitOfWork)
    mock_uow.datasets = MagicMock()  # Sync repository
    mock_uow.metadata_documents = MagicMock()  # Sync repository
    mock_uow.supporting_documents = MagicMock()  # Sync repository
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=None)
    mock_uow.commit = MagicMock()  # Sync commit
    return mock_uow


@pytest.fixture
def etl_service(temp_identifiers_file, mock_unit_of_work):
    """Create ETL service instance for testing"""
    service = ETLService(
        identifiers_file=temp_identifiers_file,
        unit_of_work=mock_unit_of_work,
        batch_size=2,
        max_concurrent_downloads=3,
        dry_run=False,
        enable_supporting_docs=False  # Disable for unit tests
    )
    
    # Mock external services
    service.ceh_extractor = AsyncMock()
    
    # Mock the cached fetcher that wraps the extractor
    service.cached_fetcher = MagicMock()
    service.cached_fetcher.fetch_xml = AsyncMock(return_value="<xml>...</xml>")
    service.cached_fetcher.fetch_json = AsyncMock(return_value='{"key": "value"}')
    service.cached_fetcher.fetch_rdf = AsyncMock(return_value="<rdf>...</rdf>")
    service.cached_fetcher.fetch_schema_org = AsyncMock(return_value=None)
    service.cached_fetcher.clear_fetch_cache_status = MagicMock()
    service.cached_fetcher.fetch_cache_status = {}
    
    service.iso_parser = AsyncMock()
    service.json_parser = AsyncMock()
    service.rdf_parser = AsyncMock()
    service.schema_org_parser = AsyncMock()
    
    return service


# ============================================================================
# TEST: Identifier Reading
# ============================================================================

class TestIdentifierReading:
    """Test dataset identifier file reading"""
    
    def test_read_identifiers_success(self, etl_service):
        """Test successful identifier reading"""
        identifiers = etl_service._read_identifiers()
        
        assert len(identifiers) == 3
        assert "identifier-001" in identifiers
        assert "identifier-002" in identifiers
        assert "identifier-003" in identifiers
        assert all(not line.startswith('#') for line in identifiers)
    
    def test_read_identifiers_with_limit(self, etl_service):
        """Test reading identifiers with limit"""
        identifiers = etl_service._read_identifiers(limit=2)
        
        assert len(identifiers) == 2 
    
    def test_read_identifiers_file_not_found(self, mock_unit_of_work):
        """Test error handling for missing file"""
        service = ETLService(
            identifiers_file=Path("/nonexistent/file.txt"),
            unit_of_work=mock_unit_of_work,
            batch_size=10,
            max_concurrent_downloads=5,
            dry_run=False,
            enable_supporting_docs=False  # Disable to avoid abstract class instantiation
        )
        
        with pytest.raises(Exception):
            service._read_identifiers()
    
    def test_read_identifiers_skips_comments_and_empty(self, temp_identifiers_file, mock_unit_of_work):
        """Test that comments and empty lines are properly skipped"""
        # ✅ FIXED: Added mock_unit_of_work parameter and all required args
        service = ETLService(
            identifiers_file=temp_identifiers_file,
            unit_of_work=mock_unit_of_work,
            batch_size=10,
            max_concurrent_downloads=5,
            dry_run=False,
            enable_supporting_docs=False  # Disable to avoid abstract class instantiation
        )
        identifiers = service._read_identifiers()
        
        # Comments and empty lines should be excluded
        assert len(identifiers) == 3
        assert all(id for id in identifiers)  # All non-empty
        assert not any('#' in id for id in identifiers)  # No comments


# ============================================================================
# TEST: Extract Phase
# ============================================================================

class TestExtractPhase:
    """Test EXTRACT phase functionality"""
    
    @pytest.mark.asyncio
    async def test_extract_phase_success(self, etl_service):
        """Test successful metadata extraction"""
        identifiers = ["id-001", "id-002"]
        
        # Mock successful fetches using cached fetcher
        etl_service.cached_fetcher.fetch_xml = AsyncMock(return_value="<xml>...</xml>")
        etl_service.cached_fetcher.fetch_json = AsyncMock(return_value='{"key": "value"}')
        etl_service.cached_fetcher.fetch_rdf = AsyncMock(return_value="<rdf>...</rdf>")
        etl_service.cached_fetcher.fetch_schema_org = AsyncMock(return_value=None)
        
        result = await etl_service._extract_phase(identifiers)
        
        assert len(result) == 2
        assert all(identifier in result for identifier in identifiers)
        assert result["id-001"]["xml"] == "<xml>...</xml>"
    
    @pytest.mark.asyncio
    async def test_extract_phase_partial_failure(self, etl_service):
        """Test extraction with some failures"""
        identifiers = ["id-001", "id-002"]
        call_count = [0]
        
        async def mock_fetch_xml(identifier):
            call_count[0] += 1
            if call_count[0] <= 1:
                return "<xml>...</xml>"
            raise NetworkError("Connection timeout")
        
        etl_service.cached_fetcher.fetch_xml = mock_fetch_xml
        etl_service.cached_fetcher.fetch_json = AsyncMock(return_value=None)
        etl_service.cached_fetcher.fetch_rdf = AsyncMock(return_value=None)
        etl_service.cached_fetcher.fetch_schema_org = AsyncMock(return_value=None)
        
        result = await etl_service._extract_phase(identifiers)
        
        # Should have at least one successful extraction
        assert len(result) >= 1
    
    @pytest.mark.asyncio
    async def test_fetch_metadata_all_formats(self, etl_service):
        """Test fetching metadata in all 4 formats"""
        identifier = "test-id"
        
        etl_service.cached_fetcher.fetch_xml = AsyncMock(return_value="<xml/>")
        etl_service.cached_fetcher.fetch_json = AsyncMock(return_value="{}")
        etl_service.cached_fetcher.fetch_rdf = AsyncMock(return_value="<rdf/>")
        etl_service.cached_fetcher.fetch_schema_org = AsyncMock(return_value="{}")
        
        result = await etl_service._fetch_metadata_for_identifier(identifier)
        
        assert result['identifier'] == identifier
        assert result['xml'] is not None
        assert result['json'] is not None
        assert result['rdf'] is not None
        assert result['schema_org'] is not None


# ============================================================================
# TEST: Transform Phase
# ============================================================================

class TestTransformPhase:
    """Test TRANSFORM phase functionality"""
    
    @pytest.mark.asyncio
    async def test_parse_metadata_primary_format_success(self, etl_service):
        """Test parsing with primary format (XML) success"""
        metadata = {
            'identifier': 'id-001',
            'xml': '<xml>data</xml>',
            'json': None,
            'rdf': None,
            'schema_org': None
        }
        
        mock_dataset = MagicMock(spec=Dataset)
        mock_dataset.file_identifier = 'id-001'
        etl_service.iso_parser.parse = AsyncMock(return_value=mock_dataset)
        
        # ✅ FIXED: Now using the correct method name
        result = await etl_service._parse_metadata_with_fallback('id-001', metadata)
        
        assert result is not None
        assert result.file_identifier == 'id-001'
        etl_service.iso_parser.parse.assert_called_once_with('<xml>data</xml>')
    
    @pytest.mark.asyncio
    async def test_parse_metadata_fallback_chain(self, etl_service):
        """Test fallback chain: XML → JSON → RDF → Schema.org"""
        metadata = {
            'identifier': 'id-001',
            'xml': None,
            'json': '{"data": "json"}',
            'rdf': None,
            'schema_org': None
        }
        
        # XML not available, JSON succeeds
        mock_dataset = MagicMock(spec=Dataset)
        mock_dataset.file_identifier = 'id-001'
        etl_service.json_parser.parse = AsyncMock(return_value=mock_dataset)
        
        # ✅ FIXED: Now using the correct method name
        result = await etl_service._parse_metadata_with_fallback('id-001', metadata)
        
        assert result is not None
        assert result.file_identifier == 'id-001'
        etl_service.json_parser.parse.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parse_metadata_all_formats_fail(self, etl_service):
        """Test when all format parsers fail"""
        metadata = {
            'identifier': 'id-001',
            'xml': '<invalid>',
            'json': '{invalid}',
            'rdf': '<invalid>',
            'schema_org': '{invalid}'
        }
        
        # All parsers fail
        from src.services.etl.etl_error_handler import ParsingError
        etl_service.iso_parser.parse.side_effect = ParsingError("Invalid")
        etl_service.json_parser.parse.side_effect = ParsingError("Invalid")
        etl_service.rdf_parser.parse.side_effect = ParsingError("Invalid")
        etl_service.schema_org_parser.parse.side_effect = ParsingError("Invalid")
        
        # ✅ FIXED: Now using the correct method name
        result = await etl_service._parse_metadata_with_fallback('id-001', metadata)
        
        assert result is None


# ============================================================================
# TEST: Load Phase
# ============================================================================

class TestLoadPhase:
    """Test LOAD phase functionality"""
    
    @pytest.mark.asyncio
    async def test_load_dataset_to_database(self, etl_service, mock_unit_of_work):
        """Test loading dataset to database"""
        dataset = MagicMock(spec=Dataset)
        dataset.file_identifier = 'id-001'
        
        metadata = {
            'xml': '<xml>data</xml>',
            'json': '{"data": "json"}',
            'rdf': None,
            'schema_org': None
        }
        
        # Mock upsert_by_identifier to return a dataset with an id
        mock_result = MagicMock(spec=Dataset)
        mock_result.id = 'db-id-001'
        mock_unit_of_work.datasets.upsert_by_identifier.return_value = mock_result
        
        # Mock get_by_dataset_and_type to return None (no existing metadata)
        mock_unit_of_work.metadata_documents.get_by_dataset_and_type.return_value = None
        
        # ✅ FIXED: Now using the correct method name
        await etl_service._load_dataset_to_database('id-001', dataset, metadata)
        
        # Verify upsert was called
        mock_unit_of_work.datasets.upsert_by_identifier.assert_called_once()
        
        # Verify metadata documents were added
        assert mock_unit_of_work.metadata_documents.insert.call_count >= 1
        
        # Verify commit was called
        mock_unit_of_work.commit.assert_called()


# ============================================================================
# TEST: Error Handler - Retry Logic
# ============================================================================

class TestErrorHandlerRetryLogic:
    """Test error handling and retry mechanisms"""
    
    @pytest.mark.asyncio
    async def test_retry_with_eventual_success(self):
        """Test retry mechanism with eventual success"""
        handler = ETLErrorHandler(
            retry_config=RetryConfig(
                max_retries=3,
                strategy=RetryStrategy.FIXED_DELAY,
                initial_delay=0.01
            )
        )
        
        call_count = [0]
        
        async def flaky_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RecoverableError("Temporary failure")
            return "success"
        
        result = await handler.execute_with_retry(
            flaky_operation,
            "test-id",
            "test operation"
        )
        
        assert result == "success"
        assert call_count[0] == 3
        assert "test-id" in handler.recovered_identifiers
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test retry exhaustion"""
        handler = ETLErrorHandler(
            retry_config=RetryConfig(
                max_retries=2,
                strategy=RetryStrategy.FIXED_DELAY,
                initial_delay=0.01
            )
        )
        
        async def always_fails():
            raise RecoverableError("Persistent failure")
        
        result = await handler.execute_with_retry(
            always_fails,
            "test-id",
            "test operation"
        )
        
        assert result is None
        assert "test-id" in handler.failed_identifiers
    
    @pytest.mark.asyncio
    async def test_non_recoverable_error_not_retried(self):
        """Test that non-recoverable errors are not retried"""
        handler = ETLErrorHandler(
            retry_config=RetryConfig(max_retries=3)
        )
        
        call_count = [0]
        
        async def operation_with_validation_error():
            call_count[0] += 1
            raise ValidationError("Invalid data")
        
        result = await handler.execute_with_retry(
            operation_with_validation_error,
            "test-id",
            "test operation"
        )
        
        assert result is None
        assert call_count[0] == 1  # Should be called only once
    
    def test_circuit_breaker_logic(self):
        """Test circuit breaker pattern"""
        handler = ETLErrorHandler()
        handler.circuit_breaker_threshold = 0.5
        
        # Simulate balanced success/failure
        handler.success_count = 5
        handler.failure_count = 5
        
        # 50% failure rate should NOT trigger circuit breaker
        assert handler.should_continue() is True
        
        # Simulate high failure rate (60%)
        handler.failure_count = 6
        handler.success_count = 4
        
        # Circuit should open
        assert handler.should_continue() is False


# ============================================================================
# TEST: Error Handler - Delay Calculation
# ============================================================================

class TestErrorHandlerDelayCalculation:
    """Test retry delay calculations"""
    
    def test_exponential_backoff_delay(self):
        """Test exponential backoff delay calculation"""
        handler = ETLErrorHandler(
            retry_config=RetryConfig(
                initial_delay=1.0,
                backoff_multiplier=2.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                jitter=False
            )
        )
        
        delay_0 = handler._calculate_delay(0)
        delay_1 = handler._calculate_delay(1)
        delay_2 = handler._calculate_delay(2)
        
        assert delay_0 == 1.0
        assert delay_1 == 2.0
        assert delay_2 == 4.0
    
    def test_linear_backoff_delay(self):
        """Test linear backoff delay calculation"""
        handler = ETLErrorHandler(
            retry_config=RetryConfig(
                initial_delay=1.0,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                jitter=False
            )
        )
        
        delay_0 = handler._calculate_delay(0)
        delay_1 = handler._calculate_delay(1)
        delay_2 = handler._calculate_delay(2)
        
        assert delay_0 == 1.0
        assert delay_1 == 2.0
        assert delay_2 == 3.0
    
    def test_max_delay_cap(self):
        """Test that max delay is capped"""
        handler = ETLErrorHandler(
            retry_config=RetryConfig(
                initial_delay=10.0,
                backoff_multiplier=2.0,
                max_delay=30.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                jitter=False
            )
        )
        
        delay = handler._calculate_delay(5)  # Would be 320 without cap
        assert delay == 30.0  # Capped at max_delay


# ============================================================================
# TEST: Error Handler - Reporting
# ============================================================================

class TestErrorHandlerReporting:
    """Test error report generation"""
    
    def test_error_report_generation(self):
        """Test error report generation"""
        handler = ETLErrorHandler()
        handler.success_count = 8
        handler.failure_count = 2
        handler.failed_identifiers.add("id-001")
        handler.failed_identifiers.add("id-002")
        handler.recovered_identifiers.add("id-003")
        
        report = handler.get_error_report()
        
        assert report['total_operations'] == 10
        assert report['successful'] == 8
        assert report['failed'] == 2
        assert report['recovery_count'] == 1
        assert "80.0%" in report['success_rate']
        assert len(report['failed_identifiers']) == 2


# ============================================================================
# TEST: Adaptive Batch Processor
# ============================================================================

class TestAdaptiveBatchProcessor:
    """Test adaptive batch processing"""
    
    def test_initial_batch_size(self):
        """Test processor initialization"""
        processor = AdaptiveBatchProcessor(initial_batch_size=10)
        
        assert processor.batch_size == 10
    
    def test_adapt_batch_size_on_high_failure(self):
        """Test batch size reduction on high failure rate"""
        processor = AdaptiveBatchProcessor(initial_batch_size=10)
        
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=5.0,
            items_processed=10,
            successful=2,
            failed=8  # 20% success rate
        )
        
        processor._adapt_batch_size(metrics)
        
        # Should reduce batch size
        assert processor.batch_size < 10
    
    def test_adapt_batch_size_on_slow_processing(self):
        """Test batch size reduction on slow processing"""
        processor = AdaptiveBatchProcessor(
            initial_batch_size=10,
            target_duration_per_batch=10.0
        )
        
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=20.0,  # 2x target duration
            items_processed=10,
            successful=10,
            failed=0
        )
        
        processor._adapt_batch_size(metrics)
        
        # Should reduce batch size
        assert processor.batch_size < 10
    
    def test_adapt_batch_size_on_fast_processing(self):
        """Test batch size increase on fast processing"""
        processor = AdaptiveBatchProcessor(
            initial_batch_size=10,
            target_duration_per_batch=10.0,
            max_batch_size=100
        )
        
        metrics = PerformanceMetrics(
            batch_size=10,
            duration=3.0,  # 0.3x target duration
            items_processed=10,
            successful=10,
            failed=0
        )
        
        processor._adapt_batch_size(metrics)
        
        # Should increase batch size
        assert processor.batch_size > 10


# ============================================================================
# TEST: Concurrency Optimizer
# ============================================================================

class TestConcurrencyOptimizer:
    """Test concurrency optimization"""
    
    def test_initial_concurrency(self):
        """Test optimizer initialization"""
        optimizer = ConcurrencyOptimizer(initial_concurrency=5)
        
        assert optimizer.concurrency == 5
    
    def test_increase_concurrency_on_good_throughput(self):
        """Test concurrency increase on improving throughput"""
        optimizer = ConcurrencyOptimizer(initial_concurrency=5, max_concurrency=20)
        
        # Record improving throughput
        for throughput in [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5]:
            optimizer.record_throughput(throughput)
        
        # Concurrency should increase
        assert optimizer.concurrency > 5


# ============================================================================
# TEST: Caching Processor
# ============================================================================

class TestCachingBatchProcessor:
    """Test result caching"""
    
    def test_cache_hit(self):
        """Test successful cache hit"""
        processor = CachingBatchProcessor()
        
        processor.cache_result("id-001", {"data": "value"})
        result = processor.get_cached("id-001")
        
        assert result == {"data": "value"}
        assert processor.cache_hits == 1
    
    def test_cache_miss(self):
        """Test cache miss"""
        processor = CachingBatchProcessor()
        
        result = processor.get_cached("id-nonexistent")
        
        assert result is None
        assert processor.cache_misses == 1
    
    def test_cache_stats(self):
        """Test cache statistics"""
        processor = CachingBatchProcessor()
        
        processor.cache_result("id-001", {"data": "value"})
        processor.get_cached("id-001")  # Hit
        processor.get_cached("id-002")  # Miss
        
        stats = processor.get_cache_stats()
        
        assert stats['cached_items'] == 1
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert "50.0%" in stats['hit_rate']


# ============================================================================
# TEST: Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete pipeline"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_dry_run(self, etl_service, mock_unit_of_work):
        """Test complete ETL pipeline in dry-run mode"""
        etl_service.dry_run = True
        etl_service.enable_supporting_docs = False
        
        # Mock all components
        etl_service.ceh_extractor.fetch_dataset_xml = AsyncMock(return_value="<xml>data</xml>")
        etl_service.ceh_extractor.fetch_dataset_json = AsyncMock(return_value=None)
        etl_service.ceh_extractor.fetch_dataset_rdf = AsyncMock(return_value=None)
        etl_service.ceh_extractor.fetch_dataset_schema_org = AsyncMock(return_value=None)
        
        mock_dataset = MagicMock(spec=Dataset)
        mock_dataset.file_identifier = None
        etl_service.iso_parser.parse.return_value = mock_dataset
        
        # Run pipeline
        result = await etl_service.run_pipeline(limit=2)
        
        assert result['total_identifiers'] == 2
        assert result['successful'] >= 0
