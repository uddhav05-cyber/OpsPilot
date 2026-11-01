"""Tests for answering pipeline and providers."""

import pytest
from opsilot.knowledge_base.loader import KnowledgeBase, Runbook
from opsilot.retrieval.retriever import TFIDFRetriever
from opsilot.answering.pipeline import AnsweringPipeline
from opsilot.providers.mock import MockProvider


@pytest.fixture
def sample_knowledge_base():
    """Create a sample knowledge base for testing."""
    runbooks = [
        Runbook(
            runbook_id="kb-001",
            title="Printer Troubleshooting",
            category="hardware",
            content="Check printer is on and shows Ready. Same network subnet (10.0.x.x office). Re-add in Settings > Devices. Use universal driver from software portal. Cancel stuck jobs. Download driver from hp.com/support. Contact facilities@corp.example.com for hardware issues.",
            tags=["printer", "hardware", "troubleshooting"],
        ),
        Runbook(
            runbook_id="kb-002",
            title="VPN Setup",
            category="network",
            content="Install VPN client from portal. Use corporate credentials. Select 'Office' gateway. Enable split tunneling. Test connection to 10.0.1.1.",
            tags=["vpn", "network", "remote"],
        ),
    ]
    return KnowledgeBase(runbooks)


@pytest.fixture
def retriever(sample_knowledge_base):
    return TFIDFRetriever(sample_knowledge_base)


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def pipeline(sample_knowledge_base, retriever, mock_provider):
    return AnsweringPipeline(
        knowledge_base=sample_knowledge_base,
        retriever=retriever,
        llm_provider=mock_provider,
        min_relevance_score=0.1,
        top_k=2,
    )


class TestMockProvider:
    """Tests for MockProvider."""

    def test_mock_provider_available(self):
        provider = MockProvider()
        assert provider.is_available() is True
        assert provider.name == "mock"

    @pytest.mark.asyncio
    async def test_mock_generate(self, mock_provider):
        response = await mock_provider.generate(
            system_prompt="You are helpful.",
            user_prompt="Test question",
            temperature=0.3,
            max_tokens=100,
        )
        assert response.model == "mock-v1.0"
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_mock_health_check(self, mock_provider):
        health = await mock_provider.health_check()
        assert health["provider"] == "mock"
        assert health["status"] == "healthy"
        assert health["model"] == "mock-v1.0"


class TestAnsweringPipeline:
    """Tests for AnsweringPipeline."""

    @pytest.mark.asyncio
    async def test_answer_with_relevant_context(self, pipeline):
        answer = await pipeline.answer("How do I fix printer issues?")
        assert isinstance(answer.answer, str)
        assert len(answer.answer) > 0
        assert answer.provider == "mock"
        assert answer.cached is False

    @pytest.mark.asyncio
    async def test_answer_insufficient_context(self, pipeline):
        answer = await pipeline.answer("How do I bake a cake?")
        assert "enough information" in answer.answer.lower()
        assert answer.citations == []
        assert answer.retrieval_scores == []

    @pytest.mark.asyncio
    async def test_answer_citations_format(self, pipeline):
        answer = await pipeline.answer("Printer not working")
        for citation in answer.citations:
            assert "runbook_id" in citation
            assert "title" in citation
            assert "category" in citation
            assert "score" in citation

    def test_system_prompt_contains_rules(self):
        prompt = AnsweringPipeline.SYSTEM_PROMPT
        assert "OpsPilot" in prompt
        assert "ONLY from the supplied context" in prompt
        assert "[doc_N]" in prompt
        assert "enough information" in prompt