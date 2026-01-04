"""
Search Service Module

Provides semantic search capabilities for dataset discovery via vector similarity.

Main Classes:
    - SearchService: Orchestrates semantic search pipeline
    - SearchServiceError: Custom exception for search failures

Example Usage:
    from src.services.search import SearchService
    from src.services.embeddings import EmbeddingService, VectorStore
    from src.repositories import UnitOfWork
    
    search_service = SearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        unit_of_work=unit_of_work
    )
    
    results = search_service.search("climate data UK", top_k=10)
"""

from .search_service import SearchService, SearchServiceError

__all__ = ["SearchService", "SearchServiceError"]
