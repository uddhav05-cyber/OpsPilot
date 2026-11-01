"""LLM Provider package exports."""

from opsilot.providers.base import LLMProvider, LLMResponse

# Import concrete implementations
from opsilot.providers.mock import MockProvider
from opsilot.providers.gemini_provider import GeminiProvider
from opsilot.providers.openai_provider import OpenAIProvider


def get_provider(name: str) -> LLMProvider | None:
    """Get provider instance by name."""
    providers = {
        "mock": MockProvider(),
        "gemini": GeminiProvider(),
        "openai": OpenAIProvider(),
    }
    return providers.get(name.lower())


def list_providers() -> list[LLMProvider]:
    """List all available provider instances."""
    return [MockProvider(), GeminiProvider(), OpenAIProvider()]


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "MockProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "get_provider",
    "list_providers",
]