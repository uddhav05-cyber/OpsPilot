# Multi-stage build for OpsPilot
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY src/ ./src/
COPY knowledge_base/ ./knowledge_base/
COPY .env.example .env.example

# Set PATH to include user packages
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app/src

# Fix for uvloop/uvicorn import issue with non-root user
ENV HOME=/home/appuser

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)"

# Run application
CMD ["python", "-m", "uvicorn", "opsilot.api.main:app", "--host", "0.0.0.0", "--port", "8000"]