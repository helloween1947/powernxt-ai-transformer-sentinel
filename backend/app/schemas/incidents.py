"""Versioned incident API control and retrieval contracts."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from backend.app.analytics.person_b.persistence import QUANTITIES
from backend.app.schemas.analytics import StoredAnalytics
from backend.app.schemas.assets import Finite, StrictSchema, UTCDateTime


class Rule(StrictSchema):
    name: str = Field(
        min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    )
    quantity: str
    unit: Literal["%", "C"]
    trigger: Finite
    recovery: Finite
    persistence_s: Finite = Field(gt=0)
    recovery_s: Finite = Field(gt=0)
    severity: Literal["info", "warning", "critical"]

    @model_validator(mode="after")
    def valid_rule(self):
        if QUANTITIES.get(self.quantity) != self.unit or self.recovery >= self.trigger:
            raise ValueError("Supported quantity/unit and recovery < trigger required")
        return self


class Policy(StrictSchema):
    version: str = Field(min_length=1, max_length=100)
    provenance: Literal["assumed", "measured", "team_agreed"]
    max_gap_s: Finite = Field(gt=0)
    rules: list[Rule] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def unique_names(self):
        if len({r.name for r in self.rules}) != len(self.rules):
            raise ValueError("Unique rule names required")
        return self


class Handover(StrictSchema):
    schema_version: Literal["incident-control-1.0.0"]
    expected_version: int = Field(ge=0, strict=True)
    idempotency_key: UUID
    source: Literal["device", "simulator", "file_replay"]
    run_id: str | None = Field(default=None, min_length=1, max_length=100)
    configuration_version: int = Field(gt=0, strict=True)
    model_version: Literal[
        "stored-reading-top-oil-1.0.1", "stored-reading-top-oil-1.0.2"
    ]
    detector_version: Literal["sustained-threshold-1.0.1"]
    policy: Policy
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def stream(self):
        if (self.source == "device") != (self.run_id is None):
            raise ValueError("Device requires null run; simulator/replay require run")
        return self


class ModelHandover(Handover):
    """Explicit namespace transition without opting into detection."""

    schema_version: Literal["model-control-1.0.0"]
    model_version: Literal["stored-reading-top-oil-1.0.2"]
    detector_version: Literal["sustained-threshold-1.0.1"] = "sustained-threshold-1.0.1"
    policy: None = None


class Acknowledgement(StrictSchema):
    schema_version: Literal["incident-acknowledgement-1.0.0"]
    expected_version: int = Field(gt=0, strict=True)
    idempotency_key: UUID


class AckState(StrictSchema):
    status: Literal["unacknowledged", "acknowledged"]
    acknowledged_at: UTCDateTime | None
    actor_ref: UUID | None


class IncidentResponse(StrictSchema):
    schema_version: Literal["incident-1.0.0"] = "incident-1.0.0"
    incident_id: UUID
    incident_version: int
    asset_id: str
    source: Literal["analytics"] = "analytics"
    measurement_source: Literal["device", "simulator", "file_replay"]
    run_id: str | None
    category: str
    severity: Literal["info", "warning", "critical"]
    detector_epoch: UUID
    detector_episode_key: str
    condition_status: Literal["active", "recovered"]
    monitoring_status: Literal["monitoring", "interrupted"]
    opened_at: UTCDateTime
    recovered_at: UTCDateTime | None
    last_evaluated_measurement_time: UTCDateTime
    last_evidence_status: Literal["available", "unavailable"]
    acknowledgement: AckState


class EvidenceResponse(StrictSchema):
    evidence_id: int
    incident_id: UUID
    incident_version: int
    recorded_at: UTCDateTime
    payload: dict


class EventResponse(StrictSchema):
    event_id: UUID
    incident_id: UUID
    incident_version: int
    event_type: str
    evidence_id: int | None
    actor_id: UUID | None
    recorded_at: UTCDateTime
    payload: dict


class IncidentPage(StrictSchema):
    schema_version: Literal["incident-page-1.0.0"] = "incident-page-1.0.0"
    items: list[IncidentResponse]
    next_cursor: UUID | None


class EvidencePage(StrictSchema):
    schema_version: Literal["incident-evidence-page-1.0.0"] = (
        "incident-evidence-page-1.0.0"
    )
    items: list[EvidenceResponse]
    next_cursor: int | None


class EventPage(StrictSchema):
    schema_version: Literal["incident-event-page-1.0.0"] = "incident-event-page-1.0.0"
    items: list[EventResponse]
    next_cursor: int | None


class ControlResponse(StrictSchema):
    schema_version: Literal["incident-control-result-1.0.0"] = (
        "incident-control-result-1.0.0"
    )
    control_version: int
    detector_epoch: UUID
    previous_epoch: UUID | None
    asset_id: str
    source: str
    run_id: str | None
    configuration_version: int
    model_version: str
    detector_version: str
    parameter_version: str
    policy_fingerprint: str
    actor_ref: UUID
    boundary_measurement_time: UTCDateTime | None


class ErrorResponse(StrictSchema):
    schema_version: Literal["incident-error-1.0.0"] = "incident-error-1.0.0"
    code: str
    message: str
    current_version: int | None = None


class OperatorResponse(StrictSchema):
    schema_version: Literal["incident-operator-1.0.0"] = "incident-operator-1.0.0"
    actor_ref: UUID
    name: str
    role: Literal["reader", "operator", "admin"]
    expires_at: UTCDateTime


class ExactResultResponse(StrictSchema):
    schema_version: Literal["incident-stored-result-1.0.0"] = (
        "incident-stored-result-1.0.0"
    )
    result: StoredAnalytics
