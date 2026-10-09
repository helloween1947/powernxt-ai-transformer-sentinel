# Incident registry usage and API examples

See the [implemented API contract](../../docs/contracts/incident-api-contract.md)
and [worker/configuration handover](../../docs/incident-worker-handover.md).
No development services or data were changed during implementation. The current
development API may still return 404 for these routes until reviewed deployment.

## Trusted credentials

First create a private directory outside Git and restrict its Windows ACL to the
intended operator. The examples assume that directory already exists.
From a server-administrator shell with DATABASE_URL pointing to the intended
migrated database, issue a private credential outside the repository. Restrict
the private directory ACL to the operator on Windows; do not commit or share its
contents in logs/chat. Example PowerShell (choose a new private file path):

```powershell
python -m backend.app.operators issue --name Alice --role operator --hours 8 --token-file "$env:LOCALAPPDATA\PowerNXT-private\alice-session.txt"
# Server admin only: rotate by issuing to a different NEW file with the same name.
python -m backend.app.operators revoke --name Alice
```

To enable/change detector policy, provision a separate admin credential. Reader
credentials can inspect incidents. There is no default seeded operator/token.
The database stores hashes, roles, active status and expiry; responses never
return bearer credentials. Keep bearer values process-local and use HTTPS for
non-loopback traffic. Existing sample maintenance does not gain trusted identity
automatically.

## PowerShell API examples

Assumes reviewed code is deployed and an operator credential privately delivered;
the asset/configuration/run must really exist on that API. Do not reuse the test
UUIDs as universal production identifiers.

```powershell
$Base = 'http://127.0.0.1:8000'
$TokenFile = "$env:LOCALAPPDATA\PowerNXT-private\alice-session.txt"
$Headers = @{ Authorization = 'Bearer ' + (Get-Content -Raw $TokenFile).Trim() }
$Me = Invoke-RestMethod "$Base/api/v1/operators/me" -Headers $Headers
$AssetId = '<registered-asset-id>'
$RunId = '<actual-simulator-run-id>'
$Query = '?asset_id=' + [uri]::EscapeDataString($AssetId) + '&source=simulator&run_id=' + [uri]::EscapeDataString($RunId)
$Page = Invoke-RestMethod "$Base/api/v1/incidents$Query" -Headers $Headers
$IncidentId = $Page.items[0].incident_id
$Incident = Invoke-RestMethod "$Base/api/v1/incidents/$IncidentId" -Headers $Headers
$Evidence = Invoke-RestMethod "$Base/api/v1/incidents/$IncidentId/evidence?limit=20&cursor=0" -Headers $Headers
$ResultId = $Evidence.items[0].payload.result_id
Invoke-RestMethod "$Base/api/v1/analytics/results/$ResultId" -Headers $Headers
Invoke-RestMethod "$Base/api/v1/incidents/$IncidentId/events?limit=20&cursor=0" -Headers $Headers
$Ack = @{ schema_version = 'incident-acknowledgement-1.0.0'; expected_version = $Incident.incident_version; idempotency_key = [guid]::NewGuid().ToString() } | ConvertTo-Json
$Result = Invoke-RestMethod "$Base/api/v1/incidents/$IncidentId/acknowledgements" -Method Post -Headers $Headers -ContentType 'application/json' -Body $Ack
# Identical retry: same body/actor/key returns original result without another event.
Invoke-RestMethod "$Base/api/v1/incidents/$IncidentId/acknowledgements" -Method Post -Headers $Headers -ContentType 'application/json' -Body $Ack
```

Administrator policy example: [control JSON](../../data/sample/incident-control-sample.json).
The assumed thresholds are an illustrative policy, not approved/calibrated limits.
Initial expected_version is 0; later handovers require current control version.
Each distinct control operation gets a new idempotency key; exact retries reuse it.

```powershell
$AdminHeaders = @{ Authorization = 'Bearer ' + (Get-Content -Raw '<private-admin-token-file>').Trim() }
$Control = Get-Content -Raw .\data\sample\incident-control-sample.json | ConvertFrom-Json
$Control.run_id = $RunId
$ConfigurationVersion = 1 # Replace with the actual registered version.
$Control.configuration_version = $ConfigurationVersion
$Control.idempotency_key = [guid]::NewGuid().ToString()
$Body = $Control | ConvertTo-Json -Depth 12
Invoke-RestMethod "$Base/api/v1/assets/$AssetId/detector-handovers" -Method Post -Headers $AdminHeaders -ContentType 'application/json' -Body $Body
```

A first result starts persistence at zero and may only initialize thermal state;
an instantaneous breach creates no incident. Actual eligible forward readings
must sustain the explicit policy. The existing opt-in worker handles them; there
is no public POST that accepts fabricated incident evidence/condition/actor.

## Repeatable isolated verification (PowerShell)

Use a new test container/database/API port. These commands never restart/rebuild
the development backend/worker, apply development migrations or delete volumes.
Run from repository root with backend/requirements-dev.txt already installed:

```powershell
$DbName = 'incident_registry_' + [guid]::NewGuid().ToString('N') + '_test'
$Container = 'incident-registry-' + [guid]::NewGuid().ToString('N')
$TestPassword = [guid]::NewGuid().ToString('N')
docker run -d --name $Container -e POSTGRES_USER=sentinel -e "POSTGRES_PASSWORD=$TestPassword" -e "POSTGRES_DB=$DbName" -p 127.0.0.1:15439:5432 postgres:16-alpine
docker exec $Container pg_isready -U sentinel -d $DbName
# Wait for pg_isready success before the commands below.
$TestUrl = "postgresql+psycopg://sentinel:${TestPassword}@127.0.0.1:15439/$DbName"
# Preserve any preexisting process-local variables; restore them after testing.
$SavedDatabaseUrl = $env:DATABASE_URL
$SavedTestDatabaseUrl = $env:TEST_DATABASE_URL
$env:DATABASE_URL = $TestUrl
$env:TEST_DATABASE_URL = $TestUrl
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini check
python -m pytest backend/tests -q --tb=short
$PrivateToken = "$env:LOCALAPPDATA\PowerNXT-private\incident-test-$([guid]::NewGuid().ToString('N')).txt"
python -m backend.app.operators issue --name isolated-admin --role admin --token-file $PrivateToken
# In a separate terminal set DATABASE_URL to the SAME $TestUrl, then:
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 15440
```

With only that temporary API running, execute in the test terminal:

```powershell
python -m integration.verify_incident_registry --base-url http://127.0.0.1:15440 --database-url $TestUrl --token-file $PrivateToken --output "$env:TEMP\incident-registry-verification.json"
$env:DATABASE_URL = $SavedDatabaseUrl
$env:TEST_DATABASE_URL = $SavedTestDatabaseUrl
# Ctrl+C only the API you started, then stop only $Container if desired.
# Retain test data and private credential files securely for inspection/revocation.
```

The script requires a PostgreSQL database ending `_test`, a dedicated loopback
API port and an admin credential. It creates a unique synthetic asset/run/config,
uses actual HTTP endpoints and fenced worker transactions, verifies opening/
ack/recovery, exact-result evidence, stream isolation and no duplicate records.
It does not delete records, restart services or certify browser/calibration/task
integration. Fresh schema/database migration tests are included in backend/tests.
