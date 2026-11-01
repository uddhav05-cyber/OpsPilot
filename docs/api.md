# API Reference

Base URL: `http://localhost:8000` (or your deployed host)

All endpoints return JSON. Errors follow RFC 7807 Problem Details format.

## Authentication

Most endpoints require an API key via header:

```
X-API-Key: your-api-key
```

The API key is configured via the `API_KEY` environment variable (or defaults to `test-api-key-12345` in development).

**Public endpoints** (no auth required):
- `GET /health`
- `GET /api/v1/providers`

## Endpoints

### Health Check

```http
GET /health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "provider": "gemini",
  "provider_available": true,
  "knowledge_base_size": 42,
  "cache_stats": {
    "total_requests": 150,
    "cache_hits": 45,
    "cache_misses": 105,
    "hit_rate": 0.30
  }
}
```

**Fields**:
- `status`: `healthy` or `degraded`
- `provider`: Active provider name
- `provider_available`: Whether provider is configured and reachable
- `knowledge_base_size`: Number of loaded runbooks
- `cache_stats`: Cache performance metrics

---

### List Providers

```http
GET /api/v1/providers
```

**Response** (200 OK):
```json
{
  "providers": [
    {
      "name": "mock",
      "available": true,
      "model": "mock-v1.0"
    },
    {
      "name": "gemini",
      "available": true,
      "model": "gemini-2.0-flash-exp"
    },
    {
      "name": "openai",
      "available": false,
      "model": "gpt-4o-mini"
    }
  ],
  "active": "gemini"
}
```

---

### Ask a Question

```http
POST /api/v1/answer
Content-Type: application/json
X-API-Key: your-api-key

{
  "question": "How do I reset a user's MFA?",
  "provider": "gemini",  // optional, overrides default
  "temperature": 0.3,    // optional, 0.0-1.0
  "max_tokens": 500      // optional, 1-4096
}
```

**Request Fields**:
| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `question` | Yes | - | User's question |
| `provider` | No | `LLM_PROVIDER` env | Override provider for this request |
| `temperature` | No | `0.3` | Sampling temperature |
| `max_tokens` | No | `500` | Max response tokens |

**Response** (200 OK):
```json
{
  "answer": "To reset a user's MFA, follow these steps:\n1. Navigate to Admin Console > Users\n2. Select the user\n3. Click 'Reset MFA' [doc_12]\n4. User will be prompted to re-enroll on next login [doc_12]",
  "citations": [
    {
      "runbook_id": "mfa-reset-001",
      "title": "MFA Reset Procedure",
      "category": "security",
      "score": 0.87
    }
  ],
  "retrieval_scores": [0.87, 0.42, 0.31],
  "provider": "gemini",
  "model": "gemini-2.0-flash-exp",
  "cached": false
}
```

**Response Fields**:
| Field | Description |
|-------|-------------|
| `answer` | Generated answer with inline citations `[doc_N]` |
| `citations` | Array of source documents with metadata |
| `retrieval_scores` | Cosine similarity scores for each retrieved doc |
| `provider` | Provider used for generation |
| `model` | Model name used |
| `cached` | Whether response came from cache |

**Error Responses**:

| Status | Code | Description |
|--------|------|-------------|
| 401 | `UNAUTHORIZED` | Missing or invalid API key |
| 422 | `VALIDATION_ERROR` | Invalid request body |
| 429 | `RATE_LIMITED` | Rate limit exceeded |
| 500 | `INTERNAL_ERROR` | Provider or internal error |
| 503 | `PROVIDER_UNAVAILABLE` | LLM provider not configured |

---

### Cache Statistics

```http
GET /api/v1/cache/stats
X-API-Key: your-api-key
```

**Response** (200 OK):
```json
{
  "total_requests": 150,
  "cache_hits": 45,
  "cache_misses": 105,
  "hit_rate": 0.30,
  "entries": 42,
  "expired_entries": 3
}
```

---

### Clear Cache

```http
POST /api/v1/cache/clear
X-API-Key: your-api-key
```

**Response** (200 OK):
```json
{
  "cleared": 42,
  "message": "Cache cleared successfully"
}
```

---

## Request/Response Schemas

### AnswerRequest
```json
{
  "question": "string (required, min 1 char)",
  "provider": "string (optional, enum: mock|gemini|openai)",
  "temperature": "number (optional, 0.0-1.0, default 0.3)",
  "max_tokens": "integer (optional, 1-4096, default 500)"
}
```

### AnswerResponse
```json
{
  "answer": "string",
  "citations": [
    {
      "runbook_id": "string",
      "title": "string",
      "category": "string",
      "score": "number"
    }
  ],
  "retrieval_scores": ["number"],
  "provider": "string",
  "model": "string",
  "cached": "boolean"
}
```

### Citation
```json
{
  "runbook_id": "string",
  "title": "string",
  "category": "string",
  "score": "number (0.0-1.0)"
}
```

### HealthResponse
```json
{
  "status": "string (healthy|degraded)",
  "provider": "string",
  "provider_available": "boolean",
  "knowledge_base_size": "integer",
  "cache_stats": {
    "total_requests": "integer",
    "cache_hits": "integer",
    "cache_misses": "integer",
    "hit_rate": "number"
  }
}
```

### ProvidersResponse
```json
{
  "providers": [
    {
      "name": "string",
      "available": "boolean",
      "model": "string"
    }
  ],
  "active": "string"
}
```

### CacheStatsResponse
```json
{
  "total_requests": "integer",
  "cache_hits": "integer",
  "cache_misses": "integer",
  "hit_rate": "number",
  "entries": "integer",
  "expired_entries": "integer"
}
```

### ClearCacheResponse
```json
{
  "cleared": "integer",
  "message": "string"
}
```

---

## Error Format

All errors follow RFC 7807:

```json
{
  "type": "https://tools.ietf.org/html/rfc7231#section-6.5.1",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Missing API key. Provide X-API-Key header.",
  "instance": "/api/v1/answer"
}
```

---

## Rate Limiting Headers

When rate limiting is enabled, responses include:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Max requests in window |
| `X-RateLimit-Remaining` | Requests remaining |
| `X-RateLimit-Reset` | Seconds until reset |

---

## Example Usage

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/api/v1/answer \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-12345" \
  -d '{"question": "How do I configure DHCP?"}'

# Check cache stats
curl -H "X-API-Key: test-api-key-12345" \
  http://localhost:8000/api/v1/cache/stats
```

### Python (httpx)

```python
import httpx

client = httpx.Client(
    base_url="http://localhost:8000",
    headers={"X-API-Key": "test-api-key-12345"}
)

# Ask a question
response = client.post("/api/v1/answer", json={
    "question": "How do I reset MFA?",
    "temperature": 0.2
})
data = response.json()
print(data["answer"])
for cite in data["citations"]:
    print(f"  Source: {cite['title']} (score: {cite['score']:.2f})")
```

### JavaScript (fetch)

```javascript
async function askQuestion(question) {
  const response = await fetch('http://localhost:8000/api/v1/answer', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'test-api-key-12345'
    },
    body: JSON.stringify({ question })
  });
  return response.json();
}

askQuestion("How do I troubleshoot VPN?").then(data => {
  console.log(data.answer);
  data.citations.forEach(c => console.log(`  [${c.runbook_id}] ${c.title}`));
});
```