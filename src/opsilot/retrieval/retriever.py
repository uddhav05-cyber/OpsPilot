"""Implements TF-IDF based document retrieval with cosine similarity ranking.

Includes query expansion for synonyms and abbreviations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from opsilot.knowledge_base.loader import KnowledgeBase, Runbook


@dataclass
class RetrievalResult:
    """Result of a retrieval query."""

    documents: list[Runbook]
    scores: list[float]
    runbook_ids: list[str]


class QueryExpander:
    """Expands queries with synonyms and abbreviation expansions."""

    # Common IT abbreviations
    ABBREVIATIONS: dict[str, str] = {
        "dhcp": "dynamic host configuration protocol",
        "dns": "domain name system",
        "api": "application programming interface",
        "ssl": "secure sockets layer",
        "tls": "transport layer security",
        "vpn": "virtual private network",
        "mfa": "multi-factor authentication",
        "2fa": "two-factor authentication",
        "iam": "identity and access management",
        "sso": "single sign-on",
        "pki": "public key infrastructure",
        "ca": "certificate authority",
        "csr": "certificate signing request",
        "sql": "structured query language",
        "nosql": "not only sql",
        "ci": "continuous integration",
        "cd": "continuous deployment",
        "cicd": "continuous integration continuous deployment",
        "k8s": "kubernetes",
        "kube": "kubernetes",
        "pod": "kubernetes pod",
        "svc": "kubernetes service",
        "ing": "kubernetes ingress",
        "cm": "configmap",
        "secret": "kubernetes secret",
        "pv": "persistent volume",
        "pvc": "persistent volume claim",
        "lb": "load balancer",
        "nat": "network address translation",
        "acl": "access control list",
        "fw": "firewall",
        "ids": "intrusion detection system",
        "ips": "intrusion prevention system",
        "siem": "security information and event management",
        "soar": "security orchestration automation and response",
        "edr": "endpoint detection and response",
        "xdr": "extended detection and response",
        "rpo": "recovery point objective",
        "rto": "recovery time objective",
        "bcp": "business continuity plan",
        "drp": "disaster recovery plan",
        "ha": "high availability",
        "lb": "load balancer",
        "az": "availability zone",
    }

    # Domain-specific synonyms
    _SYNONYM_MAP: dict[str, list[str]] = {
        "reset": ["reconfigure", "reinitialize", "restore"],
        "configure": ["set up", "setup", "provision"],
        "install": ["deploy", "provision", "add"],
        "remove": ["delete", "uninstall", "decommission"],
        "fix": ["resolve", "troubleshoot", "repair"],
        "error": ["issue", "problem", "failure", "incident"],
        "monitor": ["observe", "watch", "track"],
        "scale": ["resize", "expand", "grow"],
        "backup": ["snapshot", "archive"],
        "restore": ["recover", "rollback"],
        "migrate": ["move", "transfer"],
        "update": ["upgrade", "patch"],
        "rotate": ["renew", "regenerate"],
        "revoke": ["invalidate", "disable"],
        "grant": ["assign", "provision"],
        "audit": ["review", "inspect"],
        "comply": ["conform", "adhere"],
    }

    def __init__(self):
        pass

    def expand(self, query: str) -> str:
        """Expand query with synonyms and abbreviation expansions."""
        expanded_terms = [query]

        # Expand abbreviations
        words = query.lower().split()
        for word in words:
            # Check for abbreviation matches (with or without punctuation)
            clean_word = re.sub(r"[^\w]", "", word)
            if clean_word in self.ABBREVIATIONS:
                expanded_terms.append(self.ABBREVIATIONS[clean_word])

        # Expand synonyms
        for word in words:
            clean_word = re.sub(r"[^\w]", "", word)
            if clean_word in self._SYNONYM_MAP:
                expanded_terms.extend(self._SYNONYM_MAP[clean_word])

        return " ".join(expanded_terms)


class TextNormalizer:
    """Normalizes text for consistent processing."""

    def normalize(self, text: str) -> str:
        """Normalize: lowercase, collapse whitespace, remove punctuation, preserve abbreviations."""
        # Lowercase
        normalized = text.lower()
        # Remove punctuation (replace with empty string)
        normalized = re.sub(r"[^\w\s]", "", normalized)
        # Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        # Strip leading/trailing
        normalized = normalized.strip()
        return normalized


class TFIDFRetriever:
    """TF-IDF based document retrieval with cosine similarity ranking."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        vectorizer_params: Optional[dict] = None,
    ):
        self._kb = knowledge_base
        self._vectorizer_params = vectorizer_params or {
            "ngram_range": (1, 2),
            "max_features": 10000,
            "stop_words": "english",
            "min_df": 1,
            "max_df": 0.95,
        }
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._document_texts: list[str] = []
        self._document_ids: list[str] = []
        self._query_expander = QueryExpander()
        self._text_normalizer = TextNormalizer()
        self._build_index()

    def _build_index(self) -> None:
        """Build TF-IDF index from knowledge base."""
        self._document_texts = []
        self._document_ids = []

        for runbook in self._kb.runbooks:
            # Combine title, category, tags, and content for indexing
            text_parts = [
                runbook.title,
                runbook.category,
                " ".join(runbook.tags),
                runbook.content,
            ]
            combined = " ".join(text_parts)
            normalized = self._text_normalizer.normalize(combined)
            self._document_texts.append(normalized)
            self._document_ids.append(runbook.runbook_id)

        if self._document_texts:
            self._vectorizer = TfidfVectorizer(**self._vectorizer_params)
            self._tfidf_matrix = self._vectorizer.fit_transform(self._document_texts)

    def configure(self, **vectorizer_params) -> None:
        """Reconfigure vectorizer and rebuild index."""
        self._vectorizer_params.update(vectorizer_params)
        self._build_index()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.15,
    ) -> RetrievalResult:
        """Retrieve top-k documents for query."""
        if not self._document_texts or self._tfidf_matrix is None:
            return RetrievalResult(documents=[], scores=[], runbook_ids=[])

        # Expand and normalize query
        expanded_query = self._query_expander.expand(query)
        normalized_query = self._text_normalizer.normalize(expanded_query)

        # Vectorize query
        query_vec = self._vectorizer.transform([normalized_query])

        # Compute cosine similarities
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Get top-k indices above threshold
        top_indices = np.argsort(similarities)[::-1]
        filtered = [(i, similarities[i]) for i in top_indices if similarities[i] >= min_score]
        top_filtered = filtered[:top_k]

        # Build result
        documents = []
        scores = []
        runbook_ids = []

        for idx, score in top_filtered:
            runbook = self._kb.get(self._document_ids[idx])
            if runbook:
                documents.append(runbook)
                scores.append(float(score))
                runbook_ids.append(runbook.runbook_id)

        return RetrievalResult(
            documents=documents,
            scores=scores,
            runbook_ids=runbook_ids,
        )