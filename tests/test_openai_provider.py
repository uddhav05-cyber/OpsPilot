"""Tests for OpenAI provider."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opsilot.providers.openai_provider import OpenAIProvider


class TestOpenAIProvider:
    """Tests for OpenAIProvider class."""

    def setup_method(self):
        """Reset mocks before each test."""
        pass

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_openai_provider_available_with_key(self, mock_openai_class):
        """Test that provider is available when API key is set."""
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance

        provider = OpenAIProvider()
        assert provider.is_available() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_openai_provider_not_available_without_key(self):
        """Test that provider is not available when API key is not set."""
        provider = OpenAIProvider(api_key=None)
        assert provider.is_available() is False

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    async def test_generate_response(self, mock_openai_class):
        """Test generating a response."""
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance

        # Mock the chat.completions.create response
        mock_choice = MagicMock()
        mock_choice.message.content = "Test response from OpenAI"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client_instance.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o-mini")
        response = await provider.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is 2+2?",
            temperature=0.3,
            max_tokens=100,
        )

        assert response.content == "Test response from OpenAI"
        assert response.model == "gpt-4o-mini"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    async def test_generate_with_custom_params(self, mock_openai_class):
        """Test generating with custom temperature and max_tokens."""
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance

        mock_choice = MagicMock()
        mock_choice.message.content = "Custom response"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 15
        mock_usage.total_tokens = 20

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client_instance.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider()
        await provider.generate(
            system_prompt="System prompt",
            user_prompt="User question",
            temperature=0.7,
            max_tokens=200,
        )

        # Verify the call was made with correct parameters
        call_args = mock_client_instance.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.7
        assert call_args.kwargs["max_tokens"] == 200
        assert call_args.kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_generate_raises_when_unavailable(self):
        """Test that generate raises RuntimeError when provider unavailable."""
        provider = OpenAIProvider(api_key=None)
        with pytest.raises(RuntimeError, match="not available"):
            await provider.generate("system", "user")

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    async def test_health_check_healthy(self, mock_openai_class):
        """Test health check returns healthy when client works."""
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance
        mock_client_instance.models.list.return_value = []

        provider = OpenAIProvider()
        health = await provider.health_check()

        assert health["provider"] == "openai"
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    async def test_health_check_degraded(self, mock_openai_class):
        """Test health check returns degraded when client fails."""
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance
        mock_client_instance.models.list.side_effect = Exception("Connection failed")

        provider = OpenAIProvider()
        health = await provider.health_check()

        assert health["provider"] == "openai"
        assert health["status"] == "degraded"
        assert "error" in health

    @pytest.mark.asyncio
    async def test_health_check_unavailable(self):
        """Test health check returns unavailable when no API key."""
        provider = OpenAIProvider(api_key=None)
        health = await provider.health_check()

        assert health["provider"] == "openai"
        assert health["status"] == "unavailable"
        assert health["reason"] == "Missing OPENAI_API_KEY"

    def test_name_property(self):
        """Test name property returns 'openai'."""
        provider = OpenAIProvider()
        assert provider.name == "openai"

    def test_model_property(self):
        """Test model is set correctly."""
        provider = OpenAIProvider(model="custom-model")
        assert provider._model == "custom-model"

    @patch.dict(os.environ, {"OPENAI_MODEL": "env-model"})
    def test_model_from_env(self):
        """Test model can be set from environment variable."""
        provider = OpenAIProvider()
        assert provider._model == "env-model"