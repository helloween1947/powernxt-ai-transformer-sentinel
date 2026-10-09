"""Short PostgreSQL claims and fenced commits; deterministic computation outside locks."""

import json
import math
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased

from backend.app.analytics import adapter
from backend.app.models import AssetConfiguration
from backend.app.models.analytics import (
    AnalyticsResult,
    AnalyticsState,
    AnalyticsStream,
)
from backend.app.models.telemetry import ProcessingJob, TelemetryReading
from backend.app.services.incidents import persist_plan, mark_continuity_break
from backend.app.analytics.person_b.incident_orchestration import IncidentPlanningError

NONTERMINAL = ("pending", "retry", "processing")


@dataclass(frozen=True)
class Claim:
    job_id: int
    token: UUID


class StaleClaim(Exception):
    """Lease expired or a different worker owns this stream/job."""


class ComputationError(Exception):
    pass


def stream_key(reading):
    return (reading.asset_id, reading.source, reading.run_key)


def db_time(db):
    return db.scalar(select(func.clock_timestamp()))


def claim_next(factory, *, lease_seconds=60, max_attempts=3):
    if not math.isfinite(lease_seconds) or lease_seconds <= 0 or max_attempts < 1:
        raise ValueError("Positive lease and retry bound required")
    with factory.begin() as db:
        now = db_time(db)
        earlier_job, earlier_reading = aliased(ProcessingJob), aliased(TelemetryReading)
        earlier = exists(
            select(earlier_job.id)
            .join(earlier_reading, earlier_reading.id == earlier_job.reading_id)
            .where(
                earlier_job.status.in_(NONTERMINAL),
                earlier_reading.asset_id == TelemetryReading.asset_id,
                earlier_reading.source == TelemetryReading.source,
                earlier_reading.run_key == TelemetryReading.run_key,
                or_(
                    earlier_reading.measurement_time
                    < TelemetryReading.measurement_time,
                    and_(
                        earlier_reading.measurement_time
                        == TelemetryReading.measurement_time,
                        earlier_reading.id < TelemetryReading.id,
                    ),
                ),
            )
        )
        eligible = or_(
            and_(
                ProcessingJob.status.in_(("pending", "retry")),
                ProcessingJob.available_at <= now,
            ),
            and_(
                ProcessingJob.status == "processing", ProcessingJob.lease_until <= now
            ),
        )
        # One earliest nonterminal job per stream. Delayed retries hold that stream,
        # but SKIP LOCKED permits independent streams to make progress.
        rows = db.execute(
            select(ProcessingJob, TelemetryReading)
            .join(TelemetryReading, TelemetryReading.id == ProcessingJob.reading_id)
            .where(eligible, ~earlier)
            .order_by(TelemetryReading.measurement_time, TelemetryReading.id)
            .limit(64)
            .with_for_update(of=ProcessingJob, skip_locked=True)
        )
        for job, reading in rows:
            key = stream_key(reading)
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
                .with_for_update(skip_locked=True)
            )
            if head is None or (head.active_token and head.lease_until > now):
                continue
            if job.attempts >= max_attempts:
                job.status, job.last_error, job.completed_at = (
                    "failed",
                    "lease_expired_attempts_exhausted",
                    now,
                )
                job.claim_token = job.lease_until = None
                mark_continuity_break(db, reading, state_policy=job.state_policy)
                if head.active_job_id == job.id:
                    head.active_token = head.active_job_id = head.lease_until = None
                continue
            token = uuid4()
            job.status, job.attempts, job.claim_token = (
                "processing",
                job.attempts + 1,
                token,
            )
            job.lease_until = now + timedelta(seconds=lease_seconds)
            head.active_token, head.active_job_id, head.lease_until = (
                token,
                job.id,
                job.lease_until,
            )
            return Claim(job.id, token)
    return None


def fenced(db, claim):
    job = db.scalar(
        select(ProcessingJob).where(ProcessingJob.id == claim.job_id).with_for_update()
    )
    if job is None:
        raise StaleClaim
    reading = db.get(TelemetryReading, job.reading_id)
    head = db.scalar(
        select(AnalyticsStream)
        .where(
            AnalyticsStream.asset_id == reading.asset_id,
            AnalyticsStream.source == reading.source,
            AnalyticsStream.run_key == reading.run_key,
        )
        .with_for_update()
    )
    now = db_time(db)
    if (
        job.status != "processing"
        or job.claim_token != claim.token
        or job.lease_until <= now
        or head is None
        or head.active_token != claim.token
        or head.active_job_id != job.id
        or head.lease_until <= now
    ):
        raise StaleClaim
    return job, reading, head, now


def namespace(reading, config):
    return (
        *stream_key(reading),
        adapter.MODEL_ID,
        adapter.MODEL_VERSION,
        reading.configuration_version,
        adapter.parameter_identity(config),
    )


def identity(key):
    return json.dumps(key[3:], separators=(",", ":"))


def process_claim(factory, claim, *, compute=None, before_commit=None):
    # Read snapshot under the same fencing checks; release DB locks during compute.
    with factory.begin() as db:
        job, reading, head, _ = fenced(db, claim)
        config = db.scalar(
            select(AssetConfiguration).where(
                AssetConfiguration.asset_id == reading.asset_id,
                AssetConfiguration.version == reading.configuration_version,
            )
        )
        config_payload = adapter.configuration_payload(config)
        key = namespace(reading, config_payload)
        saved = db.get(AnalyticsState, key)
        previous = (
            saved.state if saved and head.last_identity == identity(key) else None
        )
        policy = job.state_policy
        if (
            head.watermark_time is not None
            and reading.measurement_time <= head.watermark_time
        ):
            policy = "historical_only"
        # Scalar/JSON values remain available after this session closes.
        db.expunge(reading)
    output = (compute or adapter.compute)(reading, config_payload, previous, policy)
    json.dumps(output, allow_nan=False)
    if output["execution_status"]["outcome"] == "computation_error":
        # Roll back this reading's state and retry; never commit failed evolution.
        raise ComputationError
    if (
        output["metadata"]["model_id"] != key[3]
        or output["metadata"]["model_version"] != key[4]
        or output["metadata"]["parameter_version"] != key[6]
    ):
        raise ComputationError("model_binding_mismatch")
    with factory.begin() as db:
        job, reading, head, now = fenced(db, claim)
        authorized_until = min(job.lease_until, head.lease_until)
        advancing = output["execution_status"]["state_advanced"]
        if advancing and (
            policy != "forward_only"
            or (
                head.watermark_time is not None
                and reading.measurement_time <= head.watermark_time
            )
        ):
            raise StaleClaim
        # Partial bootstrap/unsupported thermal is a completed computation with
        # explicit metric availability. Insufficient input/state is unavailable.
        status = (
            "unavailable"
            if output["execution_status"]["outcome"] == "insufficient_input_or_state"
            else "completed"
        )
        result = AnalyticsResult(
            reading_id=reading.id,
            model_id=key[3],
            model_version=key[4],
            parameter_version=key[6],
            schema_version=output["metadata"]["result_schema_version"],
            status=status,
            payload=output,
        )
        db.add(result)
        db.flush()  # Detector evidence binds to this real result ID, never a placeholder.
        persist_plan(db, reading, result, now, state_policy=policy)
        if advancing:
            state = db.get(AnalyticsState, key)
            if state is None:
                state = AnalyticsState(
                    **dict(
                        zip(
                            (
                                "asset_id",
                                "source",
                                "run_key",
                                "model_id",
                                "model_version",
                                "configuration_version",
                                "parameter_version",
                            ),
                            key,
                        )
                    ),
                    state=output["updated_state"],
                    advances=1,
                    updated_at=now,
                )
                db.add(state)
            else:
                state.state, state.advances, state.updated_at = (
                    output["updated_state"],
                    state.advances + 1,
                    now,
                )
            head.watermark_time, head.watermark_reading_id, head.last_identity = (
                reading.measurement_time,
                reading.id,
                identity(key),
            )
            head.advances += 1
        job.status, job.completed_at, job.last_error = status, now, None
        job.claim_token = job.lease_until = None
        head.active_token = head.active_job_id = head.lease_until = None
        db.flush()
        if before_commit:
            before_commit(db)  # Fault injection for transactional regression tests.
        if db_time(db) >= authorized_until:
            raise StaleClaim
    return output


def record_failure(factory, claim, error, *, max_attempts=3, retry_seconds=1):
    with factory.begin() as db:
        job, reading, head, now = fenced(db, claim)
        # Persist bounded machine codes, never exception text/payload/credentials.
        job.last_error = (
            error.code
            if isinstance(error, IncidentPlanningError)
            else "invalid_computation_input"
            if isinstance(error, ValueError)
            else "thermal_computation_error"
            if isinstance(error, ComputationError)
            else "worker_computation_error"
        )
        job.status = "failed" if job.attempts >= max_attempts else "retry"
        if job.status == "failed":
            mark_continuity_break(db, reading, state_policy=job.state_policy)
        job.available_at = now + timedelta(
            seconds=min(300, retry_seconds * 2 ** (job.attempts - 1))
        )
        job.completed_at = now if job.status == "failed" else None
        job.claim_token = job.lease_until = None
        head.active_token = head.active_job_id = head.lease_until = None


def run_once(factory, **options):
    claim = claim_next(factory, **options)
    if claim is None:
        return False
    try:
        process_claim(factory, claim)
    except StaleClaim:
        pass  # Another worker can recover; a stale owner must not write even errors.
    except Exception as error:  # noqa: BLE001 — isolate unexpected model failures for bounded retry
        try:
            record_failure(
                factory, claim, error, max_attempts=options.get("max_attempts", 3)
            )
        except StaleClaim:
            pass
    return True
