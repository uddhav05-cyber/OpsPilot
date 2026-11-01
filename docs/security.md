# Security

## Overview

OpsPilot implements multiple security layers:

1. **API Key Authentication** - Required for all mutating endpoints
2. **Rate Limiting** - Prevents abuse and DoS
3. **Input Validation** - Pydantic models with strict schemas
4. **Error Sanitization** - No stack traces or internals in responses
5. **Non-root Container** - Docker runs as unprivileged user
6. **Secrets Management** - Environment variables only, no hardcoded secrets

## Authentication

### API Key

All protected endpoints require the `X-API-Key` header:

```http
X-API-Key: your-secure-api-key
```

The valid key is configured via the `API_KEY` environment variable. In development, a default test key (`test-api-key-12345`) is used if not set.

### Key Generation

Generate a secure API key:

```bash
# OpenSSL
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### Rotation

To rotate keys without downtime:
1. Add new key to environment
2. Update clients
3. Remove old key
4. Restart pods (rolling update)

## Rate Limiting

Implemented with [SlowAPI](https://github.com/laurt/SlowAPI).

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable |
| `RATE_LIMIT_REQUESTS` | `60` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Window in seconds |

### Limits by Endpoint

| Endpoint | Limit |
|----------|-------|
| `GET /health` | Unlimited (public) |
| `GET /api/v1/providers` | 60/min |
| `POST /api/v1/answer` | 30/min |
| `GET /api/v1/cache/stats` | 60/min |
| `POST /api/v1/cache/clear` | 10/min |

### Response Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 42
```

### Exceeded Response (429)

```json
{
  "type": "https://tools.ietf.org/html/rfc6585#section-4",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit exceeded. Try again in 42 seconds.",
  "instance": "/api/v1/answer"
}
```

## Input Validation

All request bodies validated with Pydantic v2:

- **String fields**: Min/max length, pattern matching
- **Numeric fields**: Range constraints (ge, le)
- **Enum fields**: Strict value validation
- **Extra fields**: Rejected (`extra='forbid'`)

Example:
```python
class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    provider: Optional[Literal["mock", "gemini", "openai"]] = None
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=500, ge=1, le=4096)

    model_config = ConfigDict(extra='forbid')
```

## Error Sanitization

### Production Errors

In production (`ENVIRONMENT=production`), error responses never include:
- Stack traces
- Internal file paths
- Database queries
- Configuration values
- Provider-specific error details

### Development Errors

In development, detailed errors are returned for debugging:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "question"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### Custom Exception Handlers

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if settings.environment == "production":
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://httpstatuses.com/{exc.status_code}",
                "title": exc.detail,
                "status": exc.status_code,
            }
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
```

## Container Security

### Non-root User

Dockerfile creates and uses `appuser` (UID 1000):

```dockerfile
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
```

### Read-only Root Filesystem (Recommended)

```dockerfile
# Add to runtime stage
RUN chmod -R 555 /app && chmod -R 777 /app/knowledge_base
```

### Capabilities

No additional capabilities granted. Default Docker capabilities only.

### Security Scanning

```bash
# Scan image with Trivy
trivy image opspilot:latest

# Scan with Snyk
snyk container test opspilot:latest
```

## Secrets Management

### Environment Variables

All secrets via environment variables:
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `API_KEY`

### Docker Secrets (Swarm/K8s)

```yaml
# docker-compose.yml
services:
  opspilot:
    secrets:
      - gemini_api_key
      - openai_api_key
      - api_key

secrets:
  gemini_api_key:
    external: true
  openai_api_key:
    external: true
  api_key:
    external: true
```

In application:
```python
import os
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or open("/run/secrets/gemini_api_key").read().strip()
```

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: opspilot-secrets
type: Opaque
stringData:
  GEMINI_API_KEY: "your-key"
  OPENAI_API_KEY: "your-key"
  API_KEY: "your-api-key"
```

## Network Security

### HTTPS/TLS

In production, terminate TLS at:
- Load balancer (AWS ALB, GCP Cloud Load Balancing, Azure Front Door)
- Ingress controller (NGINX, Traefik, Istio)
- Reverse proxy (NGINX, Caddy)

Application runs HTTP internally; TLS handled by infrastructure.

### CORS

Configure for your frontend domain:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Internal Communication

- Service-to-service: mTLS (Istio, Linkerd) or network policies
- Database: Not applicable (file-based knowledge base)
- Cache: In-memory per pod (Redis for shared cache would need auth)

## Vulnerability Management

### Dependencies

```bash
# Audit dependencies
pip audit

# Check for known vulnerabilities
snyk test --all-projects

# Update vulnerable packages
pip install --upgrade package_name
```

### Base Image

- Uses `python:3.11-slim` (Debian-based, minimal)
- Regularly rebuild to pick up security patches
- Consider `python:3.11-alpine` for smaller attack surface

### Scanning in CI

```yaml
# .github/workflows/security.yml
- name: Run Trivy scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'opsilot:latest'
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload to GitHub Security
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

## Compliance Considerations

| Requirement | Implementation |
|-------------|----------------|
| Data encryption at rest | Knowledge base files - encrypt volume |
| Data encryption in transit | TLS termination at edge |
| Access logging | Structured JSON logs with request IDs |
| Audit trail | Log all `/api/v1/answer` requests with user/hash |
| Data retention | Cache TTL configurable, no persistent PII |
| Right to deletion | Clear cache endpoint, no user data stored |

## Incident Response

### Key Contacts

- Security issues: security@your-org.com
- Infrastructure: ops@your-org.com

### Playbooks

1. **API Key Compromise**: Rotate immediately, audit access logs
2. **Rate Limit Bypass**: Check for header manipulation, tighten limits
3. **Provider API Key Leak**: Rotate provider key, check usage/billing
4. **Container Escape**: Update base image, scan for CVEs, redeploy

## Security Checklist (Pre-deployment)

- [ ] `ENVIRONMENT=production`
- [ ] Strong `API_KEY` generated and set
- [ ] Provider API keys set and validated
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] Rate limits appropriate for traffic
- [ ] HTTPS/TLS configured at edge
- [ ] CORS restricted to known origins
- [ ] Non-root user in container
- [ ] Secrets in secret manager (not env files)
- [ ] Base image scanned and current
- [ ] Dependencies audited
- [ ] Logging configured (no PII)
- [ ] Health checks passing
- [ ] Backup/restore tested for knowledge base