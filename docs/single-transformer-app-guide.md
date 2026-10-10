# Single-transformer application

This is an owned review application assembled from PR36's integrated source, not merged main or a development deployment. It uses the existing backend, durable worker, models and frontend adapters. The focused build fixes `powernxt-single-transformer` across all screens and removes fleet navigation. Source/run selection is shared by the monitoring, incidents and What-if screens. Maintenance stays on the same asset and defaults to incident-linked tasks; its existing sample mode remains explicitly labelled.

## Windows startup and shutdown

From this branch's worktree, with Docker Desktop running:

```powershell
.\integration\start-single-transformer.ps1
```

The helper creates a unique `powernxt_single_*` project, chooses available ports beginning at18300/18301/18302, and saves a random database password in ignored `data/generated/single-transformer/private.env`. It builds the normal repository backend Dockerfile and the frontend's production Nginx image, waits for PostgreSQL/migration/API/frontend readiness, issues private24-hour prototype credentials, and seeds through supported APIs. On repeat execution it retains the same project/database/volume and uses identical telemetry retries, without appending configuration versions. It never changes parent environment variables. Protect the private directory as local credentials; never commit or share its contents.

Actual tested local project: `powernxt_single_71a55838`; frontend `http://127.0.0.1:18300`, API `http://127.0.0.1:18301`, PostgreSQL loopback18302. The standalone file must never be combined with development `compose.yaml`.

Exact underlying commands for the existing local settings:

```powershell
docker compose --env-file data/generated/single-transformer/private.env -f integration/compose.single-transformer.yaml build backend frontend
docker compose --env-file data/generated/single-transformer/private.env -f integration/compose.single-transformer.yaml up -d --no-build --wait --wait-timeout 150
docker compose --env-file data/generated/single-transformer/private.env -f integration/compose.single-transformer.yaml exec -T backend python -m integration.seed_single_transformer
```

Stop only this application and retain all records/volumes:

```powershell
.\integration\start-single-transformer.ps1 -Stop
# Equivalent:
docker compose --env-file data/generated/single-transformer/private.env -f integration/compose.single-transformer.yaml stop
```

No volume deletion, Docker prune, development restart/migration or deployment is part of this procedure. Separate development remains on API8000 and its original database/worker/frontend.

## Transformer and interpretation

The isolated application database starts empty; a read-only development inventory identified several existing demonstrations, including the prior configuration2 thermal asset. No supported cross-database copy procedure preserving every linked record was established, so existing data was left intact and fresh synthetic data was generated instead.

- Asset: `powernxt-single-transformer`, **PowerNXT synthetic transformer**.
- Source: `simulator`; default run: `single-transformer-demo-v1`.
- Immutable configuration:1; model: `stored-reading-top-oil-1.0.2`.
- Six deterministic packets at2026-10-10 12:00–12:05UTC. Fixed UUIDv4-format message identities make retries idempotent.
- Assumed ratings1000kVA,11000V line-to-line/primary,52.49A; ONAN. Thermal assumptions40°C rise,180min time constant, loss ratio5, exponent0.8; assumed105°C limit.
- Synthetic measured oil55°C, ambient30°C,150% phase current loading. Two persisted incidents follow a separately labelled assumed detector policy; they are not field fault labels.
- The first reading initializes from measurement with no independent prediction/residual. Five later predictions/residuals use60-second elapsed intervals. Health/confidence and unsupported measurements remain unavailable.

The UI shows asset/source/run/configuration/model. Every chart selects one configuration and stored model; all history remains available for individual inspection. QA streams use the same transformer but separate run IDs; they never enter the default demonstration chart. Historical source/configuration/model identities are not rewritten.

## Local authentication and workflows

Open the frontend. Paste the private **operator** credential from `data/generated/single-transformer/private/operator.txt` into the authentication bar. This is a locally provisioned, expiring prototype identity, not production SSO. Reader credentials disable mutations. Admin is only for detector/setup administration; never embed any token in browser build variables or URLs.

Use Digital twin/Electrical/Thermal, Trends, Condition explorer and Reports for backend records. Query Alerts & incidents, inspect immutable evidence, acknowledge independently, and create a linked task. Maintenance supports owner assignment, in-progress/completed status with required notes, cancellation with a reason, explicit version conflicts and retained task history. Completion does not recover or acknowledge an incident. What-if captures eligible committed state and compares bounded constant-load healthy-model scenarios without editing worker state. Unsupported state returns an explicit unavailable response.

Credentials expire after24hours. To renew, issue to a **new private filename** (the CLI refuses overwriting), rotate the operator, and authenticate with that new file. For example, replace `operator-new.txt` with a unique filename:

```powershell
docker compose --env-file data/generated/single-transformer/private.env -f integration/compose.single-transformer.yaml exec -T backend python -m backend.app.operators issue --name single-app-operator --role operator --hours 24 --token-file /evidence/private/operator-new.txt
```

To reseed after admin expiry, issue a new admin file likewise and run `integration.seed_single_transformer --token-file /evidence/private/admin-new.txt`. Preserve original credential files privately or revoke old credentials through the supported CLI; never delete application data to renew identity.

## Verification and review

See `single-transformer-app-verification.md` and the structured evidence manifest. Backend/contract tests use a separate `single_transformer_contract_test` database in the owned cluster, not application/dev records. Actual Chrome uses the production frontend and real API with no response fixtures. Separate worker QA runs test retries/recovery/restarts while preserving the original six records. All retained QA records remain under the one asset.

Integration ancestry includes the reported PR36 commit493092ee1fbca71245c8f4e3e01f81df134bded5 and current backend dependencyfae21510c83e2595708078df39f6468b70cfb2a0. The latter advancement adds reports only. Those inherited reports are not an endorsement of attributed teammate sign-offs; this branch's verification records independent observations. PR34/36 and this focused PR require coordinated A/C/D review and a decision on overlapping adoption; do not merge overlapping frontend integrations twice.

No model equation, migration, backend contract or production authentication was changed. Physical calibration, production SSO, reviewed merged-main acceptance and deployment remain separate gates.
