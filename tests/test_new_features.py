"""Targeted tests for new features: SUPPORT_PHONE, KNOWLEDGE_BASE_PATH validation, CORS."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from opsilot.answering.pipeline import AnsweringPipeline
from opsilot.knowledge_base.loader import KnowledgeBase
from opsilot.providers.mock import MockProvider
from opsilot.retrieval.retriever import TFIDFRetriever


class TestSupportPhoneConfiguration:
    """Tests for SUPPORT_PHONE configuration in answering pipeline."""

    def test_default_support_phone(self):
        """Test that default phone number is used when not configured."""
        kb = KnowledgeBase.from_json_file("knowledge_base/runbooks.json")
        retriever = TFIDFRetriever(kb)
        provider = MockProvider()
        pipeline = AnsweringPipeline(kb, retriever, provider)

        assert pipeline.INSUFFICIENT_CONTEXT_MSG == (
            "I don't have enough information in the knowledge base to answer this question. "
            "Please contact the IT Service Desk at +1-555-0200 for assistance."
        )

    def test_custom_support_phone_via_constructor(self):
        """Test that custom phone number via constructor is used."""
        kb = KnowledgeBase.from_json_file("knowledge_base/runbooks.json")
        retriever = TFIDFRetriever(kb)
        provider = MockProvider()
        pipeline = AnsweringPipeline(kb, retriever, provider, support_phone="+1-800-123-4567")

        assert pipeline.INSUFFICIENT_CONTEXT_MSG == (
            "I don't have enough information in the knowledge base to answer this question. "
            "Please contact the IT Service Desk at +1-800-123-4567 for assistance."
        )

    def test_support_phone_env_var(self):
        """Test that SUPPORT_PHONE env var is used when set."""
        os.environ["SUPPORT_PHONE"] = "+1-999-888-7777"
        try:
            kb = KnowledgeBase.from_json_file("knowledge_base/runbooks.json")
            retriever = TFIDFRetriever(kb)
            provider = MockProvider()
            pipeline = AnsweringPipeline(kb, retriever, provider)

            assert pipeline.INSUFFICIENT_CONTEXT_MSG == (
                "I don't have enough information in the knowledge base to answer this question. "
                "Please contact the IT Service Desk at +1-999-888-7777 for assistance."
            )
        finally:
            os.environ.pop("SUPPORT_PHONE", None)

    def test_constructor_overrides_env_var(self):
        """Test that constructor parameter overrides env var."""
        os.environ["SUPPORT_PHONE"] = "+1-999-888-7777"
        try:
            kb = KnowledgeBase.from_json_file("knowledge_base/runbooks.json")
            retriever = TFIDFRetriever(kb)
            provider = MockProvider()
            pipeline = AnsweringPipeline(kb, retriever, provider, support_phone="+1-111-222-3333")

            assert pipeline.INSUFFICIENT_CONTEXT_MSG == (
                "I don't have enough information in the knowledge base to answer this question. "
                "Please contact the IT Service Desk at +1-111-222-3333 for assistance."
            )
        finally:
            os.environ.pop("SUPPORT_PHONE", None)


class TestKnowledgeBasePathValidation:
    """Tests for KNOWLEDGE_BASE_PATH validation during startup."""

    def test_missing_knowledge_base_path(self):
        """Test that missing knowledge base file raises RuntimeError."""
        # Set env var BEFORE importing the module
        os.environ["KNOWLEDGE_BASE_PATH"] = "/nonexistent/path.json"
        os.environ["LLM_PROVIDER"] = "mock"

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)
        from opsilot.api.main import lifespan
        from fastapi import FastAPI

        app = FastAPI(lifespan=lifespan)

        import asyncio
        async def test_lifespan():
            async with lifespan(app) as _:
                pass

        with pytest.raises(RuntimeError, match="Knowledge base file not found"):
            asyncio.run(test_lifespan())

        os.environ.pop("KNOWLEDGE_BASE_PATH", None)

    def test_directory_instead_of_file(self):
        """Test that directory path raises RuntimeError."""
        # Set env var to a directory BEFORE importing
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["KNOWLEDGE_BASE_PATH"] = tmpdir
            os.environ["LLM_PROVIDER"] = "mock"

            import importlib
            import opsilot.api.main
            importlib.reload(opsilot.api.main)
            from opsilot.api.main import lifespan
            from fastapi import FastAPI

            app = FastAPI(lifespan=lifespan)

            import asyncio
            async def test_lifespan():
                async with lifespan(app) as _:
                    pass

            with pytest.raises(RuntimeError, match="is not a file"):
                asyncio.run(test_lifespan())

        os.environ.pop("KNOWLEDGE_BASE_PATH", None)

    def test_valid_knowledge_base_path(self):
        """Test that valid knowledge base path works."""
        os.environ["KNOWLEDGE_BASE_PATH"] = "knowledge_base/runbooks.json"
        os.environ["LLM_PROVIDER"] = "mock"

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)
        from opsilot.api.main import lifespan
        from fastapi import FastAPI

        app = FastAPI(lifespan=lifespan)

        import asyncio
        async def test_lifespan():
            async with lifespan(app) as _:
                pass

        # Should not raise
        asyncio.run(test_lifespan())

        os.environ.pop("KNOWLEDGE_BASE_PATH", None)


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_defaults(self):
        """Test default CORS configuration."""
        from opsilot.api.main import CORS_ALLOWED_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOWED_METHODS, CORS_ALLOWED_HEADERS

        assert CORS_ALLOWED_ORIGINS == ["*"]
        assert CORS_ALLOW_CREDENTIALS is True
        assert CORS_ALLOWED_METHODS == ["*"]
        assert CORS_ALLOWED_HEADERS == ["*"]

    def test_cors_custom_origins(self):
        """Test custom CORS origins from env var."""
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://app.example.com,https://admin.example.com"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"
        os.environ["CORS_ALLOWED_METHODS"] = "GET,POST"
        os.environ["CORS_ALLOWED_HEADERS"] = "Content-Type,Authorization"

        # Need to reimport to pick up new env vars
        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.CORS_ALLOWED_ORIGINS == ["https://app.example.com", "https://admin.example.com"]
        assert opsilot.api.main.CORS_ALLOW_CREDENTIALS is True
        assert opsilot.api.main.CORS_ALLOWED_METHODS == ["GET", "POST"]
        assert opsilot.api.main.CORS_ALLOWED_HEADERS == ["Content-Type", "Authorization"]

        # Cleanup
        os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        os.environ.pop("CORS_ALLOW_CREDENTIALS", None)
        os.environ.pop("CORS_ALLOWED_METHODS", None)
        os.environ.pop("CORS_ALLOWED_HEADERS", None)

    def test_cors_credentials_with_wildcard_origin(self):
        """Test that credentials with wildcard origin is handled by FastAPI/Starlette."""
        # FastAPI's CORSMiddleware will handle this - it allows credentials with "*"
        # but in production this should be avoided. The middleware itself doesn't
        # prevent this configuration; it's a security best practice note.
        # We test that the configuration is parsed correctly.
        os.environ["CORS_ALLOWED_ORIGINS"] = "*"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.CORS_ALLOWED_ORIGINS == ["*"]
        assert opsilot.api.main.CORS_ALLOW_CREDENTIALS is True

        os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        os.environ.pop("CORS_ALLOW_CREDENTIALS", None)


class TestConfigurationParsing:
    """Tests for configuration parsing."""

    def test_knowledge_base_path_default(self):
        """Test KNOWLEDGE_BASE_PATH default value."""
        os.environ.pop("KNOWLEDGE_BASE_PATH", None)

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.KNOWLEDGE_BASE_PATH == "knowledge_base/runbooks.json"

    def test_cors_parsing_empty_string(self):
        """Test CORS parsing with empty string results in empty list."""
        os.environ["CORS_ALLOWED_ORIGINS"] = ""

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.CORS_ALLOWED_ORIGINS == []

        os.environ.pop("CORS_ALLOWED_ORIGINS", None)

    def test_rate_limit_parsing(self):
        """Test rate limit configuration parsing."""
        os.environ["RATE_LIMIT_ENABLED"] = "false"
        os.environ["RATE_LIMIT_REQUESTS"] = "100"
        os.environ["RATE_LIMIT_WINDOW"] = "120"

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.RATE_LIMIT_ENABLED is False
        assert opsilot.api.main.RATE_LIMIT_REQUESTS == 100
        assert opsilot.api.main.RATE_LIMIT_WINDOW == 120

        os.environ.pop("RATE_LIMIT_ENABLED", None)
        os.environ.pop("RATE_LIMIT_REQUESTS", None)
        os.environ.pop("RATE_LIMIT_WINDOW", None)


class TestCORSValidation:
    """Tests for CORS production validation."""

    def test_production_rejects_wildcard_with_credentials(self):
        """Test that production mode rejects wildcard origins with credentials."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["CORS_ALLOWED_ORIGINS"] = "*"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"

        import importlib
        import opsilot.api.main
        try:
            importlib.reload(opsilot.api.main)
            pytest.fail("Expected RuntimeError for wildcard origins with credentials in production")
        except RuntimeError as e:
            assert "CORS configuration error" in str(e)
            assert "wildcard origin" in str(e).lower() or "CORS_ALLOW_CREDENTIALS" in str(e)
        finally:
            os.environ.pop("ENVIRONMENT", None)
            os.environ.pop("CORS_ALLOWED_ORIGINS", None)
            os.environ.pop("CORS_ALLOW_CREDENTIALS", None)

    def test_production_rejects_wildcard_in_origins_list_with_credentials(self):
        """Test that production mode rejects wildcard in origins list with credentials."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://app.example.com,*"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"

        import importlib
        import opsilot.api.main
        try:
            importlib.reload(opsilot.api.main)
            pytest.fail("Expected RuntimeError for wildcard in origins list with credentials in production")
        except RuntimeError as e:
            assert "CORS configuration error" in str(e)
            assert "wildcard" in str(e).lower()
        finally:
            os.environ.pop("ENVIRONMENT", None)
            os.environ.pop("CORS_ALLOWED_ORIGINS", None)
            os.environ.pop("CORS_ALLOW_CREDENTIALS", None)

    def test_production_allows_explicit_origins_with_credentials(self):
        """Test that production mode allows explicit origins with credentials."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://app.example.com,https://admin.example.com"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.CORS_ALLOWED_ORIGINS == ["https://app.example.com", "https://admin.example.com"]
        assert opsilot.api.main.CORS_ALLOW_CREDENTIALS is True

        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        os.environ.pop("CORS_ALLOW_CREDENTIALS", None)

    def test_production_allows_wildcard_without_credentials(self):
        """Test that production mode allows wildcard origins when credentials disabled."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["CORS_ALLOWED_ORIGINS"] = "*"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "false"

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.CORS_ALLOWED_ORIGINS == ["*"]
        assert opsilot.api.main.CORS_ALLOW_CREDENTIALS is False

        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        os.environ.pop("CORS_ALLOW_CREDENTIALS", None)

    def test_development_allows_wildcard_with_credentials(self):
        """Test that development mode allows wildcard origins with credentials."""
        os.environ["ENVIRONMENT"] = "development"
        os.environ["CORS_ALLOWED_ORIGINS"] = "*"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.CORS_ALLOWED_ORIGINS == ["*"]
        assert opsilot.api.main.CORS_ALLOW_CREDENTIALS is True

        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        os.environ.pop("CORS_ALLOW_CREDENTIALS", None)

    def test_cors_strips_whitespace(self):
        """Test that CORS origin parsing strips whitespace."""
        os.environ["CORS_ALLOWED_ORIGINS"] = " https://app.example.com , https://admin.example.com "

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.CORS_ALLOWED_ORIGINS == ["https://app.example.com", "https://admin.example.com"]

        os.environ.pop("CORS_ALLOWED_ORIGINS", None)

    def test_cors_handles_empty_elements(self):
        """Test that CORS parsing handles empty elements gracefully."""
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://app.example.com,,https://admin.example.com,"

        import importlib
        import opsilot.api.main
        importlib.reload(opsilot.api.main)

        assert opsilot.api.main.CORS_ALLOWED_ORIGINS == ["https://app.example.com", "https://admin.example.com"]

        os.environ.pop("CORS_ALLOWED_ORIGINS", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])