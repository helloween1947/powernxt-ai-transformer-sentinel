"""Only normalized telemetry/quality/bound configuration reach Person B's model."""

from backend.app.analytics.person_b import worker as model
from backend.app.analytics.person_b.worker import _parameter_version, compute_analytics
from backend.app.schemas.assets import ConfigurationResponse


def configuration_payload(config):
    return ConfigurationResponse.model_validate(config).model_dump(mode="json")


def parameter_identity(config):
    return _parameter_version(config)


def compute(reading, config, previous_state, policy):
    return compute_analytics(
        reading.normalized_telemetry,
        config,
        reading.quality_flags,
        reading.id,
        previous_state,
        state_policy=policy,
    )


MODEL_ID = model.MODEL_ID
MODEL_VERSION = model.MODEL_VERSION
