// A deferred outside event from the previous close must not dismiss a new open.
export function occurredBeforeOpen(eventTime, openedAt) {
  return Number.isFinite(eventTime) && Number.isFinite(openedAt) && eventTime < openedAt;
}
