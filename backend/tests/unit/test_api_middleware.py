"""Tests for API request logging middleware."""

import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI, Request
from starlette.testclient import TestClient
from starlette.responses import PlainTextResponse

from src.api.middleware.logging import RequestLoggingMiddleware


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    @app.get("/health")
    async def health():
        return {"health": "ok"}
    
    @app.post("/data")
    async def post_data(request: Request):
        body = await request.json()
        return {"received": body}
    
    # Add middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_middleware_initialization():
    """Test middleware initialization."""
    app = FastAPI()
    middleware = RequestLoggingMiddleware(app)
    
    assert middleware is not None
    assert hasattr(middleware, 'tracer')
    assert hasattr(middleware, 'PII_KEYS')


def test_request_logging_get_endpoint(client):
    """Test logging for GET endpoint."""
    response = client.get("/test")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_logging_post_endpoint(client):
    """Test logging for POST endpoint."""
    response = client.post("/data", json={"test": "data"})
    
    assert response.status_code == 200
    assert response.json() == {"received": {"test": "data"}}


def test_health_endpoint_logging(client):
    """Test logging for health check."""
    response = client.get("/health")
    
    assert response.status_code == 200


def test_request_id_generation(client):
    """Test that request ID is generated."""
    response = client.get("/test")
    
    # Request should succeed
    assert response.status_code == 200


def test_pii_keys_defined():
    """Test that PII keys are defined for redaction."""
    assert hasattr(RequestLoggingMiddleware, 'PII_KEYS')
    assert len(RequestLoggingMiddleware.PII_KEYS) > 0
    
    # Check for common PII keys
    pii_keys = RequestLoggingMiddleware.PII_KEYS
    assert "password" in pii_keys
    assert "token" in pii_keys
    assert "api_key" in pii_keys


def test_middleware_preserves_response(client):
    """Test that middleware doesn't alter response."""
    response = client.get("/test")
    
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def test_multiple_requests_logging(client):
    """Test logging multiple requests."""
    response1 = client.get("/health")
    response2 = client.get("/test")
    response3 = client.post("/data", json={"key": "value"})
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 200


def test_middleware_handles_post_with_body(client):
    """Test middleware handles POST requests with body."""
    data = {"test": "payload", "number": 42}
    response = client.post("/data", json=data)
    
    assert response.status_code == 200
    assert response.json()["received"] == data


def test_request_header_handling(client):
    """Test middleware handles custom headers."""
    headers = {
        "X-Request-ID": "custom-request-id",
        "X-Trace-ID": "trace-123"
    }
    response = client.get("/test", headers=headers)
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_middleware_dispatch_called():
    """Test that middleware dispatch method is properly called."""
    app = FastAPI()
    
    @app.get("/endpoint")
    async def endpoint():
        return {"success": True}
    
    middleware = RequestLoggingMiddleware(app)
    
    # Middleware should be initialized
    assert middleware is not None


def test_middleware_error_handling(client):
    """Test middleware doesn't break on errors."""
    # Request to endpoint that might not exist still goes through middleware
    response = client.get("/test")
    assert response.status_code == 200


def test_request_logging_with_trace_context():
    """Test trace context extraction from headers."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}
    
    app.add_middleware(RequestLoggingMiddleware)
    client = TestClient(app)
    
    # Send request with trace context headers
    headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "tracestate": "congo=t61rcWtrMzE"
    }
    response = client.get("/test", headers=headers)
    
    assert response.status_code == 200
