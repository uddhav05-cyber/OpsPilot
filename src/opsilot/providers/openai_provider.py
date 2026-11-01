"""OpenAI API provider for live LLM responses."""

import os
from typing import Optional

from opsilot.providers.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI API provider for live LLM responses."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._timeout = timeout
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "OpenAI provider not available. Install 'openai' package."
                )
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """Generate a response using OpenAI API."""
        if not self.is_available():
            raise RuntimeError(
                "OpenAI provider not available. Check API key and openai package."
            )

        client = self._get_client()

        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self._timeout,
            )

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                model=self._model,
                content=choice.message.content or "",
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            )

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

    async def health_check(self) -> dict:
        if not self.is_available():
            return {
                "provider": self.name,
                "status": "unavailable",
                "reason": "Missing OPENAI_API_KEY",
                "model": self._model,
            }

        try:
            client = self._get_client()
            # Quick model list call to verify connectivity
            client.models.list()
            return {
                "provider": self.name,
                "status": "healthy",
                "model": self._model,
            }
        except Exception as e:
            return {
                "provider": self.name,
                "status": "degraded",
                "error": str(e),
                "model": self._model,
            }