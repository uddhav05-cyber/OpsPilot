# OpsPilot

**IT Operations Knowledge Copilot** - A production-ready RAG system for answering operational questions using curated runbooks and configurable LLM providers.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()

---

## Features

- **RAG Pipeline**: TF-IDF retrieval + LLM generation with citations
- **Multi-Provider**: Mock (offline), Google Gemini, OpenAI - swap via config
- **Smart Caching**: TTL-based with negation guard (prevents enable/disable confusion)
- **Query Expansion**: Synonyms + IT abbreviations (MFA, DHCP, API, TLS, etc.)
- **Rate Limiting**: Per-endpoint, configurable, SlowAPI-powered
- **API Key Auth**: Simple header-based authentication
- **Evaluation Suite**: Accuracy, recall, latency metrics with CI integration
- **Production Ready**: Docker multi-stage, non-root, health checks, structured logging

## Quick Start

### Docker (Recommended)

```bash
git clone <repository-url>
cd OpsPilot
cp .env.example .env
# Edit .env with your API keys (or use LLM_PROVIDER=mock for demo)

docker build -t opspilot .
docker run -d -p 8000:8000 --env-file .env opspilot
```

### Local Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Run with mock provider (no API keys needed)
LLM_PROVIDER=mock python -m uvicorn opsilot.api.main:app --reload
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/api/v1/answer \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-12345" \
  -d '{"question": "How do I reset a user MFA?"}'
```

## Architecture

```
Question → Query Expansion → TF-IDF Retrieval → Top-K Docs → LLM Generation → Cited Answer
                ↑                                              ↓
            Synonyms                                    Cache Check/Store
            Abbreviations
```

### Components

| Module | Purpose |
|--------|---------|
| `knowledge_base/loader.py` | Load/runbook management |
| `retrieval/retriever.py` | TF-IDF + cosine similarity + query expansion |
| `providers/base.py` | Abstract LLM provider interface |
| `providers/mock.py` | Template-based responses (offline) |
| `providers/gemini_provider.py` | Google Gemini via `google-genai` SDK |
| `providers/openai_provider.py` | OpenAI via `openai` SDK |
| `answering/pipeline.py` | RAG orchestration + citations |
| `cache/cache.py` | TTL cache with negation guard |
| `api/main.py` | FastAPI server + auth + rate limiting |
| `evaluation/runner.py` | Automated quality metrics |

## Configuration

All settings via environment variables (see `.env.example`):

```bash
# Required: Choose provider
LLM_PROVIDER=gemini          # mock | gemini | openai

# If Gemini:
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.0-flash-exp

# If OpenAI:
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini

# Optional tuning
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60
CACHE_TTL_SECONDS=3600
MIN_RELEVANCE_SCORE=0.15
TOP_K=5
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | No | Health + provider status |
| `GET` | `/api/v1/providers` | No | List available providers |
| `POST` | `/api/v1/answer` | Yes | Ask a question |
| `GET` | `/api/v1/cache/stats` | Yes | Cache statistics |
| `POST` | `/api/v1/cache/clear` | Yes | Clear cache |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/answer \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "question": "How do I troubleshoot VPN connectivity?",
    "provider": "gemini",
    "temperature": 0.3,
    "max_tokens": 500
  }'
```

### Example Response

```json
{
  "answer": "To troubleshoot VPN:\n1. Verify user credentials [doc_07]\n2. Check firewall rules for UDP 500/4500 [doc_07]\n3. Validate certificate expiration [doc_12]\n4. Review connection logs [doc_12]",
  "citations": [
    {"runbook_id": "vpn-troubleshoot-001", "title": "VPN Troubleshooting", "category": "network", "score": 0.91},
    {"runbook_id": "cert-mgmt-003", "title": "Certificate Management", "category": "security", "score": 0.78}
  ],
  "retrieval_scores": [0.91, 0.78, 0.45, 0.32, 0.18],
  "provider": "gemini",
  "model": "gemini-2.0-flash-exp",
  "cached": false
}
```

## Knowledge Base

Runbooks stored in `knowledge_base/runbooks.json`:

```json
[
  {
    "runbook_id": "mfa-reset-001",
    "title": "MFA Reset Procedure",
    "category": "security",
    "content": "To reset a user's MFA: 1. Navigate to Admin Console > Users...",
    "tags": ["mfa", "authentication", "reset"]
  }
]
```

Categories: `security`, `network`, `infrastructure`, `application`

## Testing

```bash
# All tests
pytest -v

# With coverage
pytest --cov=src/opsilot --cov-report=term

# Specific module
pytest tests/test_retrieval.py -v
pytest tests/test_gemini_provider.py -v

# Evaluation suite
python -m opsilot.evaluation.runner --cases tests/eval_cases.json
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System design, data flow, components |
| [Deployment](docs/deployment.md) | Docker, Kubernetes, local dev |
| [Configuration](docs/configuration.md) | All environment variables |
| [API Reference](docs/api.md) | Complete endpoint specs |
| [Development](docs/development.md) | Contributing, code standards, debugging |
| [Security](docs/security.md) | Auth, rate limiting, secrets, compliance |
| [Evaluation](docs/evaluation.md) | Metrics, test cases, CI integration |

## Project Structure

```
OpsPilot/
├── src/opsilot/           # Main package
│   ├── answering/         # RAG pipeline
│   ├── api/               # FastAPI server
│   ├── cache/             # TTL caching
│   ├── evaluation/        # Quality metrics
│   ├── knowledge_base/    # Runbook loading
│   ├── providers/         # LLM providers (mock, gemini, openai)
│   └── retrieval/         # TF-IDF + query expansion
├── tests/                 # Pytest suite (8 modules)
├── knowledge_base/        # Runbooks JSON
├── docs/                  # Documentation (8 files)
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest -v`)
4. Run type check (`mypy src/opsilot`)
5. Run linter (`ruff check src/ tests/`)
6. Submit PR

See [Development Guide](docs/development.md) for details.