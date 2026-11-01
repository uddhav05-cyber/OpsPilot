"""Tests for retrieval module."""

import pytest
from opsilot.knowledge_base.loader import KnowledgeBase, Runbook
from opsilot.retrieval.retriever import TFIDFRetriever, QueryExpander, TextNormalizer


@pytest.fixture
def sample_knowledge_base():
    runbooks = [
        Runbook(
            runbook_id="hw-001",
            title="Printer Troubleshooting",
            category="hardware",
            content="Check printer is on, same network subnet, re-add in Settings. Use universal driver from portal.",
            tags=["printer", "hardware"],
        ),
        Runbook(
            runbook_id="net-001",
            title="DHCP Issues",
            category="network",
            content="Check DHCP server status, verify scope not exhausted, check for rogue DHCP servers.",
            tags=["dhcp", "network"],
        ),
        Runbook(
            runbook_id="sec-001",
            title="MFA Reset",
            category="security",
            content="Navigate to Admin Console > Users. Select user. Click Reset MFA. User re-enrolls on next login.",
            tags=["mfa", "security"],
        ),
    ]
    return KnowledgeBase(runbooks)


@pytest.fixture
def retriever(sample_knowledge_base):
    return TFIDFRetriever(sample_knowledge_base)


class TestTextNormalizer:
    """Tests for TextNormalizer."""

    def test_normalize_basic(self):
        normalizer = TextNormalizer()
        assert normalizer.normalize("  Hello   World  ") == "hello world"
        assert normalizer.normalize("UPPERCASE") == "uppercase"
        assert normalizer.normalize("Special!@#Chars") == "specialchars"

    def test_normalize_preserves_abbreviations(self):
        normalizer = TextNormalizer()
        # Abbreviations should be preserved (lowercased but not expanded)
        result = normalizer.normalize("DHCP and DNS issues")
        assert "dhcp" in result
        assert "dns" in result

    def test_normalize_collapses_whitespace(self):
        normalizer = TextNormalizer()
        assert normalizer.normalize("multiple    spaces") == "multiple spaces"
        assert normalizer.normalize("\ttabs\tand\nnewlines") == "tabs and newlines"


class TestQueryExpander:
    """Tests for QueryExpander."""

    def test_expand_basic(self):
        expander = QueryExpander()
        result = expander.expand("reset mfa")
        assert "reset" in result
        assert "reconfigure" in result or "reinitialize" in result

    def test_expand_abbreviations(self):
        expander = QueryExpander()
        result = expander.expand("dhcp not working")
        assert "dynamic host configuration protocol" in result

    def test_expand_multiple_abbreviations(self):
        expander = QueryExpander()
        result = expander.expand("vpn mfa dhcp")
        assert "virtual private network" in result
        assert "multi-factor authentication" in result
        assert "dynamic host configuration protocol" in result

    def test_expand_no_change_for_unknown(self):
        expander = QueryExpander()
        result = expander.expand("xyz unknown term")
        assert result == "xyz unknown term"


class TestTFIDFRetriever:
    """Tests for TFIDFRetriever."""

    def test_retrieve_basic(self, retriever):
        result = retriever.retrieve("printer not working", top_k=2, min_score=0.1)
        assert len(result.documents) <= 2
        assert len(result.scores) == len(result.documents)
        assert len(result.runbook_ids) == len(result.documents)
        # Should find printer runbook
        assert any("printer" in doc.title.lower() for doc in result.documents)

    def test_retrieve_dhcp(self, retriever):
        result = retriever.retrieve("dhcp issues", top_k=2, min_score=0.1)
        assert any("dhcp" in doc.title.lower() for doc in result.documents)

    def test_retrieve_mfa(self, retriever):
        result = retriever.retrieve("reset mfa", top_k=2, min_score=0.1)
        assert any("mfa" in doc.title.lower() for doc in result.documents)

    def test_retrieve_min_score_filter(self, retriever):
        # High threshold should return fewer results
        result_low = retriever.retrieve("printer", top_k=5, min_score=0.01)
        result_high = retriever.retrieve("printer", top_k=5, min_score=0.5)
        assert len(result_high.documents) <= len(result_low.documents)

    def test_retrieve_top_k_limit(self, retriever):
        result = retriever.retrieve("printer", top_k=1, min_score=0.01)
        assert len(result.documents) <= 1

    def test_retrieve_no_results(self, retriever):
        result = retriever.retrieve("completely unrelated xyz", top_k=5, min_score=0.5)
        assert len(result.documents) == 0

    def test_retrieve_scores_sorted(self, retriever):
        result = retriever.retrieve("printer", top_k=3, min_score=0.01)
        scores = result.scores
        assert scores == sorted(scores, reverse=True)

    def test_configure_rebuilds_index(self, retriever, sample_knowledge_base):
        original_params = retriever._vectorizer_params.copy()
        retriever.configure(ngram_range=(1, 3))
        assert retriever._vectorizer_params["ngram_range"] == (1, 3)
        assert retriever._vectorizer_params != original_params

    def test_retrieval_result_structure(self, retriever):
        result = retriever.retrieve("printer", top_k=2, min_score=0.1)
        assert hasattr(result, "documents")
        assert hasattr(result, "scores")
        assert hasattr(result, "runbook_ids")
        assert isinstance(result.documents, list)
        assert isinstance(result.scores, list)
        assert isinstance(result.runbook_ids, list)