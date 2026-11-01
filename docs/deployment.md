# Deployment

## Docker (Recommended)

### Build Image

```bash
docker build -t opspilot:latest .
```

### Run Container

```bash
# Development
docker run -d \
  --name opspilot \
  -p 8000:8000 \
  --env-file .env \
  opspilot:latest

# Production with restart policy
docker run -d \
  --name opspilot \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  opspilot:latest
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  opspilot:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

Run with: `docker-compose up -d`

## Kubernetes

### Deployment Manifest

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opspilot
  labels:
    app: opspilot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: opspilot
  template:
    metadata:
      labels:
        app: opspilot
    spec:
      containers:
      - name: opspilot
        image: your-registry/opsilot:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: opspilot-secrets
        - configMapRef:
            name: opspilot-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: opspilot
spec:
  selector:
    app: opspilot
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opspilot-config
data:
  ENVIRONMENT: "production"
  RATE_LIMIT_ENABLED: "true"
  RATE_LIMIT_REQUESTS: "100"
  RATE_LIMIT_WINDOW: "60"
  CACHE_TTL_SECONDS: "3600"
  MIN_RELEVANCE_SCORE: "0.15"
  TOP_K: "5"
  LOG_LEVEL: "INFO"
---
# k8s/secret.yaml (apply with kubectl create secret generic opspilot-secrets --from-literal=GEMINI_API_KEY=xxx --from-literal=OPENAI_API_KEY=xxx --from-literal=API_KEY=xxx)
apiVersion: v1
kind: Secret
metadata:
  name: opspilot-secrets
type: Opaque
stringData:
  GEMINI_API_KEY: "<your-gemini-key>"
  OPENAI_API_KEY: "<your-openai-key>"
  API_KEY: "<your-api-key>"
```

### Apply to Cluster

```bash
kubectl apply -f k8s/
```

## Local Development

### Prerequisites

- Python 3.11+
- pip / pipx
- Git

### Setup

```bash
# Clone repository
git clone <repository-url>
cd OpsPilot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run development server
python -m uvicorn opsilot.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Development with Mock Provider (No API Keys)

```bash
# .env
LLM_PROVIDER=mock
ENVIRONMENT=development
RATE_LIMIT_ENABLED=false
```

This runs fully offline with template-based responses.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `mock` | `mock`, `gemini`, or `openai` |
| `GEMINI_API_KEY` | If Gemini | - | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash-exp` | Gemini model name |
| `OPENAI_API_KEY` | If OpenAI | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model name |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `RATE_LIMIT_ENABLED` | No | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | No | `60` | Requests per window |
| `RATE_LIMIT_WINDOW` | No | `60` | Window in seconds |
| `CACHE_TTL_SECONDS` | No | `3600` | Cache TTL |
| `MIN_RELEVANCE_SCORE` | No | `0.15` | Minimum retrieval score |
| `TOP_K` | No | `5` | Top K documents to retrieve |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Health Checks

The `/health` endpoint returns:

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

## Monitoring

### Prometheus Metrics (Future)

Add `prometheus-fastapi-instrumentator` to requirements and instrument:

```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

### Logging

Structured JSON logging in production:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
```

## Scaling Considerations

| Component | Scaling Strategy |
|-----------|------------------|
| API Server | Horizontal (stateless), add replicas behind load balancer |
| Knowledge Base | Read-only, replicate across pods, reload on config change |
| Cache | In-memory per pod (consider Redis for shared cache) |
| Rate Limiting | In-memory per pod (consider Redis for distributed) |
| LLM Providers | External APIs handle their own scaling |

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: uvicorn` | Ensure `HOME=/home/appuser` in Docker (fixes user install path) |
| `Gemini 404: model not found` | Use supported model name (`gemini-2.0-flash-exp`) |
| `Rate limit exceeded` | Increase `RATE_LIMIT_REQUESTS` or disable in dev |
| `API key invalid` | Check `X-API-Key` header matches `API_KEY` env var |
| `Knowledge base empty` | Verify `knowledge_base/runbooks.json` exists and is valid JSON |

### Logs

```bash
# Docker
docker logs -f opspilot

# Kubernetes
kubectl logs -f deployment/opsilot

# Local
tail -f logs/opsilot.log  # if configured
```