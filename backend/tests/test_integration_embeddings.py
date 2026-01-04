"""
Integration test for Embedding Service with ETL Pipeline (Issue 7).

Tests the complete flow:
1. Create sample datasets in database
2. Generate embeddings
3. Index into vector store
4. Search and verify results

Run this to verify Issue 7 integration before committing.
"""

import tempfile
import pytest
from pathlib import Path
from datetime import datetime

from src.infrastructure import Database
from src.repositories import UnitOfWork
from src.models import DatasetEntity
from src.services.embeddings import EmbeddingService, VectorStore, IndexingService
from src.config import settings


@pytest.fixture
def temp_database():
    """Create temporary database for integration test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        db.connect()
        db.create_tables()
        yield db
        db.close()


@pytest.fixture
def temp_vector_store():
    """Create temporary vector store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield VectorStore(persist_dir=tmpdir)


class TestEmbeddingIntegration:
    """Integration tests for embedding service with ETL pipeline."""
    
    def test_embedding_service_initialization(self):
        """Test that embedding service initializes without errors."""
        service = EmbeddingService()
        assert service._model is not None
        assert service._embedding_dim == 384
        print("✓ EmbeddingService initialized successfully")
    
    def test_single_text_embedding(self):
        """Test embedding a single text."""
        service = EmbeddingService()
        text = "Climate dataset for UK temperature measurements"
        embedding = service.embed_text(text)
        
        assert embedding is not None
        assert len(embedding) == 384
        assert embedding.dtype in [float, 'float32', 'float64']
        print(f"✓ Single embedding generated: {len(embedding)}-dim")
    
    def test_batch_embedding(self):
        """Test batch embedding of multiple texts."""
        service = EmbeddingService()
        texts = [
            "Climate dataset for UK",
            "Temperature measurements",
            "Biodiversity in UK",
        ]
        embeddings = service.embed_texts(texts)
        
        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)
        print(f"✓ Batch embeddings generated: {len(embeddings)} texts")
    
    def test_vector_store_operations(self):
        """Test vector store add and search operations."""
        store = VectorStore()
        
        # Add test dataset
        embedding = [0.1] * 384
        store.add_dataset(
            file_identifier="test-001",
            embedding=embedding,
            metadata={
                "title": "Test Climate Dataset",
                "abstract": "UK climate data",
                "text_content": "Test Climate Dataset UK climate data"
            }
        )
        
        count = store.get_dataset_count()
        assert count >= 1
        print(f"✓ Vector store has {count} dataset(s)")
        
        # Search
        results = store.search_datasets(embedding, limit=5)
        assert len(results) > 0
        assert "similarity_score" in results[0]
        print(f"✓ Search returned {len(results)} result(s)")
    
    def test_indexing_with_sample_data(self, temp_database):
        """Test indexing sample datasets from database."""
        # Create sample datasets in database
        with UnitOfWork(temp_database) as uow:
            # Create first dataset
            ds1 = DatasetEntity(
                file_identifier="uk-climate-001",
                title="UK Climate Data 2020-2024",
                abstract="Comprehensive climate measurements across UK regions",
                topic_category="climatology",
                keywords=["climate", "temperature", "UK", "weather"],
                lineage="Collected from Met Office",
                supplemental_info="Quality assured data"
            )
            uow.datasets.insert(ds1)
            
            # Create second dataset
            ds2 = DatasetEntity(
                file_identifier="uk-biodiversity-001",
                title="UK Biodiversity Survey",
                abstract="Species distribution and abundance across UK habitats",
                topic_category="biota",
                keywords=["biodiversity", "species", "habitat", "UK"],
                lineage="Partnership with Wildlife Trust",
                supplemental_info="Long-term monitoring data"
            )
            uow.datasets.insert(ds2)
            
            # Create third dataset
            ds3 = DatasetEntity(
                file_identifier="uk-soil-001",
                title="UK Soil Properties Database",
                abstract="Soil composition and characteristics",
                topic_category="geology",
                keywords=["soil", "geology", "composition"],
                lineage="BGS Survey",
                supplemental_info="Standardized measurements"
            )
            uow.datasets.insert(ds3)
            
            uow.commit()
        
        print(f"✓ Created 3 sample datasets in database")
        
        # Now test indexing with TEMPORARY vector store (not persistent one)
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            embedding_service = EmbeddingService()
            vector_store = VectorStore(persist_dir=tmpdir)  # Use temporary vector store
            indexing_service = IndexingService(
                database=temp_database,
                embedding_service=embedding_service,
                vector_store=vector_store,
                extract_supporting_docs=False  # Skip for this test
            )
            
            # Run indexing
            progress = indexing_service.index_all_datasets(supporting_docs=False)
            
            assert progress.total_datasets == 3
            assert progress.total_indexed == 3
            assert progress.success_rate == 100.0
            print(f"✓ Indexed {progress.total_indexed}/{progress.total_datasets} datasets")
            print(f"✓ Success rate: {progress.success_rate:.1f}%")
            
            # Verify vector store has embeddings
            count = vector_store.get_dataset_count()
            assert count == 3, f"Expected 3 embeddings, got {count}"
            print(f"✓ Vector store contains {count} embeddings")
            
            # Test search
            query_text = "Climate and weather data"
            query_embedding = embedding_service.embed_text(query_text)
            results = vector_store.search_datasets(query_embedding, limit=5)
            
            assert len(results) > 0
            # First result should be climate dataset (highest similarity)
            assert "climate" in results[0]["metadata"]["title"].lower()
            print(f"✓ Search query returned {len(results)} results")
            print(f"  Top result: {results[0]['metadata']['title']}")
            print(f"  Similarity: {results[0]['similarity_score']:.3f}")
    
    def test_semantic_search_accuracy(self, temp_database):
        """Test that semantic search returns semantically relevant results."""
        # Create diverse datasets
        with UnitOfWork(temp_database) as uow:
            datasets = [
                DatasetEntity(
                    file_identifier="dataset-001",
                    title="Arctic Temperature Records",
                    abstract="Historical temperature data from Arctic regions",
                    topic_category="climatology",
                    keywords=["arctic", "temperature", "climate"]
                ),
                DatasetEntity(
                    file_identifier="dataset-002",
                    title="Tropical Rainforest Biodiversity",
                    abstract="Species inventory in tropical rainforest ecosystems",
                    topic_category="biota",
                    keywords=["rainforest", "biodiversity", "species"]
                ),
                DatasetEntity(
                    file_identifier="dataset-003",
                    title="Antarctic Ice Core Analysis",
                    abstract="Ice core samples from Antarctica showing climate history",
                    topic_category="climatology",
                    keywords=["antarctica", "ice", "climate", "paleoclimate"]
                ),
            ]
            for ds in datasets:
                uow.datasets.insert(ds)
            uow.commit()
        
        # Index datasets
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        indexing_service = IndexingService(
            database=temp_database,
            embedding_service=embedding_service,
            vector_store=vector_store,
            extract_supporting_docs=False
        )
        indexing_service.index_all_datasets(supporting_docs=False)
        
        # Search for climate-related query
        query = "Climate change and global warming"
        query_embedding = embedding_service.embed_text(query)
        results = vector_store.search_datasets(query_embedding, limit=3)
        
        # Should return climate datasets with good scores
        assert len(results) > 0
        # Top results should be climate-related
        top_result_title = results[0]["metadata"]["title"].lower()
        assert "climate" in top_result_title or "arctic" in top_result_title or "antarctic" in top_result_title
        print(f"✓ Semantic search returned relevant dataset: {results[0]['metadata']['title']}")
        print(f"  Similarity: {results[0]['similarity_score']:.3f}")
        
        # Search for biodiversity
        query2 = "Species and ecosystem diversity"
        query_embedding2 = embedding_service.embed_text(query2)
        results2 = vector_store.search_datasets(query_embedding2, limit=3)
        
        # Should find biodiversity-related dataset
        assert any("biodiversity" in r["metadata"]["title"].lower() for r in results2)
        print(f"✓ Semantic search correctly identified biodiversity dataset in top results")


class TestIntegrationWithRealData:
    """Test integration with actual database data (if available)."""
    
    def test_index_existing_datasets(self, temp_database):
        """Test indexing datasets already in the database."""
        # Check if database has any datasets
        with UnitOfWork(temp_database) as uow:
            datasets = uow.datasets.get_all()
        
        if not datasets:
            pytest.skip("No datasets in database")
        
        print(f"Found {len(datasets)} datasets in database")
        
        # Index them
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        indexing_service = IndexingService(
            database=temp_database,
            embedding_service=embedding_service,
            vector_store=vector_store
        )
        
        progress = indexing_service.index_all_datasets()
        
        print(f"✓ Indexed {progress.total_indexed} datasets")
        if progress.errors:
            print(f"⚠ {len(progress.errors)} errors encountered")
            for error in progress.errors[:3]:
                print(f"  - {error}")


class TestPerformance:
    """Performance and efficiency tests."""
    
    def test_batch_embedding_vs_single(self):
        """Compare batch vs single embedding performance."""
        import time
        
        service = EmbeddingService()
        texts = [
            f"Dataset description number {i} with climate data for region {i}"
            for i in range(10)
        ]
        
        # Single embeddings
        start = time.time()
        for text in texts:
            service.embed_text(text)
        single_time = time.time() - start
        
        # Batch embeddings
        start = time.time()
        service.embed_texts(texts)
        batch_time = time.time() - start
        
        efficiency = single_time / batch_time
        print(f"✓ Single: {single_time:.2f}s, Batch: {batch_time:.2f}s (efficiency: {efficiency:.1f}x)")
        assert batch_time < single_time, "Batch should be faster than single"
    
    def test_large_batch_efficiency(self):
        """Test efficiency with larger batch sizes."""
        service = EmbeddingService()
        
        # Create 100 texts
        texts = [
            f"Climate and temperature measurement {i}: Details about weather patterns in region {i%10}"
            for i in range(100)
        ]
        
        import time
        start = time.time()
        embeddings = service.embed_texts(texts)
        elapsed = time.time() - start
        
        assert len(embeddings) == 100
        avg_time_per_text = (elapsed / 100) * 1000
        print(f"✓ Embedded 100 texts in {elapsed:.2f}s ({avg_time_per_text:.1f}ms per text)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
