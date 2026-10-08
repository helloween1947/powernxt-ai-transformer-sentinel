"""Deterministic synthetic normal envelope; not a validated predictive model."""

import csv
import hashlib
import json
import math
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from backend.app.schemas.assets import ConfigurationResponse, StrictSchema
from backend.app.schemas.telemetry import Identifier, ISOTime, TelemetryCreate

VERSION = "normal-operation-1.0.0"


class Parameters(StrictSchema):
    """All defaults are simulation assumptions, not transformer nameplate values."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    load_mean_pu: float = Field(default=0.60, ge=0.2, le=0.8)
    load_amplitude_pu: float = Field(default=0.15, ge=0, le=0.3)
    load_period_seconds: float = Field(default=3600, ge=60)
    phase_difference_pu: float = Field(default=0.01, ge=0, le=0.02)
    electrical_noise_pu: float = Field(default=0.002, ge=0, le=0.005)
    voltage_variation_pu: float = Field(default=0.01, ge=0, le=0.02)
    ambient_mean_c: float = Field(default=25, ge=0, le=35)
    ambient_amplitude_c: float = Field(default=2, ge=0, le=5)
    ambient_period_seconds: float = Field(default=86400, ge=60)
    thermal_rise_c: float = Field(default=40, gt=0, le=50)
    thermal_time_constant_minutes: float = Field(default=60, ge=1, le=1440)
    oil_level_pct: float | None = Field(default=None, ge=10, le=95)

    @model_validator(mode="after")
    def bounded_load(self):
        if self.load_mean_pu - self.load_amplitude_pu < 0.1:
            raise ValueError("minimum synthetic load must be at least 0.1 pu")
        if (self.load_mean_pu + self.load_amplitude_pu) * (
            1 + self.phase_difference_pu + self.electrical_noise_pu
        ) > 0.95:
            raise ValueError("maximum synthetic phase current must be <= 0.95 pu")
        return self


class RunSpec(StrictSchema):
    asset_id: Identifier
    configuration_version: int = Field(strict=True, gt=0)
    run_id: Identifier
    seed: int = Field(strict=True)
    start: ISOTime
    duration_seconds: int = Field(strict=True, gt=0, le=604800)
    interval_seconds: int = Field(strict=True, gt=0, le=604800)
    initial_oil_temperature_c: float = Field(
        ge=0, le=95, allow_inf_nan=False, strict=True
    )
    parameters: Parameters = Field(default_factory=Parameters)

    @model_validator(mode="after")
    def safe_sampling(self):
        if self.sample_count > 100000:
            raise ValueError("maximum 100000 samples per run")
        # Overflow must be detected before generation or writing any artifact.
        try:
            self.start + timedelta(seconds=self.duration_seconds)
        except OverflowError:
            raise ValueError("run end exceeds datetime range") from None
        return self

    @property
    def sample_count(self):
        return (
            self.duration_seconds + self.interval_seconds - 1
        ) // self.interval_seconds


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def noise(seed, index, channel):
    """Independent deterministic uniform [-1,1] noise from SHA-256, no global RNG."""
    digest = hashlib.sha256(f"{VERSION}:{seed}:{index}:{channel}".encode()).digest()
    return 2 * int.from_bytes(digest[:8], "big") / (2**64 - 1) - 1


def validate_configuration(spec, config):
    if config.asset_id != spec.asset_id or config.version != spec.configuration_version:
        raise ValueError(
            "configuration asset/version does not match explicit run reference"
        )
    p = spec.parameters
    factor = math.sqrt(3) if config.voltage_convention == "line_to_line" else 3
    kva = factor * config.rated_voltage_v * config.rated_current_a / 1000
    if not math.isclose(kva, config.rated_kva, rel_tol=0.05):
        raise ValueError(
            "selected-side voltage/current ratings disagree with three-phase kVA by >5%"
        )
    voltage_delta = (
        p.voltage_variation_pu + p.phase_difference_pu + p.electrical_noise_pu
    )
    limits = config.operational_limits
    if limits.min_voltage_pu is not None and 1 - voltage_delta < limits.min_voltage_pu:
        raise ValueError("synthetic voltage envelope falls below configured minimum")
    if limits.max_voltage_pu is not None and 1 + voltage_delta > limits.max_voltage_pu:
        raise ValueError("synthetic voltage envelope exceeds configured maximum")
    peak_load = (p.load_mean_pu + p.load_amplitude_pu) * (
        1 + p.phase_difference_pu + p.electrical_noise_pu
    )
    if (
        limits.max_load_pct is not None
        and peak_load * (1 + voltage_delta) * kva / config.rated_kva * 100
        > limits.max_load_pct
    ):
        raise ValueError("synthetic apparent-load envelope exceeds configured maximum")
    max_oil = min(
        95, limits.max_top_oil_temp_c if limits.max_top_oil_temp_c is not None else 95
    )
    equilibrium_max = (
        p.ambient_mean_c
        + p.ambient_amplitude_c
        + p.thermal_rise_c * (p.load_mean_pu + p.load_amplitude_pu) ** 2
    )
    if max(spec.initial_oil_temperature_c, equilibrium_max) > max_oil:
        raise ValueError("synthetic thermal envelope exceeds permitted top-oil maximum")
    if spec.initial_oil_temperature_c < p.ambient_mean_c - p.ambient_amplitude_c:
        raise ValueError("initial oil temperature must be >= minimum synthetic ambient")


def generate(spec: RunSpec, config: ConfigurationResponse):
    validate_configuration(spec, config)
    p = spec.parameters
    oil = spec.initial_oil_temperature_c
    previous_target = oil
    packets = []
    for index in range(spec.sample_count):
        elapsed = index * spec.interval_seconds
        load = p.load_mean_pu + p.load_amplitude_pu * math.sin(
            2 * math.pi * elapsed / p.load_period_seconds
        )
        ambient = p.ambient_mean_c + p.ambient_amplitude_c * math.sin(
            2 * math.pi * elapsed / p.ambient_period_seconds
        )
        if index:
            # Previous interval equilibrium held constant; exact first-order step.
            oil = previous_target + (oil - previous_target) * math.exp(
                -spec.interval_seconds / (60 * p.thermal_time_constant_minutes)
            )
        previous_target = ambient + p.thermal_rise_c * load**2
        values = {}
        for phase, difference in zip(
            "ryb", (-p.phase_difference_pu, 0, p.phase_difference_pu)
        ):
            voltage_pu = (
                1
                + p.voltage_variation_pu
                * math.sin(2 * math.pi * elapsed / p.load_period_seconds)
                + difference
                + p.electrical_noise_pu * noise(spec.seed, index, f"voltage_{phase}")
            )
            current_pu = load * (
                1
                + difference
                + p.electrical_noise_pu * noise(spec.seed, index, f"current_{phase}")
            )
            values[f"voltage_{phase}_v"] = round(config.rated_voltage_v * voltage_pu, 6)
            values[f"current_{phase}_a"] = round(config.rated_current_a * current_pu, 6)
        values.update(
            oil_temperature_c=round(oil, 6),
            ambient_temperature_c=round(ambient, 6),
            oil_level_pct=p.oil_level_pct,
        )
        packet = {
            "schema_version": "1.0.0",
            "asset_id": spec.asset_id,
            "source": "simulator",
            "run_id": spec.run_id,
            "configuration_version": spec.configuration_version,
            "timestamp": (spec.start + timedelta(seconds=elapsed))
            .isoformat()
            .replace("+00:00", "Z"),
            "measurements": values,
            "measurement_quality": {
                key: "missing" if value is None else "good"
                for key, value in values.items()
            },
        }
        # Deterministic identifier with RFC UUID4 version/variant bits, not uuid5.
        identity = {
            "version": VERSION,
            "spec": spec.model_dump(mode="json"),
            "configuration": config.model_dump(mode="json"),
            "packet": packet,
        }
        packet["message_id"] = str(
            UUID(
                bytes=hashlib.sha256(canonical(identity).encode()).digest()[:16],
                version=4,
            )
        )
        TelemetryCreate.model_validate(packet)
        packets.append(packet)
    return packets


def write_artifacts(spec, config, directory):
    packets = generate(spec, config)
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    paths = [
        output / name
        for name in ("telemetry.jsonl", "telemetry.csv", "run-metadata.json")
    ]
    if any(path.exists() for path in paths):
        raise ValueError("output artifacts already exist; choose a new directory")
    metadata = {
        "simulator_version": VERSION,
        "scenario": "synthetic normal-operation envelope",
        "specification": spec.model_dump(mode="json"),
        "configuration": config.model_dump(mode="json"),
        "sample_count": len(packets),
        "sampling_policy": "start + i*interval_seconds < start + duration_seconds; no partial final step",
        "equations": "K=mean+amplitude*sin(2*pi*t/period); target=ambient+rise*K^2; oil_next=target_prev+(oil_prev-target_prev)*exp(-dt/(60*tau_minutes))",
        "assumptions": [
            "RMS magnitudes on the configured measurement side and voltage convention",
            "constant configured ratings; assumed smooth load and bounded synthetic noise",
            "not IEEE C57.91, validated physics, predictive analytics, or evidence of detector accuracy",
            "producer good flags mean present synthetic values; absent oil level remains null",
        ],
        "csv_null_policy": "empty field represents null; zeros are numeric zero",
    }
    paths[0].write_text(
        "".join(canonical(packet) + "\n" for packet in packets), encoding="utf-8"
    )
    columns = [
        "schema_version",
        "message_id",
        "asset_id",
        "source",
        "run_id",
        "configuration_version",
        "timestamp",
    ]
    measurement_columns = list(packets[0]["measurements"])
    with paths[1].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            lineterminator="\n",
            fieldnames=columns
            + measurement_columns
            + [key + "_quality" for key in measurement_columns],
        )
        writer.writeheader()
        for packet in packets:
            writer.writerow(
                {
                    **{key: packet[key] for key in columns},
                    **packet["measurements"],
                    **{
                        key + "_quality": flag
                        for key, flag in packet["measurement_quality"].items()
                    },
                }
            )
    paths[2].write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return packets
