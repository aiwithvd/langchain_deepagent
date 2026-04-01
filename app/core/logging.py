import time
import uuid
import logging
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

settings = get_settings()


def setup_logging(log_level: str = "INFO", debug: bool = False) -> None:
    """Configure structlog for JSON (production) or colored console (debug)."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if debug:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so uvicorn/fastapi logs go through structlog
    logging.basicConfig(
        format="%(message)s",
        level=logging.getLevelName(log_level.upper()),
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status, duration, and request_id."""

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
