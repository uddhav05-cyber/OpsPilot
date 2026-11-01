"""Tests for Gemini provider."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opsilot.providers.gemini_provider import GeminiProvider


class TestGeminiProvider:
    """Tests for GeminiProvider class."""

    def setup_method(self):
        """Reset mocks before each test."""
        pass

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("google.genai.Client")
    def test_gemini_provider_available_with_key(self, mock_client_class):
        """Test that provider is available when API key is set."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        provider = GeminiProvider()
        assert provider.is_available() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_gemini_provider_not_available_without_key(self):
        """Test that provider is not available when API key is not set."""
        provider = GeminiProvider(api_key=None)
        assert provider.is_available() is False

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("google.genai.Client")
    async def test_generate_response(self, mock_client_class):
        """Test generating a response."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        # Mock the generate_content response
        mock_response = MagicMock()
        mock_response.text = "Test response from Gemini"
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 20
        mock_response.usage_metadata = mock_usage

        mock_client_instance.models.generate_content.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash-exp")
        response = await provider.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is 2+2?",
            temperature=0.3,
            max_tokens=100,
        )

        assert response.content == "Test response from Gemini"
        assert response.model == "gemini-2.0-flash-exp"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("google.genai.Client")
    async def test_generate_with_custom_params(self, mock_client_class):
        """Test generating with custom temperature and max_tokens."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        mock_response = MagicMock()
        mock_response.text = "Custom response"
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 5
        mock_usage.candidates_token_count = 15
        mock_response.usage_metadata = mock_usage

        mock_client_instance.models.generate_content.return_value = mock_response

        provider = GeminiProvider()
        await provider.generate(
            system_prompt="System prompt",
            user_prompt="User question",
            temperature=0.7,
            max_tokens=200,
        )

        # Verify GenerateContentConfig was called with correct params
        call_args = mock_client_instance.models.generate_content.call_args
        config = call_args.kwargs.get("config")
        assert config is not None
        assert config.temperature == 0.7
        assert config.max_output_tokens == 200

    @pytest.mark.asyncio
    async def test_generate_raises_when_unavailable(self):
        """Test that generate raises RuntimeError when provider unavailable."""
        provider = GeminiProvider(api_key=None)
        with pytest.raises(RuntimeError, match="not available"):
            await provider.generate("system", "user")

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("google.genai.Client")
    async def test_health_check_healthy(self, mock_client_class):
        """Test health check returns healthy when client works."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.models.list.return_value = iter([])

        provider = GeminiProvider()
        health = await provider.health_check()

        assert health["provider"] == "gemini"
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("google.genai.Client")
    async def test_health_check_degraded(self, mock_client_class):
        """Test health check returns degraded when client fails."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.models.list.side_effect = Exception("Connection failed")

        provider = GeminiProvider()
        health = await provider.health_check()

        assert health["provider"] == "gemini"
        assert health["status"] == "degraded"
        assert "error" in health

    @pytest.mark.asyncio
    async def test_health_check_unavailable(self):
        """Test health check returns unavailable when no API key."""
        provider = GeminiProvider(api_key=None)
        health = await provider.health_check()

        assert health["provider"] == "gemini"
        assert health["status"] == "unavailable"
        assert health["reason"] == "Missing GEMINI_API_KEY"

    def test_name_property(self):
        """Test name property returns 'gemini'."""
        provider = GeminiProvider()
        assert provider.name == "gemini"

    def test_model_property(self):
        """Test model is set correctly."""
        provider = GeminiProvider(model="custom-model")
        assert provider._model == "custom-model"

    @patch.dict(os.environ, {"GEMINI_MODEL": "env-model"})
    def test_model_from_env(self):
        """Test model can be set from environment variable."""
        provider = GeminiProvider()
        assert provider._model == "env-model"