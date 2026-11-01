"""Mock provider that generates template-based responses for demo purposes."""

import os
import random
from typing import Optional

from opsilot.providers.base import LLMProvider, LLMResponse


class MockProvider(LLMProvider):
    """Mock provider that generates template-based responses for demo purposes."""

    _call_count: int = 0

    # Demo response templates by category
    _TEMPLATES: dict[str, list[str]] = {
        "security": [
            "Based on the runbook '{title}' (ID: {runbook_id}):\n{content}",
            "Security procedure from '{title}':\n{content}",
        ],
        "network": [
            "Network troubleshooting from '{title}' (ID: {runbook_id}):\n{content}",
            "Following the '{title}' runbook:\n{content}",
        ],
        "infrastructure": [
            "Infrastructure operation from '{title}' (ID: {runbook_id}):\n{content}",
            "Per '{title}' runbook:\n{content}",
        ],
        "application": [
            "Application management from '{title}' (ID: {runbook_id}):\n{content}",
            "App procedure '{title}':\n{content}",
        ],
        "default": [
            "According to '{title}' (ID: {runbook_id}):\n{content}",
            "Runbook '{title}' states:\n{content}",
        ],
    }

    DEMO_PREFIX = "[DEMO MODE] "

    @property
    def name(self) -> str:
        return "mock"

    def is_available(self) -> bool:
        return True

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """Generate a mock response based on the prompt content."""
        MockProvider._call_count += 1

        # Extract context from user prompt
        context_docs = self._extract_context(user_prompt)
        sources = self._extract_sources(user_prompt)
        question = self._extract_question_part(user_prompt)

        # Check if we have relevant context
        if not context_docs or not self._is_context_sufficient(context_docs, question):
            content = (
                f"{self.DEMO_PREFIX}I don't have enough information in the knowledge base "
                "to answer this question. Please contact the IT Service Desk at "
                "+1-555-0200 for assistance."
            )
            return self._build_response(content, sources)

        # Generate mock content based on context
        content = self._generate_mock_content(context_docs, sources, question)

        return self._build_response(content, sources)

    def _extract_context(self, user_prompt: str) -> list[str]:
        """Extract context documents from prompt."""
        # Look for context sections in the prompt
        lines = user_prompt.split("\n")
        context_docs = []
        in_context = False

        for line in lines:
            if "CONTEXT DOCUMENTS" in line.upper() or "CONTEXT:" in line.upper():
                in_context = True
                continue
            if in_context and line.strip().startswith("["):
                # Format: [doc_0] Title: content
                context_docs.append(line.strip())
            elif in_context and not line.strip():
                break

        return context_docs

    def _extract_sources(self, user_prompt: str) -> list[dict]:
        """Extract source citations from prompt."""
        import re

        sources = []
        # Match patterns like [doc_0] Title (category) - score: 0.85
        pattern = r"\[doc_(\d+)\]\s+([^(]+)\s*\(([^)]+)\)\s*-\s*score:\s*([\d.]+)"
        for match in re.finditer(pattern, user_prompt):
            sources.append({
                "runbook_id": match.group(2).strip(),
                "title": match.group(2).strip(),
                "category": match.group(3).strip(),
                "score": float(match.group(4)),
            })
        return sources

    def _extract_question_part(self, user_prompt: str) -> str:
        """Extract the actual question from the prompt."""
        lines = user_prompt.split("\n")
        for line in lines:
            if line.strip().startswith("Question:") or line.strip().startswith("QUESTION:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _is_context_sufficient(self, context_docs: list[str], question: str) -> bool:
        """Check if context is sufficient to answer."""
        if not context_docs:
            return False
        # Simple heuristic: at least one doc with reasonable length
        return any(len(doc) > 50 for doc in context_docs)

    def _generate_mock_content(
        self,
        context_docs: list[str],
        sources: list[dict],
        question: str,
    ) -> str:
        """Generate mock answer content."""
        if not sources:
            return (
                f"{self.DEMO_PREFIX}I found some relevant documents but couldn't extract "
                "specific sources. Please contact the IT Service Desk at +1-555-0200."
            )

        # Use first source as primary
        primary = sources[0]
        category = primary.get("category", "default")

        templates = self._TEMPLATES.get(category, self._TEMPLATES["default"])
        template = random.choice(templates)

        # Build response with citations
        content_parts = []
        for i, source in enumerate(sources[:3]):  # Max 3 sources
            title = source.get("title", "Unknown")
            runbook_id = source.get("runbook_id", "unknown")
            # Find matching context doc
            context = ""
            for doc in context_docs:
                if title in doc or runbook_id in doc:
                    # Extract content after the doc marker
                    parts = doc.split(":", 1)
                    if len(parts) > 1:
                        context = parts[1].strip()[:200]
                    break

            if context:
                filled = template.format(title=title, runbook_id=runbook_id, content=context)
                content_parts.append(f"[doc_{i}] {filled}")
            else:
                content_parts.append(
                    f"[doc_{i}] {template.format(title=title, runbook_id=runbook_id, content='See runbook for details.')}"
                )

        return f"{self.DEMO_PREFIX}" + "\n\n".join(content_parts)

    def _build_response(self, content: str, sources: list[dict]) -> LLMResponse:
        """Build LLMResponse with token counts."""
        prompt_tokens = 150  # Approximate
        completion_tokens = len(content.split()) * 1.3  # Rough estimate

        return LLMResponse(
            model="mock-v1.0",
            content=content,
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            total_tokens=int(prompt_tokens + completion_tokens),
        )

    async def health_check(self) -> dict:
        return {
            "provider": self.name,
            "status": "healthy",
            "model": "mock-v1.0",
            "call_count": MockProvider._call_count,
        }