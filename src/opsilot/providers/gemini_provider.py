"""Google Gemini API provider for live LLM responses using google-genai SDK."""

import os
from typing import Optional

from opsilot.providers.base import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """Google Gemini API provider for live LLM responses using google-genai SDK."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._timeout = timeout
        self._client = None

    @property
    def name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "Gemini provider not available. Install 'google-genai' package (>=2.34.0)."
                )
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """Generate a response using Gemini API via google-genai SDK."""
        if not self.is_available():
            raise RuntimeError(
                "Gemini provider not available. Check GEMINI_API_KEY and google-genai package."
            )

        client = self._get_client()

        try:
            from google.genai import types

            # Combine system and user prompts for Gemini
            # Gemini uses a single prompt with system instruction
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            response = client.models.generate_content(
                model=self._model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
                # Apply timeout
                timeout=self._timeout,
            )

            # Extract content
            content = response.text or ""

            # Extract token usage
            usage_metadata = getattr(response, "usage_metadata", None)
            if usage_metadata:
                prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0)
                completion_tokens = getattr(usage_metadata, "candidates_token_count", 0)
                total_tokens = prompt_tokens + completion_tokens
            else:
                # Fallback estimates
                prompt_tokens = len(full_prompt.split()) * 1.3
                completion_tokens = len(content.split()) * 1.3
                total_tokens = prompt_tokens + completion_tokens

            return LLMResponse(
                model=self._model,
                content=content,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=int(total_tokens),
            )

        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}") from e

    async def health_check(self) -> dict:
        if not self.is_available():
            return {
                "provider": self.name,
                "status": "unavailable",
                "reason": "Missing GEMINI_API_KEY",
                "model": self._model,
            }

        try:
            client = self._get_client()
            # Quick model list call to verify connectivity
            list(client.models.list())
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