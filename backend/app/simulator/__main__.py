"""Run from repository root: python -m backend.app.simulator --help."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from backend.app.schemas.assets import ConfigurationResponse
from backend.app.simulator.client import ApiError, Client, SubmissionError
from backend.app.simulator.generator import Parameters, RunSpec, write_artifacts


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Synthetic normal-operation generator/sender; analytics stays pending"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=float, default=10)
    parser.add_argument("--retries", type=int, default=3)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser(
        "generate", help="generate artifacts only; no telemetry submission"
    )
    generate.add_argument("--asset-id", required=True)
    generate.add_argument("--configuration-version", required=True, type=int)
    generate.add_argument("--run-id", required=True)
    generate.add_argument("--seed", required=True, type=int)
    generate.add_argument(
        "--start", required=True, help="timezone-aware ISO-8601, normalized to UTC"
    )
    generate.add_argument("--duration-seconds", required=True, type=int)
    generate.add_argument("--interval-seconds", required=True, type=int)
    generate.add_argument("--initial-oil-temperature-c", required=True, type=float)
    generate.add_argument("--output-dir", required=True)
    generate.add_argument(
        "--parameters-json",
        help="optional JSON overrides of documented simulation parameters",
    )
    generate.add_argument(
        "--configuration-json",
        help="explicit ConfigurationResponse JSON; otherwise fetch exact version from API",
    )
    send = sub.add_parser(
        "send", help="send existing API-ready JSONL, immediate by default"
    )
    send.add_argument("--input", required=True)
    send.add_argument(
        "--paced",
        action="store_true",
        help="wait measurement-time gaps between deliveries; timestamps never change",
    )
    args = parser.parse_args(argv)
    try:
        client = Client(args.base_url, args.timeout_seconds, args.retries)
        if args.command == "generate":
            parameters = (
                Parameters.model_validate_json(Path(args.parameters_json).read_bytes())
                if args.parameters_json
                else Parameters()
            )
            spec = RunSpec(
                asset_id=args.asset_id,
                configuration_version=args.configuration_version,
                run_id=args.run_id,
                seed=args.seed,
                start=args.start,
                duration_seconds=args.duration_seconds,
                interval_seconds=args.interval_seconds,
                initial_oil_temperature_c=args.initial_oil_temperature_c,
                parameters=parameters,
            )
            config = (
                ConfigurationResponse.model_validate_json(
                    Path(args.configuration_json).read_bytes()
                )
                if args.configuration_json
                else client.configuration(spec.asset_id, spec.configuration_version)
            )
            packets = write_artifacts(spec, config, args.output_dir)
            print(
                json.dumps(
                    {
                        "generated": len(packets),
                        "output_dir": args.output_dir,
                        "source": "simulator",
                        "run_id": spec.run_id,
                        "configuration_version": spec.configuration_version,
                    }
                )
            )
        else:
            with Path(args.input).open("rb") as handle:
                print(json.dumps(client.send(handle, paced=args.paced)))
    except SubmissionError as error:
        print(json.dumps({**error.summary, "error": str(error)}))
        return 1
    except ValidationError as error:
        issues = [
            {"field": ".".join(map(str, item["loc"])), "message": item["msg"]}
            for item in error.errors(include_input=False, include_url=False)
        ]
        print(json.dumps({"error": "Input/schema validation failed", "issues": issues}))
        return 1
    except (ApiError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    except OSError:
        print(
            json.dumps(
                {
                    "error": "Artifact I/O failed; check file path and output directory permissions"
                }
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
