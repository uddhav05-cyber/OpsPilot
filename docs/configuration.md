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

### CORS Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ALLOWED_ORIGINS` | `*` | Comma-separated list of allowed origins (e.g., `https://app.example.com,https://admin.example.com`). **In production with credentials enabled, must be explicit list, not `*`.** |
| `CORS_ALLOW_CREDENTIALS` | `true` | Allow credentials (cookies, auth headers). **In production with wildcard origins, must be `false`.** |
| `CORS_ALLOWED_METHODS` | `*` | Comma-separated list of allowed HTTP methods |
| `CORS_ALLOWED_HEADERS` | `*` | Comma-separated list of allowed request headers |

**Production CORS Requirements:**
- When `ENVIRONMENT=production` and `CORS_ALLOW_CREDENTIALS=true`, `CORS_ALLOWED_ORIGINS` must be an explicit list of trusted origins (not `*`). The application will fail to start with a clear error message if this combination is detected.
- For development (`ENVIRONMENT=development`), the permissive defaults (`*`) are allowed for convenience.
- To allow credentials in production: `CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com` and `CORS_ALLOW_CREDENTIALS=true`
- To use wildcard origins in production: `CORS_ALLOW_CREDENTIALS=false` (no cookies/auth headers from browsers)

Set `CORS_ALLOWED_ORIGINS` to a specific list of origins in production for security.

### Support Phone

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPPORT_PHONE` | `+1-555-0200` | Phone number shown when the knowledge base cannot answer a question |

### Rate Limiting

Uses [SlowAPI](https://github.com/laurt/SlowAPI) with **in-memory storage**.

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `RATE_LIMIT_REQUESTS` | `60` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Window in seconds |

In `development` mode, rate limiting can be disabled for easier testing.

> **Note on Rate Limiting:** The current implementation uses in-memory storage for rate limiting. This works for single-instance deployments but **does not work correctly in multi-instance (scaled) deployments** where each instance has its own rate limit counter. For production deployments with multiple replicas, use a distributed rate limiter backed by Redis (e.g., `slowapi` with `RedisStorage`) or an API gateway (nginx, Traefik, Kong) for centralized rate limiting.

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