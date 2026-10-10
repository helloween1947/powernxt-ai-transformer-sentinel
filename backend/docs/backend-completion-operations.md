# Combined backend candidate: API, isolated startup and recovery

This guide covers the review candidate, not the running development image.
Its sole migration head is `d006_combined_integration`. Development at D004
does not expose the candidate's incidents, What-if or handovers. Review and a
separately authorized rollout must precede changing development.

## Windows isolated acceptance

Run from the owned worktree, with Docker Desktop running:

```powershell
function Check-Native {
    if ($LASTEXITCODE -ne 0) { throw "Native command failed: $LASTEXITCODE" }
}
& '<project-venv>\Scripts\python.exe' -m pip install -r backend/requirements-dev.txt -r analytics/contracts/requirements-test.txt
Check-Native
& '<project-venv>\Scripts\python.exe' -m integration.run_backend_completion
Check-Native
```

The coordinator checks subprocess exits, allocates free loopback ports and a
unique `analytics_worker_test_` project, and supplies Windows semicolon-separated
Compose files through child environments. It uses the normal repository
Dockerfile with `--pull --no-cache`, unique image tags/containers and a retained
project volume. Sanitized resolved Compose proof and command/result logs are
under `data/generated/backend-completion-<timestamp>/`. It stops only that
project in `finally` and never changes the caller's environment. A port bind
race is a failed setup, not a pass. Inspect only that project's logs on failure.

Full suites run on Windows against Docker PostgreSQL and in the normal Python
3.12 image with declared verification dependencies in a temporary test container.
This dependency installation is separate from the clean production-image build.
Each test fixture owns a fresh schema; no development data is selected.
The older hard-coded candidate verifier now delegates to these strict guards.

## Supported identity and API behavior

Use the actual candidate `/openapi.json`. Registry and telemetry retain the
existing local contracts; this candidate does not introduce producer credentials
or per-asset tenancy. Genuine incident/task reads require reader/operator/admin;
mutations require operator/admin; handover requires admin. Sample tasks retain
their explicitly untrusted demonstration label. SSO is outside agreed scope.

Provision credentials through the server-admin CLI into an exclusive new file:

```text
python -m backend.app.operators issue --name <operator> --role operator --hours 8 --token-file <private-new-file>
python -m backend.app.operators revoke --name <operator>
```

Reissuing a name rotates its credential; old tokens stop working. Lifetimes are
1–24 hours. Invalid/expired/revoked credentials return401. Protect the directory
and file with OS access controls: POSIX mode is not a Windows ACL. Never print
tokens, put them in URLs, commit them or capture Authorization headers. A failed
database commit removes the newly written credential file.

New model handovers return201; identical retries return200 with the original
receipt. OpenAPI documents both. Reuse the original idempotency key/intent on
retry; changed intent conflicts. Handover archives old state and cold-starts a
new namespace. It does not imply incident recovery or task completion.

What-if creates/reuses an immutable capture while leaving worker jobs/results/
states unchanged. 'No worker mutation' therefore does not mean 'no database
writes'. Historical dispatch follows the capture, without fallback/relabeling.
Missing eligibility/parameters produce the documented unavailable error.
Generic event/WebSocket transport remains proposed. The implemented outbox uses
a supplied callback after commit, lease fencing, per-incident order and stable
event IDs; receivers must deduplicate at-least-once redelivery. Acceptance uses
only a local HTTP receiver; no production callback is configured.

## Migration and recovery

Existing A001/A002/D005/W001 branches join at D006. This completion adds no
migration and rewrites none. Fresh upgrade and Alembic consistency must pass.
`test_combined_integration` covers nine populated supported revision combinations;
the independent D004 rehearsal compares original fields/counts/hashes across nine
existing tables.

`verify_backend_restore` takes a real custom-format `pg_dump` and restores it
into a second `_test` database in the owned PostgreSQL container. It compares
every public table's exact canonical row hash/count, including migration revision
and worker/incident/task history. Source data is retained. Dump contents stay in
the isolated container and are never committed. The retained volume contains
both databases.

Before separately approved deployment, retain a private backup and source/image
identities, rehearse restoration/upgrade, and obtain B/C/D review plus green
exact-head CI. Do not force downgrade populated history. A code rollback must
respect stored identities and adoption boundaries; choosing an old model is not
equivalent to restoring a verified compatible backup. This verification performs
no development migration, rollback, restart, merge or deployment.
