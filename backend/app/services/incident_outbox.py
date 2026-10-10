"""Post-commit, at-least-once dispatch with per-incident ordering and lease fencing.

No transport is configured here. A caller supplies publish(envelope); it must
deduplicate event_id. A crash after publish but before receipt can cause a retry.
"""

import math
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import aliased

from backend.app.models.incidents import IncidentDelivery, IncidentEvent


@dataclass(frozen=True)
class DeliveryClaim:
    event_id: UUID
    token: UUID


class StaleDelivery(Exception):
    pass


def claim_next(factory, *, lease_seconds=60):
    if not math.isfinite(lease_seconds) or lease_seconds <= 0:
        raise ValueError("Positive finite delivery lease required")
    with factory.begin() as db:
        now = db.scalar(select(func.clock_timestamp()))
        prior_event, prior_delivery = aliased(IncidentEvent), aliased(IncidentDelivery)
        earlier = exists(
            select(prior_event.event_id)
            .join(prior_delivery, prior_delivery.event_id == prior_event.event_id)
            .where(
                prior_event.incident_id == IncidentEvent.incident_id,
                prior_event.incident_version < IncidentEvent.incident_version,
                prior_delivery.delivered_at.is_(None),
            )
        )
        delivery = db.scalar(
            select(IncidentDelivery)
            .join(IncidentEvent, IncidentEvent.event_id == IncidentDelivery.event_id)
            .where(
                IncidentDelivery.delivered_at.is_(None),
                or_(
                    IncidentDelivery.lease_until.is_(None),
                    IncidentDelivery.lease_until <= now,
                ),
                ~earlier,
            )
            .order_by(IncidentEvent.recorded_at, IncidentEvent.event_id)
            .limit(1)
            .with_for_update(of=IncidentDelivery, skip_locked=True)
        )
        if delivery is None:
            return None
        delivery.claim_token = uuid4()
        delivery.lease_until = now + timedelta(seconds=lease_seconds)
        delivery.attempts += 1
        return DeliveryClaim(delivery.event_id, delivery.claim_token)


def fenced(db, claim):
    delivery = db.scalar(
        select(IncidentDelivery)
        .where(IncidentDelivery.event_id == claim.event_id)
        .with_for_update()
    )
    now = db.scalar(select(func.clock_timestamp()))
    if (
        delivery is None
        or delivery.delivered_at is not None
        or delivery.claim_token != claim.token
        or delivery.lease_until is None
        or delivery.lease_until <= now
    ):
        raise StaleDelivery
    return delivery, now


def publish_claim(factory, claim, publish):
    # No uncommitted worker/session objects cross this boundary. Claims and event
    # snapshots are reloaded through a separate transaction before external I/O.
    with factory.begin() as db:
        _, now = fenced(db, claim)
        event = db.get(IncidentEvent, claim.event_id)
        incident = event.payload["incident"]
        envelope = {
            "schema_version": "incident-publication-1.0.0",
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "asset_id": incident["asset_id"],
            "measurement_source": incident["measurement_source"],
            "run_id": incident["run_id"],
            "measurement_time": incident["last_evaluated_measurement_time"],
            "publication_time": now.isoformat(),
            "data": event.payload,
        }
    publish(envelope)  # After commit; never inside worker/API/delivery transactions.
    with factory.begin() as db:
        delivery, now = fenced(db, claim)
        delivery.delivered_at = now
        delivery.claim_token = delivery.lease_until = None
    return envelope


def run_once(factory, publish, *, lease_seconds=60):
    claim = claim_next(factory, lease_seconds=lease_seconds)
    if claim is None:
        return False
    publish_claim(factory, claim, publish)
    return True
