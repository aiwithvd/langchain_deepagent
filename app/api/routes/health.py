import httpx
from fastapi import APIRouter

from app.core.config import get_settings
from app.core.rate_limit import check_redis_health
from app.models.schemas import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", summary="Liveness probe", tags=["health"])
async def liveness() -> dict[str, str]:
    """
    Liveness probe — returns 200 immediately if the process is running.
    Use this for container/Kubernetes liveness checks.
    """
    return {"status": "ok"}


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    tags=["health"],
)
async def readiness() -> HealthResponse:
    """
    Readiness probe — checks that all external dependencies are reachable.

    - Pings the Ollama API (`/api/tags`)
    - Pings Redis

    Returns `status: "ok"` only when both are reachable.
    Use this for container/Kubernetes readiness checks.
    """
    ollama_reachable = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_reachable = resp.status_code == 200
    except Exception:
        pass

    redis_reachable = await check_redis_health()

    status = "ok" if (ollama_reachable and redis_reachable) else "degraded"

    return HealthResponse(
        status=status,
        version=settings.app_version,
        ollama_reachable=ollama_reachable,
        redis_reachable=redis_reachable,
    )
