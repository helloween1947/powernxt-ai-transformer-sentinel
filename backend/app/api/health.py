import logging
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from backend.app.db.session import check_db_health
from backend.app.schemas.health import (
    HealthLiveResponse,
    HealthNotReadyResponse,
    HealthReadyResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/live",
    response_model=HealthLiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Process Liveness Check",
    description="Returns HTTP 200 when backend application process is alive. Does not depend on external services.",
)
def health_live() -> HealthLiveResponse:
    """Liveness probe to confirm the server process is responsive."""
    return HealthLiveResponse()


@router.get(
    "/ready",
    response_model=HealthReadyResponse,
    responses={
        200: {"model": HealthReadyResponse, "description": "Database connectivity operational"},
        503: {"model": HealthNotReadyResponse, "description": "Database connectivity unavailable"},
    },
    summary="Dependency Readiness Check",
    description="Probes PostgreSQL database readiness using SELECT 1. Returns 503 if unavailable.",
)
def health_ready() -> JSONResponse:
    """Readiness probe that tests database reachability without leaking credentials or tracebacks."""
    is_ready = check_db_health()
    if is_ready:
        payload = HealthReadyResponse().model_dump(mode="json")
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)

    logger.warning("Readiness probe reported database unavailable")
    payload = HealthNotReadyResponse().model_dump(mode="json")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
