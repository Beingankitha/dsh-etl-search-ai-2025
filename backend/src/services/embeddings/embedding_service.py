"""
Embedding Service - Vector Embedding Generation

This module handles generation of vector embeddings for dataset metadata
and supporting document content using sentence-transformers.

Architecture:
    - EmbeddingService: High-level API for generating embeddings
    - TextChunker: Split large documents into overlapping chunks
    - EmbeddingConfig: Configuration container (dataclass)
    - Follows Single Responsibility Principle
    - Supports batch processing for efficiency

Features:
    - Batch embedding generation (memory efficient)
    - Device selection (CPU/GPU)
    - Configurable model selection
    - Text chunking with overlap for RAG
    - Error handling with detailed logging
    - Observability with tracing spans

Usage Example:
    from src.services.embeddings import EmbeddingService, TextChunker
    
    # Initialize service
    service = EmbeddingService(model_name="all-MiniLM-L6-v2", device="cpu")
    
    # Single embedding
    text = "Climate dataset for UK"
    vector = service.embed_text(text)
    
    # Batch embeddings
    texts = ["Text 1", "Text 2", "Text 3"]
    vectors = service.embed_texts(texts)
    
    # Chunk text for RAG
    chunker = TextChunker(chunk_size=1000, overlap=200)
    chunks = chunker.chunk_text(long_document)
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

# Lazy initialize tracer to avoid issues in tests
_tracer = None


def get_tracer_instance():
    """Get tracer instance lazily."""
    global _tracer
    if _tracer is None:
        try:
            from src.services.observability import get_tracer
            _tracer = get_tracer(__name__)
        except Exception:
            # Tracing not available
            _tracer = None
    return _tracer


class _DummySpan:
    """Dummy span for when tracing is not available."""
    
    def start_as_current_span(self, name):
        """Return a no-op context manager."""
        return _DummySpanContext()


class _DummySpanContext:
    """Dummy span context."""
    
    def __enter__(self):
        """No-op enter."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """No-op exit."""
        pass
    
    def set_attribute(self, key, value):
        """No-op set attribute."""
        pass


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model_name: str = settings.embedding_model
    batch_size: int = settings.embedding_batch_size
    device: str = settings.embedding_device
    show_progress_bar: bool = False


class EmbeddingService:
    """
    Generate embeddings for text using sentence-transformers.
    
    This service wraps the SentenceTransformer model and provides:
    - Single and batch embedding generation
    - Memory-efficient batch processing
    - Proper error handling and logging
    - Embedding dimension query
    
    Design Pattern: Facade
    - Simplifies SentenceTransformer API
    - Provides consistent interface
    - Handles configuration and lifecycle
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize embedding service.
        
        Args:
            config: EmbeddingConfig instance. If None, uses defaults from settings.
        
        Raises:
            RuntimeError: If model fails to load
        """
        self.config = config or EmbeddingConfig()
        self._model: Optional[SentenceTransformer] = None
        self._embedding_dim: Optional[int] = None
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """
        Initialize the embedding model.
        
        Downloads model from Hugging Face if not cached locally.
        Uses settings for model name and device.
        
        Raises:
            RuntimeError: If model initialization fails
        """
        try:
            logger.info(
                f"Loading embedding model: {self.config.model_name} "
                f"on device: {self.config.device}"
            )
            
            self._model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device,
                trust_remote_code=False
            )
            
            # Cache embedding dimension
            self._embedding_dim = self._model.get_sentence_embedding_dimension()
            
            logger.info(
                f"✓ Embedding model loaded successfully. "
                f"Dimension: {self._embedding_dim}"
            )
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Embedding model initialization failed: {e}") from e
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
            
        Raises:
            ValueError: If text is None or empty
            RuntimeError: If embedding generation fails
        """
        if not text or not isinstance(text, str):
            logger.warning(f"Invalid text provided for embedding: {type(text)}")
            # Return zero vector instead of raising
            return np.zeros(self._embedding_dim or 384)
        
        text = text.strip()
        if not text:
            return np.zeros(self._embedding_dim or 384)
        
        try:
            with (get_tracer_instance() or _DummySpan()).start_as_current_span("embed_text") as span:
                span.set_attribute("text_length", len(text))
                
                embeddings = self._model.encode(
                    text,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                
                span.set_attribute("embedding_dim", len(embeddings))
                return embeddings
                
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            raise RuntimeError(f"Text embedding failed: {e}") from e
    
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts (batch operation).
        
        Batch processing provides better memory efficiency and throughput
        compared to embedding texts individually.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            ValueError: If texts is not a list
            RuntimeError: If batch embedding fails
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding")
            return []
        
        if not isinstance(texts, list):
            raise ValueError(f"Expected list, got {type(texts)}")
        
        try:
            with (get_tracer_instance() or _DummySpan()).start_as_current_span("embed_texts_batch") as span:
                # Identify which texts are empty (need special handling)
                empty_indices = []
                clean_texts = []
                
                for i, t in enumerate(texts):
                    clean_text = t.strip() if isinstance(t, str) else ""
                    if not clean_text:
                        empty_indices.append(i)
                    clean_texts.append(clean_text)
                
                text_count = len([t for t in clean_texts if t])
                
                span.set_attribute("total_texts", len(texts))
                span.set_attribute("non_empty_texts", text_count)
                span.set_attribute("batch_size", self.config.batch_size)
                
                logger.info(
                    f"Generating embeddings for {text_count} texts "
                    f"(batch size: {self.config.batch_size})"
                )
                
                embeddings = self._model.encode(
                    clean_texts,
                    batch_size=self.config.batch_size,
                    show_progress_bar=self.config.show_progress_bar,
                    convert_to_numpy=True
                )
                
                # Replace empty string embeddings with zero vectors
                for idx in empty_indices:
                    embeddings[idx] = np.zeros(self._embedding_dim or 384)
                
                logger.info(f"✓ Generated {len(embeddings)} embeddings")
                span.set_attribute("embeddings_generated", len(embeddings))
                
                return [emb for emb in embeddings]
                
        except Exception as e:
            logger.error(f"Error batch embedding texts: {e}")
            raise RuntimeError(f"Batch embedding failed: {e}") from e
    
    def get_embedding_dimension(self) -> int:
        """
        Get dimension of embeddings produced by model.
        
        Returns:
            Embedding dimension (e.g., 384 for all-MiniLM-L6-v2)
        """
        return self._embedding_dim or 384


class TextChunker:
    """
    Split text into overlapping chunks for RAG.
    
    Rationale:
    - LLMs have token limits, so long documents must be chunked
    - Overlapping chunks preserve context at boundaries
    - Configurable chunk size and overlap for different use cases
    
    Design Pattern: Strategy
    - Encapsulates chunking algorithm
    - Supports different chunk sizes
    - Can be replaced with other chunking strategies (e.g., sentence-level)
    """
    
    def __init__(
        self,
        chunk_size: int = settings.text_chunk_size,
        overlap: int = settings.text_chunk_overlap
    ):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
            
        Raises:
            ValueError: If overlap >= chunk_size
        """
        if overlap >= chunk_size:
            raise ValueError(
                f"Overlap ({overlap}) must be less than chunk_size ({chunk_size})"
            )
        
        self.chunk_size = chunk_size
        self.overlap = overlap
        logger.info(
            f"TextChunker initialized: chunk_size={chunk_size}, overlap={overlap}"
        )
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Algorithm:
        1. Start at position 0
        2. Extract chunk_size characters
        3. Move forward by (chunk_size - overlap) characters
        4. Repeat until end of text
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks (stripped)
        """
        if not text or not isinstance(text, str):
            logger.warning(f"Invalid text for chunking: {type(text)}")
            return []
        
        text = text.strip()
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + self.chunk_size, len(text))
            
            # Extract chunk and strip whitespace
            chunk = text[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            
            # Move start position (with overlap)
            start = end - self.overlap
        
        logger.debug(
            f"Chunked text into {len(chunks)} chunks "
            f"(size={self.chunk_size}, overlap={self.overlap})"
        )
        return chunks
    
    def chunk_texts_with_source(
        self,
        texts: List[tuple]
    ) -> List[tuple]:
        """
        Chunk multiple texts while tracking source.
        
        Args:
            texts: List of (text, source_id) tuples
            
        Returns:
            List of (chunk, source_id) tuples
        """
        chunked = []
        for text, source_id in texts:
            chunks = self.chunk_text(text)
            for chunk in chunks:
                chunked.append((chunk, source_id))
        
        logger.info(
            f"Chunked {len(texts)} texts into {len(chunked)} chunks with source tracking"
        )
        return chunked


__all__ = [
    "EmbeddingService",
    "TextChunker",
    "EmbeddingConfig",
]
