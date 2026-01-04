"""
Embeddings Module - Vector Store and Semantic Search Support

This module provides comprehensive embedding and vector storage capabilities
for semantic search and RAG (Retrieval-Augmented Generation).

Components:
    - EmbeddingService: Generates embeddings using sentence-transformers
    - VectorStore: Manages ChromaDB vector database with persistent storage
    - DocumentChunking: Splits documents into searchable chunks
    - IndexingService: Orchestrates embedding and indexing of datasets

Usage:
    from src.services.embeddings import EmbeddingService, VectorStore, IndexingService
    
    # Initialize services
    embedding_service = EmbeddingService(model_name="all-MiniLM-L6-v2")
    vector_store = VectorStore(persist_dir="./data/chroma")
    
    # Generate embedding
    embedding = await embedding_service.generate_embedding("Dataset title and abstract")
    
    # Store in vector database
    vector_store.add_dataset(
        file_identifier="abc123",
        title="Dataset Title",
        abstract="Abstract text",
        embedding=embedding
    )
    
    # Index datasets
    indexing_service = IndexingService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        database=db
    )
    await indexing_service.index_all_datasets()
"""

from .embedding_service import (
    EmbeddingService,
    EmbeddingConfig,
    TextChunker,
)
from .vector_store import (
    VectorStore,
    VectorStoreError,
)
from .indexing_service import (
    IndexingService,
    IndexingProgress,
)

__all__ = [
    # Embedding Service
    "EmbeddingService",
    "EmbeddingConfig",
    "TextChunker",
    # Vector Store
    "VectorStore",
    "VectorStoreError",
    # Indexing Service
    "IndexingService",
    "IndexingProgress",
]
