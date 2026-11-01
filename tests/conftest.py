"""Shared test configuration and fixtures."""

import pytest
import tempfile
import json
from pathlib import Path

from opsilot.knowledge_base.loader import KnowledgeBase, Runbook
from opsilot.retrieval.retriever import TFIDFRetriever
from opsilot.answering.pipeline import AnsweringPipeline
from opsilot.providers.mock import MockProvider
from opsilot.cache.cache import AnswerCache


@pytest.fixture
def sample_runbooks():
    """Sample runbooks for testing."""
    return [
        Runbook(
            runbook_id="mfa-reset-001",
            title="MFA Reset Procedure",
            category="security",
            content=(
                "To reset a user's MFA: 1. Navigate to Admin Console > Users. "
                "2. Select the user. 3. Click 'Reset MFA'. "
                "4. User will be prompted to re-enroll on next login."
            ),
            tags=["mfa", "authentication", "reset"],
        ),
        Runbook(
            runbook_id="vpn-troubleshoot-001",
            title="VPN Troubleshooting",
            category="network",
            content=(
                "VPN troubleshooting steps: 1. Verify user credentials. "
                "2. Check firewall rules for UDP 500/4500. "
                "3. Validate certificate expiration. "
                "4. Review connection logs."
            ),
            tags=["vpn", "network", "troubleshooting"],
        ),
        Runbook(
            runbook_id="dhcp-issues-001",
            title="DHCP Issues",
            category="network",
            content=(
                "DHCP troubleshooting: 1. Check DHCP server status. "
                "2. Verify scope not exhausted. "
                "3. Check for rogue DHCP servers. "
                "4. Review DHCP logs for errors."
            ),
            tags=["dhcp", "network", "ip"],
        ),
        Runbook(
            runbook_id="cert-renewal-001",
            title="Certificate Renewal",
            category="security",
            content=(
                "To renew SSL/TLS certificate: 1. Generate new CSR. "
                "2. Submit to CA. 3. Install new certificate. "
                "4. Update load balancer. 5. Verify expiration date."
            ),
            tags=["certificate", "ssl", "tls", "renewal"],
        ),
    ]


@pytest.fixture
def knowledge_base(sample_runbooks):
    """Create a KnowledgeBase with sample runbooks."""
    return KnowledgeBase(sample_runbooks)


@pytest.fixture
def retriever(knowledge_base):
    """Create a TFIDFRetriever with sample knowledge base."""
    return TFIDFRetriever(knowledge_base)


@pytest.fixture
def mock_provider():
    """Create a MockProvider for testing."""
    return MockProvider()


@pytest.fixture
def full_pipeline(knowledge_base, retriever, mock_provider):
    """Create a full AnsweringPipeline with mock provider."""
    return AnsweringPipeline(
        knowledge_base=knowledge_base,
        retriever=retriever,
        llm_provider=mock_provider,
        min_relevance_score=0.1,
        top_k=3,
    )


@pytest.fixture
def temp_eval_file():
    """Create a temporary evaluation cases file."""
    cases = [
        {
            "question": "How do I reset MFA?",
            "expected_answerable": True,
            "expected_sources": ["mfa-reset-001"],
            "category": "security",
            "difficulty": "easy",
        },
        {
            "question": "What is the meaning of life?",
            "expected_answerable": False,
            "expected_sources": [],
            "category": "general",
            "difficulty": "trick",
        },
        {
            "question": "How to troubleshoot VPN?",
            "expected_answerable": True,
            "expected_sources": ["vpn-troubleshoot-001"],
            "category": "network",
            "difficulty": "easy",
        },
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(cases, f)
        temp_path = f.name
    yield temp_path
    Path(temp_path).unlink(missing_ok=True)