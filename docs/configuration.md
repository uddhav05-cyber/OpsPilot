# Configuration

OpsPilot is configured entirely through environment variables. All settings have sensible defaults for development.

## Environment Variables Reference

### LLM Provider Selection

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `LLM_PROVIDER` | `mock`, `gemini`, `openai` | `mock` | Active LLM provider |

### Provider-Specific Settings

#### Gemini (Google)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *required* | API key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.0-flash-exp` | Model name (see [Google models](https://ai.google.dev/models/gemini)) |

Supported models: `gemini-2.0-flash-exp`, `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-1.0-pro`

#### OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *required* | API key from OpenAI Platform |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name (see [OpenAI models](https://platform.openai.com/docs/models)) |

Supported models: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`, `gpt-4-turbo`

#### Mock Provider

No additional configuration needed. Uses built-in templates.

### Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Port number |
| `ENVIRONMENT` | `development` | `development` or `production` |

### Rate Limiting

Uses [SlowAPI](https://github.com/laurt/SlowAPI) with in-memory storage.

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `RATE_LIMIT_REQUESTS` | `60` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Window in seconds |

In `development` mode, rate limiting can be disabled for easier testing.

### Cache Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL_SECONDS` | `3600` | Time-to-live for cached answers (1 hour) |

Cache uses exact-match keys with configuration hash to prevent stale answers when settings change.

### Retrieval Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_RELEVANCE_SCORE` | `0.15` | Minimum cosine similarity for retrieval |
| `TOP_K` | `5` | Maximum documents to retrieve |

Lower `MIN_RELEVANCE_SCORE` = more documents retrieved (higher recall, lower precision).

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Configuration Examples

### Development (Mock Provider, No Rate Limit)

```bash
# .env.development
LLM_PROVIDER=mock
ENVIRONMENT=development
RATE_LIMIT_ENABLED=false
LOG_LEVEL=DEBUG
```

### Production (Gemini)

```bash
# .env.production
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash-exp
ENVIRONMENT=production
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
CACHE_TTL_SECONDS=7200
LOG_LEVEL=INFO
```

### Production (OpenAI)

```bash
# .env.production
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
ENVIRONMENT=production
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
CACHE_TTL_SECONDS=7200
LOG_LEVEL=INFO
```

### Docker with Custom Config

```bash
docker run -d \
  --name opspilot \
  -p 8000:8000 \
  -e LLM_PROVIDER=gemini \
  -e GEMINI_API_KEY=your-key \
  -e RATE_LIMIT_REQUESTS=200 \
  opspilot:latest
```

## Configuration Validation

On startup, the application validates:
1. `LLM_PROVIDER` is one of `mock`, `gemini`, `openai`
2. Required API keys are present for selected provider
3. Rate limit values are positive integers
4. Cache TTL is positive
5. Retrieval parameters are in valid ranges

Invalid configuration raises a clear error at startup.

## Dynamic Configuration (Future)

For runtime configuration changes without restart:
- Use a configuration service (Consul, etcd, AWS Parameter Store)
- Implement `/admin/config/reload` endpoint
- Watch for file changes to `.env` in development