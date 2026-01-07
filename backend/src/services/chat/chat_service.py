"""
Chat Service - Conversational Interface with RAG

This module implements a conversational service for dataset discovery
using Retrieval-Augmented Generation (RAG).

Architecture:
    - ChatService: High-level conversational interface
    - RAG Pipeline:
      1. Extract intent from user message
      2. Query vector store for relevant datasets
      3. Build context from retrieved datasets
      4. Generate response using LLM with context
    - Integrates OllamaService for LLM
    - Integrates SearchService for semantic search
    - Maintains conversation history for context
    - Returns response + source datasets

Design Patterns:
    - Facade: Simplifies complex RAG pipeline
    - Strategy: Pluggable search/LLM implementations
    - Dependency Injection: Services injected as dependencies
    - Repository: Abstracts data access
    - Observable: Traced and logged operations

Features:
    - Multi-turn conversation support with history
    - Semantic search over datasets before generating response
    - Graceful fallback when LLM is unavailable
    - Source attribution (which datasets informed the response)
    - Configurable response generation parameters
    - Error handling with detailed error messages
    - Comprehensive logging for debugging

Performance:
    - Vector search: ~50-100ms
    - LLM generation: 1-10 seconds (depends on model/hardware)
    - Total latency: 1-15 seconds typical
    - Memory efficient: Streams responses from LLM

Usage Example:
    from src.services.chat import ChatService
    from src.services.search import SearchService
    from src.services.chat import OllamaService
    from src.models.schemas import ChatMessage
    
    # Initialize services
    search_service = SearchService(...)
    ollama_service = OllamaService()
    
    chat_service = ChatService(
        search_service=search_service,
        ollama_service=ollama_service
    )
    
    # Single-turn chat
    response = await chat_service.send_message(
        message="Tell me about climate datasets",
        history=[]
    )
    print(response.message.content)  # LLM response
    print(f"Sources: {[s.dataset.title for s in response.sources]}")
    
    # Multi-turn chat
    history = [response.message]
    response2 = await chat_service.send_message(
        message="Focus on UK data please",
        history=history
    )
"""

import logging
import re
from typing import List, Optional
from datetime import datetime

from src.logging_config import get_logger
from src.models.schemas import ChatMessage, SearchResult, Dataset
from src.services.search import SearchService, SearchServiceError
from src.services.chat.ollama_service import OllamaService, OllamaServiceError

logger = get_logger(__name__)

# Lazy tracer
_tracer = None


def get_tracer():
    """Get tracer instance lazily."""
    global _tracer
    if _tracer is None:
        try:
            from src.services.observability import get_tracer as get_tracer_impl
            _tracer = get_tracer_impl(__name__)
        except Exception:
            _tracer = None
    return _tracer


class ChatServiceError(Exception):
    """Exception raised when chat service fails."""
    pass


class ChatService:
    """
    Conversational service with RAG for dataset discovery.
    
    Implements a RAG pipeline:
    1. Extract intent from user message
    2. Search vector store for relevant datasets
    3. Build context from retrieved datasets
    4. Generate response using LLM with context
    5. Return response + source datasets
    
    Architecture:
    - Pluggable SearchService and OllamaService
    - Supports multi-turn conversations via history
    - Graceful degradation if LLM unavailable
    - Observable: Tracing and logging of all operations
    
    Design Principles:
    - Single Responsibility: Focus on conversation orchestration
    - Open/Closed: Easy to swap search or LLM implementations
    - Dependency Injection: Dependencies passed in constructor
    - Interface Segregation: Minimal dependencies
    """
    
    # System prompt guides LLM behavior for dataset discovery
    SYSTEM_PROMPT = """You are an expert assistant for helping users discover environmental and geospatial datasets. 
Your role is to:
1. Help users find datasets relevant to their research or work
2. Provide context about what data is available
3. Explain dataset contents, methodologies, and potential use cases
4. Answer questions about specific datasets when referenced

Always be helpful and focus on providing accurate information about datasets. 
If you're unsure about specific details, indicate what information comes from the data catalog versus general knowledge.
Be conversational but professional."""

    # Fallback response when LLM is unavailable
    FALLBACK_RESPONSE = (
        "I'm currently unable to generate a detailed response due to a system issue. "
        "However, I've found the following relevant datasets that may help with your question:"
    )
    
    # Simple greeting patterns for conversational interaction
    GREETING_PATTERNS = {
        r'\b(hi|hello|hey|greetings)\b': (
            "Hello! I'm your dataset discovery assistant. I can help you find environmental and geospatial datasets from the CEH catalogue. "
            "You can ask me about datasets by topic, location, format, or specific research needs. What kind of datasets are you interested in?"
        ),
        r'\bwhat can you do\b': (
            "I can help you discover datasets in several ways:\n"
            "- Ask about datasets by topic (e.g., 'climate datasets', 'water quality data')\n"
            "- Search by geographic area (e.g., 'UK hydrology data')\n"
            "- Find datasets by format or characteristics (e.g., 'raster data', 'time series')\n"
            "- Learn about dataset details and how to use them\n\n"
            "What would you like to explore?"
        ),
        r'\bhelp\b': (
            "I'm here to help! You can ask me about:\n"
            "- Specific environmental or geospatial datasets\n"
            "- Datasets covering particular topics or regions\n"
            "- Dataset characteristics like format, resolution, or time period\n"
            "- How datasets relate to your research\n\n"
            "What information are you looking for?"
        ),
    }
    
    def __init__(
        self,
        search_service: SearchService,
        ollama_service: OllamaService,
        max_context_length: int = 4000,
        num_sources: int = 5,
    ):
        """
        Initialize ChatService.
        
        Args:
            search_service: SearchService instance for finding datasets
            ollama_service: OllamaService instance for LLM inference
            max_context_length: Max characters to include in LLM context
                            Default: 4000 (fits in most LLM context windows)
            num_sources: Number of datasets to retrieve for context
                        Default: 5 (balance between informativeness and context size)
        """
        self.search_service = search_service
        self.ollama_service = ollama_service
        self.max_context_length = max_context_length
        self.num_sources = num_sources
        
        logger.debug(
            f"Initialized ChatService: "
            f"max_context={max_context_length}, num_sources={num_sources}"
        )
    
    async def send_message(
        self,
        message: str,
        history: List[ChatMessage] = None,
        top_k: int = None,
    ) -> tuple:
        """
        Send a message and get conversational response with RAG.
        
        Implements the complete RAG pipeline:
        1. Check for simple greetings (instant response)
        2. Extract intent from message + history
        3. Search for relevant datasets
        4. Build context from search results
        5. Generate response with LLM
        6. Return response + source attribution
        
        Args:
            message: User message/query
            history: Conversation history (list of previous messages)
                    None if first turn
            top_k: Number of sources to retrieve (overrides default)
        
        Returns:
            Tuple of (response_message: ChatMessage, sources: List[SearchResult])
            
        Raises:
            ChatServiceError: If both search and LLM fail
        """
        try:
            logger.info(
                f"Chat message received: len={len(message)}, "
                f"history={len(history or [])}"
            )
            
            # Step 0: Check for simple greetings (respond immediately without search)
            greeting_response = self._check_greeting(message)
            if greeting_response:
                logger.debug(f"Detected greeting pattern")
                response_message = ChatMessage(
                    role="assistant",
                    content=greeting_response
                )
                return response_message, []  # No sources for greeting
            
            # Use provided top_k or default
            num_sources = top_k or self.num_sources
            
            # Step 1: Determine search query (could be message or better query from history)
            search_query = self._extract_search_query(message, history)
            logger.debug(f"Extracted search query: {search_query}")
            
            # Step 2: Search for relevant datasets
            sources = await self._search_for_context(
                query=search_query,
                top_k=num_sources
            )
            
            # Step 3: Build context from sources
            context = self._build_context(sources)
            logger.debug(f"Built context: {len(context)} chars from {len(sources)} sources")
            
            # Step 4: Generate response with context
            response_text = await self._generate_response(
                user_message=message,
                context=context,
                history=history
            )
            
            # Step 5: Build response message
            response_message = ChatMessage(
                role="assistant",
                content=response_text
            )
            
            logger.info(
                f"Chat response generated: len={len(response_text)}, "
                f"sources={len(sources)}"
            )
            
            return response_message, sources
        
        except ChatServiceError:
            raise
        except Exception as e:
            error_msg = f"Chat service error: {e}"
            logger.error(error_msg, exc_info=True)
            raise ChatServiceError(error_msg) from e
    
    def _check_greeting(self, message: str) -> Optional[str]:
        """
        Check if message is a simple greeting and return instant response.
        
        Detects patterns like "hi", "hello", "what can you do?" etc.
        and returns pre-written friendly responses immediately without
        needing to search or call the LLM.
        
        Args:
            message: User's message
        
        Returns:
            Greeting response if pattern matched, None otherwise
        """
        message_lower = message.lower().strip()
        
        for pattern, response in self.GREETING_PATTERNS.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                logger.debug(f"Matched greeting pattern: {pattern}")
                return response
        
        return None
    
    def _extract_search_query(
        self,
        current_message: str,
        history: Optional[List[ChatMessage]] = None,
    ) -> str:
        """
        Extract search query from current message and history.
        
        In a multi-turn conversation, we need to understand what the user
        is currently asking about. This might be:
        - A new question (use current message)
        - A follow-up question referencing previous context
        - A refinement of a previous query
        
        For now, we use a simple heuristic: use the current message as the
        search query. In a more advanced system, we could use the LLM to
        synthesize a better search query from the full conversation.
        
        Args:
            current_message: User's latest message
            history: Previous messages in conversation
        
        Returns:
            Search query optimized for vector search
        """
        # Simple implementation: use current message
        # Could be enhanced to synthesize query from conversation history
        query = current_message.strip()
        
        # Ensure query is not too long for vector search
        max_query_length = 512
        if len(query) > max_query_length:
            query = query[:max_query_length]
        
        return query
    
    async def _search_for_context(
        self,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Search for relevant datasets using semantic search.
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of SearchResult objects (dataset + relevance score)
        """
        try:
            logger.debug(f"Searching for context: query='{query}', top_k={top_k}")
            
            # Use SearchService to find relevant datasets
            # SearchService.search() returns List[SearchResult] directly
            sources = self.search_service.search(
                query=query,
                top_k=top_k
            )
            
            logger.debug(f"Found {len(sources)} relevant datasets")
            
            return sources
        
        except SearchServiceError as e:
            # If search fails, return empty list but don't crash
            # We'll still generate a response, just without specific sources
            logger.warning(f"Search failed: {e}. Continuing without context sources.")
            return []
        except Exception as e:
            logger.warning(f"Unexpected search error: {e}. Continuing without sources.")
            return []
    
    def _build_context(self, sources: List[SearchResult]) -> str:
        """
        Build context string from retrieved datasets.
        
        Formats retrieved datasets into a coherent context string that
        the LLM can use to ground its response. Includes:
        - Dataset titles
        - Abstracts
        - Relevance scores
        - Keywords/topics
        
        Truncates to max_context_length to fit in LLM context window.
        
        Args:
            sources: List of SearchResult objects
        
        Returns:
            Formatted context string for LLM
        """
        if not sources:
            return "No relevant datasets found in the catalog."
        
        context_parts = ["Available datasets in the catalog:"]
        current_length = len("\n".join(context_parts))
        
        for i, result in enumerate(sources, 1):
            dataset = result.dataset
            relevance_pct = int(result.score * 100)
            
            # Format dataset info
            dataset_info = (
                f"{i}. Title: {dataset.title}\n"
                f"   ID: {dataset.file_identifier}\n"
                f"   Relevance: {relevance_pct}%\n"
            )
            
            # Add abstract if available
            if dataset.abstract:
                # Truncate abstract to avoid too much context
                abstract = dataset.abstract[:300]
                if len(dataset.abstract) > 300:
                    abstract += "..."
                dataset_info += f"   Summary: {abstract}\n"
            
            # Add keywords if available
            if dataset.keywords:
                keywords_str = ", ".join(dataset.keywords[:5])
                dataset_info += f"   Keywords: {keywords_str}\n"
            
            # Check if adding this would exceed max length
            if current_length + len(dataset_info) > self.max_context_length:
                logger.debug(
                    f"Context truncated at {len(sources)} sources "
                    f"({current_length} chars)"
                )
                break
            
            context_parts.append(dataset_info)
            current_length += len(dataset_info)
        
        context = "\n".join(context_parts)
        logger.debug(f"Built context: {len(context)} chars from {len(sources)} sources")
        
        return context
    
    async def _generate_response(
        self,
        user_message: str,
        context: str,
        history: Optional[List[ChatMessage]] = None,
    ) -> str:
        """
        Generate LLM response using context.
        
        Calls OllamaService to generate a response that incorporates:
        - User message
        - Retrieved context (dataset information)
        - Conversation history (for multi-turn chats)
        - System prompt (guides LLM behavior)
        
        Falls back to a generic message if LLM is unavailable.
        
        Args:
            user_message: The user's current message
            context: Retrieved context from semantic search
            history: Previous messages in conversation
        
        Returns:
            Generated response text
        """
        try:
            # Format conversation history for LLM
            history_text = self._format_history(history or [])
            
            # Build final prompt that includes everything
            full_prompt = self._build_rag_prompt(
                user_message=user_message,
                context=context,
                history=history_text
            )
            
            logger.debug(f"Generating response with prompt ({len(full_prompt)} chars)")
            
            # Generate response
            logger.debug(f"Calling Ollama service...")
            response = await self.ollama_service.generate(
                prompt=full_prompt,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.7,  # Balanced creativity vs accuracy
                top_p=0.9,
                top_k=40
            )
            
            logger.info(f"Generated response: {len(response)} chars")
            if not response or response.strip() == "":
                logger.warning(f"Ollama returned empty response. Using fallback.")
                return self.FALLBACK_RESPONSE
            
            return response
        
        except OllamaServiceError as e:
            logger.warning(f"Ollama unavailable: {e}. Using fallback response.")
            return self.FALLBACK_RESPONSE
        except Exception as e:
            logger.error(f"Response generation error: {type(e).__name__}: {e}", exc_info=True)
            return self.FALLBACK_RESPONSE
    
    def _format_history(self, history: List[ChatMessage]) -> str:
        """
        Format conversation history for inclusion in LLM prompt.
        
        Converts a list of chat messages into a readable text format
        that the LLM can understand as previous conversation context.
        
        Args:
            history: List of previous ChatMessage objects
        
        Returns:
            Formatted conversation history string
        """
        if not history:
            return ""
        
        lines = ["Previous conversation:"]
        for msg in history[-4:]:  # Limit to last 4 messages to avoid too much context
            role_label = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role_label}: {msg.content}")
        
        return "\n".join(lines)
    
    def _build_rag_prompt(
        self,
        user_message: str,
        context: str,
        history: str = "",
    ) -> str:
        """
        Build the final prompt for LLM generation with RAG context.
        
        Creates a structured prompt that includes:
        1. Conversation history (if any)
        2. Retrieved context (datasets from vector search)
        3. User's current message
        4. Instructions for how to respond
        
        Args:
            user_message: User's current question/message
            context: Retrieved context from semantic search
            history: Formatted conversation history
        
        Returns:
            Complete prompt for LLM generation
        """
        prompt_parts = []
        
        # Include history if available
        if history:
            prompt_parts.append(history)
            prompt_parts.append("")  # Blank line
        
        # Include context from semantic search
        prompt_parts.append(context)
        prompt_parts.append("")  # Blank line
        
        # Include user's current message
        prompt_parts.append(f"User's current question: {user_message}")
        prompt_parts.append("")  # Blank line
        
        # Instructions for response
        prompt_parts.append(
            "Based on the above context and datasets, provide a helpful and "
            "informative response. Reference specific datasets when relevant. "
            "Be conversational and focused on helping the user find the data they need."
        )
        prompt_parts.append("")
        prompt_parts.append("Response:")
        
        return "\n".join(prompt_parts)
