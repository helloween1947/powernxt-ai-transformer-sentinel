"""Telemetry 1.0.0 validation; missing fields stay null and faults are forbidden."""

import re
from typing import Annotated, Literal

from pydantic import (
    UUID4,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.app.schemas.assets import StrictSchema, UTCDateTime

Identifier = Annotated[
    str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
]
Source = Literal["device", "simulator", "file_replay"]
Quality = Literal["good", "suspect", "bad", "missing"]
MeasurementName = Literal[
    "voltage_r_v",
    "voltage_y_v",
    "voltage_b_v",
    "current_r_a",
    "current_y_a",
    "current_b_a",
    "oil_temperature_c",
    "ambient_temperature_c",
    "oil_level_pct",
]
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


def require_iso_timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:[Zz]|[+-]\d{2}:\d{2})",
        value,
    ):
        raise ValueError("timestamp must be a timezone-aware ISO-8601 string")
    return value


ISOTime = Annotated[UTCDateTime, BeforeValidator(require_iso_timestamp)]


class Measurements(StrictSchema):
    voltage_r_v: Number | None = None
    voltage_y_v: Number | None = None
    voltage_b_v: Number | None = None
    current_r_a: Number | None = None
    current_y_a: Number | None = None
    current_b_a: Number | None = None
    oil_temperature_c: Number | None = None
    ambient_temperature_c: Number | None = None
    oil_level_pct: Number | None = None


class TelemetryCreate(StrictSchema):
    model_config = ConfigDict(str_strip_whitespace=False)

    schema_version: Literal["1.0.0"]
    message_id: UUID4
    asset_id: Identifier
    timestamp: UTCDateTime
    source: Source
    run_id: Identifier | None = None
    configuration_version: Annotated[int, Field(strict=True, gt=0)]
    measurements: Measurements
    measurement_quality: dict[MeasurementName, Quality] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_is_string(cls, value):
        return require_iso_timestamp(value)

    @model_validator(mode="after")
    def valid_stream_and_quality(self):
        if self.source == "device" and self.run_id is not None:
            raise ValueError("device telemetry must use run_id=null")
        if self.source != "device" and self.run_id is None:
            raise ValueError("simulator and file_replay telemetry require run_id")
        for name, flag in self.measurement_quality.items():
            missing = getattr(self.measurements, name) is None
            if missing != (flag == "missing"):
                raise ValueError(
                    f"measurement_quality.{name} must agree with measurement presence"
                )
        return self


class JobResponse(StrictSchema):
    id: int
    status: Literal["pending", "processing", "retry", "completed", "unavailable", "failed"]
    state_policy: Literal["forward_only", "historical_only"]


class TelemetryResponse(StrictSchema):
    id: int
    asset_id: str
    source: Source
    run_id: str | None
    message_id: UUID4
    configuration_version: int
    measurement_time: UTCDateTime
    arrival_time: UTCDateTime
    original_payload: dict
    normalized_telemetry: TelemetryCreate
    quality_flags: dict[str, list[str]]
    out_of_order: bool
    analytics_status: Literal["pending", "processing", "retry", "completed", "unavailable", "failed"] = "pending"
    processing_job: JobResponse


class TelemetryPage(StrictSchema):
    items: list[TelemetryResponse]
    limit: int
    offset: int
