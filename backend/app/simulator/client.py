"""Small bounded HTTP client; retries retain the exact packet bytes."""

import json
import math
import time
from dataclasses import asdict, dataclass
from itertools import pairwise
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from backend.app.schemas.assets import ConfigurationResponse
from backend.app.schemas.telemetry import TelemetryCreate


class ApiError(RuntimeError):
    pass


@dataclass
class Summary:
    created: int = 0
    identical_duplicates: int = 0
    failures: int = 0


class SubmissionError(ApiError):
    def __init__(self, message, summary):
        super().__init__(message)
        self.summary = asdict(summary)


class Client:
    def __init__(
        self,
        base_url="http://127.0.0.1:8000",
        timeout_seconds=10,
        retries=3,
        backoff_seconds=0.25,
    ):
        parts = urlsplit(base_url)
        if (
            parts.scheme not in ("http", "https")
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path not in ("", "/")
        ):
            raise ValueError(
                "API base URL must be an HTTP(S) origin without credentials or /api/v1"
            )
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("request timeout must be finite and positive")
        if type(retries) is not int or not 0 <= retries <= 10:
            raise ValueError("retries must be an integer in 0..10")
        if not math.isfinite(backoff_seconds) or not 0 <= backoff_seconds <= 5:
            raise ValueError("backoff must be finite in 0..5 seconds")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.backoff_seconds = backoff_seconds

    def request(self, path, data=None, expected=(200,)):
        for attempt in range(self.retries + 1):
            try:
                req = Request(
                    self.base_url + path,
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                with urlopen(req, timeout=self.timeout_seconds) as response:
                    if response.status not in expected:
                        raise ApiError(f"Unexpected HTTP {response.status}")
                    return response.status, json.load(response)
            except HTTPError as error:
                status = error.code
                error.close()
                if status not in (408, 429) and not 500 <= status <= 599:
                    explanation = {
                        409: "deduplication conflict: same key has different content",
                        422: "invalid request or configuration reference",
                        404: "asset/configuration not found",
                    }.get(status, "request rejected")
                    raise ApiError(
                        f"HTTP {status}: {explanation}; stopped without retry"
                    ) from None
            except (URLError, TimeoutError, ConnectionError):
                pass
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ApiError("API returned invalid JSON; stopped") from None
            if attempt == self.retries:
                raise ApiError(
                    f"Transient delivery failed after {attempt + 1} attempts; resend the same artifact safely"
                ) from None
            time.sleep(min(5, self.backoff_seconds * 2**attempt))
        raise AssertionError("unreachable")

    def configuration(self, asset_id, version):
        # Existing supported registry interface; never silently select current version.
        offset = 0
        while True:
            _, page = self.request(
                f"/api/v1/assets/{asset_id}/configurations?limit=100&offset={offset}"
            )
            for item in page["items"]:
                config = ConfigurationResponse.model_validate(item)
                if config.asset_id == asset_id and config.version == version:
                    return config
            if len(page["items"]) < 100:
                raise ApiError("Explicit configuration version not found")
            offset += 100

    def send(self, lines, paced=False):
        # Validate the entire input before making any POST; retain original bytes.
        packets = []
        for line in lines:
            data = line.encode("utf-8") if isinstance(line, str) else line
            if not data.strip():
                continue
            packet = TelemetryCreate.model_validate_json(data)
            if packet.source != "simulator":
                raise ValueError(
                    "sender only accepts source=simulator; replay is outside scope"
                )
            packets.append((data, packet))
        if not packets:
            raise ValueError("JSONL contains no telemetry packets")
        if paced and any(
            right[1].timestamp < left[1].timestamp for left, right in pairwise(packets)
        ):
            raise ValueError("paced input timestamps must be nondecreasing")
        summary = Summary()
        previous = None
        for data, packet in packets:
            if paced and previous is not None:
                time.sleep((packet.timestamp - previous).total_seconds())
            try:
                status, _ = self.request("/api/v1/telemetry", data, expected=(200, 201))
            except ApiError as error:
                summary.failures += 1
                raise SubmissionError(str(error), summary) from None
            if status == 201:
                summary.created += 1
            else:
                summary.identical_duplicates += 1
            previous = packet.timestamp
        return asdict(summary)
