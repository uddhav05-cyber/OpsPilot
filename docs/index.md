# OpsPilot Documentation

**OpsPilot** is an IT Operations Knowledge Copilot that combines retrieval-augmented generation (RAG) with LLM providers to answer operational questions using a curated knowledge base of runbooks.

## Quick Links

- [Architecture](architecture.md) - System design and data flow
- [Deployment](deployment.md) - Docker, Kubernetes, and local development
- [Configuration](configuration.md) - Environment variables and settings
- [API Reference](api.md) - REST endpoints and schemas
- [Development](development.md) - Contributing, testing, and code standards
- [Security](security.md) - Authentication, rate limiting, and best practices
- [Evaluation](evaluation.md) - Quality metrics and benchmarking

## Overview

OpsPilot provides a FastAPI-based REST API that:
1. **Retrieves** relevant runbook sections using TF-IDF + cosine similarity
2. **Generates** grounded answers using configurable LLM providers (Gemini, OpenAI, or Mock)
3. **Caches** responses for performance with TTL and negation guards
4. **Evaluates** answer quality with automated metrics

## Supported LLM Providers

| Provider | Model | Use Case |
|----------|-------|----------|
| **Mock** | `mock-v1.0` | Development, testing, demos (no API key needed) |
| **Gemini** | `gemini-2.0-flash-exp` | Production, Google Cloud environments |
| **OpenAI** | `gpt-4o-mini` | Production, OpenAI-compatible endpoints |

## Quick Start

```bash
# Clone and configure
git clone <repo>
cd OpsPilot
cp .env.example .env
# Edit .env with your API keys

# Run with Docker
docker build -t opspilot .
docker run -p 8000:8000 --env-file .env opspilot

# Or run locally
pip install -r requirements.txt
python -m uvicorn opsilot.api.main:app --reload
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (public) |
| `GET` | `/api/v1/providers` | List available LLM providers |
| `POST` | `/api/v1/answer` | Ask a question (requires API key) |
| `GET` | `/api/v1/cache/stats` | Cache statistics |
| `POST` | `/api/v1/cache/clear` | Clear cache |

## License

MIT License - See LICENSE file for details.