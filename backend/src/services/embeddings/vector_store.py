"""
Vector Store Module - ChromaDB Integration for Semantic Search

This module manages the vector store using ChromaDB for persistent storage
and retrieval of dataset embeddings and supporting document content.

Architecture:
    - VectorStore: Main interface for vector store operations
    - CollectionManager: Manages ChromaDB collections lifecycle
    - Supports two collections: 'datasets' and 'supporting_documents'
    - Persistent storage with configurable path
    
Design Patterns:
    - Facade: Simplifies ChromaDB API
    - Repository: Manages persistent storage
    - Singleton: Optional for shared instance
    
Features:
    - Persistent ChromaDB storage with parquet backend
    - Multiple collections with independent schemas
    - Batch operations for efficiency
    - Metadata association for retrieval
    - Search with similarity scoring (0-1 normalized)
    - Collection management (create, delete, exists)
    - Error recovery and logging

Usage Example:
    from src.services.vector_store import VectorStore
    
    # Initialize
    store = VectorStore(persist_dir="./data/chroma")
    
    # Add dataset embedding
    embedding = [0.1, 0.2, ...]  # 384-dim for all-MiniLM-L6-v2
    store.add_dataset(
        file_identifier="dataset-001",
        embedding=embedding,
        metadata={"title": "Climate Data", "abstract": "UK climate..."}
    )
    
    # Search
    results = store.search_datasets(query_embedding, limit=10)
    for result in results:
        print(f"Score: {result['similarity_score']:.3f}")
        print(f"Title: {result['metadata']['title']}")
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

# Tracing is optional
def _get_dummy_span():
    """Get dummy span for no-op tracing."""
    class DummySpan:
        def start_as_current_span(self, name):
            class DummyContext:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def set_attribute(self, k, v): pass
            return DummyContext()
    return DummySpan()


try:
    from src.services.observability import get_tracer
    tracer = get_tracer(__name__)
except Exception:
    tracer = _get_dummy_span()


# Dummy context for span decoration
class _with_span:
    """No-op context manager for tracing."""
    def __init__(self, name):
        self.name = name
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


def with_span(name):
    """Decorator for tracing (no-op if tracing unavailable)."""
    def decorator(func):
        return func
    return decorator


class VectorStoreError(Exception):
    """Vector store specific errors."""
    pass


class VectorStore:
    """
    Main interface for vector store operations using ChromaDB.
    
    Manages persistent vector storage with two collections:
    1. 'datasets': Embeddings for dataset metadata (title + abstract + keywords)
    2. 'supporting_documents': Embeddings for document chunks with RAG content
    
    Both collections use cosine distance for similarity search.
    """
    
    def __init__(self, persist_dir: Optional[str] = None):
        """
        Initialize vector store with persistent storage.
        
        Args:
            persist_dir: Directory for persistent storage.
                        If None, uses config value (default: ./data/chroma).
                        
        Raises:
            VectorStoreError: If initialization fails
        """
        self.persist_dir = Path(persist_dir or settings.chroma_path)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Initializing ChromaDB with persist_dir: {self.persist_dir}")
            
            # Create ChromaDB client with persistent storage using new API
            # New ChromaDB (0.5+) uses persistent_client instead of Settings
            self.client = chromadb.PersistentClient(path=str(self.persist_dir))
            
            # Initialize collections
            self._datasets_collection: Optional[Any] = None
            self._supporting_docs_collection: Optional[Any] = None
            
            self._initialize_collections()
            logger.info("✓ Vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise VectorStoreError(f"Vector store initialization failed: {e}") from e
    
    def _initialize_collections(self) -> None:
        """
        Initialize or retrieve ChromaDB collections.
        
        Creates two collections if they don't exist:
        1. 'datasets': For dataset metadata embeddings
        2. 'supporting_documents': For supporting document chunks
        
        Both use cosine distance metric.
        
        Raises:
            VectorStoreError: If collection creation fails
        """
        try:
            # Get or create datasets collection
            # New ChromaDB API: distance_function in metadata instead of parameter
            self._datasets_collection = self.client.get_or_create_collection(
                name="datasets",
                metadata={
                    "description": "Dataset metadata embeddings",
                    "version": "1.0",
                    "hnsw:space": "cosine"
                }
            )
            logger.info("✓ Datasets collection ready")
            
            # Get or create supporting documents collection
            self._supporting_docs_collection = self.client.get_or_create_collection(
                name="supporting_documents",
                metadata={
                    "description": "Supporting document content embeddings for RAG",
                    "version": "1.0",
                    "hnsw:space": "cosine"
                }
            )
            logger.info("✓ Supporting documents collection ready")
            
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            raise VectorStoreError(f"Collection initialization failed: {e}") from e
    
    @with_span("add_dataset")
    def add_dataset(
        self,
        file_identifier: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Add dataset embedding to vector store.
        
        The document ID is deterministic: 'dataset_{file_identifier}'
        This allows for idempotent upsert operations.
        
        Args:
            file_identifier: Unique dataset identifier from CEH catalogue
            embedding: Vector embedding (list of floats, e.g., 384-dim)
            metadata: Associated metadata dict:
                - file_identifier: Unique ID
                - title: Dataset title
                - abstract: Dataset abstract
                - keywords: Space-separated keywords
                - topic_category: Primary topic
                - text_content: Combined text for full-text search
                
        Returns:
            Document ID (str)
            
        Raises:
            VectorStoreError: If add operation fails
        """
        try:
            doc_id = f"dataset_{file_identifier}"
            
            # Ensure metadata is serializable
            if not isinstance(metadata, dict):
                raise ValueError("Metadata must be a dictionary")
            
            self._datasets_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[metadata.get("text_content", "")]
            )
            
            logger.debug(f"Added dataset to vector store: {file_identifier}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add dataset {file_identifier}: {e}")
            raise VectorStoreError(f"Failed to add dataset: {e}") from e
    
    @with_span("add_datasets_batch")
    def add_datasets(self, datasets: List[Dict[str, Any]]) -> List[str]:
        """
        Batch add dataset embeddings (efficient for large number of datasets).
        
        Args:
            datasets: List of dicts, each with keys:
                - file_identifier: Unique ID
                - embedding: Vector embedding
                - metadata: Dict with title, abstract, etc.
                
        Returns:
            List of document IDs
            
        Raises:
            VectorStoreError: If batch operation fails
        """
        if not datasets:
            logger.warning("Empty dataset list provided")
            return []
        
        try:
            ids = [f"dataset_{d['file_identifier']}" for d in datasets]
            embeddings = [d['embedding'] for d in datasets]
            metadatas = [d['metadata'] for d in datasets]
            documents = [d['metadata'].get('text_content', '') for d in datasets]
            
            self._datasets_collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            
            logger.info(f"✓ Added {len(ids)} datasets to vector store")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to batch add datasets: {e}")
            raise VectorStoreError(f"Batch add failed: {e}") from e
    
    @with_span("add_supporting_document")
    def add_supporting_document(
        self,
        doc_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        text_chunk: str
    ) -> str:
        """
        Add supporting document chunk to vector store for RAG.
        
        Document chunks are linked back to datasets via metadata.
        Enables filtering queries to specific datasets and retrieval
        of full chunk content.
        
        Args:
            doc_id: Unique document chunk identifier
            embedding: Vector embedding of chunk
            metadata: Dict with:
                - dataset_id: Foreign key to dataset
                - dataset_file_identifier: For reference
                - document_url: Source document URL
                - title: Document title
                - file_extension: pdf, docx, etc.
                - chunk_index: Which chunk this is
            text_chunk: Full text of the chunk
            
        Returns:
            Document ID used in vector store
            
        Raises:
            VectorStoreError: If add fails
        """
        try:
            full_id = f"doc_{doc_id}"
            
            self._supporting_docs_collection.add(
                ids=[full_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text_chunk]
            )
            
            logger.debug(f"Added supporting document: {full_id}")
            return full_id
            
        except Exception as e:
            logger.error(f"Failed to add supporting document {doc_id}: {e}")
            raise VectorStoreError(f"Failed to add supporting document: {e}") from e
    
    @with_span("search_datasets")
    def search_datasets(
        self,
        query_embedding: List[float],
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search datasets by embedding similarity.
        
        Uses cosine distance similarity. Returns results ranked by relevance.
        
        Args:
            query_embedding: Query embedding vector (384-dim)
            limit: Maximum results to return (default: 10)
            where: ChromaDB where filter for metadata (optional)
                   E.g., {"topic_category": {"$eq": "climate"}}
            
        Returns:
            List of search results sorted by relevance (descending):
            [
                {
                    "id": "dataset_xyz",
                    "similarity_score": 0.95,  # 0-1, higher is better
                    "metadata": {...},
                    "content": "..."
                },
                ...
            ]
            
        Raises:
            VectorStoreError: If search fails
        """
        try:
            results = self._datasets_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where,
                include=["distances", "metadatas", "documents"]
            )
            
            return self._transform_query_results(results)
            
        except Exception as e:
            logger.error(f"Failed to search datasets: {e}")
            raise VectorStoreError(f"Dataset search failed: {e}") from e
    
    @with_span("search_supporting_docs")
    def search_supporting_docs(
        self,
        query_embedding: List[float],
        limit: int = 10,
        dataset_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search supporting documents by embedding similarity.
        
        Can filter to specific dataset for focused retrieval.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum results (default: 10)
            dataset_id: Filter by dataset ID (optional)
            
        Returns:
            List of search results with text chunks
            
        Raises:
            VectorStoreError: If search fails
        """
        try:
            where = None
            if dataset_id is not None:
                where = {"dataset_id": {"$eq": dataset_id}}
            
            results = self._supporting_docs_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where,
                include=["distances", "metadatas", "documents"]
            )
            
            return self._transform_query_results(results)
            
        except Exception as e:
            logger.error(f"Failed to search supporting documents: {e}")
            raise VectorStoreError(f"Supporting docs search failed: {e}") from e
    
    def _transform_query_results(self, chroma_results: Dict) -> List[Dict[str, Any]]:
        """
        Transform ChromaDB query results to user-friendly format.
        
        Converts cosine distances (0-2 range) to similarity scores (0-1 range).
        Higher similarity is better.
        
        Args:
            chroma_results: Raw ChromaDB query results
            
        Returns:
            Formatted results list with similarity_score, metadata, content
        """
        if not chroma_results["ids"] or not chroma_results["ids"][0]:
            return []
        
        results = []
        ids = chroma_results["ids"][0]
        distances = chroma_results["distances"][0]
        metadatas = chroma_results["metadatas"][0]
        documents = chroma_results["documents"][0]
        
        for doc_id, distance, metadata, document in zip(
            ids, distances, metadatas, documents
        ):
            # Convert cosine distance to similarity (0-1, higher is better)
            # Cosine distance: 0 = identical, 2 = opposite
            # Cosine similarity: 1 - (distance / 2)
            # Clamp to [0, 1] to handle floating point precision issues
            similarity = max(0.0, min(1.0, 1 - (distance / 2)))
            
            results.append({
                "id": doc_id,
                "similarity_score": similarity,
                "metadata": metadata,
                "content": document
            })
        
        return results
    
    def delete_dataset(self, file_identifier: str) -> None:
        """
        Delete dataset from vector store.
        
        Args:
            file_identifier: Dataset to delete
            
        Raises:
            VectorStoreError: If delete fails
        """
        try:
            doc_id = f"dataset_{file_identifier}"
            self._datasets_collection.delete(ids=[doc_id])
            logger.debug(f"Deleted dataset: {file_identifier}")
        except Exception as e:
            logger.error(f"Failed to delete dataset: {e}")
            raise VectorStoreError(f"Delete failed: {e}") from e
    
    def delete_supporting_document(self, doc_id: str) -> None:
        """Delete supporting document from vector store."""
        try:
            full_id = f"doc_{doc_id}"
            self._supporting_docs_collection.delete(ids=[full_id])
            logger.debug(f"Deleted supporting document: {full_id}")
        except Exception as e:
            logger.error(f"Failed to delete supporting document: {e}")
            raise VectorStoreError(f"Delete failed: {e}") from e
    
    def get_dataset_count(self) -> int:
        """Get number of datasets in vector store."""
        try:
            return self._datasets_collection.count()
        except Exception as e:
            logger.error(f"Failed to get dataset count: {e}")
            return 0
    
    def get_supporting_docs_count(self) -> int:
        """Get number of supporting document chunks in vector store."""
        try:
            return self._supporting_docs_collection.count()
        except Exception as e:
            logger.error(f"Failed to get supporting docs count: {e}")
            return 0
    
    def clear_all(self) -> None:
        """
        Clear all collections (use with caution!).
        
        Raises:
            VectorStoreError: If clear fails
        """
        try:
            self.client.delete_collection(name="datasets")
            self.client.delete_collection(name="supporting_documents")
            self._initialize_collections()
            logger.warning("⚠ Vector store cleared - all embeddings deleted")
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            raise VectorStoreError(f"Clear failed: {e}") from e


__all__ = [
    "VectorStore",
    "VectorStoreError",
]
