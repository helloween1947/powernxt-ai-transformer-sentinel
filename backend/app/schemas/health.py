from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthLiveResponse(BaseModel):
    """Schema for liveness probe response."""

    status: str = Field(default="live", description="Process liveness state")
    service: str = Field(default="backend-api", description="Service identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp in UTC",
    )


class HealthReadyResponse(BaseModel):
    """Schema for readiness probe response when database is connected."""

    status: str = Field(default="ready", description="Application readiness state")
    database: str = Field(default="connected", description="Database connection state")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp in UTC",
    )


class HealthNotReadyResponse(BaseModel):
    """Schema for readiness probe response when database is unavailable."""

    status: str = Field(default="unhealthy", description="Application readiness state")
    database: str = Field(default="disconnected", description="Database connection state")
    detail: str = Field(default="Database connection probe failed", description="Sanitized status message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp in UTC",
    )
