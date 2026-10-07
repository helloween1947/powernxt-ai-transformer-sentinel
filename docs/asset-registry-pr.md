Add versioned transformer asset registry

The backend lacked persisted transformer identities and configuration history. This adds
asset creation, paginated listing and retrieval, plus append-only configuration creation
and paginated history under `/api/v1/assets`. Retrieval exposes the latest configuration.

Configurations validate explicit kVA/voltage/current units, measurement side, voltage
convention, IANA timezones, operational limits, optional thermal inputs, and per-parameter
provenance. PostgreSQL parent-row locking and a unique asset/version constraint allocate
versions safely under concurrent requests. Database errors are rolled back and sanitized.

Migration `f272b723f71b` creates the registry tables without clearing existing data. CI now
provides an isolated PostgreSQL 16 database. API documentation, assumed sample parameters,
and a repeatable API/restart verification script are included.

Validation: 36 backend tests passed, including all existing health/CORS tests, concurrent
configuration writes, and migration round-trip checks. Docker API liveness/readiness and
versions 1/2 surviving backend/database restart passed. Alembic reported no schema drift;
Ruff and whitespace checks passed. The cloud build needed temporary proxy DNS and trusted
platform-CA adjustments; the repository Dockerfile and Compose settings remain unchanged.
Windows execution and hosted GitHub Actions were not run.

Dependency: this branch is based on unmerged `chore/team-repository-setup` at
`2619044900e0e0fd1ec76d151559d1ecf868342a`. The main-target comparison includes that foundation.
Review/merge the setup PR first; do not merge this draft until that dependency is resolved.

Person B should confirm the proposed registry model-input names, three-phase kVA convention,
RMS voltage/line-current side, thermal-rise references, minute units, loss ratio and exponents.
The existing proposed analytics contract remains unchanged.
