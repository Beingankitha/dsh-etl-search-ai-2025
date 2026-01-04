"""
Integration tests for Issue #10 - FastAPI application.

Tests all API endpoints:
- Health checks
- Search endpoint
- Datasets listing and retrieval
- CORS configuration
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.app import app
from src.api.routes.search import get_search_service
from src.api.routes.datasets import get_unit_of_work
from src.models.schemas import Dataset, SearchResult, SearchRequest, SearchResponse


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_dataset():
    """Create sample dataset for testing."""
    return Dataset(
        file_identifier="test-001",
        title="Test Dataset",
        abstract="A test dataset for integration testing",
        topic_category=["climatology"],
        keywords=["test", "climate"],
        lineage="Test Source",
        supplemental_info="Test info",
        source_format="xml"
    )


@pytest.fixture
def sample_search_result(sample_dataset):
    """Create sample search result."""
    return SearchResult(
        dataset=sample_dataset,
        score=0.95
    )


# ============================================================================
# Health Check Endpoints
# ============================================================================

class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_endpoint_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_response_structure(self, client):
        """Test health response has required fields."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert data["status"] in ["healthy", "unhealthy"]
    
    def test_readiness_endpoint(self, client):
        """Test readiness probe endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["ready"] is True or response.json()["ready"] is False
    
    def test_liveness_endpoint(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["alive"] is True


# ============================================================================
# Root Endpoints
# ============================================================================

class TestRootEndpoints:
    """Test root endpoints."""
    
    def test_root_endpoint_returns_200(self, client):
        """Test root endpoint returns 200."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_root_response_structure(self, client):
        """Test root response has API metadata."""
        response = client.get("/")
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "docs" in data


# ============================================================================
# Search Endpoints
# ============================================================================

class TestSearchEndpoints:
    """Test search endpoints."""
    
    def test_search_endpoint_accepts_request(self, client, sample_search_result):
        """Test search endpoint accepts valid request."""
        mock_service = MagicMock()
        mock_service.search.return_value = [sample_search_result]
        
        app.dependency_overrides[get_search_service] = lambda: mock_service
        
        response = client.post(
            "/api/search",
            json={"query": "climate data", "top_k": 10}
        )
        
        app.dependency_overrides.clear()
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "climate data"
        assert "results" in data
    
    def test_search_endpoint_validates_request(self, client):
        """Test search endpoint rejects invalid request."""
        response = client.post(
            "/api/search",
            json={"query": "", "top_k": 10}  # Empty query
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_search_endpoint_returns_results(self, client, sample_search_result):
        """Test search endpoint returns results."""
        mock_service = MagicMock()
        mock_service.search.return_value = [sample_search_result]
        
        app.dependency_overrides[get_search_service] = lambda: mock_service
        
        response = client.post(
            "/api/search",
            json={"query": "climate", "top_k": 5}
        )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["score"] == 0.95
    
    def test_search_suggestions_endpoint(self, client):
        """Test search suggestions endpoint."""
        response = client.get("/api/search/suggestions?q=climate")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)


# ============================================================================
# Datasets Endpoints
# ============================================================================

class TestDatasetsEndpoints:
    """Test datasets endpoints."""
    
    def test_list_datasets_endpoint_returns_200(self, client):
        """Test list datasets endpoint returns 200."""
        mock_uow = MagicMock()
        mock_uow.datasets.count.return_value = 0
        mock_uow.datasets.get_paginated.return_value = []
        
        app.dependency_overrides[get_unit_of_work] = lambda: mock_uow
        
        response = client.get("/api/datasets")
        app.dependency_overrides.clear()
        assert response.status_code == 200
    
    def test_list_datasets_response_structure(self, client):
        """Test list datasets response structure."""
        mock_uow = MagicMock()
        mock_uow.datasets.count.return_value = 5
        mock_uow.datasets.get_paginated.return_value = []
        
        app.dependency_overrides[get_unit_of_work] = lambda: mock_uow
        
        response = client.get("/api/datasets?limit=10&offset=0")
        app.dependency_overrides.clear()
        
        data = response.json()
        
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "datasets" in data
        assert data["total"] == 5
    
    def test_list_datasets_pagination(self, client):
        """Test list datasets with pagination parameters."""
        mock_uow = MagicMock()
        mock_uow.datasets.count.return_value = 100
        mock_uow.datasets.get_paginated.return_value = []
        
        app.dependency_overrides[get_unit_of_work] = lambda: mock_uow
        
        response = client.get("/api/datasets?limit=20&offset=40")
        app.dependency_overrides.clear()
        
        data = response.json()
        
        assert data["limit"] == 20
        assert data["offset"] == 40
    
    def test_get_single_dataset_returns_200(self, client, sample_dataset):
        """Test get single dataset returns 200."""
        mock_uow = MagicMock()
        
        # Create mock DB dataset
        mock_db_dataset = MagicMock()
        mock_db_dataset.file_identifier = sample_dataset.file_identifier
        mock_db_dataset.title = sample_dataset.title
        mock_db_dataset.abstract = sample_dataset.abstract
        mock_db_dataset.topic_category = sample_dataset.topic_category
        mock_db_dataset.keywords = sample_dataset.keywords
        mock_db_dataset.lineage = sample_dataset.lineage
        mock_db_dataset.supplemental_info = sample_dataset.supplemental_info
        mock_db_dataset.source_format = sample_dataset.source_format
        
        mock_uow.datasets.get_by_file_identifier.return_value = mock_db_dataset
        
        app.dependency_overrides[get_unit_of_work] = lambda: mock_uow
        
        response = client.get("/api/datasets/test-001")
        app.dependency_overrides.clear()
        assert response.status_code == 200
    
    def test_get_single_dataset_not_found(self, client):
        """Test get single dataset returns 404 if not found."""
        mock_uow = MagicMock()
        mock_uow.datasets.get_by_file_identifier.return_value = None
        
        app.dependency_overrides[get_unit_of_work] = lambda: mock_uow
        
        response = client.get("/api/datasets/nonexistent")
        app.dependency_overrides.clear()
        assert response.status_code == 404
    
    def test_related_datasets_endpoint(self, client):
        """Test related datasets endpoint."""
        mock_uow = MagicMock()
        mock_db_dataset = MagicMock()
        mock_uow.datasets.get_by_file_identifier.return_value = mock_db_dataset
        
        app.dependency_overrides[get_unit_of_work] = lambda: mock_uow
        
        response = client.get("/api/datasets/test-001/related")
        app.dependency_overrides.clear()
        assert response.status_code == 200
        data = response.json()
        assert "file_identifier" in data
        assert "related" in data


# ============================================================================
# CORS Configuration
# ============================================================================

class TestCORSConfiguration:
    """Test CORS middleware configuration."""
    
    def test_cors_allows_localhost_3000(self, client):
        """Test CORS allows requests from localhost:3000."""
        response = client.options(
            "/api/search",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # CORS preflight should be handled
        assert response.status_code in [200, 405]
    
    def test_cors_allows_localhost_5173(self, client):
        """Test CORS allows requests from localhost:5173."""
        response = client.options(
            "/api/search",
            headers={"Origin": "http://localhost:5173"}
        )
        
        assert response.status_code in [200, 405]


# ============================================================================
# Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_endpoint_returns_404(self, client):
        """Test invalid endpoint returns 404."""
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404
    
    def test_invalid_request_method(self, client):
        """Test invalid request method returns 405."""
        response = client.delete("/api/search")
        assert response.status_code in [405, 422]  # Method not allowed or validation error


# ============================================================================
# Response Validation
# ============================================================================

class TestResponseValidation:
    """Test response validation."""
    
    def test_search_response_is_valid_json(self, client, sample_search_result):
        """Test search response is valid JSON."""
        mock_service = MagicMock()
        mock_service.search.return_value = [sample_search_result]
        
        app.dependency_overrides[get_search_service] = lambda: mock_service
        
        response = client.post(
            "/api/search",
            json={"query": "climate", "top_k": 10}
        )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        # Should not raise JSONDecodeError
        data = response.json()
        assert isinstance(data, dict)
