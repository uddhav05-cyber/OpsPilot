"""LLM Provider package exports."""

from opsilot.providers.base import LLMProvider, LLMResponse

# Import concrete implementations
from opsilot.providers.mock import MockProvider
from opsilot.providers.gemini_provider import GeminiProvider
from opsilot.providers.openai_provider import OpenAIProvider

# Cache for provider instances
_provider_cache: dict[str, LLMProvider] = {}


def get_provider(name: str) -> LLMProvider | None:
    """Get provider instance by name (cached)."""
    name = name.lower()
    if name not in _provider_cache:
        providers = {
            "mock": MockProvider(),
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
        }
        _provider_cache[name] = providers.get(name)
    return _provider_cache.get(name)


def list_providers() -> list[LLMProvider]:
    """List all available provider instances (cached)."""
    providers = []
    for name in ["mock", "gemini", "openai"]:
        providers.append(get_provider(name))
    return providers


def clear_provider_cache() -> None:
    """Clear the provider instance cache (useful for testing)."""
    _provider_cache.clear()


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "MockProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "get_provider",
    "list_providers",
    "clear_provider_cache",
]