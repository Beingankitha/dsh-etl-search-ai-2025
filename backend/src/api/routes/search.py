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
from src.infrastructure import Database
from src.config import get_settings

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# Dependency Injection
def get_search_service() -> SearchService:
    """Instantiate SearchService with dependencies.
    
    Creates a fresh UnitOfWork per request to ensure thread-safety with SQLite.
    SQLite connections cannot be shared across threads, so we create a new
    connection for each request.
    """
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    
    # Create a fresh database connection for this request
    # (SQLite connections are thread-unsafe and cannot be reused across threads)
    settings = get_settings()
    database = Database(settings.database_path)
    database.connect()
    unit_of_work = UnitOfWork(database)
    # Initialize repositories with this connection
    unit_of_work.__enter__()
    
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
    
    Searches dataset titles, abstracts, and keywords for matches.
    Returns up to 10 suggestions sorted by relevance.
    
    Args:
        q: Partial query string (case-insensitive)
        
    Returns:
        Dictionary with 'suggestions' list of matching datasets/keywords
        
    Examples:
        GET /api/search/suggestions?q=soil
        Response:
        {
            "suggestions": [
                "Soil carbon data UK",
                "Soil moisture monitoring",
                "Soil properties survey",
                ...
            ]
        }
    """
    try:
        if not q or len(q.strip()) < 1:
            return {"suggestions": []}
        
        # Create database connection for this request
        settings = get_settings()
        database = Database(settings.database_path)
        database.connect()
        unit_of_work = UnitOfWork(database)
        unit_of_work.__enter__()
        
        try:
            # Query database for matching titles and keywords
            query_lower = q.lower().strip()
            
            # Get all datasets
            all_datasets = unit_of_work.datasets.get_all()
            
            # Extract unique suggestions from titles and keywords
            suggestions = set()
            
            for dataset in all_datasets:
                # Add title if it matches
                if query_lower in dataset.title.lower():
                    suggestions.add(dataset.title)
                
                # Add keywords that match
                if dataset.keywords:
                    for keyword in dataset.keywords:
                        if query_lower in keyword.lower():
                            suggestions.add(keyword)
            
            # Convert to sorted list and limit to 10
            sorted_suggestions = sorted(list(suggestions))[:10]
            
            logger.info(f"Suggestions for '{q}': found {len(sorted_suggestions)} results")
            
            return {"suggestions": sorted_suggestions}
            
        finally:
            unit_of_work.__exit__(None, None, None)
            database.close()
            
    except Exception as e:
        logger.error(f"Error fetching suggestions: {e}", exc_info=True)
        # Return empty suggestions on error instead of failing
        return {"suggestions": []}
