"""
Tests for Semantic Search Service (Issue 8).

Comprehensive tests for SearchService covering:
- Query validation and normalization
- Query embedding generation
- Vector store search
- Result hydration and mapping
- Relevance score normalization
- Result sorting and ranking
- Empty/invalid query handling
- Error handling and recovery

Tests use mocks to avoid dependencies on:
- Real embedding model (sentence-transformers)
- Real ChromaDB instance
- Real database

This keeps tests fast and isolated.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import numpy as np

from src.models.schemas import Dataset, SearchResult
from src.services.search import SearchService, SearchServiceError
from src.models.database_models import Dataset as DBDataset
from src.repositories.unit_of_work import UnitOfWork


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_embedding_service():
    """Mock embedding service that returns consistent embeddings."""
    service = MagicMock()
    
    def embed_text(text):
        """Return consistent embedding based on text."""
        if not text or not text.strip():
            return np.zeros(384)
        
        # Create deterministic embedding based on text
        # (same text always returns same embedding for testing)
        seed = sum(ord(c) for c in text[:10]) % 10000
        np.random.seed(seed)
        return np.random.randn(384).astype(np.float32)
    
    service.embed_text = embed_text
    return service


@pytest.fixture
def mock_vector_store():
    """Mock vector store with predefined search results."""
    store = MagicMock()
    
    def search_datasets(query_embedding, limit=10):
        """Return mock search results with VectorStore format.
        
        VectorStore already normalizes distances to similarity_score (0-1).
        Result format:
        - id: Document ID
        - similarity_score: Normalized score (0-1, higher = better)
        - metadata: Dict with file_identifier, etc.
        - content: Document content
        """
        # Simulate 3 results with similarity scores (already normalized)
        return [
            {
                "id": "dataset_dataset-001",
                "similarity_score": 0.95,  # Very similar (cosine distance 0.1 -> 1-(0.1/2) = 0.95)
                "metadata": {"file_identifier": "dataset-001"},
                "content": "UK Climate Dataset content"
            },
            {
                "id": "dataset_dataset-002",
                "similarity_score": 0.75,  # Moderately similar (cosine distance 0.5 -> 1-(0.5/2) = 0.75)
                "metadata": {"file_identifier": "dataset-002"},
                "content": "UK Precipitation content"
            },
            {
                "id": "dataset_dataset-003",
                "similarity_score": 0.40,  # Less similar (cosine distance 1.2 -> 1-(1.2/2) = 0.40)
                "metadata": {"file_identifier": "dataset-003"},
                "content": "UK Temperature content"
            },
        ]
    
    def search_supporting_docs(query_embedding, limit=10):
        """Return mock supporting docs results."""
        return []
    
    store.search_datasets = search_datasets
    store.search_supporting_docs = search_supporting_docs
    return store


@pytest.fixture
def sample_dataset():
    """Create sample Dataset entity for testing."""
    return Dataset(
        file_identifier="dataset-001",
        title="UK Climate Dataset",
        abstract="Long-term climate data for the United Kingdom",
        topic_category=["climatologyMeteorologyAtmosphere"],
        keywords=["climate", "temperature", "precipitation"],
        lineage="Derived from Met Office",
        supplemental_info="Updated monthly"
    )


@pytest.fixture
def sample_db_dataset():
    """Create sample database Dataset entity."""
    return DBDataset(
        id=1,
        file_identifier="dataset-001",
        title="UK Climate Dataset",
        abstract="Long-term climate data for the United Kingdom",
        topic_category=["climatologyMeteorologyAtmosphere"],
        keywords=["climate", "temperature", "precipitation"],
        lineage="Derived from Met Office",
        supplemental_info="Updated monthly",
        source_format="xml"
    )


@pytest.fixture
def mock_unit_of_work(sample_db_dataset):
    """Mock unit of work with dataset repository."""
    uow = MagicMock(spec=UnitOfWork)
    
    # Mock dataset repository
    mock_repo = MagicMock()
    
    def get_by_file_identifier(file_id):
        if file_id == "dataset-001":
            return sample_db_dataset
        elif file_id == "dataset-002":
            d = DBDataset(
                id=2,
                file_identifier="dataset-002",
                title="UK Precipitation Dataset",
                abstract="Annual precipitation measurements",
                topic_category=["climatology"],
                keywords=["precipitation", "rainfall"],
                lineage=None,
                supplemental_info=None,
                source_format="json"
            )
            return d
        elif file_id == "dataset-003":
            d = DBDataset(
                id=3,
                file_identifier="dataset-003",
                title="UK Temperature Records",
                abstract="Historical temperature data",
                topic_category=["climatology"],
                keywords=["temperature", "heat"],
                lineage=None,
                supplemental_info=None,
                source_format="json"
            )
            return d
        return None
    
    mock_repo.get_by_file_identifier = get_by_file_identifier
    uow.datasets = mock_repo
    
    # Make UnitOfWork support context manager protocol for 'with' statement
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=False)
    
    return uow


@pytest.fixture
def search_service(mock_embedding_service, mock_vector_store, mock_unit_of_work):
    """Create SearchService with mocked dependencies."""
    return SearchService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        unit_of_work=mock_unit_of_work,
        enable_caching=False
    )


# ============================================================================
# Test: Initialization & Validation
# ============================================================================

class TestSearchServiceInitialization:
    """Test SearchService initialization and dependency validation."""
    
    def test_initialization_success(self, mock_embedding_service, mock_vector_store, mock_unit_of_work):
        """Test successful service initialization."""
        service = SearchService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            unit_of_work=mock_unit_of_work
        )
        
        assert service.embedding_service is mock_embedding_service
        assert service.vector_store is mock_vector_store
        assert service.unit_of_work is mock_unit_of_work
    
    def test_initialization_missing_embedding_service(self, mock_vector_store, mock_unit_of_work):
        """Test initialization fails without embedding service."""
        with pytest.raises(SearchServiceError, match="EmbeddingService is required"):
            SearchService(
                embedding_service=None,
                vector_store=mock_vector_store,
                unit_of_work=mock_unit_of_work
            )
    
    def test_initialization_missing_vector_store(self, mock_embedding_service, mock_unit_of_work):
        """Test initialization fails without vector store."""
        with pytest.raises(SearchServiceError, match="VectorStore is required"):
            SearchService(
                embedding_service=mock_embedding_service,
                vector_store=None,
                unit_of_work=mock_unit_of_work
            )
    
    def test_initialization_missing_unit_of_work(self, mock_embedding_service, mock_vector_store):
        """Test initialization fails without unit of work."""
        with pytest.raises(SearchServiceError, match="UnitOfWork is required"):
            SearchService(
                embedding_service=mock_embedding_service,
                vector_store=mock_vector_store,
                unit_of_work=None
            )


# ============================================================================
# Test: Query Validation & Empty Query Handling
# ============================================================================

class TestQueryValidation:
    """Test query validation and normalization."""
    
    def test_search_empty_query_returns_empty_list(self, search_service):
        """Test empty query returns empty list."""
        results = search_service.search("")
        assert results == []
    
    def test_search_whitespace_only_query_returns_empty_list(self, search_service):
        """Test whitespace-only query returns empty list."""
        results = search_service.search("   \t\n  ")
        assert results == []
    
    def test_search_none_query_returns_empty_list(self, search_service):
        """Test None query returns empty list."""
        results = search_service.search(None)
        assert results == []
    
    def test_search_numeric_query_returns_empty_list(self, search_service):
        """Test non-string query returns empty list."""
        results = search_service.search(12345)
        assert results == []
    
    def test_search_very_long_query_is_truncated(self, search_service):
        """Test very long query is truncated."""
        long_query = "word " * 300  # 1500 chars
        
        # Should not raise error, but truncate
        results = search_service.search(long_query, top_k=5)
        
        # Mocked store should still return results
        assert isinstance(results, list)


# ============================================================================
# Test: Query Embedding Generation
# ============================================================================

class TestQueryEmbedding:
    """Test query embedding generation."""
    
    def test_embed_query_generates_vector(self, search_service):
        """Test query embedding generation."""
        embedding = search_service._embed_query("climate data")
        
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # Expected dimension
    
    def test_embed_query_returns_none_on_error(self, mock_embedding_service, mock_vector_store, mock_unit_of_work):
        """Test embedding generation returns None on error."""
        # Make embedding service raise error
        mock_embedding_service.embed_text = MagicMock(side_effect=Exception("Model load failed"))
        
        service = SearchService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            unit_of_work=mock_unit_of_work
        )
        
        embedding = service._embed_query("climate data")
        assert embedding is None


# ============================================================================
# Test: Score Validation
# ============================================================================

class TestScoreValidation:
    """Test that scores from VectorStore are in valid range."""
    
    def test_scores_in_valid_range(self, search_service):
        """Test that all returned scores are in [0, 1] range."""
        # VectorStore already normalizes scores, we just validate them
        results = search_service.search("climate data", top_k=10)
        
        for result in results:
            assert 0 <= result.score <= 1


# ============================================================================
# Test: Result Hydration & Mapping
# ============================================================================

class TestResultHydration:
    """Test vector results hydration to SearchResult objects."""
    
    def test_hydrate_single_result(self, search_service):
        """Test hydrating single vector result."""
        vector_result = [
            {
                "id": "dataset_dataset-001",
                "similarity_score": 0.95,
                "metadata": {"file_identifier": "dataset-001"},
                "content": "content"
            }
        ]
        
        results = search_service._hydrate_results(vector_result)
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].dataset.file_identifier == "dataset-001"
        assert results[0].dataset.title == "UK Climate Dataset"
        assert results[0].score == 0.95
    
    def test_hydrate_multiple_results_preserves_order(self, search_service):
        """Test hydrating multiple results preserves order."""
        vector_results = [
            {
                "id": "dataset_dataset-001",
                "similarity_score": 0.95,
                "metadata": {"file_identifier": "dataset-001"},
                "content": "content"
            },
            {
                "id": "dataset_dataset-002",
                "similarity_score": 0.75,
                "metadata": {"file_identifier": "dataset-002"},
                "content": "content"
            },
            {
                "id": "dataset_dataset-003",
                "similarity_score": 0.40,
                "metadata": {"file_identifier": "dataset-003"},
                "content": "content"
            },
        ]
        
        results = search_service._hydrate_results(vector_results)
        
        assert len(results) == 3
        assert results[0].dataset.file_identifier == "dataset-001"
        assert results[1].dataset.file_identifier == "dataset-002"
        assert results[2].dataset.file_identifier == "dataset-003"
    
    def test_hydrate_skips_missing_file_identifier(self, search_service):
        """Test hydration skips results with missing file_identifier."""
        vector_results = [
            {
                "id": "dataset_unknown",
                "distance": 0.1,
                "metadata": {}  # Missing file_identifier
            }
        ]
        
        results = search_service._hydrate_results(vector_results)
        
        assert len(results) == 0
    
    def test_hydrate_skips_not_found_datasets(self, search_service):
        """Test hydration skips datasets not in database."""
        vector_results = [
            {
                "id": "dataset_unknown-999",
                "distance": 0.1,
                "metadata": {"file_identifier": "unknown-999"}
            }
        ]
        
        results = search_service._hydrate_results(vector_results)
        
        assert len(results) == 0


# ============================================================================
# Test: Search Pipeline Integration
# ============================================================================

class TestSearchPipeline:
    """Test complete semantic search pipeline."""
    
    def test_search_returns_results_sorted_by_score(self, search_service):
        """Test search returns results sorted by score (descending)."""
        results = search_service.search("climate precipitation UK", top_k=10)
        
        assert len(results) == 3
        
        # Check sorted by score descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_search_results_have_normalized_scores(self, search_service):
        """Test search results have normalized scores in [0, 1]."""
        results = search_service.search("climate data", top_k=10)
        
        for result in results:
            assert isinstance(result.score, float)
            assert 0 <= result.score <= 1
    
    def test_search_results_include_full_datasets(self, search_service):
        """Test search results include full Dataset objects."""
        results = search_service.search("climate precipitation", top_k=10)
        
        for result in results:
            assert isinstance(result.dataset, Dataset)
            assert result.dataset.file_identifier
            assert result.dataset.title
    
    def test_search_respects_top_k_limit(self, search_service):
        """Test search respects top_k parameter."""
        with patch.object(search_service.vector_store, 'search_datasets') as mock_search:
            # Mock to respect limit parameter
            def search_with_limit(query_embedding, limit=10):
                results = [
                    {
                        "id": "dataset_dataset-001",
                        "similarity_score": 0.95,
                        "metadata": {"file_identifier": "dataset-001"},
                        "content": "content"
                    },
                    {
                        "id": "dataset_dataset-002",
                        "similarity_score": 0.75,
                        "metadata": {"file_identifier": "dataset-002"},
                        "content": "content"
                    },
                    {
                        "id": "dataset_dataset-003",
                        "similarity_score": 0.40,
                        "metadata": {"file_identifier": "dataset-003"},
                        "content": "content"
                    },
                ]
                return results[:limit]  # Return only what was requested
            
            mock_search.side_effect = search_with_limit
            
            results = search_service.search("climate", top_k=2)
            
            # Should only return 2 results
            assert len(results) == 2
    
    def test_search_invalid_top_k_uses_default(self, search_service):
        """Test invalid top_k falls back to default."""
        # top_k = -1 should be invalid
        results = search_service.search("climate", top_k=-1)
        
        # Should still return results (default top_k=10)
        assert isinstance(results, list)
    
    def test_search_completes_in_reasonable_time(self, search_service):
        """Test search completes within acceptable time."""
        import time
        
        start = time.time()
        results = search_service.search("climate precipitation UK", top_k=10)
        elapsed = time.time() - start
        
        # Mocked search should be fast (< 1s)
        assert elapsed < 1.0
        assert isinstance(results, list)


# ============================================================================
# Test: Edge Cases & Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_search_with_special_characters(self, search_service):
        """Test search with special characters."""
        results = search_service.search("climate & weather @#$%")
        
        assert isinstance(results, list)
    
    def test_search_with_unicode_characters(self, search_service):
        """Test search with unicode characters."""
        results = search_service.search("température précipitations données 中文")
        
        assert isinstance(results, list)
    
    def test_search_no_results_returns_empty_list(self, mock_embedding_service, mock_vector_store, mock_unit_of_work):
        """Test search with no matching results."""
        # Mock vector store to return empty results
        mock_vector_store.search_datasets = MagicMock(return_value=[])
        
        service = SearchService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            unit_of_work=mock_unit_of_work
        )
        
        results = service.search("very obscure query", top_k=10)
        
        assert results == []
    
    def test_vector_store_search_error_raises_exception(self, mock_embedding_service, mock_vector_store, mock_unit_of_work):
        """Test vector store search error raises SearchServiceError."""
        mock_vector_store.search_datasets = MagicMock(side_effect=Exception("ChromaDB error"))
        
        service = SearchService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            unit_of_work=mock_unit_of_work
        )
        
        with pytest.raises(SearchServiceError, match="Vector store search failed"):
            service.search("climate", top_k=10)
    
    def test_hydration_error_gracefully_skips_failing_results(self, mock_embedding_service, mock_vector_store, mock_unit_of_work):
        """Test hydration errors are handled gracefully, not raised.
        
        When a result fails to hydrate (e.g., DB error), the search should
        skip that result and continue with others rather than raising an error.
        This provides graceful degradation.
        """
        # Mock unit of work to raise error during hydration
        mock_unit_of_work.datasets.get_by_file_identifier = MagicMock(side_effect=Exception("DB error"))
        
        service = SearchService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            unit_of_work=mock_unit_of_work
        )
        
        # Search should not raise - instead it should gracefully skip all results
        # since all hydrations fail
        results = service.search("climate", top_k=10)
        
        # All results are skipped due to DB error, so we get empty list
        assert isinstance(results, list)
        assert len(results) == 0


# ============================================================================
# Test: Result Scoring Details
# ============================================================================

class TestScoringDetails:
    """Test detailed relevance scoring behavior."""
    
    def test_results_sorted_by_score_descending(self, search_service):
        """Test that results are sorted by score (highest first)."""
        results = search_service.search("climate data", top_k=10)
        
        # Check results are sorted by score descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# Test: Collection Parameter
# ============================================================================

class TestCollectionParameter:
    """Test collection parameter in search."""
    
    def test_search_uses_datasets_collection_by_default(self, search_service):
        """Test search uses datasets collection by default."""
        results = search_service.search("climate", top_k=10)
        
        # Should return results from datasets collection
        assert isinstance(results, list)
    
    def test_search_supports_supporting_documents_collection(self, search_service):
        """Test search supports supporting_documents collection."""
        # Mock supporting docs search to return empty (no results)
        with patch.object(search_service.vector_store, 'search_supporting_docs', return_value=[]):
            results = search_service.search("climate", top_k=10, collection="supporting_documents")
            
            assert isinstance(results, list)
            assert len(results) == 0  # No supporting docs mocked
