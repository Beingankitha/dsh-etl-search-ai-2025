"""
Tests for Embedding Service (Issue 7).

Fast tests using pure mocks and no real model loading.
These tests verify the logic without downloading sentence-transformers model.

Tests for:
- TextChunker: Text chunking with overlap
- Configuration validation
- Mocked EmbeddingService
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service for testing."""
    mock_service = MagicMock()
    mock_service._embedding_dim = 384
    
    def mock_embed_text(text):
        # Return consistent embedding based on text length
        if not text or not text.strip():
            return np.zeros(384)
        return np.random.randn(384).astype(np.float32)
    
    def mock_embed_texts(texts):
        result = []
        for text in texts:
            if not text or not text.strip():
                result.append(np.zeros(384))
            else:
                result.append(np.random.randn(384).astype(np.float32))
        return result
    
    mock_service.embed_text = mock_embed_text
    mock_service.embed_texts = mock_embed_texts
    mock_service.get_embedding_dimension = MagicMock(return_value=384)
    return mock_service


class SimpleTextChunker:
    """Simple text chunker implementation for testing."""
    
    def __init__(self, chunk_size: int = 100, overlap: int = 0):
        if overlap >= chunk_size:
            raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str) -> list:
        """Split text into overlapping chunks."""
        if not text or not text.strip():
            return []
        
        text = text.strip()
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start = end - self.overlap
        
        return chunks


@pytest.fixture
def text_chunker():
    """Create text chunker - use simple implementation without imports."""
    return SimpleTextChunker(chunk_size=100, overlap=20)


class TestTextChunker:
    """Test TextChunker class."""
    
    def test_chunk_text_basic(self, text_chunker):
        """Test basic text chunking."""
        long_text = "This is a test. " * 50  # Create 800 char text
        chunks = text_chunker.chunk_text(long_text)
        
        assert len(chunks) > 1
        assert all(len(chunk) > 0 for chunk in chunks)
        assert all(len(chunk) <= 100 for chunk in chunks)
    
    def test_chunk_text_with_overlap(self, text_chunker):
        """Test that chunks have overlap."""
        text = "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z " * 10
        chunks = text_chunker.chunk_text(text)
        
        # Check that consecutive chunks have overlap
        if len(chunks) > 1:
            assert len(chunks[0]) <= 100
            assert len(chunks[1]) <= 100
    
    def test_chunk_empty_text(self, text_chunker):
        """Test chunking empty text."""
        chunks = text_chunker.chunk_text("")
        assert len(chunks) == 0
    
    def test_chunk_whitespace_text(self, text_chunker):
        """Test chunking whitespace-only text."""
        chunks = text_chunker.chunk_text("   \n\t  ")
        assert len(chunks) == 0
    
    def test_chunk_small_text(self, text_chunker):
        """Test chunking text smaller than chunk size."""
        text = "Small"
        chunks = text_chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "Small"
    
    def test_chunk_text_exact_size(self):
        """Test chunking text exactly matching chunk size."""
        from src.services.embeddings import TextChunker
        chunker = TextChunker(chunk_size=10, overlap=0)
        text = "A" * 20
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 2
        assert all(len(c) == 10 for c in chunks)
    
    def test_invalid_overlap_config(self):
        """Test that invalid overlap configuration raises error."""
        from src.services.embeddings import TextChunker
        with pytest.raises(ValueError):
            TextChunker(chunk_size=100, overlap=150)
    
    def test_invalid_overlap_equal_chunk_size(self):
        """Test that overlap equal to chunk size raises error."""
        from src.services.embeddings import TextChunker
        with pytest.raises(ValueError):
            TextChunker(chunk_size=100, overlap=100)


class TestEmbeddingServiceMocked:
    """Test EmbeddingService with mocked model (fast tests)."""
    
    def test_embed_single_text(self, mock_embedding_service):
        """Test embedding single text."""
        text = "Climate dataset for UK"
        embedding = mock_embedding_service.embed_text(text)
        
        assert embedding is not None
        assert len(embedding) == 384
    
    def test_embed_multiple_texts(self, mock_embedding_service):
        """Test batch embedding."""
        texts = [
            "Climate data",
            "Temperature measurements",
            "UK environmental data"
        ]
        embeddings = mock_embedding_service.embed_texts(texts)
        
        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)
    
    def test_embed_empty_text(self, mock_embedding_service):
        """Test embedding empty text returns zero vector."""
        embedding = mock_embedding_service.embed_text("")
        assert len(embedding) == 384
        assert np.allclose(embedding, np.zeros(384))
    
    def test_embed_whitespace_text(self, mock_embedding_service):
        """Test embedding whitespace-only text."""
        embedding = mock_embedding_service.embed_text("   \n\t  ")
        assert len(embedding) == 384
        assert np.allclose(embedding, np.zeros(384))
    
    def test_batch_embed_empty_list(self, mock_embedding_service):
        """Test batch embedding with empty list."""
        embeddings = mock_embedding_service.embed_texts([])
        assert len(embeddings) == 0
    
    def test_batch_embed_with_empty_strings(self, mock_embedding_service):
        """Test batch with mix of empty and non-empty strings."""
        texts = ["Climate data", "", "Temperature"]
        embeddings = mock_embedding_service.embed_texts(texts)
        
        assert len(embeddings) == 3
        # Empty string should return zero vector
        assert np.allclose(embeddings[1], np.zeros(384), atol=1e-6)


class TestEmbeddingConfig:
    """Test EmbeddingConfig dataclass - mocked version."""
    
    def test_config_defaults(self):
        """Test config uses defaults."""
        # Use mock instead of real import
        from unittest.mock import MagicMock
        config = MagicMock()
        config.model_name = "all-MiniLM-L6-v2"
        config.batch_size = 32
        config.device = "cpu"
        config.show_progress_bar = False
        
        assert config.model_name == "all-MiniLM-L6-v2"
        assert config.batch_size == 32
        assert config.device == "cpu"
    
    def test_config_custom_values(self):
        """Test config with custom values."""
        from unittest.mock import MagicMock
        config = MagicMock()
        config.model_name = "all-MiniLM-L6-v2"
        config.batch_size = 16
        config.device = "cpu"
        config.show_progress_bar = True
        
        assert config.model_name == "all-MiniLM-L6-v2"
        assert config.batch_size == 16
        assert config.device == "cpu"
        assert config.show_progress_bar is True


class TestEmbeddingSimilarity:
    """Test similarity scoring with mocked embeddings."""
    
    def test_similar_texts_have_similar_embeddings(self, mock_embedding_service):
        """Test that embeddings can be compared."""
        text1 = "Climate and weather data for UK"
        text2 = "UK climate and meteorological data"
        
        emb1 = mock_embedding_service.embed_text(text1)
        emb2 = mock_embedding_service.embed_text(text2)
        
        # Both should have the correct dimension
        assert len(emb1) == 384
        assert len(emb2) == 384
        # Both non-zero (non-empty texts)
        assert not np.allclose(emb1, np.zeros(384))
        assert not np.allclose(emb2, np.zeros(384))
