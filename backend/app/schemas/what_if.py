"""Bounded public scenario inputs; no serialized model state or coefficients."""

from typing import Literal

from pydantic import UUID4, Field, model_validator

from backend.app.schemas.assets import Finite, StrictSchema, UTCDateTime
from backend.app.schemas.telemetry import Identifier, Source


class Segment(StrictSchema):
    duration_s: Finite = Field(gt=0, le=86400)
    thermal_load_pu: Finite = Field(ge=0, le=10)
    ambient_temperature_c: Finite = Field(ge=-50, le=80)


class WhatIfRequest(StrictSchema):
    schema_version: Literal["what-if-request-1.0.0"]
    source: Source
    run_id: Identifier | None = None
    state_ref: UUID4 | None = None
    baseline: Segment
    reduced_load: Segment

    @model_validator(mode="after")
    def comparison(self):
        if (self.source == "device") != (self.run_id is None):
            raise ValueError("Device uses null run; simulator/replay require run")
        if self.baseline.duration_s != self.reduced_load.duration_s:
            raise ValueError("Equal durations required")
        if self.reduced_load.thermal_load_pu > self.baseline.thermal_load_pu:
            raise ValueError("Reduced load cannot exceed baseline")
        if (
            self.reduced_load.ambient_temperature_c
            != self.baseline.ambient_temperature_c
        ):
            raise ValueError("Equal ambient required to isolate load effect")
        return self


class Point(StrictSchema):
    elapsed_s: Finite = Field(ge=0)
    estimated_top_oil_temperature_c: Finite


class Crossing(StrictSchema):
    status: Literal["crossing", "no_crossing_within_horizon", "unavailable"]
    time_s: Finite | None
    reasons: list[str]


class Scenario(StrictSchema):
    inputs: Segment
    points: list[Point] = Field(min_length=2, max_length=97)
    final_top_oil_temperature_c: Finite
    peak_top_oil_temperature_c: Finite
    limit_crossing: Crossing


class StateReference(StrictSchema):
    state_ref: UUID4
    asset_id: str
    source: Source
    run_id: str | None
    reading_id: int
    result_id: int
    measurement_time: UTCDateTime
    captured_at: UTCDateTime


class ConfigurationReference(StrictSchema):
    asset_id: str
    version: int
    created_at: UTCDateTime
    parameter_version: str


class WhatIfResponse(StrictSchema):
    schema_version: Literal["what-if-response-1.0.0"] = "what-if-response-1.0.0"
    state: StateReference
    configuration: ConfigurationReference
    model: dict[str, str]
    units: dict[str, str]
    parameter_provenance: dict[str, str]
    assumptions: list[str]
    sampling: dict[str, str | int]
    configured_top_oil_limit_c: Finite | None
    limit_reasons: list[str]
    baseline: Scenario
    reduced_load: Scenario
    final_temperature_difference_c: Finite


class WhatIfErrorDetail(StrictSchema):
    schema_version: Literal["what-if-error-1.0.0"]
    code: Literal[
        "invalid_request",
        "asset_not_found",
        "state_not_found",
        "state_unavailable",
        "incompatible_state_identity",
        "ineligible_state",
        "missing_model_parameters",
        "computation_unavailable",
        "database_unavailable",
    ]
    message: str
    reasons: list[str]


class WhatIfErrorResponse(StrictSchema):
    detail: WhatIfErrorDetail
