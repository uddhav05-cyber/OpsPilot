"""Tests for cache module."""

import pytest
import time
from opsilot.cache.cache import AnswerCache, QuestionNormalizer, CacheEntry, CacheStats
from opsilot.answering.pipeline import Answer
from opsilot.knowledge_base.loader import Runbook


@pytest.fixture
def sample_answer():
    return Answer(
        answer="Test answer with citations.",
        citations=[{"runbook_id": "kb-001", "title": "Test", "category": "test", "score": 0.9}],
        retrieval_scores=[0.9],
        provider="mock",
        model="mock-v1.0",
    )


@pytest.fixture
def cache():
    return AnswerCache(ttl_seconds=1)  # Short TTL for testing


class TestQuestionNormalizer:
    """Tests for QuestionNormalizer."""

    def test_normalize_basic(self):
        normalizer = QuestionNormalizer()
        assert normalizer.normalize("  How to Reset MFA?  ") == "how to reset mfa"
        assert normalizer.normalize("ENABLE/DISABLE") == "enable disable"

    def test_normalize_case_insensitive(self):
        normalizer = QuestionNormalizer()
        assert normalizer.normalize("ENABLE") == "enable"
        assert normalizer.normalize("enable") == "enable"

    def test_has_opposite_intent_enable_disable(self):
        normalizer = QuestionNormalizer()
        assert normalizer.has_opposite_intent("how to enable and disable feature") is True

    def test_has_opposite_intent_allow_block(self):
        normalizer = QuestionNormalizer()
        assert normalizer.has_opposite_intent("allow and block traffic") is True

    def test_has_opposite_intent_install_uninstall(self):
        normalizer = QuestionNormalizer()
        assert normalizer.has_opposite_intent("install and uninstall package") is True

    def test_no_opposite_intent_same_action(self):
        normalizer = QuestionNormalizer()
        assert normalizer.has_opposite_intent("how to enable feature") is False

    def test_no_opposite_intent_different_topic(self):
        normalizer = QuestionNormalizer()
        assert normalizer.has_opposite_intent("enable feature and configure network") is False


class TestAnswerCache:
    """Tests for AnswerCache."""

    def test_get_miss_empty_cache(self, cache, sample_answer):
        result = cache.get("question", "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        assert result is None

    def test_set_and_get(self, cache, sample_answer):
        cache.set("test question", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        result = cache.get("test question", "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        assert result is not None
        assert result.answer == sample_answer.answer

    def test_get_miss_different_question(self, cache, sample_answer):
        cache.set("question one", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        result = cache.get("question two", "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        assert result is None

    def test_get_miss_different_config(self, cache, sample_answer):
        cache.set("question", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        result = cache.get("question", "mock", "mock-v1.0", 0.5, 500, 0.15, 5)  # Different temp
        assert result is None

    def test_ttl_expiration(self, cache, sample_answer):
        cache.set("question", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        # Immediately available
        assert cache.get("question", "mock", "mock-v1.0", 0.3, 500, 0.15, 5) is not None
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("question", "mock", "mock-v1.0", 0.3, 500, 0.15, 5) is None

    def test_negation_guard_prevents_caching(self, cache, sample_answer):
        # Question with opposite intent should not be cached
        cache.set("enable and disable feature", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        result = cache.get("enable and disable feature", "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        assert result is None

    def test_evict_expired(self, cache, sample_answer):
        cache.set("q1", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        cache.set("q2", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        time.sleep(1.1)
        evicted = cache._evict_expired()
        assert evicted == 2
        stats = cache.stats()
        assert stats.entries == 0

    def test_clear(self, cache, sample_answer):
        cache.set("q1", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        cache.set("q2", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        cleared = cache.clear()
        assert cleared == 2
        stats = cache.stats()
        assert stats.entries == 0

    def test_stats(self, cache, sample_answer):
        cache.set("q1", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        # Hit
        cache.get("q1", "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        # Miss
        cache.get("q2", "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        stats = cache.stats()
        assert stats.total_requests == 2
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.hit_rate == 0.5

    def test_config_hash_differentiates(self, cache, sample_answer):
        cache.set("question", sample_answer, "mock", "mock-v1.0", 0.3, 500, 0.15, 5)
        result = cache.get("question", "gemini", "gemini-model", 0.3, 500, 0.15, 5)
        assert result is None  # Different provider = different config hash