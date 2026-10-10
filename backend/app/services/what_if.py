"""Capture a coherent current state or use an immutable ref; no worker mutations."""

import json
import math
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.app.analytics import adapter
from backend.app.analytics.person_b.scenario_validation import worker_state
from backend.app.analytics.person_b.scenarios import (
    FORECAST_VERSION,
    forecast_from_worker_state,
)
from backend.app.analytics.person_b.worker import STATE_VERSION, _validate_config
from backend.app.models import Asset, AssetConfiguration
from backend.app.models.analytics import (
    AnalyticsResult,
    AnalyticsState,
    AnalyticsStream,
)
from backend.app.models.telemetry import TelemetryReading
from backend.app.models.what_if import WhatIfSnapshot


class WhatIfError(Exception):
    def __init__(self, status, code, message, reasons=()):
        self.status, self.code, self.message, self.reasons = (
            status,
            code,
            message,
            list(reasons),
        )


def reject(code, message, reasons=()):
    raise WhatIfError(409, code, message, reasons)


def validate_state(state, reading, result, config, source, run_key):
    try:
        worker_state(state, STATE_VERSION)
        binding = state["binding"]
        expected = {
            "stream": {
                "asset_id": reading.asset_id,
                "source": source,
                "run_id": run_key or None,
            },
            "configuration_version": reading.configuration_version,
            "model_version": adapter.MODEL_VERSION,
            "parameter_version": adapter.parameter_identity(config),
        }
        metadata = result.payload["metadata"]
        if (
            binding != expected
            or reading.source != source
            or reading.run_key != run_key
            or result.model_id != adapter.MODEL_ID
            or result.model_version != adapter.MODEL_VERSION
            or result.parameter_version != expected["parameter_version"]
            or metadata["stream"] != expected["stream"]
            or metadata["configuration_version"] != reading.configuration_version
            or metadata["reading_identity"]
            != {"reading_id": reading.id, "message_id": str(reading.message_id)}
            or metadata["model_id"] != result.model_id
            or metadata["model_version"] != result.model_version
            or metadata["parameter_version"] != result.parameter_version
            or state["last_reading_identity"] != metadata["reading_identity"]
            or datetime.fromisoformat(
                state["last_measurement_time"].replace("Z", "+00:00")
            )
            != reading.measurement_time
            or datetime.fromisoformat(
                metadata["measurement_time"].replace("Z", "+00:00")
            )
            != reading.measurement_time
            or result.payload["execution_status"]["state_advanced"] is not True
        ):
            reject(
                "incompatible_state_identity",
                "State/result/stream/configuration/model identities do not match",
            )
        missing = _validate_config(
            {
                "asset_id": reading.asset_id,
                "configuration_version": reading.configuration_version,
            },
            config,
        )
        if missing:
            reject(
                "missing_model_parameters",
                "Required thermal parameters unavailable",
                missing,
            )
        thermal = state["thermal"]
        if not thermal["initialized"] or not thermal["valid"]:
            reject(
                "ineligible_state",
                "A valid initialized thermal state is required",
                [thermal["reason"] or "thermal_state_not_initialized"],
            )
        if result.status != "completed":
            reject(
                "ineligible_state",
                "The state origin did not complete analytics",
                ["analytics_result_unavailable"],
            )
    except (ValueError, KeyError, TypeError, OverflowError):
        reject(
            "incompatible_state_identity",
            "Stored state or configuration is incompatible",
        )


def configuration(db, asset_id, version):
    config = db.scalar(
        select(AssetConfiguration).where(
            AssetConfiguration.asset_id == asset_id,
            AssetConfiguration.version == version,
        )
    )
    if config is None:
        reject(
            "incompatible_state_identity", "Bound immutable configuration is missing"
        )
    return adapter.configuration_payload(config)


def resolve(db, asset_id, payload):
    if db.get(Asset, asset_id) is None:
        raise WhatIfError(404, "asset_not_found", "Asset not found")
    run_key = payload.run_id or ""
    if payload.state_ref:
        snapshot = db.get(WhatIfSnapshot, payload.state_ref)
        if snapshot is None:
            raise WhatIfError(404, "state_not_found", "State reference not found")
        if (snapshot.asset_id, snapshot.source, snapshot.run_key) != (
            asset_id,
            payload.source,
            run_key,
        ):
            reject(
                "incompatible_state_identity",
                "State reference belongs to a different asset/stream",
            )
        config = configuration(db, asset_id, snapshot.configuration_version)
        state = deepcopy(snapshot.state)
        # Never reconstruct or reselect state through a mutable result/cache. The
        # insertion guard established the exact result binding at capture time.
        try:
            worker_state(state, STATE_VERSION)
            if (
                state["binding"]
                != {
                    "stream": {
                        "asset_id": asset_id,
                        "source": payload.source,
                        "run_id": payload.run_id,
                    },
                    "configuration_version": snapshot.configuration_version,
                    "model_version": adapter.MODEL_VERSION,
                    "parameter_version": adapter.parameter_identity(config),
                }
                or snapshot.model_id != adapter.MODEL_ID
                or snapshot.model_version != adapter.MODEL_VERSION
                or snapshot.parameter_version != state["binding"]["parameter_version"]
                or datetime.fromisoformat(
                    state["last_measurement_time"].replace("Z", "+00:00")
                )
                != snapshot.measurement_time
            ):
                reject(
                    "incompatible_state_identity",
                    "Captured state/configuration/model binding is incompatible",
                )
            missing = _validate_config(
                {
                    "asset_id": asset_id,
                    "configuration_version": snapshot.configuration_version,
                },
                config,
            )
            if missing:
                reject(
                    "missing_model_parameters",
                    "Required thermal parameters unavailable",
                    missing,
                )
            if (
                state["thermal"]["initialized"] is not True
                or state["thermal"]["valid"] is not True
            ):
                reject(
                    "ineligible_state", "Captured state is not initialized and valid"
                )
        except (ValueError, KeyError, TypeError, OverflowError):
            reject("incompatible_state_identity", "Captured state is incompatible")
        return snapshot, config
    # Same stream row lock as the worker, in shared mode: no partial/torn cache.
    # A live claim may be computing outside locks; this captures its last committed state.
    head = db.scalar(
        select(AnalyticsStream)
        .where(
            AnalyticsStream.asset_id == asset_id,
            AnalyticsStream.source == payload.source,
            AnalyticsStream.run_key == run_key,
        )
        .with_for_update(read=True)
    )
    if head is None or head.last_identity is None or head.watermark_reading_id is None:
        reject("state_unavailable", "No committed forward state exists for this stream")
    try:
        namespace = json.loads(head.last_identity)
        if len(namespace) != 4 or namespace[:2] != [
            adapter.MODEL_ID,
            adapter.MODEL_VERSION,
        ]:
            reject("incompatible_state_identity", "Current state model is unsupported")
        saved = db.get(AnalyticsState, (asset_id, payload.source, run_key, *namespace))
        reading = db.get(TelemetryReading, head.watermark_reading_id)
        config = configuration(db, asset_id, namespace[2])
        result = db.scalar(
            select(AnalyticsResult).where(
                AnalyticsResult.reading_id == reading.id,
                AnalyticsResult.model_id == namespace[0],
                AnalyticsResult.model_version == namespace[1],
                AnalyticsResult.parameter_version == namespace[3],
            )
        )
        if (
            saved is None
            or result is None
            or head.watermark_time != reading.measurement_time
        ):
            reject(
                "incompatible_state_identity",
                "Current cache/result watermark is inconsistent",
            )
        state = deepcopy(saved.state)
        if state != result.payload.get("updated_state"):
            reject(
                "incompatible_state_identity",
                "Current cache differs from the stored result state",
            )
        validate_state(state, reading, result, config, payload.source, run_key)
    except (ValueError, TypeError, KeyError, AttributeError):
        reject("incompatible_state_identity", "Current state cannot be resolved safely")
    db.execute(
        insert(WhatIfSnapshot)
        .values(
            id=uuid4(),
            result_id=result.id,
            asset_id=asset_id,
            source=payload.source,
            run_key=run_key,
            configuration_version=reading.configuration_version,
            model_id=result.model_id,
            model_version=result.model_version,
            parameter_version=result.parameter_version,
            measurement_time=reading.measurement_time,
            state=state,
        )
        .on_conflict_do_nothing(index_elements=["result_id"])
    )
    snapshot = db.scalar(
        select(WhatIfSnapshot).where(WhatIfSnapshot.result_id == result.id)
    )
    return snapshot, config


def scenario(state, config, segment):
    profile = [
        {
            "duration_s": segment.duration_s,
            "thermal_load_pu": segment.thermal_load_pu,
            "ambient_temp_c": segment.ambient_temperature_c,
        }
    ]
    forecast = forecast_from_worker_state(state, config, profile)
    count = max(1, min(96, math.ceil(segment.duration_s / 60)))
    points = [
        {
            "elapsed_s": 0.0,
            "estimated_top_oil_temperature_c": state["thermal"]["oil_temp_c"],
        }
    ]
    for index in range(1, count + 1):
        elapsed = (
            segment.duration_s if index == count else segment.duration_s * index / count
        )
        partial = (
            forecast
            if index == count
            else forecast_from_worker_state(
                state, config, [{**profile[0], "duration_s": elapsed}]
            )
        )
        points.append(
            {
                "elapsed_s": elapsed,
                "estimated_top_oil_temperature_c": partial[
                    "final_top_oil_temperature_c"
                ],
            }
        )
    crossing = forecast["first_limit_crossing_s"]
    return {
        "inputs": segment.model_dump(),
        "points": points,
        "final_top_oil_temperature_c": forecast["final_top_oil_temperature_c"],
        "peak_top_oil_temperature_c": forecast["peak_top_oil_temperature_c"],
        "limit_crossing": {
            "status": "unavailable"
            if forecast["configured_top_oil_limit_c"] is None
            else "no_crossing_within_horizon"
            if crossing is None
            else "crossing",
            "time_s": None
            if crossing is None
            else max(0.0, min(segment.duration_s, crossing)),
            "reasons": ["configured_top_oil_limit_missing"]
            if forecast["configured_top_oil_limit_c"] is None
            else [],
        },
    }


def compare(db, asset_id, payload):
    snapshot, config = resolve(db, asset_id, payload)
    state = deepcopy(snapshot.state)
    try:
        baseline = scenario(state, config, payload.baseline)
        reduced = scenario(state, config, payload.reduced_load)
        result = {
            "state": {
                "state_ref": snapshot.id,
                "asset_id": snapshot.asset_id,
                "source": snapshot.source,
                "run_id": snapshot.run_key or None,
                "reading_id": state["last_reading_identity"]["reading_id"],
                "result_id": snapshot.result_id,
                "measurement_time": snapshot.measurement_time,
                "captured_at": snapshot.captured_at,
            },
            "configuration": {
                "asset_id": config["asset_id"],
                "version": config["version"],
                "created_at": config["created_at"],
                "parameter_version": snapshot.parameter_version,
            },
            "model": {
                "model_id": snapshot.model_id,
                "model_version": snapshot.model_version,
                "forecast_version": FORECAST_VERSION,
            },
            "units": {"temperature": "C", "elapsed_time": "s", "thermal_load": "pu"},
            "parameter_provenance": config["parameter_provenance"],
            "assumptions": [
                "Conditional simplified healthy-model estimate; not fault diagnosis or a physical accuracy guarantee.",
                "Same immutable state/configuration and constant ambient in both scenarios; only load may differ.",
                "Initial state is the healthy worker estimate or an observed bootstrap; bootstrap is not independent prediction.",
                "Configured coefficients/provenance retained; no tuning, cooling intervention, confidence or health estimate.",
                "Peak uses monotonic constant-segment endpoints including time zero; crossing is analytic, not sampled.",
                "Measurement time is the state origin, not a claim that this state is fresh at request time.",
            ],
            "sampling": {
                "policy": "uniform_including_initial_and_final",
                "interval_count": len(baseline["points"]) - 1,
                "maximum_points_per_scenario": 97,
            },
            "configured_top_oil_limit_c": config["operational_limits"].get(
                "max_top_oil_temp_c"
            ),
            "limit_reasons": []
            if config["operational_limits"].get("max_top_oil_temp_c") is not None
            else ["configured_top_oil_limit_missing"],
            "baseline": baseline,
            "reduced_load": reduced,
            "final_temperature_difference_c": reduced["final_top_oil_temperature_c"]
            - baseline["final_top_oil_temperature_c"],
        }
        from backend.app.schemas.what_if import WhatIfResponse

        response = WhatIfResponse.model_validate(result)
    except (ValueError, OverflowError, ZeroDivisionError, TypeError, KeyError):
        raise WhatIfError(
            422,
            "computation_unavailable",
            "Conditional top-oil computation unavailable",
            ["thermal_arithmetic_unavailable"],
        ) from None
    db.commit()  # Only the immutable capture, never worker state/results/jobs.
    return response
