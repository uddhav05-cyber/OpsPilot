"""FastAPI application for OpsPilot."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, ConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from opsilot.answering.pipeline import AnsweringPipeline
from opsilot.cache.cache import AnswerCache
from opsilot.knowledge_base.loader import KnowledgeBase
from opsilot.providers import get_provider, list_providers
from opsilot.providers.base import LLMProvider
from opsilot.retrieval.retriever import TFIDFRetriever


# Configuration from environment
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_KEY = os.getenv("API_KEY", "test-api-key-12345")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.15"))
TOP_K = int(os.getenv("TOP_K", "5"))
KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "knowledge_base/runbooks.json")

# Global state
_knowledge_base: Optional[KnowledgeBase] = None
_retriever: Optional[TFIDFRetriever] = None
_pipeline: Optional[AnsweringPipeline] = None
_answer_cache: Optional[AnswerCache] = None
_llm_provider: Optional[LLMProvider] = None

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_WINDOW}seconds"]
    if RATE_LIMIT_ENABLED and ENVIRONMENT == "production"
    else [],
)

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
        )
    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )
    return api_key


def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key from API key or IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"
    return get_remote_address(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    global _knowledge_base, _retriever, _pipeline, _answer_cache, _llm_provider

    # Startup
    print(f"Starting OpsPilot in {ENVIRONMENT} mode...")
    print(f"LLM Provider: {LLM_PROVIDER}")

    # Load knowledge base
    _knowledge_base = KnowledgeBase.from_json_file(KNOWLEDGE_BASE_PATH)
    print(f"Loaded {len(_knowledge_base)} runbooks from {KNOWLEDGE_BASE_PATH}")

    # Initialize retriever
    _retriever = TFIDFRetriever(_knowledge_base)

    # Initialize LLM provider
    _llm_provider = get_provider(LLM_PROVIDER)
    if _llm_provider is None:
        print(f"WARNING: Unknown provider '{LLM_PROVIDER}', falling back to mock")
        from opsilot.providers.mock import MockProvider
        _llm_provider = MockProvider()

    if not _llm_provider.is_available():
        print(f"WARNING: Provider '{LLM_PROVIDER}' not available (missing API key?)")

    # Initialize pipeline
    _pipeline = AnsweringPipeline(
        _knowledge_base,
        _retriever,
        _llm_provider,
        min_relevance_score=MIN_RELEVANCE_SCORE,
        top_k=TOP_K,
    )

    # Initialize cache
    _answer_cache = AnswerCache(ttl_seconds=CACHE_TTL_SECONDS)

    print("OpsPilot started successfully!")

    yield

    # Shutdown
    print("Shutting down OpsPilot...")


# FastAPI app
app = FastAPI(
    title="OpsPilot API",
    description="IT Operations Knowledge Copilot - RAG-powered Q&A for IT runbooks",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Custom exception handler for validation errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if ENVIRONMENT == "production":
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://httpstatuses.com/{exc.status_code}",
                "title": exc.detail,
                "status": exc.status_code,
            },
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Pydantic models
class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="User's question")
    provider: Optional[str] = Field(None, description="Override provider for this request")
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: int = Field(500, ge=1, le=4096, description="Max response tokens")

    model_config = ConfigDict(extra="forbid")


class Citation(BaseModel):
    runbook_id: str
    title: str
    category: str
    score: float


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieval_scores: list[float]
    provider: str
    model: str
    cached: bool


class ProviderInfo(BaseModel):
    name: str
    available: bool
    model: str


class ProvidersResponse(BaseModel):
    providers: list[ProviderInfo]
    active: str


class CacheStatsResponse(BaseModel):
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    entries: int
    expired_entries: int


class ClearCacheResponse(BaseModel):
    cleared: int
    message: str


class HealthResponse(BaseModel):
    status: str
    provider: str
    provider_available: bool
    knowledge_base_size: int
    cache_stats: CacheStatsResponse


# Endpoints
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint (public)."""
    provider_info = {
        "name": _llm_provider.name if _llm_provider else "unknown",
        "available": _llm_provider.is_available() if _llm_provider else False,
        "model": getattr(_llm_provider, "_model", "unknown") if _llm_provider else "unknown",
    }

    cache_stats = _answer_cache.stats() if _answer_cache else None

    return HealthResponse(
        status="healthy" if (provider_info["available"] or ENVIRONMENT == "development") else "degraded",
        provider=provider_info["name"],
        provider_available=provider_info["available"],
        knowledge_base_size=len(_knowledge_base) if _knowledge_base else 0,
        cache_stats=CacheStatsResponse(
            total_requests=cache_stats.total_requests if cache_stats else 0,
            cache_hits=cache_stats.cache_hits if cache_stats else 0,
            cache_misses=cache_stats.cache_misses if cache_stats else 0,
            hit_rate=cache_stats.hit_rate if cache_stats else 0.0,
            entries=cache_stats.entries if cache_stats else 0,
            expired_entries=cache_stats.expired_entries if cache_stats else 0,
        ),
    )


@app.get("/api/v1/providers", response_model=ProvidersResponse, tags=["Providers"])
async def list_providers_endpoint():
    """List available LLM providers."""
    providers = []
    for p in list_providers():
        providers.append(ProviderInfo(
            name=p.name,
            available=p.is_available(),
            model=getattr(p, "_model", "unknown"),
        ))

    return ProvidersResponse(
        providers=providers,
        active=LLM_PROVIDER,
    )


@app.post("/api/v1/answer", response_model=AnswerResponse, tags=["Q&A"])
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_WINDOW}seconds")
async def answer_question(
    request: Request,
    body: AnswerRequest,
    api_key: str = Depends(verify_api_key),
):
    """Ask a question and get a grounded answer with citations."""
    # Determine provider
    provider = _llm_provider
    provider_name = LLM_PROVIDER
    model = getattr(_llm_provider, "_model", "unknown")

    if body.provider and body.provider != LLM_PROVIDER:
        temp_provider = get_provider(body.provider)
        if temp_provider and temp_provider.is_available():
            provider = temp_provider
            provider_name = body.provider
            model = getattr(temp_provider, "_model", "unknown")

    # Check cache first
    cached_answer = None
    if _answer_cache:
        cached_answer = _answer_cache.get(
            question=body.question,
            provider=provider_name,
            model=model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            min_relevance_score=MIN_RELEVANCE_SCORE,
            top_k=TOP_K,
        )

    if cached_answer:
        return AnswerResponse(
            answer=cached_answer.answer,
            citations=[Citation(**c) for c in cached_answer.citations],
            retrieval_scores=cached_answer.retrieval_scores,
            provider=cached_answer.provider,
            model=cached_answer.model,
            cached=True,
        )

    # Generate answer
    answer = await provider.generate(
        system_prompt=AnsweringPipeline.SYSTEM_PROMPT,
        user_prompt=body.question,  # Pipeline will build full prompt
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    # Actually use pipeline for full RAG
    pipeline_answer = await _pipeline.answer(body.question)

    # Cache the result
    if _answer_cache:
        _answer_cache.set(
            question=body.question,
            answer=pipeline_answer,
            provider=provider_name,
            model=model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            min_relevance_score=MIN_RELEVANCE_SCORE,
            top_k=TOP_K,
        )

    return AnswerResponse(
        answer=pipeline_answer.answer,
        citations=[Citation(**c) for c in pipeline_answer.citations],
        retrieval_scores=pipeline_answer.retrieval_scores,
        provider=pipeline_answer.provider,
        model=pipeline_answer.model,
        cached=False,
    )


@app.get("/api/v1/cache/stats", response_model=CacheStatsResponse, tags=["Cache"])
async def cache_stats(api_key: str = Depends(verify_api_key)):
    """Get cache statistics."""
    if not _answer_cache:
        return CacheStatsResponse(
            total_requests=0,
            cache_hits=0,
            cache_misses=0,
            hit_rate=0.0,
            entries=0,
            expired_entries=0,
        )

    stats = _answer_cache.stats()
    return CacheStatsResponse(
        total_requests=stats.total_requests,
        cache_hits=stats.cache_hits,
        cache_misses=stats.cache_misses,
        hit_rate=stats.hit_rate,
        entries=stats.entries,
        expired_entries=stats.expired_entries,
    )


@app.post("/api/v1/cache/clear", response_model=ClearCacheResponse, tags=["Cache"])
async def clear_cache(api_key: str = Depends(verify_api_key)):
    """Clear all cache entries."""
    if not _answer_cache:
        return ClearCacheResponse(cleared=0, message="Cache not initialized")

    cleared = _answer_cache.clear()
    return ClearCacheResponse(
        cleared=cleared,
        message="Cache cleared successfully",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)