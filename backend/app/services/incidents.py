"""Fenced incident persistence and trusted, versioned operator operations."""

import hashlib
import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.app.analytics import adapter
from backend.app.analytics.person_b.incident_orchestration import (
    IncidentPlanningError,
    evaluate_incident_candidates,
)
from backend.app.analytics.person_b.persistence import DETECTOR_VERSION
from backend.app.models import Asset, AssetConfiguration
from backend.app.models.analytics import AnalyticsState, AnalyticsStream
from backend.app.models.incidents import (
    DetectorControl,
    DetectorEpoch,
    Incident,
    IncidentEvent,
    IncidentEvidence,
    IncidentOperation,
)
from backend.app.schemas.incidents import ControlResponse, IncidentResponse


class IncidentError(Exception):
    def __init__(self, status, code, message, current_version=None):
        self.status, self.code, self.message, self.current_version = (
            status,
            code,
            message,
            current_version,
        )


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def get_incident(db, incident_id, *, lock=False):
    query = select(Incident).where(Incident.id == incident_id)
    if lock:
        query = query.with_for_update()
    incident = db.scalar(query)
    if incident is None:
        raise IncidentError(404, "incident_not_found", "Incident not found")
    return incident


def serialize(incident):
    return IncidentResponse(
        incident_id=incident.id,
        incident_version=incident.version,
        asset_id=incident.asset_id,
        measurement_source=incident.measurement_source,
        run_id=incident.run_key or None,
        category=incident.category,
        severity=incident.severity,
        detector_epoch=incident.detector_epoch,
        detector_episode_key=incident.detector_episode_key,
        condition_status=incident.condition_status,
        monitoring_status=incident.monitoring_status,
        opened_at=incident.opened_at,
        recovered_at=incident.recovered_at,
        last_evaluated_measurement_time=incident.last_evaluated_measurement_time,
        last_evidence_status=incident.last_evidence_status,
        acknowledgement={
            "status": "acknowledged" if incident.actor_id else "unacknowledged",
            "acknowledged_at": incident.acknowledged_at,
            "actor_ref": incident.actor_id,
        },
    )


def event(db, incident, kind, now, *, evidence_id=None, actor_id=None, details=None):
    snapshot = serialize(incident).model_dump(mode="json")
    db.add(
        IncidentEvent(
            event_id=uuid4(),
            incident_id=incident.id,
            incident_version=incident.version,
            event_type="incident." + kind,
            evidence_id=evidence_id,
            actor_id=actor_id,
            recorded_at=now,
            payload={
                "schema_version": "incident-event-1.0.0",
                "incident": snapshot,
                "details": details or {},
            },
        )
    )


def retry(db, scope, payload, actor):
    fingerprint = digest({**payload.model_dump(mode="json"), "actor_id": str(actor.id)})
    receipt = db.get(IncidentOperation, (scope, payload.idempotency_key))
    if receipt and receipt.fingerprint != fingerprint:
        raise IncidentError(
            409,
            "idempotency_conflict",
            "Idempotency key reused with different request or actor",
        )
    return receipt, fingerprint


def acknowledge(db, incident_id, payload, actor, now):
    incident = get_incident(db, incident_id, lock=True)
    scope = "ack:" + str(incident_id)
    receipt, fingerprint = retry(db, scope, payload, actor)
    if receipt:
        return receipt.response, False
    if payload.expected_version != incident.version:
        raise IncidentError(
            409, "version_conflict", "Incident version changed", incident.version
        )
    if incident.actor_id is not None:
        raise IncidentError(
            409,
            "already_acknowledged",
            "Incident already acknowledged",
            incident.version,
        )
    incident.version += 1
    incident.actor_id, incident.acknowledged_at = actor.id, now
    event(db, incident, "acknowledged", now, actor_id=actor.id)
    response = serialize(incident).model_dump(mode="json")
    db.add(
        IncidentOperation(
            scope=scope,
            key=payload.idempotency_key,
            actor_id=actor.id,
            fingerprint=fingerprint,
            response=response,
        )
    )
    db.commit()
    return response, True


def handover(db, asset_id, payload, actor, now):
    if db.get(Asset, asset_id) is None:
        raise IncidentError(404, "asset_not_found", "Asset not found")
    key = (asset_id, payload.source, payload.run_id or "")
    # Same stream lock as the worker. A live lease must finish/expire before control changes.
    db.execute(
        insert(AnalyticsStream)
        .values(asset_id=key[0], source=key[1], run_key=key[2])
        .on_conflict_do_nothing()
    )
    head = db.scalar(
        select(AnalyticsStream)
        .where(
            AnalyticsStream.asset_id == key[0],
            AnalyticsStream.source == key[1],
            AnalyticsStream.run_key == key[2],
        )
        .with_for_update()
    )
    scope = "handover:" + digest(key)
    receipt, fingerprint = retry(db, scope, payload, actor)
    if receipt:
        return receipt.response, False
    control = db.get(DetectorControl, key)
    current = control.version if control else 0
    if payload.expected_version != current:
        raise IncidentError(
            409, "version_conflict", "Detector control version changed", current
        )
    if head.active_token is not None and head.lease_until > now:
        raise IncidentError(
            409,
            "stream_busy",
            "Retry after the current worker lease finishes or expires",
            current,
        )
    config = db.scalar(
        select(AssetConfiguration).where(
            AssetConfiguration.asset_id == asset_id,
            AssetConfiguration.version == payload.configuration_version,
        )
    )
    if config is None:
        raise IncidentError(
            404, "configuration_not_found", "Asset configuration not found"
        )
    parameter = adapter.parameter_identity(adapter.configuration_payload(config))
    previous_twin_state = None
    if head.last_identity is not None:
        previous_namespace = json.loads(head.last_identity)
        saved = db.get(AnalyticsState, (*key, *previous_namespace))
        if saved is not None:
            previous_twin_state = {
                "namespace": previous_namespace,
                "state": saved.state,
                "advances": saved.advances,
                "updated_at": saved.updated_at.isoformat(),
            }
    epoch = DetectorEpoch(
        id=uuid4(),
        asset_id=key[0],
        source=key[1],
        run_key=key[2],
        configuration_version=payload.configuration_version,
        model_version=payload.model_version,
        parameter_version=parameter,
        detector_version=payload.detector_version,
        policy=payload.policy.model_dump(mode="json"),
        policy_fingerprint=digest(payload.policy.model_dump(mode="json")),
        context=None,
        previous_twin_state=previous_twin_state,
        actor_id=actor.id,
        reason=payload.reason,
        boundary_time=head.watermark_time,
        created_at=now,
    )
    db.add(epoch)
    db.flush()
    previous_epoch = control.epoch_id if control else None
    if control:
        # Preserve active episodes and acknowledgement; interruption is not recovery.
        active = db.scalars(
            select(Incident)
            .where(
                Incident.detector_epoch == control.epoch_id,
                Incident.condition_status == "active",
            )
            .order_by(Incident.id)
            .with_for_update()
        ).all()
        for incident in active:
            incident.version += 1
            incident.monitoring_status = "interrupted"
            incident.last_evidence_status = "unavailable"
            event(
                db,
                incident,
                "monitoring_interrupted",
                now,
                actor_id=actor.id,
                details={"reason": payload.reason, "successor_epoch": str(epoch.id)},
            )
        control.epoch_id, control.version, control.continuity_break = (
            epoch.id,
            current + 1,
            False,
        )
    else:
        db.add(
            DetectorControl(
                asset_id=key[0],
                source=key[1],
                run_key=key[2],
                epoch_id=epoch.id,
                version=1,
                continuity_break=False,
            )
        )
    # Cold start even for a reset with identical model/config. Retain all old state rows.
    head.last_identity = None
    head.active_token = head.active_job_id = head.lease_until = None
    response = ControlResponse(
        control_version=current + 1,
        detector_epoch=epoch.id,
        previous_epoch=previous_epoch,
        asset_id=asset_id,
        source=payload.source,
        run_id=payload.run_id,
        configuration_version=epoch.configuration_version,
        model_version=epoch.model_version,
        detector_version=epoch.detector_version,
        parameter_version=parameter,
        policy_fingerprint=epoch.policy_fingerprint,
        actor_ref=actor.id,
        boundary_measurement_time=epoch.boundary_time,
    ).model_dump(mode="json")
    db.add(
        IncidentOperation(
            scope=scope,
            key=payload.idempotency_key,
            actor_id=actor.id,
            fingerprint=fingerprint,
            response=response,
        )
    )
    db.commit()
    return response, True


def mark_continuity_break(db, reading, *, state_policy="forward_only"):
    if state_policy != "forward_only":
        return
    head = db.get(AnalyticsStream, (reading.asset_id, reading.source, reading.run_key))
    if head and head.watermark_time and reading.measurement_time <= head.watermark_time:
        return
    control = db.get(
        DetectorControl, (reading.asset_id, reading.source, reading.run_key)
    )
    if control:
        control.continuity_break = True


def persist_plan(db, reading, result, now, *, state_policy="forward_only"):
    """Called only inside the worker's final fenced transaction. Never commits."""
    control = db.get(
        DetectorControl, (reading.asset_id, reading.source, reading.run_key)
    )
    if control is None:
        return  # Explicit opt-in only; existing analytics unchanged.
    # Historical results do not inspect/install a successor namespace or consume barriers.
    if not result.payload["execution_status"]["state_advanced"]:
        mark_continuity_break(db, reading, state_policy=state_policy)
        return
    epoch = db.get(DetectorEpoch, control.epoch_id)
    if (
        epoch.configuration_version != reading.configuration_version
        or epoch.model_version != result.model_version
        or epoch.parameter_version != result.parameter_version
        or epoch.detector_version != DETECTOR_VERSION
        or epoch.policy_fingerprint != digest(epoch.policy)
    ):
        raise IncidentPlanningError(
            "incident_handover_required",
            "Recorded handover required before namespace change",
        )
    meta = result.payload["metadata"]
    if (
        meta["stream"]
        != {
            "asset_id": reading.asset_id,
            "source": reading.source,
            "run_id": reading.run_key or None,
        }
        or meta["reading_identity"]
        != {"reading_id": reading.id, "message_id": str(reading.message_id)}
        or datetime.fromisoformat(meta["measurement_time"].replace("Z", "+00:00"))
        != reading.measurement_time
        or meta["configuration_version"] != reading.configuration_version
    ):
        raise IncidentPlanningError(
            "incident_invalid_input_or_state", "Authoritative result binding mismatch"
        )
    plan = evaluate_incident_candidates(
        result.payload,
        epoch.policy,
        detector_epoch=str(epoch.id),
        result_id=result.id,
        previous_context=epoch.context,
        continuity_break=control.continuity_break,
    )
    for command in plan["mutations"]:
        mapping = command["mapping_key"]
        incident = db.scalar(
            select(Incident)
            .where(
                Incident.asset_id == reading.asset_id,
                Incident.detector_epoch == epoch.id,
                Incident.detector_episode_key == mapping["detector_episode_key"],
            )
            .with_for_update()
        )
        kind, evidence = command["kind"], command["evidence"]
        if incident is None:
            if kind != "opened":
                raise IncidentPlanningError(
                    "incident_invalid_input_or_state", "Missing canonical mapping"
                )
            incident = Incident(
                id=uuid4(),
                asset_id=reading.asset_id,
                measurement_source=reading.source,
                run_key=reading.run_key,
                detector_epoch=epoch.id,
                detector_episode_key=mapping["detector_episode_key"],
                category=command["category"],
                severity=command["severity"],
                version=1,
                condition_status="active",
                monitoring_status="monitoring",
                opened_at=reading.measurement_time,
                recovered_at=None,
                last_evaluated_measurement_time=reading.measurement_time,
                last_evidence_status="available",
                actor_id=None,
                acknowledged_at=None,
            )
            db.add(incident)
            db.flush()
        else:
            if (
                kind == "opened"
                or incident.condition_status != "active"
                or incident.measurement_source != reading.source
                or incident.run_key != reading.run_key
                or incident.category != command["category"]
                or reading.measurement_time <= incident.last_evaluated_measurement_time
            ):
                raise IncidentPlanningError(
                    "incident_invalid_input_or_state", "Contradictory canonical mapping"
                )
            incident.version += 1
        incident.last_evaluated_measurement_time = reading.measurement_time
        incident.last_evidence_status = (
            "available" if evidence["rule_evidence"]["available"] else "unavailable"
        )
        if kind == "recovered":
            incident.condition_status, incident.recovered_at = (
                "recovered",
                reading.measurement_time,
            )
        snapshot = IncidentEvidence(
            incident_id=incident.id,
            incident_version=incident.version,
            result_id=result.id,
            reading_id=reading.id,
            detector_version=epoch.detector_version,
            policy_fingerprint=epoch.policy_fingerprint,
            payload=evidence,
            recorded_at=now,
        )
        db.add(snapshot)
        db.flush()
        event(db, incident, kind, now, evidence_id=snapshot.id)
    epoch.context = plan["updated_context"]
    if plan["continuity_break_consumed"]:
        control.continuity_break = False
