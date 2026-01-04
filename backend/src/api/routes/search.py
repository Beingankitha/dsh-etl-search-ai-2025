"""
Semantic search endpoints.

Provides API for natural language dataset discovery via vector similarity.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.logging_config import get_logger
from src.models.schemas import SearchRequest, SearchResponse, SearchResult
from src.services.search import SearchService, SearchServiceError
from src.services.embeddings import EmbeddingService, VectorStore
from src.repositories import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# Dependency Injection
def get_search_service() -> SearchService:
    """Instantiate SearchService with dependencies."""
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    unit_of_work = UnitOfWork()
    
    return SearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        unit_of_work=unit_of_work,
    )


@router.post("", response_model=SearchResponse)
async def search_datasets(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """
    Search datasets using natural language query.
    
    Performs semantic search over dataset titles, abstracts, and metadata
    using vector similarity. Results are ranked by relevance score.
    
    Args:
        request: SearchRequest with query and optional top_k limit
        search_service: Injected SearchService
        
    Returns:
        SearchResponse with matched datasets sorted by relevance
        
    Raises:
        HTTPException: If search fails
        
    Examples:
        ```json
        POST /api/search
        {
            "query": "climate change precipitation patterns",
            "top_k": 10
        }
        
        Response:
        {
            "query": "climate change precipitation patterns",
            "results": [
                {
                    "dataset": {...},
                    "score": 0.95
                },
                ...
            ]
        }
        ```
    """
    try:
        logger.info(f"Search request: query={request.query[:50]}... top_k={request.top_k}")
        
        # Perform semantic search
        results = search_service.search(
            query=request.query,
            top_k=request.top_k,
            collection="datasets"
        )
        
        logger.info(f"Search completed: found {len(results)} results")
        
        return SearchResponse(
            query=request.query,
            results=results,
        )
        
    except SearchServiceError as e:
        logger.error(f"Search service error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in search: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during search"
        )


@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Partial query for suggestions"),
) -> dict:
    """
    Get search suggestions/autocomplete for a partial query.
    
    Args:
        q: Partial query string
        
    Returns:
        List of suggested search queries
        
    Note:
        This is a placeholder for future enhancement with:
        - Popular search queries
        - Dataset title/keyword suggestions
        - Recent searches
    """
    # TODO: Implement with popular queries, keyword suggestions, etc.
    return {
        "suggestions": [
            "climate data UK",
            "precipitation measurements",
            "environmental monitoring",
        ]
    }
