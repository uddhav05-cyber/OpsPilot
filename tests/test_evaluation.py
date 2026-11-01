"""Tests for evaluation module."""

import pytest
import json
import tempfile
from pathlib import Path

from opsilot.evaluation.runner import EvaluationRunner, EvalCase, EvalMetrics
from opsilot.knowledge_base.loader import KnowledgeBase, Runbook
from opsilot.retrieval.retriever import TFIDFRetriever
from opsilot.providers.mock import MockProvider
from opsilot.answering.pipeline import AnsweringPipeline


@pytest.fixture
def sample_pipeline():
    runbooks = [
        Runbook("kb-001", "MFA Reset", "security", "Reset MFA steps...", ["mfa"]),
        Runbook("kb-002", "VPN Setup", "network", "VPN setup steps...", ["vpn"]),
    ]
    kb = KnowledgeBase(runbooks)
    retriever = TFIDFRetriever(kb)
    provider = MockProvider()
    return AnsweringPipeline(kb, retriever, provider, min_relevance_score=0.1, top_k=2)


@pytest.fixture
def eval_cases():
    return [
        EvalCase(
            question="How do I reset MFA?",
            expected_answerable=True,
            expected_sources=["kb-001"],
            category="security",
            difficulty="easy",
        ),
        EvalCase(
            question="What is the meaning of life?",
            expected_answerable=False,
            expected_sources=[],
            category="general",
            difficulty="trick",
        ),
        EvalCase(
            question="How to setup VPN?",
            expected_answerable=True,
            expected_sources=["kb-002"],
            category="network",
            difficulty="easy",
        ),
    ]


class TestEvalCase:
    """Tests for EvalCase."""

    def test_from_dict(self):
        data = {
            "question": "Test question?",
            "expected_answerable": True,
            "expected_sources": ["kb-001"],
            "category": "test",
            "difficulty": "easy",
        }
        case = EvalCase.from_dict(data)
        assert case.question == "Test question?"
        assert case.expected_answerable is True
        assert case.expected_sources == ["kb-001"]
        assert case.category == "test"
        assert case.difficulty == "easy"

    def test_from_dict_minimal(self):
        data = {
            "question": "Test?",
            "expected_answerable": False,
        }
        case = EvalCase.from_dict(data)
        assert case.expected_sources == []
        assert case.category == ""
        assert case.difficulty == ""


class TestEvalMetrics:
    """Tests for EvalMetrics."""

    def test_empty_metrics(self):
        metrics = EvalMetrics()
        assert metrics.answer_accuracy == 0.0
        assert metrics.answerable_accuracy == 0.0
        assert metrics.unanswerable_accuracy == 0.0
        assert metrics.source_recall == 0.0

    def test_answer_accuracy(self):
        metrics = EvalMetrics(
            total_cases=10,
            correct_answers=7,
            correct_abstentions=2,
        )
        assert metrics.answer_accuracy == 0.9

    def test_answerable_accuracy(self):
        metrics = EvalMetrics(
            answerable_cases=8,
            correct_answers=6,
        )
        assert metrics.answerable_accuracy == 0.75

    def test_unanswerable_accuracy(self):
        metrics = EvalMetrics(
            unanswerable_cases=2,
            correct_abstentions=2,
        )
        assert metrics.unanswerable_accuracy == 1.0

    def test_source_recall(self):
        metrics = EvalMetrics(
            source_recall_sum=3.0,
            source_recall_count=4,
        )
        assert metrics.source_recall == 0.75

    def test_latency_percentiles(self):
        metrics = EvalMetrics(latencies_ms=[100, 200, 300, 400, 500])
        assert metrics.p50_latency_ms == 300
        assert metrics.p95_latency_ms == 500
        assert metrics.p99_latency_ms == 500


class TestEvaluationRunner:
    """Tests for EvaluationRunner."""

    @pytest.mark.asyncio
    async def test_run_evaluation(self, sample_pipeline, eval_cases):
        runner = EvaluationRunner(sample_pipeline)
        metrics = await runner.run_evaluation(eval_cases)

        assert metrics.total_cases == 3
        assert metrics.answerable_cases == 2
        assert metrics.unanswerable_cases == 1

    def test_load_cases_from_file(self, eval_cases):
        data = [
            {"question": c.question, "expected_answerable": c.expected_answerable,
             "expected_sources": c.expected_sources, "category": c.category, "difficulty": c.difficulty}
            for c in eval_cases
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        try:
            loaded = EvaluationRunner.load_cases(temp_path)
            assert len(loaded) == 3
            assert loaded[0].question == "How do I reset MFA?"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_save_results(self, sample_pipeline, eval_cases):
        runner = EvaluationRunner(sample_pipeline)
        metrics = await runner.run_evaluation(eval_cases)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name
        try:
            EvaluationRunner.save_results(metrics, eval_cases, [], temp_path)
            with open(temp_path) as f:
                saved = json.load(f)
            assert "metrics" in saved
            assert "per_case" in saved
            assert saved["metrics"]["total_cases"] == 3
        finally:
            Path(temp_path).unlink(missing_ok=True)