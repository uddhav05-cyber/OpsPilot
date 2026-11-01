"""TTL-based cache for answers with exact-match keys and negation guard."""

from __future__ import annotations

import hashlib
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from opsilot.answering.pipeline import Answer


@dataclass
class CacheEntry:
    """A cached answer entry."""

    answer: Answer
    question_normalized: str
    ttl_seconds: int
    config_hash: str
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds


@dataclass
class CacheStats:
    """Cache statistics."""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    entries: int = 0
    expired_entries: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests


class QuestionNormalizer:
    """Normalizes questions for cache key generation."""

    # Pairs of opposite intents - if both appear, don't cache
    NEGATION_PAIRS: list[tuple[str, str]] = [
        ("enable", "disable"),
        ("allow", "block"),
        ("install", "uninstall"),
        ("start", "stop"),
        ("create", "delete"),
        ("add", "remove"),
        ("grant", "revoke"),
        ("connect", "disconnect"),
        ("lock", "unlock"),
        ("encrypt", "decrypt"),
    ]

    def __init__(self):
        self._compiled_pairs = [
            (re.compile(rf"\b{re.escape(a)}\b", re.I), re.compile(rf"\b{re.escape(b)}\b", re.I))
            for a, b in self.NEGATION_PAIRS
        ]

    def normalize(self, question: str) -> str:
        """Normalize question: lowercase, collapse whitespace, replace punctuation with space."""
        normalized = question.lower().strip()
        normalized = re.sub(r"[^\w\s]", " ", normalized)  # Replace punctuation with space
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def has_opposite_intent(self, question: str) -> bool:
        """Check if question contains both sides of a negation pair."""
        q_lower = question.lower()
        for pattern_a, pattern_b in self._compiled_pairs:
            if pattern_a.search(q_lower) and pattern_b.search(q_lower):
                return True
        return False


class AnswerCache:
    """TTL-based cache for answers with exact-match keys and negation guard."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: dict[str, CacheEntry] = {}
        self._ttl_seconds = ttl_seconds
        self._normalizer = QuestionNormalizer()
        self._stats = CacheStats()
        self._lock = threading.RLock()

    def _generate_key(self, question: str, config_hash: str) -> str:
        """Generate cache key from normalized question and config hash."""
        normalized = self._normalizer.normalize(question)
        combined = f"{normalized}|{config_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    def _generate_config_hash(self, **config) -> str:
        """Generate hash from configuration parameters."""
        config_str = "|".join(f"{k}={v}" for k, v in sorted(config.items()))
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def get(
        self,
        question: str,
        provider: str,
        model: str,
        temperature: float,
        max_tokens: int,
        min_relevance_score: float,
        top_k: int,
    ) -> Optional[Answer]:
        """Retrieve cached answer if available and not expired."""
        with self._lock:
            self._stats.total_requests += 1

            config_hash = self._generate_config_hash(
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                min_relevance_score=min_relevance_score,
                top_k=top_k,
            )

            key = self._generate_key(question, config_hash)
            entry = self._cache.get(key)

            if entry is None:
                self._stats.cache_misses += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._stats.cache_misses += 1
                return None

            # Check negation guard
            if self._normalizer.has_opposite_intent(question):
                self._stats.cache_misses += 1
                return None

            self._stats.cache_hits += 1
            return entry.answer

    def set(
        self,
        question: str,
        answer: Answer,
        provider: str,
        model: str,
        temperature: float,
        max_tokens: int,
        min_relevance_score: float,
        top_k: int,
    ) -> None:
        """Store answer in cache."""
        with self._lock:
            # Don't cache if question has opposite intent
            if self._normalizer.has_opposite_intent(question):
                return

            config_hash = self._generate_config_hash(
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                min_relevance_score=min_relevance_score,
                top_k=top_k,
            )

            key = self._generate_key(question, config_hash)
            normalized = self._normalizer.normalize(question)

            entry = CacheEntry(
                answer=answer,
                question_normalized=normalized,
                ttl_seconds=self._ttl_seconds,
                config_hash=config_hash,
            )

            self._cache[key] = entry
            self._stats.entries = len(self._cache)

    def _evict_expired(self) -> int:
        """Remove expired entries. Returns count of evicted entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            self._stats.expired_entries = len(expired_keys)
            self._stats.entries = len(self._cache)
            return len(expired_keys)

    def clear(self) -> int:
        """Clear all cache entries. Returns number of cleared entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.entries = 0
            return count

    def stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._evict_expired()
            return CacheStats(
                total_requests=self._stats.total_requests,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                entries=self._stats.entries,
                expired_entries=self._stats.expired_entries,
            )