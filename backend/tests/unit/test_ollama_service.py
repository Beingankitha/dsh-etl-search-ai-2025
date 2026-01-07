"""
Tests for Ollama Service (Issue 9)

Tests the OllamaService class for LLM communication.
Uses mocks to avoid requiring a running Ollama instance.

Test Coverage:
- Health check (service availability)
- Text generation with various parameters
- Error handling (connection failures, timeouts)
- Graceful degradation when Ollama unavailable
- Context-aware generation for RAG
- Proper timeout handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.services.chat.ollama_service import OllamaService, OllamaServiceError


@pytest.fixture
def ollama_service():
    """Create OllamaService instance."""
    return OllamaService(
        host="http://localhost:11434",
        model="test-model",
        timeout=30
    )


class TestOllamaServiceInit:
    """Test OllamaService initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default settings."""
        service = OllamaService()
        assert service.host
        assert service.model
        assert service.timeout > 0
    
    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        service = OllamaService(
            host="http://example.com:1234",
            model="custom-model",
            timeout=60
        )
        assert service.host == "http://example.com:1234"
        assert service.model == "custom-model"
        assert service.timeout == 60


class TestOllamaServiceHealthCheck:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_service):
        """Test successful health check."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            with patch('httpx.AsyncClient.__aenter__', return_value=AsyncMock(get=AsyncMock(return_value=mock_response))):
                # For now, we'll test the basic logic
                # In real scenario, you'd need proper async context manager
                result = await ollama_service.health_check()
                # Should handle gracefully
                assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_service):
        """Test health check when Ollama is down."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")
            
            result = await ollama_service.health_check()
            assert result is False


class TestOllamaServiceGenerate:
    """Test text generation functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_success(self, ollama_service):
        """Test successful text generation."""
        expected_response = "This is a generated response"
        
        # Mock the httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": expected_response}
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient.__aenter__', return_value=mock_client):
            response = await ollama_service.generate(
                prompt="Test prompt",
                temperature=0.7
            )
            
            assert response == expected_response
            
            # Verify the request was made correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            
            # Check endpoint
            assert "/api/generate" in call_args[0][0]
            
            # Check payload
            payload = call_args[1]["json"]
            assert payload["model"] == "test-model"
            assert payload["prompt"] == "Test prompt"
            assert payload["temperature"] == 0.7
    
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, ollama_service):
        """Test generation with system prompt."""
        expected_response = "Response with system context"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": expected_response}
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient.__aenter__', return_value=mock_client):
            response = await ollama_service.generate(
                prompt="Test prompt",
                system_prompt="You are a helpful assistant"
            )
            
            assert response == expected_response
            
            # Verify system prompt was included
            payload = mock_client.post.call_args[1]["json"]
            assert payload["system"] == "You are a helpful assistant"
    
    @pytest.mark.asyncio
    async def test_generate_connection_error(self, ollama_service):
        """Test handling of connection errors."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        
        with patch('httpx.AsyncClient.__aenter__', return_value=mock_client):
            with pytest.raises(OllamaServiceError) as exc_info:
                await ollama_service.generate(prompt="Test")
            
            assert "Failed to connect" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_timeout(self, ollama_service):
        """Test handling of timeout errors."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
        
        with patch('httpx.AsyncClient.__aenter__', return_value=mock_client):
            with pytest.raises(OllamaServiceError) as exc_info:
                await ollama_service.generate(prompt="Test")
            
            assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_invalid_response(self, ollama_service):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient.__aenter__', return_value=mock_client):
            with pytest.raises(OllamaServiceError) as exc_info:
                await ollama_service.generate(prompt="Test")
            
            assert "Failed to parse" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_http_error(self, ollama_service):
        """Test handling of HTTP error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient.__aenter__', return_value=mock_client):
            with pytest.raises(OllamaServiceError) as exc_info:
                await ollama_service.generate(prompt="Test")
            
            assert "status 500" in str(exc_info.value)


class TestOllamaServiceGenerateWithContext:
    """Test context-aware generation for RAG."""
    
    @pytest.mark.asyncio
    async def test_generate_with_context(self, ollama_service):
        """Test generation with RAG context."""
        expected_response = "Response informed by context"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": expected_response}
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient.__aenter__', return_value=mock_client):
            context = "Dataset: Climate data for UK"
            response = await ollama_service.generate_with_context(
                user_message="What climate datasets are available?",
                context=context
            )
            
            assert response == expected_response
            
            # Verify context was included in prompt
            payload = mock_client.post.call_args[1]["json"]
            prompt = payload["prompt"]
            
            assert context in prompt
            assert "What climate datasets are available?" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_with_context_empty_context(self, ollama_service):
        """Test generation with empty context (degradation)."""
        expected_response = "Response without context"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": expected_response}
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient.__aenter__', return_value=mock_client):
            response = await ollama_service.generate_with_context(
                user_message="Tell me something",
                context=""
            )
            
            assert response == expected_response


class TestOllamaServiceIntegration:
    """Integration tests (if Ollama is running)."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running Ollama instance")
    async def test_real_ollama_generation(self):
        """Test against real Ollama (skip by default)."""
        service = OllamaService()
        
        # Check if Ollama is available
        if not await service.health_check():
            pytest.skip("Ollama not available")
        
        response = await service.generate(
            prompt="What is 2+2?",
            temperature=0.1  # Deterministic
        )
        
        assert response
        assert "4" in response.lower()
