"""API routing module; retain both analytical results and maintenance workflows."""

from fastapi import APIRouter

from backend.app.api.analytics import router as analytics_router
from backend.app.api.assets import router as assets_router
from backend.app.api.health import router as health_router
from backend.app.api.maintenance import router as maintenance_router
from backend.app.api.telemetry import router as telemetry_router
from backend.app.api.what_if import router as what_if_router

api_router = APIRouter()
for router in (
    health_router,
    assets_router,
    telemetry_router,
    analytics_router,
    maintenance_router,
    what_if_router,
):
    api_router.include_router(router)

__all__ = [
    "analytics_router",
    "api_router",
    "assets_router",
    "health_router",
    "maintenance_router",
    "telemetry_router",
    "what_if_router",
]
