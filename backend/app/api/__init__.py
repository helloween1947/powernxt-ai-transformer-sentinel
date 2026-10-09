"""API routing module."""

from fastapi import APIRouter

from backend.app.api.assets import router as assets_router
from backend.app.api.health import router as health_router
from backend.app.api.telemetry import router as telemetry_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(assets_router)
api_router.include_router(telemetry_router)

__all__ = ["api_router", "assets_router", "health_router", "telemetry_router"]

from backend.app.api.analytics import router as analytics_router
api_router.include_router(analytics_router)
