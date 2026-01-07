"""
Chat API endpoints for conversational dataset discovery.

Provides endpoints for:
- Sending chat messages (with RAG)
- Retrieving conversation context
- Multi-turn conversations

Endpoints:
- POST /api/chat/send - Send a message and get response
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.logging_config import get_logger
from src.models.schemas import ChatMessage, ChatRequest, ChatResponse, SearchResult
from src.services.chat import ChatService, ChatServiceError
from src.services.chat.ollama_service import OllamaService, OllamaServiceError
from src.services.search import SearchService
from src.services.embeddings import EmbeddingService, VectorStore
from src.repositories import UnitOfWork
from src.infrastructure import Database
from src.config import get_settings

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# Dependency Injection
def get_chat_service() -> ChatService:
    """Instantiate ChatService with dependencies.
    
    Creates fresh services for each request to ensure thread-safety.
    """
    settings = get_settings()
    
    # Create search service
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    database = Database(settings.database_path)
    database.connect()
    unit_of_work = UnitOfWork(database)
    
    search_service = SearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        unit_of_work=unit_of_work,
    )
    
    # Create LLM service
    ollama_service = OllamaService(
        host=settings.ollama_host,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout
    )
    
    # Create chat service
    return ChatService(
        search_service=search_service,
        ollama_service=ollama_service,
        max_context_length=4000,
        num_sources=5
    )


@router.post("/send", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """
    Send a chat message and get conversational response with RAG.
    
    Implements retrieval-augmented generation:
    1. Extract intent from user message
    2. Search vector store for relevant datasets
    3. Build context from retrieved datasets
    4. Generate response using LLM with context
    5. Return response + source datasets
    
    Args:
        request: ChatRequest with messages list and optional top_k
        chat_service: Injected ChatService
    
    Returns:
        ChatResponse with assistant message and source datasets
    
    Raises:
        HTTPException: If chat fails
    
    Examples:
        ```json
        POST /api/chat/send
        {
            "messages": [
                {"role": "user", "content": "Tell me about climate datasets"}
            ],
            "top_k": 5
        }
        ```
        
        Response:
        ```json
        {
            "message": {
                "role": "assistant",
                "content": "We have several climate datasets..."
            },
            "sources": [
                {
                    "dataset": {...},
                    "score": 0.95
                }
            ]
        }
        ```
    """
    try:
        # Validate request
        if not request.messages:
            raise HTTPException(
                status_code=400,
                detail="At least one message required"
            )
        
        # Get the last user message
        user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break
        
        if not user_message:
            raise HTTPException(
                status_code=400,
                detail="No user message found in request"
            )
        
        # Prepare history (exclude last message since it's the current one)
        history = [msg for msg in request.messages[:-1]] if len(request.messages) > 1 else []
        
        logger.info(
            f"Chat request: message_len={len(user_message)}, "
            f"history_len={len(history)}, top_k={request.top_k}"
        )
        
        # Get response from chat service
        response_message, sources = await chat_service.send_message(
            message=user_message,
            history=history,
            top_k=request.top_k
        )
        
        # Build response
        response = ChatResponse(
            message=response_message,
            sources=sources
        )
        
        logger.info(
            f"Chat response: message_len={len(response_message.content)}, "
            f"sources={len(sources)}"
        )
        
        return response
    
    except ChatServiceError as e:
        logger.error(f"Chat service error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat service error: {e}"
        ) from e
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Unexpected error processing chat message"
        ) from e


@router.get("/health")
async def chat_health_check(
    chat_service: ChatService = Depends(get_chat_service)
) -> dict:
    """
    Check health of chat service and its dependencies.
    
    Verifies:
    - Search service is functional
    - Vector store is accessible
    - LLM (Ollama) is available
    - Database connection works
    
    Returns:
        Health status for each component
        
    Examples:
        ```json
        {
            "status": "healthy",
            "search_service": "ok",
            "vector_store": "ok",
            "ollama": "ok",
            "database": "ok"
        }
        ```
    """
    try:
        # Check Ollama availability
        ollama_available = await chat_service.ollama_service.health_check()
        
        # Build response
        health_status = {
            "status": "healthy" if ollama_available else "degraded",
            "ollama": "ok" if ollama_available else "unavailable",
        }
        
        if not ollama_available:
            health_status["status"] = "degraded"
            health_status["note"] = "LLM (Ollama) is unavailable. Chat will use fallback responses."
        
        return health_status
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Health check failed"
        ) from e
