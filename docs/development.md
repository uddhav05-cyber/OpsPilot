# Development Guide

## Project Structure

```
OpsPilot/
├── src/
│   └── opsilot/
│       ├── __init__.py
│       ├── answering/
│       │   ├── __init__.py
│       │   └── pipeline.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── main.py
│       ├── cache/
│       │   ├── __init__.py
│       │   └── cache.py
│       ├── evaluation/
│       │   ├── __init__.py
│       │   └── runner.py
│       ├── knowledge_base/
│       │   ├── __init__.py
│       │   └── loader.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── gemini_provider.py
│       │   ├── mock.py
│       │   └── openai_provider.py
│       └── retrieval/
│           ├── __init__.py
│           └── retriever.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_answering.py
│   ├── test_api_security.py
│   ├── test_cache.py
│   ├── test_evaluation.py
│   ├── test_gemini_provider.py
│   ├── test_knowledge_base.py
│   └── test_retrieval.py
├── knowledge_base/
│   └── runbooks.json
├── docs/
├── .env.example
├── .gitignore
├── .dockerignore
├── requirements.txt
├── Dockerfile
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- Virtual environment tool (venv, conda, or pipx)

### Setup

```bash
# Clone
git clone <repository-url>
cd OpsPilot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Configure environment
cp .env.example .env
# Edit .env as needed

# Run tests to verify
pytest -v

# Start development server
python -m uvicorn opsilot.api.main:app --reload
```

## Running Tests

### All Tests

```bash
pytest -v
```

### Specific Test Module

```bash
pytest tests/test_answering.py -v
pytest tests/test_retrieval.py -v
pytest tests/test_gemini_provider.py -v
```

### With Coverage

```bash
pytest --cov=src/opsilot --cov-report=html --cov-report=term
```

### Filter by Marker

```bash
# Unit tests only (fast)
pytest -m "not integration" -v

# Integration tests
pytest -m integration -v
```

### Parallel Execution

```bash
pytest -n auto -v
```

## Code Quality

### Type Checking

```bash
# Install mypy
pip install mypy

# Run type checking
mypy src/opsilot
```

### Linting

```bash
# Install ruff (fast Python linter)
pip install ruff

# Check code
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/
```

### Formatting

```bash
# Install black
pip install black

# Format code
black src/ tests/

# Check formatting
black --check src/ tests/
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, fastapi]
```

## Adding a New LLM Provider

1. Create `src/opsilot/providers/new_provider.py`:
```python
from opsilot.providers.base import LLMProvider, LLMResponse

class NewProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "new_provider"

    def is_available(self) -> bool:
        return bool(os.getenv("NEW_PROVIDER_API_KEY"))

    async def generate(self, system_prompt: str, user_prompt: str,
                       temperature: float = 0.3, max_tokens: int = 500) -> LLMResponse:
        # Implementation here
        pass

    async def health_check(self) -> dict:
        # Implementation here
        pass
```

2. Register in `src/opsilot/providers/__init__.py`:
```python
from opsilot.providers.new_provider import NewProvider
# Add to provider factory
```

3. Add tests in `tests/test_new_provider.py`

4. Update documentation

## Adding Runbooks

Runbooks are stored in `knowledge_base/runbooks.json`:

```json
[
  {
    "runbook_id": "unique-id",
    "title": "Descriptive Title",
    "category": "security|network|infrastructure|application",
    "content": "Full runbook content with steps...",
    "tags": ["tag1", "tag2"]
  }
]
```

Reload by restarting the application (or implement hot-reload).

## Debugging

### Enable Debug Logging

```bash
LOG_LEVEL=DEBUG python -m uvicorn opsilot.api.main:app --reload
```

### Inspect Retrieval

```python
from opsilot.retrieval.retriever import TFIDFRetriever
from opsilot.knowledge_base.loader import KnowledgeBase

kb = KnowledgeBase.from_json_file("knowledge_base/runbooks.json")
retriever = TFIDFRetriever(kb)
result = retriever.retrieve("How to reset MFA?", top_k=5, min_score=0.1)
for doc, score in zip(result.documents, result.scores):
    print(f"Score: {score:.3f} - {doc.title}")
```

### Test Provider Directly

```python
import asyncio
from opsilot.providers.mock import MockProvider

async def test():
    provider = MockProvider()
    print(f"Available: {provider.is_available()}")
    response = await provider.generate(
        system_prompt="You are a helpful assistant.",
        user_prompt="How do I reset MFA?",
        temperature=0.3,
        max_tokens=200
    )
    print(f"Response: {response.content}")
    print(f"Tokens: {response.prompt_tokens}/{response.completion_tokens}/{response.total_tokens}")

asyncio.run(test())
```

## Common Tasks

### Update Dependencies

```bash
# Check for updates
pip list --outdated

# Update requirements.txt
pip install -U package_name
pip freeze > requirements.txt
```

### Run Evaluation Suite

```bash
# Requires evaluation cases file
python -m opsilot.evaluation.runner --cases tests/eval_cases.json
```

### Profile Performance

```bash
# Install py-spy
pip install py-spy

# Profile running server
py-spy record -o profile.svg --pid <PID>
```

## IDE Configuration

### VS Code (`.vscode/settings.json`)

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".mypy_cache": true,
    ".ruff_cache": true
  }
}
```

### PyCharm

- Set interpreter to `.venv/bin/python`
- Enable Ruff: Settings → Tools → Ruff
- Enable Black: Settings → Tools → Black
- Configure pytest as test runner

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Ensure `PYTHONPATH=src` or install with `pip install -e .` |
| `ImportError: cannot import name` | Check circular imports, use TYPE_CHECKING |
| `pytest: command not found` | Run `pip install pytest` |
| `uvicorn: command not found` | Run `pip install uvicorn` |
| Tests fail with async errors | Use `@pytest.mark.asyncio` on async tests |
| Rate limit errors in tests | Set `RATE_LIMIT_ENABLED=false` in test env |