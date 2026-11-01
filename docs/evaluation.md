# Evaluation

OpsPilot includes a comprehensive evaluation framework to measure answer quality, retrieval accuracy, and provider performance.

## Overview

The evaluation system (`evaluation/runner.py`) runs labeled test cases and computes standardized metrics:

- **Answer Accuracy** - Overall correctness of generated answers
- **Answerable Accuracy** - Correctness on questions that should be answerable
- **Unanswerable Accuracy** - Correct abstention rate on unanswerable questions
- **Source Recall** - Fraction of expected sources retrieved
- **Latency** - Response time percentiles

## Test Case Format

Test cases are stored as JSON:

```json
[
  {
    "question": "How do I reset a user's MFA?",
    "expected_answerable": true,
    "expected_sources": ["mfa-reset-001", "mfa-policy-003"],
    "category": "security",
    "difficulty": "easy"
  },
  {
    "question": "What is the meaning of life?",
    "expected_answerable": false,
    "expected_sources": [],
    "category": "general",
    "difficulty": "trick"
  }
]
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | The question to ask |
| `expected_answerable` | boolean | Yes | Whether KB should contain answer |
| `expected_sources` | string[] | No | Runbook IDs expected to be cited |
| `category` | string | No | Category for grouping |
| `difficulty` | string | No | `easy`, `medium`, `hard`, `trick` |

## Running Evaluation

### Command Line

```bash
# Run full evaluation suite
python -m opsilot.evaluation.runner --cases tests/eval_cases.json

# Run with specific provider
python -m opsilot.evaluation.runner --cases tests/eval_cases.json --provider gemini

# Run with custom pipeline config
python -m opsilot.evaluation.runner --cases tests/eval_cases.json \
  --min-relevance 0.1 --top-k 10

# Output detailed results
python -m opsilot.evaluation.runner --cases tests/eval_cases.json \
  --output results.json --verbose
```

### Programmatic

```python
from opsilot.evaluation.runner import EvaluationRunner, EvalCase
from opsilot.knowledge_base.loader import KnowledgeBase
from opsilot.retrieval.retriever import TFIDFRetriever
from opsilot.providers.mock import MockProvider
from opsilot.answering.pipeline import AnsweringPipeline

# Setup
kb = KnowledgeBase.from_json_file("knowledge_base/runbooks.json")
retriever = TFIDFRetriever(kb)
provider = MockProvider()
pipeline = AnsweringPipeline(kb, retriever, provider)

# Load cases
cases = [
    EvalCase(
        question="How do I reset MFA?",
        expected_answerable=True,
        expected_sources=["mfa-reset-001"]
    ),
    # ... more cases
]

# Run
runner = EvaluationRunner(pipeline)
metrics = await runner.run_evaluation(cases)

print(f"Answer Accuracy: {metrics.answer_accuracy:.2%}")
print(f"Answerable Accuracy: {metrics.answerable_accuracy:.2%}")
print(f"Unanswerable Accuracy: {metrics.unanswerable_accuracy:.2%}")
print(f"Source Recall: {metrics.source_recall:.2%}")
```

## Metrics Definitions

### Answer Accuracy

Overall fraction of questions answered correctly:

```
answer_accuracy = (correct_answers + correct_abstentions) / total_cases
```

- **Correct answer**: Answerable question → substantive answer with relevant citations
- **Correct abstention**: Unanswerable question → "I don't have enough information..."

### Answerable Accuracy

Accuracy on questions that should be answerable:

```
answerable_accuracy = correct_answers / answerable_cases
```

### Unanswerable Accuracy

Correct abstention rate on unanswerable questions:

```
unanswerable_accuracy = correct_abstentions / unanswerable_cases
```

### Source Recall

For answerable questions, fraction of expected sources retrieved:

```
source_recall = sum(retrieved_expected_sources) / sum(expected_sources_per_case)
```

A source counts as "retrieved" if its runbook_id appears in the answer's citations.

### Latency Metrics

| Metric | Description |
|--------|-------------|
| `p50_latency_ms` | Median response time |
| `p95_latency_ms` | 95th percentile |
| `p99_latency_ms` | 99th percentile |

## Evaluation Results

### Output Format

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "provider": "mock",
  "config": {
    "min_relevance_score": 0.15,
    "top_k": 5
  },
  "metrics": {
    "total_cases": 50,
    "answerable_cases": 35,
    "unanswerable_cases": 15,
    "correct_answers": 32,
    "correct_abstentions": 14,
    "false_answers": 3,
    "incorrect_abstentions": 1,
    "answer_accuracy": 0.92,
    "answerable_accuracy": 0.914,
    "unanswerable_accuracy": 0.933,
    "source_recall_sum": 42,
    "source_recall_count": 48,
    "source_recall": 0.875,
    "p50_latency_ms": 145,
    "p95_latency_ms": 312,
    "p99_latency_ms": 521
  },
  "per_case": [
    {
      "question": "How do I reset MFA?",
      "expected_answerable": true,
      "actual_answerable": true,
      "correct": true,
      "expected_sources": ["mfa-reset-001"],
      "retrieved_sources": ["mfa-reset-001", "mfa-policy-003"],
      "source_recall": 1.0,
      "latency_ms": 132
    }
  ]
}
```

### Interpreting Results

| Metric | Target | Action if Below |
|--------|--------|-----------------|
| `answer_accuracy` | > 0.85 | Improve retrieval or prompt |
| `answerable_accuracy` | > 0.85 | Better context retrieval |
| `unanswerable_accuracy` | > 0.90 | Tune abstention threshold |
| `source_recall` | > 0.80 | Lower `MIN_RELEVANCE_SCORE` or increase `TOP_K` |
| `p95_latency_ms` | < 500ms | Optimize retrieval, cache more |

## Regression Testing

### CI Integration

```yaml
# .github/workflows/eval.yml
name: Evaluation
on: [push, pull_request]
jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m opsilot.evaluation.runner --cases tests/eval_cases.json --output eval_results.json
      - name: Check thresholds
        run: |
          python -c "
          import json
          with open('eval_results.json') as f:
              r = json.load(f)
          assert r['metrics']['answer_accuracy'] > 0.85, 'Accuracy regression!'
          assert r['metrics']['unanswerable_accuracy'] > 0.90, 'Abstention regression!'
          print('All thresholds passed')
```

### Baseline Comparison

Store baseline results and compare:

```bash
# Save baseline
python -m opsilot.evaluation.runner --cases tests/eval_cases.json --output baseline.json

# After changes
python -m opsilot.evaluation.runner --cases tests/eval_cases.json --output current.json

# Compare
python -c "
import json
with open('baseline.json') as f: b = json.load(f)
with open('current.json') as f: c = json.load(f)
for k in ['answer_accuracy', 'source_recall']:
    diff = c['metrics'][k] - b['metrics'][k]
    print(f'{k}: {b[\"metrics\"][k]:.3f} -> {c[\"metrics\"][k]:.3f} ({diff:+.3f})')
"
```

## Creating Evaluation Cases

### From Real Usage

1. Collect real user questions (with consent/anonymization)
2. Have domain experts label answerability
3. Identify expected source runbooks
4. Add to `tests/eval_cases.json`

### Categories

Organize cases by category for targeted improvement:

| Category | Example Questions |
|----------|------------------|
| `security` | MFA reset, VPN config, certificate renewal |
| `network` | DHCP troubleshooting, DNS issues, firewall rules |
| `infrastructure` | Server provisioning, backup restore, scaling |
| `application` | Deployment rollback, config changes, log analysis |
| `trick` | Out-of-scope, ambiguous, adversarial |

### Difficulty Calibration

| Difficulty | Criteria |
|------------|----------|
| `easy` | Direct match in runbook, single step |
| `medium` | Requires synthesis from 2-3 runbooks |
| `hard` | Implicit knowledge, multi-step reasoning |
| `trick` | Out of scope, conflicting info, adversarial |

## Provider Comparison

Evaluate different providers on same cases:

```bash
for provider in mock gemini openai; do
  python -m opsilot.evaluation.runner \
    --cases tests/eval_cases.json \
    --provider $provider \
    --output eval_${provider}.json
done

# Compare
python -c "
import json
for p in ['mock', 'gemini', 'openai']:
    with open(f'eval_{p}.json') as f:
        r = json.load(f)
    m = r['metrics']
    print(f'{p:8s} Acc={m[\"answer_accuracy\"]:.2%}  Ans={m[\"answerable_accuracy\"]:.2%}  Unans={m[\"unanswerable_accuracy\"]:.2%}  Recall={m[\"source_recall\"]:.2%}')
"
```

## Continuous Improvement

### Feedback Loop

1. **Collect** production questions (opt-in)
2. **Label** periodically with SMEs
3. **Add** to evaluation suite
4. **Run** on every PR
5. **Alert** on regression
6. **Iterate** on retrieval/prompt/provider

### A/B Testing

Deploy multiple provider configs behind feature flags:

```python
# In pipeline
if user_in_experiment_group:
    provider = GeminiProvider(model="gemini-2.0-flash-exp")
else:
    provider = OpenAIProvider(model="gpt-4o-mini")
```

Track metrics per variant.

## Example Evaluation Suite

See `tests/eval_cases.json` for a starter set covering:
- Security procedures (MFA, VPN, certs)
- Network troubleshooting (DHCP, DNS, firewall)
- Infrastructure operations (backup, scaling, provisioning)
- Application management (deploy, rollback, logs)
- Edge cases (ambiguous, out-of-scope, adversarial)

Run with:
```bash
python -m opsilot.evaluation.runner --cases tests/eval_cases.json
```