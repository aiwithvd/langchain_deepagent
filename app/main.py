"""
LangChain DeepAgent — FastAPI application entry point.

Startup sequence:
  1. Configure structured logging
  2. Connect to Redis and initialise rate limiter
  3. Warm up the DeepAgent (loads model, discovers SKILL.md files)

Shutdown sequence:
  1. Close Redis / rate limiter connection
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.factory import get_agent
from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import LoggingMiddleware, get_logger, setup_logging
from app.core.rate_limit import close_rate_limiter, init_rate_limiter

settings = get_settings()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ── Startup ───────────────────────────────────────────────
    setup_logging(settings.log_level, settings.debug)
    log.info(
        "Starting LangChain DeepAgent",
        version=settings.app_version,
        model=settings.ollama_model,
        debug=settings.debug,
    )

    await init_rate_limiter()
    log.info("Rate limiter ready", redis_url=settings.redis_url)

    await get_agent()
    log.info("DeepAgent warmed up and ready")

    yield

    # ── Shutdown ──────────────────────────────────────────────
    await close_rate_limiter()
    log.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Production FastAPI service powering a LangChain DeepAgent with llama3.2:3b. "
            "Provides four skills — think, plan, web_search, write_report — "
            "via a ReAct agent loop with SSE streaming and Redis rate limiting."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Middleware (order matters: outermost = first to receive request) ──────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(agent_router, prefix="/api/v1")

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", path=str(request.url.path))
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    return app


app = create_app()
