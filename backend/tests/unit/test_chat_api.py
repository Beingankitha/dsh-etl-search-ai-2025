"""
Integration tests for Chat API endpoints (Issue 9)

Tests the FastAPI endpoints for chat functionality.
Uses TestClient to simulate HTTP requests.

Test Coverage:
- POST /api/chat/send endpoint
- GET /api/chat/health endpoint
- Error handling and validation
- Request/response serialization
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.models.schemas import ChatMessage, SearchResult, Dataset, SearchResponse


@pytest.fixture
def app():
    """Create test app instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestChatSendEndpoint:
    """Test the POST /api/chat/send endpoint."""
    
    def test_send_message_success(self, client):
        """Test successful message sending."""
        # Mock the chat service
        with patch('src.api.routes.chat.ChatService') as MockChatService:
            mock_service = MagicMock()
            MockChatService.return_value = mock_service
            
            # Mock the response
            response_msg = ChatMessage(role="assistant", content="Test response")
            sources = [
                SearchResult(
                    dataset=Dataset(
                        file_identifier="id1",
                        title="Test Dataset",
                        abstract="A test dataset"
                    ),
                    score=0.9
                )
            ]
            
            # Mock async method
            async def mock_send_message(*args, **kwargs):
                return response_msg, sources
            
            mock_service.send_message = AsyncMock(side_effect=mock_send_message)
            
            # Send request
            response = client.post(
                "/api/chat/send",
                json={
                    "messages": [
                        {"role": "user", "content": "Tell me about datasets"}
                    ],
                    "top_k": 5
                }
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"]["role"] == "assistant"
            assert data["message"]["content"] == "Test response"
            assert "sources" in data
            assert len(data["sources"]) == 1
    
    def test_send_message_with_history(self, client):
        """Test message sending with conversation history."""
        with patch('src.api.routes.chat.ChatService') as MockChatService:
            mock_service = MagicMock()
            MockChatService.return_value = mock_service
            
            response_msg = ChatMessage(role="assistant", content="Response")
            mock_service.send_message = AsyncMock(return_value=(response_msg, []))
            
            response = client.post(
                "/api/chat/send",
                json={
                    "messages": [
                        {"role": "user", "content": "First message"},
                        {"role": "assistant", "content": "First response"},
                        {"role": "user", "content": "Follow up question"}
                    ],
                    "top_k": 3
                }
            )
            
            assert response.status_code == 200
    
    def test_send_message_empty_messages(self, client):
        """Test error handling for empty messages."""
        response = client.post(
            "/api/chat/send",
            json={
                "messages": [],
                "top_k": 5
            }
        )
        
        # FastAPI returns 422 for validation errors (not 400)
        assert response.status_code in [400, 422]
    
    def test_send_message_no_user_message(self, client):
        """Test error handling when no user message in request."""
        response = client.post(
            "/api/chat/send",
            json={
                "messages": [
                    {"role": "assistant", "content": "Some response"}
                ],
                "top_k": 5
            }
        )
        
        assert response.status_code == 400
    
    def test_send_message_invalid_json(self, client):
        """Test error handling for invalid JSON."""
        response = client.post(
            "/api/chat/send",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code >= 400


class TestChatHealthEndpoint:
    """Test the GET /api/chat/health endpoint."""
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        with patch('src.api.routes.chat.ChatService') as MockChatService:
            mock_service = MagicMock()
            MockChatService.return_value = mock_service
            
            # Mock async health check
            async def mock_health():
                return True
            
            mock_service.ollama_service = MagicMock()
            mock_service.ollama_service.health_check = AsyncMock(return_value=True)
            
            response = client.get("/api/chat/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "degraded"]
    
    def test_health_check_ollama_unavailable(self, client):
        """Test health check when Ollama is unavailable."""
        with patch('src.api.routes.chat.ChatService') as MockChatService:
            mock_service = MagicMock()
            MockChatService.return_value = mock_service
            
            # Mock Ollama as unavailable
            mock_service.ollama_service = MagicMock()
            mock_service.ollama_service.health_check = AsyncMock(return_value=False)
            
            response = client.get("/api/chat/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["ollama"] == "unavailable"


class TestChatEndpointIntegration:
    """Integration tests for chat endpoint."""
    
    def test_full_chat_workflow(self, client):
        """Test full chat workflow: health check, then send message."""
        with patch('src.api.routes.chat.ChatService') as MockChatService:
            mock_service = MagicMock()
            MockChatService.return_value = mock_service
            
            # Mock ollama health check
            mock_service.ollama_service = MagicMock()
            mock_service.ollama_service.health_check = AsyncMock(return_value=True)
            
            # Mock send_message
            response_msg = ChatMessage(role="assistant", content="Response")
            # Make sure the mock accepts all arguments
            mock_service.send_message = AsyncMock(return_value=(response_msg, []))
            
            # Check health first
            health_response = client.get("/api/chat/health")
            assert health_response.status_code == 200
            
            # Then send message
            chat_response = client.post(
                "/api/chat/send",
                json={
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ]
                }
            )
            
            assert chat_response.status_code == 200


class TestChatEndpointErrorHandling:
    """Test error handling in chat endpoints."""
    
    def test_chat_service_error(self, client):
        """Test handling of ChatService errors."""
        from src.services.chat import ChatServiceError
        
        with patch('src.api.routes.chat.ChatService') as MockChatService:
            mock_service = MagicMock()
            MockChatService.return_value = mock_service
            
            # Mock error
            mock_service.send_message = AsyncMock(
                side_effect=ChatServiceError("Test error")
            )
            
            response = client.post(
                "/api/chat/send",
                json={
                    "messages": [
                        {"role": "user", "content": "Test"}
                    ]
                }
            )
            
            assert response.status_code == 500
            assert "Chat service error" in response.text
    
    def test_unexpected_error(self, client):
        """Test handling of unexpected errors."""
        with patch('src.api.routes.chat.ChatService') as MockChatService:
            mock_service = MagicMock()
            MockChatService.return_value = mock_service
            
            # Mock unexpected error
            mock_service.send_message = AsyncMock(
                side_effect=Exception("Unexpected error")
            )
            
            response = client.post(
                "/api/chat/send",
                json={
                    "messages": [
                        {"role": "user", "content": "Test"}
                    ]
                }
            )
            
            assert response.status_code == 500
            assert "Unexpected error" in response.text
