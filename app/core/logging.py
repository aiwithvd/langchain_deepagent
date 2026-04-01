import logging
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

settings = get_settings()


def setup_logging(log_level: str = "INFO", debug: bool = False) -> None:
    """Configure structlog for JSON (production) or colored console (debug)."""
    level = logging.getLevelName(log_level.upper())

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    renderer: structlog.types.Processor = (
        structlog.dev.ConsoleRenderer(colors=True)
        if debug
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, httpx, etc.) through the same level
    logging.basicConfig(format="%(message)s", level=level)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request: method, path, status code, duration, request_id."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        log = get_logger("http")
        log.info("request.start")

        start = time.perf_counter()
        response: Response
        try:
            response = await call_next(request)
        except Exception:
            log.exception("request.failed")
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            status = getattr(response, "status_code", 0)
            structlog.contextvars.bind_contextvars(
                status_code=status,
                duration_ms=duration_ms,
            )
            log.info("request.complete")

        response.headers["X-Request-ID"] = request_id
        return response
