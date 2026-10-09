"""Offline configuration payload preparation; never POST, migrate or deploy.

Preserves the reading-bound configuration's electrical settings and known parameters.
"""
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from backend.app.schemas.assets import (
    ConfigurationCreate,
    ConfigurationResponse,
    ThermalParameters,
)

KEYS = ("rated_top_oil_rise_c", "oil_time_constant_min", "loss_ratio", "oil_exponent")
PROFILE = Path(__file__).resolve().parents[1] / "data/sample/thermal-demo-parameters-assumed.json"


def prepare_configuration(snapshot: dict, assumed_profile: dict) -> dict:
    """Return API-valid ConfigurationCreate; fill missing coefficients only.

    Existing non-null thermal parameters/provenance are preserved, not reclassified.
    Response-only asset/version/created_at fields never enter the POST payload.
    """
    source = ConfigurationResponse.model_validate(snapshot)
    if not isinstance(assumed_profile, dict) or set(assumed_profile) != {"thermal_parameters", "parameter_provenance"}:
        raise ValueError("Profile requires thermal_parameters and parameter_provenance only")
    values = assumed_profile["thermal_parameters"]
    expected = {f"thermal_parameters.{key}": "assumed" for key in KEYS}
    if not isinstance(values, dict) or set(values) != set(KEYS) or assumed_profile["parameter_provenance"] != expected:
        raise ValueError("Demo profile must contain exactly four explicit assumed parameters")
    validated = ThermalParameters.model_validate(values).model_dump(exclude_none=True)
    if set(validated) != set(KEYS):
        raise ValueError("All four demonstration coefficients must be positive finite numbers")
    payload = source.model_dump(mode="json", exclude={"asset_id", "version", "created_at"})
    for key in KEYS:
        if payload["thermal_parameters"].get(key) is None:
            payload["thermal_parameters"][key] = validated[key]
            payload["parameter_provenance"][f"thermal_parameters.{key}"] = "assumed"
    return ConfigurationCreate.model_validate(payload).model_dump(mode="json")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration-json", required=True, help="Saved ConfigurationResponse from the existing asset/version")
    parser.add_argument("--profile-json", default=str(PROFILE))
    parser.add_argument("--output", required=True, help="New file; existing payloads are never overwritten")
    args = parser.parse_args(argv)
    try:
        snapshot = json.loads(Path(args.configuration_json).read_text(encoding="utf-8-sig"))
        profile = json.loads(Path(args.profile_json).read_text(encoding="utf-8-sig"))
        payload = prepare_configuration(snapshot, profile)
        with Path(args.output).open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, allow_nan=False)+"\n")
    except (OSError, ValueError, ValidationError):
        print("Preparation failed: check schemas and paths; output must be a new file.")
        return 1
    print(json.dumps({"prepared": args.output, "asset_id": snapshot["asset_id"],
                      "baseline_version": snapshot["version"], "posted": False,
                      "note": "Review assumed coefficients; POST separately and capture returned version."}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
