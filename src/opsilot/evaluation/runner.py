"""Evaluation runner for OpsPilot.

Runs labelled evaluation questions and computes metrics.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from opsilot.answering.pipeline import AnsweringPipeline
from opsilot.knowledge_base.loader import KnowledgeBase
from opsilot.providers.base import LLMProvider
from opsilot.retrieval.retriever import TFIDFRetriever


@dataclass
class EvalCase:
    """Single evaluation case."""

    question: str
    expected_answerable: bool
    expected_sources: list[str] = field(default_factory=list)
    category: str = ""
    difficulty: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> EvalCase:
        return cls(
            question=data["question"],
            expected_answerable=data["expected_answerable"],
            expected_sources=data.get("expected_sources", []),
            category=data.get("category", ""),
            difficulty=data.get("difficulty", ""),
        )


@dataclass
class EvalMetrics:
    """Aggregated evaluation metrics."""

    total_cases: int = 0
    answerable_cases: int = 0
    unanswerable_cases: int = 0
    correct_answers: int = 0
    correct_abstentions: int = 0
    false_answers: int = 0
    incorrect_abstentions: int = 0
    source_recall_sum: float = 0.0
    source_recall_count: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def answer_accuracy(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return (self.correct_answers + self.correct_abstentions) / self.total_cases

    @property
    def answerable_accuracy(self) -> float:
        if self.answerable_cases == 0:
            return 0.0
        return self.correct_answers / self.answerable_cases

    @property
    def unanswerable_accuracy(self) -> float:
        if self.unanswerable_cases == 0:
            return 0.0
        return self.correct_abstentions / self.unanswerable_cases

    @property
    def source_recall(self) -> float:
        if self.source_recall_count == 0:
            return 0.0
        return self.source_recall_sum / self.source_recall_count

    @property
    def p50_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return sorted(self.latencies_ms)[len(self.latencies_ms) // 2]

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def p99_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]


class EvaluationRunner:
    """Runs evaluation suite and computes metrics."""

    def __init__(
        self,
        pipeline: AnsweringPipeline,
        insufficient_context_msg: Optional[str] = None,
    ):
        self._pipeline = pipeline
        self._insufficient_msg = insufficient_context_msg or (
            "I don't have enough information in the knowledge base to answer this question."
        )

    async def run_evaluation(
        self,
        cases: list[EvalCase],
        verbose: bool = False,
    ) -> EvalMetrics:
        """Run evaluation on a list of cases."""
        metrics = EvalMetrics()

        for case in cases:
            metrics.total_cases += 1

            if case.expected_answerable:
                metrics.answerable_cases += 1
            else:
                metrics.unanswerable_cases += 1

            # Run pipeline
            start_time = time.perf_counter()
            answer = await self._pipeline.answer(case.question)
            latency_ms = (time.perf_counter() - start_time) * 1000
            metrics.latencies_ms.append(latency_ms)

            # Check if answer indicates insufficient context
            is_abstention = self._insufficient_msg in answer.answer

            # Evaluate correctness
            if case.expected_answerable:
                if is_abstention:
                    metrics.incorrect_abstentions += 1
                else:
                    metrics.correct_answers += 1
                    # Compute source recall
                    if case.expected_sources:
                        retrieved_ids = {c["runbook_id"] for c in answer.citations}
                        expected_set = set(case.expected_sources)
                        overlap = len(retrieved_ids & expected_set)
                        metrics.source_recall_sum += overlap / len(expected_set)
                        metrics.source_recall_count += 1
            else:
                if is_abstention:
                    metrics.correct_abstentions += 1
                else:
                    metrics.false_answers += 1

            if verbose:
                status = "✓" if (
                    (case.expected_answerable and not is_abstention) or
                    (not case.expected_answerable and is_abstention)
                ) else "✗"
                print(f"{status} {case.question[:60]}...")

        return metrics

    @classmethod
    def load_cases(cls, path: str | Path) -> list[EvalCase]:
        """Load evaluation cases from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [EvalCase.from_dict(item) for item in data]

    @classmethod
    def save_results(
        cls,
        metrics: EvalMetrics,
        cases: list[EvalCase],
        answers: list,
        output_path: str | Path,
    ) -> None:
        """Save detailed evaluation results to JSON."""
        results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metrics": {
                "total_cases": metrics.total_cases,
                "answerable_cases": metrics.answerable_cases,
                "unanswerable_cases": metrics.unanswerable_cases,
                "correct_answers": metrics.correct_answers,
                "correct_abstentions": metrics.correct_abstentions,
                "false_answers": metrics.false_answers,
                "incorrect_abstentions": metrics.incorrect_abstentions,
                "answer_accuracy": metrics.answer_accuracy,
                "answerable_accuracy": metrics.answerable_accuracy,
                "unanswerable_accuracy": metrics.unanswerable_accuracy,
                "source_recall_sum": metrics.source_recall_sum,
                "source_recall_count": metrics.source_recall_count,
                "source_recall": metrics.source_recall,
                "p50_latency_ms": metrics.p50_latency_ms,
                "p95_latency_ms": metrics.p95_latency_ms,
                "p99_latency_ms": metrics.p99_latency_ms,
            },
            "per_case": [
                {
                    "question": case.question,
                    "expected_answerable": case.expected_answerable,
                    "expected_sources": case.expected_sources,
                    "category": case.category,
                    "difficulty": case.difficulty,
                    "actual_answerable": not (ans.answer == "I don't have enough information..."),
                    "retrieved_sources": [c["runbook_id"] for c in ans.citations],
                    "source_recall": (
                        len(set(case.expected_sources) & set(c["runbook_id"] for c in ans.citations))
                        / len(case.expected_sources)
                        if case.expected_sources else 1.0
                    ),
                    "latency_ms": lat,
                }
                for case, ans, lat in zip(cases, answers, metrics.latencies_ms)
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)


async def main():
    """Command-line entry point."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Run OpsPilot evaluation suite")
    parser.add_argument("--cases", required=True, help="Path to evaluation cases JSON")
    parser.add_argument("--provider", default="mock", help="LLM provider to use")
    parser.add_argument("--min-relevance", type=float, default=0.15)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", help="Output JSON path for detailed results")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # Setup components
    kb = KnowledgeBase.from_json_file("knowledge_base/runbooks.json")
    retriever = TFIDFRetriever(kb)
    from opsilot.providers import get_provider
    provider = get_provider(args.provider)
    pipeline = AnsweringPipeline(
        kb, retriever, provider,
        min_relevance_score=args.min_relevance,
        top_k=args.top_k,
    )

    # Load cases
    cases = EvaluationRunner.load_cases(args.cases)

    # Run evaluation
    runner = EvaluationRunner(pipeline)
    metrics = await runner.run_evaluation(cases, verbose=args.verbose)

    # Print summary
    print("\n" + "=" * 50)
    print("EVALUATION RESULTS")
    print("=" * 50)
    print(f"Total Cases:       {metrics.total_cases}")
    print(f"Answerable:        {metrics.answerable_cases}")
    print(f"Unanswerable:      {metrics.unanswerable_cases}")
    print(f"Correct Answers:   {metrics.correct_answers}")
    print(f"Correct Abstentions: {metrics.correct_abstentions}")
    print(f"False Answers:     {metrics.false_answers}")
    print(f"Incorrect Abstain: {metrics.incorrect_abstentions}")
    print(f"Answer Accuracy:   {metrics.answer_accuracy:.2%}")
    print(f"Answerable Acc:    {metrics.answerable_accuracy:.2%}")
    print(f"Unanswerable Acc:  {metrics.unanswerable_accuracy:.2%}")
    print(f"Source Recall:     {metrics.source_recall:.2%}")
    print(f"Latency P50:       {metrics.p50_latency_ms:.0f}ms")
    print(f"Latency P95:       {metrics.p95_latency_ms:.0f}ms")
    print(f"Latency P99:       {metrics.p99_latency_ms:.0f}ms")

    if args.output:
        EvaluationRunner.save_results(metrics, cases, [], args.output)
        print(f"\nDetailed results saved to {args.output}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())