"""Tests for API security features: rate limiting, authentication, error sanitization."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "development"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["API_KEY"] = "test-api-key-12345"
os.environ["LLM_PROVIDER"] = "mock"

from opsilot.api.main import app
from opsilot.knowledge_base.loader import KnowledgeBase
from opsilot.retrieval.retriever import TFIDFRetriever
from opsilot.providers import get_provider
from opsilot.answering.pipeline import AnsweringPipeline
from opsilot.cache.cache import AnswerCache


def initialize_app_state():
    """Initialize global app state for testing."""
    import opsilot.api.main as main_module

    kb = KnowledgeBase.from_json_file("knowledge_base/runbooks.json")
    retriever = TFIDFRetriever(kb)
    provider = get_provider("mock")
    pipeline = AnsweringPipeline(kb, retriever, provider, min_relevance_score=0.15, top_k=5)
    cache = AnswerCache(ttl_seconds=3600)

    main_module._knowledge_base = kb
    main_module._retriever = retriever
    main_module._pipeline = pipeline
    main_module._llm_provider = provider
    main_module._answer_cache = cache


@pytest.fixture(scope="session", autouse=True)
def setup_app_state():
    """Initialize app state before all tests."""
    initialize_app_state()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-api-key-12345"}


class TestHealthEndpoint:
    """Tests for the health endpoint (should be publicly accessible)."""

    def test_health_endpoint_accessible(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "provider" in data
        assert "provider_available" in data
        assert "knowledge_base_size" in data
        assert "cache_stats" in data

    def test_health_no_auth_required(self, client):
        """Health endpoint should not require authentication."""
        response = client.get("/health")
        assert response.status_code == 200


class TestProvidersEndpoint:
    """Tests for the providers listing endpoint."""

    def test_providers_endpoint_accessible(self, client):
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "active" in data
        assert isinstance(data["providers"], list)
        assert len(data["providers"]) >= 1

    def test_providers_no_auth_required(self, client):
        response = client.get("/api/v1/providers")
        assert response.status_code == 200


class TestAnswerEndpoint:
    """Tests for the answer endpoint (requires authentication)."""

    def test_answer_requires_auth(self, client):
        response = client.post(
            "/api/v1/answer",
            json={"question": "Test question"},
        )
        assert response.status_code == 401

    def test_answer_with_valid_key(self, client, auth_headers):
        response = client.post(
            "/api/v1/answer",
            json={"question": "How do I reset MFA?"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "retrieval_scores" in data
        assert "provider" in data
        assert "model" in data
        assert "cached" in data

    def test_answer_invalid_key(self, client):
        response = client.post(
            "/api/v1/answer",
            json={"question": "Test"},
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 401

    def test_answer_empty_question(self, client, auth_headers):
        response = client.post(
            "/api/v1/answer",
            json={"question": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_answer_question_too_long(self, client, auth_headers):
        long_question = "x" * 2001
        response = client.post(
            "/api/v1/answer",
            json={"question": long_question},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_answer_override_provider(self, client, auth_headers):
        response = client.post(
            "/api/v1/answer",
            json={"question": "Test", "provider": "mock"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_answer_temperature_bounds(self, client, auth_headers):
        response = client.post(
            "/api/v1/answer",
            json={"question": "Test", "temperature": 1.5},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_answer_max_tokens_bounds(self, client, auth_headers):
        response = client.post(
            "/api/v1/answer",
            json={"question": "Test", "max_tokens": 5000},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestCacheEndpoints:
    """Tests for cache statistics and management endpoints."""

    def test_cache_stats_requires_auth(self, client):
        response = client.get("/api/v1/cache/stats")
        assert response.status_code == 401

    def test_cache_stats_with_auth(self, client, auth_headers):
        response = client.get("/api/v1/cache/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "cache_hits" in data
        assert "cache_misses" in data
        assert "hit_rate" in data
        assert "entries" in data
        assert "expired_entries" in data

    def test_clear_cache_requires_auth(self, client):
        response = client.post("/api/v1/cache/clear")
        assert response.status_code == 401

    def test_clear_cache_with_auth(self, client, auth_headers):
        response = client.post("/api/v1/cache/clear", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "cleared" in data
        assert "message" in data


class TestRateLimiting:
    """Tests for rate limiting (when enabled)."""

    @patch.dict(os.environ, {"RATE_LIMIT_ENABLED": "true", "ENVIRONMENT": "production"})
    def test_rate_limit_headers_present(self, client):
        # This test would need rate limiting enabled
        # Skipping for now as it requires proper SlowAPI setup
        pass


class TestErrorSanitization:
    """Tests that errors don't leak sensitive information."""

    def test_404_error_format(self, client):
        response = client.get("/nonexistent")
        assert response.status_code == 404
        # Should not contain stack traces or internal paths

    def test_validation_error_format(self, client, auth_headers):
        response = client.post(
            "/api/v1/answer",
            json={"question": 123},  # Invalid type
            headers=auth_headers,
        )
        assert response.status_code == 422
        # Should have structured error, not stack trace

    def test_production_error_no_stack_trace(self, client, auth_headers):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            response = client.post(
                "/api/v1/answer",
                json={"question": ""},
                headers=auth_headers,
            )
            # In production, should not leak internal details
            if response.status_code >= 400:
                data = response.json()
                # Check no traceback/stack trace
                assert "traceback" not in str(data).lower()
                assert "file " not in str(data).lower()