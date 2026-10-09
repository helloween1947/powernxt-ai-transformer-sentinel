"""Serialized admission per asset; raw data, normalized data and job commit together."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import AssetConfiguration
from backend.app.models.telemetry import ProcessingJob, TelemetryReading
from backend.app.schemas.telemetry import TelemetryCreate, TelemetryResponse
from backend.app.services.assets import require_asset


class TelemetryConflict(Exception):
    pass


class ConfigurationNotFound(Exception):
    pass


class ReadingNotFound(Exception):
    pass


def stream_query(asset_id, source, run_id):
    return select(TelemetryReading).where(
        TelemetryReading.asset_id == asset_id,
        TelemetryReading.source == source,
        TelemetryReading.run_key == (run_id or ""),
    )


def response_for(db: Session, reading: TelemetryReading) -> TelemetryResponse:
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.reading_id == reading.id))
    return TelemetryResponse(
        id=reading.id,
        asset_id=reading.asset_id,
        source=reading.source,
        run_id=reading.run_key or None,
        message_id=reading.message_id,
        configuration_version=reading.configuration_version,
        measurement_time=reading.measurement_time,
        arrival_time=reading.arrival_time,
        original_payload=reading.original_payload,
        normalized_telemetry=reading.normalized_telemetry,
        quality_flags=reading.quality_flags,
        out_of_order=reading.out_of_order,
        analytics_status=job.status,
        processing_job=job,
    )


def normalize(payload: TelemetryCreate, config: AssetConfiguration):
    normalized = payload.model_dump(mode="json")
    flags = {}
    for key, value in normalized["measurements"].items():
        quality = payload.measurement_quality.get(
            key, "missing" if value is None else "good"
        )
        normalized["measurement_quality"][key] = quality
        reasons = []
        if quality != "good":
            reasons.append(quality)
        if value is not None:
            if key.startswith(("voltage_", "current_")):
                if value < 0:
                    reasons.append("negative_magnitude")
                rating = (
                    config.rated_voltage_v
                    if key.startswith("voltage_")
                    else config.rated_current_a
                )
                if value > 10 * rating:
                    reasons.append("above_10x_rating")
            elif (
                key.endswith("temperature_c")
                and (value < -273.15 or value > 250)
                or key == "oil_level_pct"
                and not 0 <= value <= 100
            ):
                reasons.append("outside_sanity_range")
        if reasons:
            flags[key] = reasons
    return normalized, flags


def ingest(db: Session, payload: TelemetryCreate, original: dict):
    # Shared registry parent lock also serializes config creation, deduplication,
    # and the event-time watermark check. The fresh queries use READ COMMITTED.
    require_asset(db, payload.asset_id, lock=True)
    fingerprint = hashlib.sha256(
        json.dumps(
            original,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    existing = db.scalar(
        stream_query(payload.asset_id, payload.source, payload.run_id).where(
            TelemetryReading.message_id == payload.message_id
        )
    )
    if existing:
        if existing.payload_fingerprint != fingerprint:
            raise TelemetryConflict
        result = response_for(db, existing)
        db.commit()
        return result, False
    config = db.scalar(
        select(AssetConfiguration).where(
            AssetConfiguration.asset_id == payload.asset_id,
            AssetConfiguration.version == payload.configuration_version,
        )
    )
    if config is None:
        raise ConfigurationNotFound
    previous_time = db.scalar(
        stream_query(payload.asset_id, payload.source, payload.run_id)
        .with_only_columns(TelemetryReading.measurement_time)
        .order_by(TelemetryReading.measurement_time.desc(), TelemetryReading.id.desc())
        .limit(1)
    )
    out_of_order = previous_time is not None and payload.timestamp < previous_time
    policy = (
        "historical_only"
        if previous_time is not None and payload.timestamp <= previous_time
        else "forward_only"
    )
    normalized, flags = normalize(payload, config)
    reading = TelemetryReading(
        asset_id=payload.asset_id,
        configuration_version=config.version,
        schema_version=payload.schema_version,
        message_id=payload.message_id,
        source=payload.source,
        run_key=payload.run_id or "",
        measurement_time=payload.timestamp,
        original_payload=original,
        payload_fingerprint=fingerprint,
        normalized_telemetry=normalized,
        quality_flags=flags,
        out_of_order=out_of_order,
    )
    db.add(reading)
    db.flush()
    db.add(ProcessingJob(reading_id=reading.id, status="pending", state_policy=policy))
    db.flush()
    result = response_for(db, reading)
    db.commit()
    return result, True


def latest(db, asset_id, source, run_id):
    require_asset(db, asset_id)
    reading = db.scalar(
        stream_query(asset_id, source, run_id)
        .order_by(TelemetryReading.measurement_time.desc(), TelemetryReading.id.desc())
        .limit(1)
    )
    if reading is None:
        raise ReadingNotFound
    return response_for(db, reading)


def history(db, asset_id, source, run_id, start, end, limit, offset):
    require_asset(db, asset_id)
    statement = stream_query(asset_id, source, run_id)
    if start is not None:
        statement = statement.where(TelemetryReading.measurement_time >= start)
    if end is not None:
        statement = statement.where(TelemetryReading.measurement_time < end)
    rows = db.scalars(
        statement.order_by(TelemetryReading.measurement_time, TelemetryReading.id)
        .limit(limit)
        .offset(offset)
    )
    return [response_for(db, row) for row in rows]
