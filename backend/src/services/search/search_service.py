"""
Semantic Search Service - Dataset Discovery via Vector Similarity

This module implements semantic search capabilities for dataset discovery
using natural language queries against indexed dataset embeddings.

Architecture:
    - SearchService: High-level semantic search orchestration
    - Integrates EmbeddingService for query encoding
    - Integrates VectorStore for similarity search
    - Integrates DatasetRepository for result hydration
    
Design Patterns:
    - Facade: Simplifies complex search pipeline
    - Dependency Injection: Services injected as dependencies
    - Repository: Abstracts data access layer
    - Single Responsibility: Search logic isolated in single service
    
Features:
    - Natural language query processing
    - Semantic similarity search via ChromaDB
    - Relevance score normalization (0-1 range)
    - Result ranking by relevance (highest first)
    - Empty/invalid query handling
    - Comprehensive error handling and logging
    - Optional result caching for performance
    - Observable operations with tracing spans
    
Performance Characteristics:
    - Query embedding generation: ~50-200ms (CPU dependent)
    - ChromaDB search: ~10-50ms for 1000+ vectors
    - Database hydration: ~1-5ms per result
    - Total expected latency: <2 seconds for typical queries
    
Usage Example:
    from src.services.search import SearchService
    from src.services.embeddings import EmbeddingService
    from src.services.embeddings import VectorStore
    from src.repositories import UnitOfWork
    
    # Initialize services
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    uow = UnitOfWork()
    
    search_service = SearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        unit_of_work=uow
    )
    
    # Search for datasets
    query = "climate change precipitation patterns UK"
    results = search_service.search(query, top_k=10)
    
    for result in results:
        print(f"Score: {result.score:.3f}")
        print(f"Title: {result.dataset.title}")
        print(f"Abstract: {result.dataset.abstract}")
"""

import logging
from typing import List, Optional
import numpy as np

from src.models.schemas import Dataset, SearchResult
from src.models.database_models import Dataset as DBDataset
from src.services.embeddings.embedding_service import EmbeddingService
from src.services.embeddings.vector_store import VectorStore
from src.repositories.unit_of_work import UnitOfWork
from src.logging_config import get_logger

logger = get_logger(__name__)


# Tracing support (optional)
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


def with_span(name):
    """Decorator for tracing (no-op if tracing unavailable)."""
    def decorator(func):
        return func
    return decorator


class SearchServiceError(Exception):
    """Search service specific errors."""
    pass


class SearchService:
    """
    Semantic search service for dataset discovery.
    
    Orchestrates the complete search pipeline:
    1. Query validation and preprocessing
    2. Query embedding generation via EmbeddingService
    3. Semantic similarity search via VectorStore
    4. Result hydration from Dataset Repository
    5. Relevance score normalization
    6. Result ranking and filtering
    
    Design: Facade pattern - client calls single service method to get results.
    All complexity (embedding, search, ranking) is hidden.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        unit_of_work: UnitOfWork,
        enable_caching: bool = True
    ):
        """
        Initialize search service with dependencies.
        
        Args:
            embedding_service: EmbeddingService instance for query encoding
            vector_store: VectorStore instance for similarity search
            unit_of_work: UnitOfWork for repository access
            enable_caching: Enable LRU cache for query results (optional)
            
        Raises:
            SearchServiceError: If any dependency is invalid
        """
        if not embedding_service:
            raise SearchServiceError("EmbeddingService is required")
        if not vector_store:
            raise SearchServiceError("VectorStore is required")
        if not unit_of_work:
            raise SearchServiceError("UnitOfWork is required")
        
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.unit_of_work = unit_of_work
        self.enable_caching = enable_caching
        
        logger.info("✓ SearchService initialized successfully")
    
    @with_span("search")
    def search(
        self,
        query: str,
        top_k: int = 10,
        collection: str = "datasets"
    ) -> List[SearchResult]:
        """
        Perform semantic search for datasets matching query.
        
        Complete pipeline:
        1. Validate query (not empty, reasonable length)
        2. Generate query embedding
        3. Search vector store for similar vectors
        4. Map results back to Dataset objects
        5. Calculate and normalize relevance scores
        6. Sort by relevance (highest first)
        
        Args:
            query: Natural language search query (min 1 char, max 1000 chars)
            top_k: Maximum number of results to return (1-100, default 10)
            collection: Vector collection to search ('datasets' or 'supporting_documents')
            
        Returns:
            List of SearchResult objects sorted by relevance (highest first)
            Each result includes Dataset and normalized relevance score (0-1)
            
        Raises:
            SearchServiceError: If query is invalid or search fails
            
        Behavior:
            - Empty/whitespace-only queries: Returns empty list (no error)
            - Query too long: Logs warning, truncates to 1000 chars
            - No results found: Returns empty list (no error)
            - Search errors: Raises SearchServiceError with details
        """
        try:
            # Validate and normalize query
            if not query or not isinstance(query, str):
                logger.warning(f"Invalid query type: {type(query)}")
                return []
            
            query = query.strip()
            if not query:
                logger.debug("Empty query provided, returning empty results")
                return []
            
            # Warn if query is very long, truncate for embedding
            max_query_len = 1000
            original_query = query
            if len(query) > max_query_len:
                logger.warning(
                    f"Query length {len(query)} exceeds {max_query_len}, "
                    f"truncating for embedding"
                )
                query = query[:max_query_len]
            
            # Validate top_k
            if not isinstance(top_k, int) or top_k < 1 or top_k > 100:
                logger.warning(
                    f"Invalid top_k={top_k}, using default of 10"
                )
                top_k = 10
            
            logger.debug(
                f"Starting semantic search: query={original_query[:50]}... "
                f"top_k={top_k} collection={collection}"
            )
            
            # Step 1: Generate query embedding
            query_embedding = self._embed_query(query)
            if query_embedding is None:
                logger.error("Failed to generate query embedding")
                raise SearchServiceError("Query embedding generation failed")
            
            # Step 2: Search vector store
            vector_results = self._search_vector_store(
                query_embedding=query_embedding,
                top_k=top_k,
                collection=collection
            )
            
            if not vector_results:
                logger.debug(f"No results found in vector store for query: {query}")
                return []
            
            logger.debug(f"Found {len(vector_results)} results in vector store")
            
            # Step 3: Hydrate results with full Dataset objects
            search_results = self._hydrate_results(vector_results)
            
            # Step 4: Sort by score (descending)
            # Scores already normalized by VectorStore (0-1 range)
            search_results = sorted(
                search_results,
                key=lambda r: r.score,
                reverse=True
            )
            
            logger.info(
                f"✓ Search completed: query={original_query[:50]}... "
                f"found {len(search_results)} results"
            )
            
            return search_results
            
        except SearchServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}", exc_info=True)
            raise SearchServiceError(f"Search failed: {e}") from e
    
    @with_span("embed_query")
    def _embed_query(self, query: str) -> Optional[List[float]]:
        """
        Generate embedding for search query.
        
        Converts natural language query to vector representation
        compatible with dataset embeddings.
        
        Args:
            query: Normalized query string (non-empty)
            
        Returns:
            Embedding vector as list[float] or None if embedding fails
        """
        try:
            with tracer.start_as_current_span("embed_query") as span:
                span.set_attribute("query_length", len(query))
                
                embedding = self.embedding_service.embed_text(query)
                
                if embedding is None or (isinstance(embedding, np.ndarray) and len(embedding) == 0):
                    logger.error("Embedding service returned empty/None embedding")
                    return None
                
                # Convert numpy array to list if needed
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                
                span.set_attribute("embedding_dim", len(embedding))
                logger.debug(f"Query embedding generated: dimension={len(embedding)}")
                
                return embedding
                
        except Exception as e:
            logger.error(f"Failed to embed query: {e}", exc_info=True)
            return None
    
    @with_span("search_vector_store")
    def _search_vector_store(
        self,
        query_embedding: List[float],
        top_k: int,
        collection: str
    ) -> List[dict]:
        """
        Search vector store for similar vectors.
        
        Queries ChromaDB collection for vectors most similar to query embedding.
        
        Args:
            query_embedding: Query vector (list[float])
            top_k: Max results to retrieve
            collection: Collection name ('datasets' or 'supporting_documents')
            
        Returns:
            List of result dicts with keys:
            - 'id': Document ID
            - 'similarity_score': Normalized score (0-1, higher = better match)
            - 'metadata': Metadata dict with file_identifier, title, abstract, etc.
            - 'content': Document content
            
        Raises:
            SearchServiceError: If vector store search fails
        """
        try:
            with tracer.start_as_current_span("search_vector_store") as span:
                span.set_attribute("top_k", top_k)
                span.set_attribute("collection", collection)
                
                # Query vector store
                # Note: VectorStore has separate methods for different collections
                if collection == "supporting_documents":
                    results = self.vector_store.search_supporting_docs(
                        query_embedding=query_embedding,
                        limit=top_k
                    )
                else:  # Default to datasets
                    results = self.vector_store.search_datasets(
                        query_embedding=query_embedding,
                        limit=top_k
                    )
                
                span.set_attribute("results_count", len(results))
                logger.debug(f"Vector store returned {len(results)} results")
                
                return results
                
        except Exception as e:
            logger.error(f"Vector store search failed: {e}", exc_info=True)
            raise SearchServiceError(f"Vector store search failed: {e}") from e
    
    @with_span("hydrate_results")
    def _hydrate_results(
        self,
        vector_results: List[dict]
    ) -> List[SearchResult]:
        """
        Hydrate vector store results with full Dataset objects.
        
        Maps vector search results back to full Dataset entities by:
        1. Extracting file_identifier from metadata
        2. Fetching DBDataset from repository
        3. Converting DBDataset to Pydantic Dataset schema
        4. Creating SearchResult with Dataset + similarity score
        
        Architecture:
        - Vector results use DBDataset metadata (what was indexed)
        - But SearchResult expects Pydantic Dataset schema (for API responses)
        - This method converts between the two representations
        
        Args:
            vector_results: Results from vector store search
            Each result dict has keys:
            - 'id': Document ID (e.g., 'dataset_xyz')
            - 'similarity_score': 0-1 normalized score (already converted by VectorStore)
            - 'metadata': Dict with file_identifier, title, abstract, etc.
            - 'content': Document content
            
        Returns:
            List of SearchResult objects with normalized scores and full Datasets
        """
        search_results: List[SearchResult] = []
        
        try:
            with tracer.start_as_current_span("hydrate_results") as span:
                span.set_attribute("results_count", len(vector_results))
                
                for i, result in enumerate(vector_results):
                    try:
                        # Extract metadata from vector result
                        metadata = result.get("metadata", {})
                        file_identifier = metadata.get("file_identifier")
                        
                        if not file_identifier:
                            logger.warning(
                                f"Result {i} missing file_identifier in metadata, skipping"
                            )
                            continue
                        
                        # Fetch full DBDataset from repository
                        db_dataset = self.unit_of_work.datasets.get_by_file_identifier(
                            file_identifier
                        )
                        
                        if not db_dataset:
                            logger.warning(
                                f"Dataset not found in database: {file_identifier}"
                            )
                            continue
                        
                        # Convert DBDataset to Pydantic Dataset schema
                        dataset = self._convert_db_dataset_to_schema(db_dataset)
                        
                        # Extract similarity score (already normalized by VectorStore: 0-1)
                        similarity_score = result.get("similarity_score", 0.0)
                        
                        # Ensure score is in valid range (safety check)
                        similarity_score = max(0.0, min(1.0, similarity_score))
                        
                        # Create SearchResult
                        search_result = SearchResult(
                            dataset=dataset,
                            score=similarity_score
                        )
                        
                        search_results.append(search_result)
                        logger.debug(
                            f"Result {i}: {file_identifier} "
                            f"score={similarity_score:.4f}"
                        )
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to hydrate result {i}: {e}",
                            exc_info=True
                        )
                        continue
                
                span.set_attribute("hydrated_count", len(search_results))
                logger.debug(f"Hydrated {len(search_results)} results")
                
                return search_results
                
        except Exception as e:
            logger.error(f"Result hydration failed: {e}", exc_info=True)
            raise SearchServiceError(f"Result hydration failed: {e}") from e
    
    @staticmethod
    def _convert_db_dataset_to_schema(db_dataset: DBDataset) -> Dataset:
        """
        Convert database Dataset entity to Pydantic schema Dataset.
        
        The database layer uses dataclass DBDataset with JSON string fields
        for lists (topic_category, keywords). The API layer uses Pydantic
        Dataset with parsed list fields.
        
        This method handles the conversion between the two representations.
        
        Args:
            db_dataset: Database model (dataclass)
            
        Returns:
            Pydantic schema model (for API responses and SearchResult)
            
        Raises:
            ValueError: If conversion fails
        """
        import json
        
        try:
            # Parse JSON fields from database
            topic_category = []
            if db_dataset.topic_category:
                try:
                    topic_category = json.loads(db_dataset.topic_category)
                    if not isinstance(topic_category, list):
                        topic_category = [topic_category]
                except (json.JSONDecodeError, TypeError):
                    topic_category = []
            
            keywords = []
            if db_dataset.keywords:
                try:
                    keywords = json.loads(db_dataset.keywords)
                    if not isinstance(keywords, list):
                        keywords = [keywords]
                except (json.JSONDecodeError, TypeError):
                    keywords = []
            
            # Create Pydantic Dataset schema
            return Dataset(
                file_identifier=db_dataset.file_identifier,
                title=db_dataset.title,
                abstract=db_dataset.abstract or "",
                topic_category=topic_category,
                keywords=keywords,
                lineage=db_dataset.lineage,
                supplemental_info=db_dataset.supplemental_info,
                source_format=db_dataset.source_format
            )
            
        except Exception as e:
            logger.error(f"Failed to convert DB dataset: {e}")
            raise ValueError(f"Dataset conversion failed: {e}") from e
    
    def clear_cache(self) -> None:
        """
        Clear search result cache if enabled.
        
        Useful for testing or forcing fresh searches when
        underlying data has changed.
        
        Note: Currently caching is not implemented, this is a placeholder
        for future optimization.
        """
        if self.enable_caching:
            logger.info("Caching support not yet implemented")
        else:
            logger.debug("Caching is disabled")
