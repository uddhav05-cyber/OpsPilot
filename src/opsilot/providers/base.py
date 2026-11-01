"""Defines the interface that all LLM providers must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    model: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @property
    def prompt_tokens(self) -> int:
        return self._prompt_tokens

    @prompt_tokens.setter
    def prompt_tokens(self, value: int) -> None:
        self._prompt_tokens = value

    @property
    def completion_tokens(self) -> int:
        return self._completion_tokens

    @completion_tokens.setter
    def completion_tokens(self, value: int) -> None:
        self._completion_tokens = value

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @total_tokens.setter
    def total_tokens(self, value: int) -> None:
        self._total_tokens = value


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'mock', 'openai', 'gemini')."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        ...

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System/instruction prompt
            user_prompt: User's question with context
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content and token counts
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """
        Health check for the provider.

        Returns:
            Dict with status information
        """
        ...