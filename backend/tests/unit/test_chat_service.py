"""
Tests for Chat Service (Issue 9)

Tests the ChatService class for conversational interface with RAG.
Uses mocks for SearchService and OllamaService to isolate functionality.

Test Coverage:
- Multi-turn conversation support
- RAG pipeline (search -> context -> generate)
- Error handling and graceful degradation
- Search query extraction from message and history
- Context building from retrieved datasets
- LLM response generation with context
- Conversation history formatting
- Source attribution
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.models.schemas import ChatMessage, SearchResult, Dataset
from src.services.chat.chat_service import ChatService, ChatServiceError
from src.services.chat.ollama_service import OllamaService, OllamaServiceError
from src.services.search import SearchService


@pytest.fixture
def mock_search_service():
    """Create mock SearchService."""
    mock_service = MagicMock(spec=SearchService)
    
    def create_search_result(title, abstract, score):
        dataset = Dataset(
            file_identifier=f"id-{title.lower().replace(' ', '-')}",
            title=title,
            abstract=abstract,
            keywords=["test", "data"],
            topic_category=["Environment"],
            lineage="Test lineage",
            source_format="xml"
        )
        return SearchResult(dataset=dataset, score=score)
    
    # Default mock behavior - returns List[SearchResult] directly
    mock_results = [
        create_search_result("Climate Dataset", "Dataset about climate", 0.9),
        create_search_result("Soil Data", "Dataset about soil", 0.8),
    ]
    mock_service.search = MagicMock(return_value=mock_results)
    
    return mock_service


@pytest.fixture
def mock_ollama_service():
    """Create mock OllamaService."""
    mock_service = AsyncMock(spec=OllamaService)
    mock_service.generate = AsyncMock(return_value="Test response from LLM")
    mock_service.generate_with_context = AsyncMock(return_value="Test response with context")
    return mock_service


@pytest.fixture
def chat_service(mock_search_service, mock_ollama_service):
    """Create ChatService with mocked dependencies."""
    return ChatService(
        search_service=mock_search_service,
        ollama_service=mock_ollama_service,
        max_context_length=2000,
        num_sources=3
    )


class TestChatServiceInit:
    """Test ChatService initialization."""
    
    def test_init_with_defaults(self, mock_search_service, mock_ollama_service):
        """Test initialization with default parameters."""
        service = ChatService(
            search_service=mock_search_service,
            ollama_service=mock_ollama_service
        )
        assert service.search_service == mock_search_service
        assert service.ollama_service == mock_ollama_service
        assert service.max_context_length > 0
        assert service.num_sources > 0
    
    def test_init_with_custom_values(self, mock_search_service, mock_ollama_service):
        """Test initialization with custom values."""
        service = ChatService(
            search_service=mock_search_service,
            ollama_service=mock_ollama_service,
            max_context_length=5000,
            num_sources=10
        )
        assert service.max_context_length == 5000
        assert service.num_sources == 10


class TestChatServiceExtractSearchQuery:
    """Test search query extraction from messages."""
    
    def test_extract_query_simple_message(self, chat_service):
        """Test extracting query from simple message."""
        message = "Tell me about climate datasets"
        query = chat_service._extract_search_query(message)
        
        assert query == message
    
    def test_extract_query_truncates_long_message(self, chat_service):
        """Test that very long queries are truncated."""
        message = "x" * 1000  # Very long message
        query = chat_service._extract_search_query(message)
        
        assert len(query) <= 512
    
    def test_extract_query_with_history(self, chat_service):
        """Test query extraction with conversation history."""
        history = [
            ChatMessage(role="user", content="What datasets exist?"),
            ChatMessage(role="assistant", content="We have climate and soil data"),
        ]
        message = "Tell me more about climate"
        query = chat_service._extract_search_query(message, history)
        
        assert query == message


class TestChatServiceBuildContext:
    """Test context building from search results."""
    
    def test_build_context_from_results(self, chat_service):
        """Test building context from search results."""
        results = [
            SearchResult(
                dataset=Dataset(
                    file_identifier="id1",
                    title="Climate Dataset",
                    abstract="Dataset about global climate patterns",
                    keywords=["climate", "temperature"],
                    topic_category=["Environment"]
                ),
                score=0.95
            ),
            SearchResult(
                dataset=Dataset(
                    file_identifier="id2",
                    title="Soil Data",
                    abstract="Dataset about soil properties",
                    keywords=["soil", "nutrients"],
                    topic_category=["Environment"]
                ),
                score=0.85
            )
        ]
        
        context = chat_service._build_context(results)
        
        # Verify context includes dataset information
        assert "Climate Dataset" in context
        assert "Soil Data" in context
        assert "95%" in context  # Relevance score
        assert "85%" in context
        assert "climate" in context  # Keywords
    
    def test_build_context_empty_results(self, chat_service):
        """Test context building with no results."""
        context = chat_service._build_context([])
        
        assert "No relevant datasets" in context
    
    def test_build_context_respects_max_length(self, chat_service):
        """Test that context respects max_context_length."""
        # Create many results with long abstracts
        results = [
            SearchResult(
                dataset=Dataset(
                    file_identifier=f"id{i}",
                    title=f"Dataset {i}",
                    abstract="x" * 500,  # Long abstract
                    keywords=[],
                    topic_category=[]
                ),
                score=0.9 - (i * 0.1)
            )
            for i in range(10)
        ]
        
        context = chat_service._build_context(results)
        
        # Context should be truncated to max length
        assert len(context) <= chat_service.max_context_length * 1.1  # Allow 10% buffer
    
    def test_build_context_with_missing_fields(self, chat_service):
        """Test context building with missing dataset fields."""
        results = [
            SearchResult(
                dataset=Dataset(
                    file_identifier="id1",
                    title="Minimal Dataset",
                    abstract="",  # Empty abstract
                    keywords=[],  # No keywords
                    topic_category=[]
                ),
                score=0.8
            )
        ]
        
        # Should not crash with missing fields
        context = chat_service._build_context(results)
        
        assert "Minimal Dataset" in context
        assert "80%" in context


class TestChatServiceFormatHistory:
    """Test conversation history formatting."""
    
    def test_format_history_empty(self, chat_service):
        """Test formatting empty history."""
        formatted = chat_service._format_history([])
        
        assert formatted == ""
    
    def test_format_history_single_message(self, chat_service):
        """Test formatting single message."""
        history = [
            ChatMessage(role="user", content="What is climate?")
        ]
        formatted = chat_service._format_history(history)
        
        assert "User: What is climate?" in formatted
    
    def test_format_history_multi_turn(self, chat_service):
        """Test formatting multi-turn conversation."""
        history = [
            ChatMessage(role="user", content="What datasets exist?"),
            ChatMessage(role="assistant", content="We have climate data"),
            ChatMessage(role="user", content="Tell me more"),
        ]
        formatted = chat_service._format_history(history)
        
        assert "User:" in formatted
        assert "Assistant:" in formatted
        assert "What datasets exist?" in formatted
        assert "Tell me more" in formatted
    
    def test_format_history_limits_messages(self, chat_service):
        """Test that history is limited to recent messages."""
        history = [
            ChatMessage(role="user", content=f"Message {i}")
            for i in range(10)
        ]
        formatted = chat_service._format_history(history)
        
        # Should limit to recent messages
        lines = [l for l in formatted.split("\n") if "Message" in l]
        assert len(lines) <= 4  # Limited to 4 most recent


class TestChatServiceBuildRagPrompt:
    """Test RAG prompt building."""
    
    def test_build_rag_prompt_with_context(self, chat_service):
        """Test building RAG prompt with context."""
        prompt = chat_service._build_rag_prompt(
            user_message="Tell me about climate",
            context="Climate dataset available"
        )
        
        assert "Tell me about climate" in prompt
        assert "Climate dataset available" in prompt
    
    def test_build_rag_prompt_with_history(self, chat_service):
        """Test building RAG prompt with history."""
        history = "User: What exists?\nAssistant: Many datasets"
        prompt = chat_service._build_rag_prompt(
            user_message="More details?",
            context="Context info",
            history=history
        )
        
        assert history in prompt
        assert "More details?" in prompt
    
    def test_build_rag_prompt_instructions(self, chat_service):
        """Test that prompt includes generation instructions."""
        prompt = chat_service._build_rag_prompt(
            user_message="Question",
            context="Context"
        )
        
        # Should include instructions
        assert "informative" in prompt.lower() or "dataset" in prompt.lower()


class TestChatServiceSendMessage:
    """Test the main send_message method."""
    
    @pytest.mark.asyncio
    async def test_send_message_simple(self, chat_service):
        """Test simple message sending."""
        response_msg, sources = await chat_service.send_message(
            message="Tell me about climate datasets"
        )
        
        assert isinstance(response_msg, ChatMessage)
        assert response_msg.role == "assistant"
        assert response_msg.content
        assert isinstance(sources, list)
        assert len(sources) > 0
    
    @pytest.mark.asyncio
    async def test_send_message_with_history(self, chat_service):
        """Test message with conversation history."""
        history = [
            ChatMessage(role="user", content="What datasets exist?"),
            ChatMessage(role="assistant", content="We have climate data"),
        ]
        
        response_msg, sources = await chat_service.send_message(
            message="Tell me more about climate",
            history=history
        )
        
        assert response_msg.role == "assistant"
        assert response_msg.content
    
    @pytest.mark.asyncio
    async def test_send_message_custom_top_k(self, chat_service):
        """Test message with custom top_k."""
        response_msg, sources = await chat_service.send_message(
            message="Tell me about datasets",
            top_k=2
        )
        
        # Should have requested 2 sources
        assert len(sources) <= 2
    
    @pytest.mark.asyncio
    async def test_send_message_search_failure(self, chat_service):
        """Test graceful handling of search failure."""
        # Mock search to raise error
        chat_service.search_service.search.side_effect = Exception("Search failed")
        
        # Should still generate response with fallback
        response_msg, sources = await chat_service.send_message(
            message="Tell me something"
        )
        
        assert response_msg.role == "assistant"
        # Sources will be empty due to search failure
        assert len(sources) == 0
    
    @pytest.mark.asyncio
    async def test_send_message_ollama_failure(self, chat_service):
        """Test graceful handling of LLM failure."""
        # Mock Ollama to raise error
        chat_service.ollama_service.generate.side_effect = OllamaServiceError("Ollama down")
        
        # Should use fallback response
        response_msg, sources = await chat_service.send_message(
            message="Tell me something"
        )
        
        assert response_msg.role == "assistant"
        assert chat_service.FALLBACK_RESPONSE in response_msg.content
    
    @pytest.mark.asyncio
    async def test_send_message_returns_sources(self, chat_service):
        """Test that response includes source attribution."""
        response_msg, sources = await chat_service.send_message(
            message="Tell me about datasets"
        )
        
        # Should have retrieved sources
        assert len(sources) > 0
        
        # Sources should be SearchResult objects
        for source in sources:
            assert hasattr(source, 'dataset')
            assert hasattr(source, 'score')
            assert source.dataset.title


class TestChatServiceSearchForContext:
    """Test the search for context method."""
    
    @pytest.mark.asyncio
    async def test_search_for_context_success(self, chat_service):
        """Test successful search for context."""
        sources = await chat_service._search_for_context(
            query="climate datasets",
            top_k=5
        )
        
        assert isinstance(sources, list)
        assert len(sources) > 0
        
        # Verify search was called with correct params
        chat_service.search_service.search.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_for_context_empty_results(self, chat_service):
        """Test search returning no results."""
        # search() now returns List[SearchResult] directly, not SearchResponse
        chat_service.search_service.search.return_value = []
        
        sources = await chat_service._search_for_context(
            query="nonexistent",
            top_k=5
        )
        
        assert sources == []
    
    @pytest.mark.asyncio
    async def test_search_for_context_handles_error(self, chat_service):
        """Test that search errors are handled gracefully."""
        chat_service.search_service.search.side_effect = Exception("Search error")
        
        # Should return empty list, not crash
        sources = await chat_service._search_for_context(query="test")
        
        assert sources == []


class TestChatServiceIntegration:
    """Integration tests for full RAG pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_rag_pipeline(self, chat_service):
        """Test complete RAG pipeline."""
        # Send a message
        response_msg, sources = await chat_service.send_message(
            message="What climate datasets are available?"
        )
        
        # Verify RAG pipeline executed
        assert response_msg.role == "assistant"
        assert len(response_msg.content) > 0
        
        # Verify sources were retrieved
        assert len(sources) > 0
        
        # Verify OllamaService was called
        chat_service.ollama_service.generate.assert_called()
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, chat_service):
        """Test multi-turn conversation."""
        # First turn
        response1_msg, sources1 = await chat_service.send_message(
            message="What datasets do you have?"
        )
        
        # Second turn with history
        history = [response1_msg]
        response2_msg, sources2 = await chat_service.send_message(
            message="Tell me more details",
            history=history
        )
        
        # Both should generate responses
        assert response1_msg.content
        assert response2_msg.content
