"""
Tests for Vector Store (Issue 7).

Tests for:
- VectorStore: Adding, searching, deleting datasets and documents
- Collection management
- Search result formatting
"""

import pytest
import tempfile
from pathlib import Path
from src.services.embeddings import VectorStore, VectorStoreError


@pytest.fixture
def temp_chroma_dir():
    """Create temporary chroma directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def vector_store(temp_chroma_dir):
    """Create vector store with temp directory."""
    return VectorStore(persist_dir=temp_chroma_dir)


class TestVectorStore:
    """Test VectorStore class."""
    
    def test_initialization(self, vector_store):
        """Test vector store initialization."""
        assert vector_store.client is not None
        assert vector_store._datasets_collection is not None
        assert vector_store._supporting_docs_collection is not None
    
    def test_add_single_dataset(self, vector_store):
        """Test adding single dataset."""
        embedding = [0.1] * 384
        metadata = {
            "file_identifier": "test-001",
            "title": "Test Dataset",
            "abstract": "Test abstract",
            "text_content": "Test Dataset Test abstract"
        }
        
        doc_id = vector_store.add_dataset(
            file_identifier="test-001",
            embedding=embedding,
            metadata=metadata
        )
        
        assert doc_id == "dataset_test-001"
    
    def test_add_dataset_with_full_metadata(self, vector_store):
        """Test adding dataset with all metadata fields."""
        embedding = [0.1] * 384
        metadata = {
            "file_identifier": "test-002",
            "title": "Climate Dataset",
            "abstract": "UK climate data",
            "keywords": "climate temperature precipitation",
            "topic_category": "climatology",
            "text_content": "Climate Dataset UK climate data"
        }
        
        doc_id = vector_store.add_dataset(
            file_identifier="test-002",
            embedding=embedding,
            metadata=metadata
        )
        
        assert doc_id is not None
    
    def test_batch_add_datasets(self, vector_store):
        """Test batch adding datasets."""
        datasets = [
            {
                "file_identifier": "test-001",
                "embedding": [0.1] * 384,
                "metadata": {"title": "Test 1", "text_content": "Test 1"}
            },
            {
                "file_identifier": "test-002",
                "embedding": [0.2] * 384,
                "metadata": {"title": "Test 2", "text_content": "Test 2"}
            },
            {
                "file_identifier": "test-003",
                "embedding": [0.3] * 384,
                "metadata": {"title": "Test 3", "text_content": "Test 3"}
            }
        ]
        
        ids = vector_store.add_datasets(datasets)
        assert len(ids) == 3
        assert all(id.startswith("dataset_") for id in ids)
    
    def test_batch_add_empty_list(self, vector_store):
        """Test batch add with empty list."""
        ids = vector_store.add_datasets([])
        assert len(ids) == 0
    
    def test_get_dataset_count_empty(self, vector_store):
        """Test getting count on empty store."""
        count = vector_store.get_dataset_count()
        assert count == 0
    
    def test_get_dataset_count_after_add(self, vector_store):
        """Test count after adding datasets."""
        datasets = [
            {
                "file_identifier": f"test-{i:03d}",
                "embedding": [0.1 * i] * 384,
                "metadata": {"title": f"Test {i}", "text_content": f"Test {i}"}
            }
            for i in range(5)
        ]
        
        vector_store.add_datasets(datasets)
        count = vector_store.get_dataset_count()
        assert count == 5
    
    def test_search_datasets_empty_store(self, vector_store):
        """Test searching empty store."""
        query_embedding = [0.1] * 384
        results = vector_store.search_datasets(query_embedding, limit=10)
        assert len(results) == 0
    
    def test_search_datasets_returns_results(self, vector_store):
        """Test that search returns results."""
        # Add some test data
        datasets = [
            {
                "file_identifier": "test-001",
                "embedding": [0.1] * 384,
                "metadata": {"title": "Climate Data", "text_content": "Climate"}
            },
            {
                "file_identifier": "test-002",
                "embedding": [0.15] * 384,
                "metadata": {"title": "Temperature", "text_content": "Temperature"}
            }
        ]
        vector_store.add_datasets(datasets)
        
        # Search with similar embedding
        query_embedding = [0.12] * 384
        results = vector_store.search_datasets(query_embedding, limit=10)
        
        assert len(results) > 0
        assert "similarity_score" in results[0]
        assert "metadata" in results[0]
        assert 0 <= results[0]["similarity_score"] <= 1
    
    def test_search_results_sorted_by_relevance(self, vector_store):
        """Test that search results are sorted by relevance (descending)."""
        datasets = [
            {
                "file_identifier": f"test-{i:03d}",
                "embedding": [0.1 + i * 0.05] * 384,
                "metadata": {"title": f"Test {i}", "text_content": f"Test {i}"}
            }
            for i in range(5)
        ]
        vector_store.add_datasets(datasets)
        
        query_embedding = [0.2] * 384
        results = vector_store.search_datasets(query_embedding, limit=10)
        
        # Check results are sorted by similarity (descending)
        scores = [r["similarity_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_search_with_limit(self, vector_store):
        """Test that search respects limit parameter."""
        datasets = [
            {
                "file_identifier": f"test-{i:03d}",
                "embedding": [0.1] * 384,
                "metadata": {"title": f"Test {i}", "text_content": f"Test {i}"}
            }
            for i in range(20)
        ]
        vector_store.add_datasets(datasets)
        
        query_embedding = [0.1] * 384
        results = vector_store.search_datasets(query_embedding, limit=5)
        
        assert len(results) <= 5
    
    def test_add_supporting_document(self, vector_store):
        """Test adding supporting document chunk."""
        doc_id = vector_store.add_supporting_document(
            doc_id="doc-001-chunk-0",
            embedding=[0.1] * 384,
            metadata={
                "dataset_id": 1,
                "document_url": "http://example.com/doc.pdf",
                "title": "Supporting Doc"
            },
            text_chunk="This is a chunk of text from the supporting document"
        )
        
        assert doc_id == "doc_doc-001-chunk-0"
    
    def test_search_supporting_docs(self, vector_store):
        """Test searching supporting documents."""
        # Add some supporting docs
        for i in range(3):
            vector_store.add_supporting_document(
                doc_id=f"doc-{i:03d}-chunk-0",
                embedding=[0.1 + i * 0.05] * 384,
                metadata={
                    "dataset_id": i,
                    "document_url": f"http://example.com/doc-{i}.pdf",
                    "title": f"Doc {i}"
                },
                text_chunk=f"Text chunk {i}"
            )
        
        query_embedding = [0.15] * 384
        results = vector_store.search_supporting_docs(query_embedding, limit=10)
        
        assert len(results) > 0
        assert all("metadata" in r for r in results)
    
    def test_delete_dataset(self, vector_store):
        """Test deleting dataset."""
        # Add dataset
        vector_store.add_dataset(
            file_identifier="test-001",
            embedding=[0.1] * 384,
            metadata={"title": "Test", "text_content": "Test"}
        )
        
        assert vector_store.get_dataset_count() == 1
        
        # Delete it
        vector_store.delete_dataset("test-001")
        
        assert vector_store.get_dataset_count() == 0
    
    def test_get_supporting_docs_count(self, vector_store):
        """Test getting supporting docs count."""
        assert vector_store.get_supporting_docs_count() == 0
        
        vector_store.add_supporting_document(
            doc_id="doc-001",
            embedding=[0.1] * 384,
            metadata={"dataset_id": 1},
            text_chunk="Test"
        )
        
        assert vector_store.get_supporting_docs_count() == 1


class TestVectorStoreErrors:
    """Test error handling."""
    
    def test_search_invalid_results_format(self, vector_store):
        """Test handling of edge cases in result transformation."""
        # Empty result should not crash
        results = vector_store._transform_query_results({
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "documents": [[]]
        })
        
        assert results == []
    
    def test_similarity_score_normalization(self, vector_store):
        """Test that similarity scores are normalized to 0-1."""
        # Add dataset
        vector_store.add_dataset(
            file_identifier="test-001",
            embedding=[0.5] * 384,
            metadata={"title": "Test", "text_content": "Test"}
        )
        
        # Search with same embedding (distance = 0, similarity = 1)
        results = vector_store.search_datasets([0.5] * 384, limit=1)
        
        assert len(results) > 0
        assert 0 <= results[0]["similarity_score"] <= 1
        assert results[0]["similarity_score"] > 0.9  # Should be very similar
