# Reviewed thermal configuration and fresh-run handoff

Reviewed 9 October 2026 against main `9d2f9cd`, the integrated adapter, immutable configuration/telemetry schemas, analytics contract, simulator guide and Person B's earlier worker handoff. No applicable AGENTS.md was present. Work is scoped to `feature/personb-thermal-demo`, based on main; the existing analytics branch and unrelated untracked file are preserved. No model/backend/deployment/database change is made.

## Diagnosis and reviewed template

The supplied Windows result for asset `demo-normal-85203b1018bc498c8b90873f383cc740`, simulator run `normal-85203b1018bc498c8b90873f383cc740`, configuration1, reading19 is reported evidence, not a record inspected locally. Its missing-coefficient reasons are correct: electrical computation can succeed while thermal prediction/residual remain unavailable. Updating a new configuration does not retroactively change that reading/result.

The existing `data/sample/asset-configuration-worker-assumed.json` passes current ConfigurationCreate validation and has all coefficients needed by model `powernxt-electrical-top-oil`, version `stored-reading-top-oil-1.0.1`. Its 1000kVA/11kV/52.49A/LL/primary ratings and limits are **illustrative assumptions**, not verified ratings for the supplied asset. Do not post that whole sample blindly.

Reviewed overlay template: `data/sample/thermal-demo-parameters-assumed.json`. It contains only four coefficients and their exact supported assumed provenance. It is **not** a standalone ConfigurationCreate payload. `integration.prepare_thermal_demo` combines it with an actual saved ConfigurationResponse to produce the complete API-valid POST payload. It preserves electrical ratings, convention, measurement side, cooling class, operational limits and their provenance; existing non-null thermal values/provenance are retained. It fills only missing coefficients and strips response-only asset_id/version/created_at. It does not contact an API or overwrite an existing output file.

| Exact field | Assumed value / unit | Schema range and model meaning | Provenance and rationale |
|---|---|---|---|
| thermal_parameters.rated_top_oil_rise_c | 40C | Finite number >0; oil rise at rated K1 in the simplified equilibrium | assumed; reuse the adopted worker demonstration profile, not measured/manufacturer data |
| thermal_parameters.oil_time_constant_min | 180min =10800s | Finite number >0; fixed first-order relaxation time | assumed; existing three-hour demonstration coefficient, not a fitted asset response |
| thermal_parameters.loss_ratio | 5 dimensionless | Finite number >0; rated load-loss/no-load-loss ratio | assumed; existing illustrative loss split, no asset loss test available |
| thermal_parameters.oil_exponent | 0.8 dimensionless | Finite number >0; exponent linking normalized total loss to oil rise | assumed; existing demonstration exponent, not independently calibrated |

For every row the exact provenance key is the dotted field name above, with value `assumed`. None is measured, manufacturer-supplied or calibrated. Positive finite schema acceptance does not establish physical suitability; no universal physically safe coefficient range is asserted. API numbers must be JSON numbers, not booleans/strings. Parameter sources are the existing [worker assumed sample](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/blob/9d2f9cd/data/sample/asset-configuration-worker-assumed.json) and [adopted deployed core](https://github.com/helloween1947/powernxt-ai-transformer-sentinel/blob/9d2f9cd/backend/app/analytics/person_b/core.py). These assumptions are reused for execution compatibility, not tuned to match the generator.

The complete payload also requires positive finite rated_kva, rated_voltage_v and rated_current_a; voltage_convention LL/LN, measurement_side primary/secondary, cooling_type, and exact provenance for all supplied parameters. The builder copies those actual fields. Optional winding/hot-spot parameters remain as originally supplied; this model does not use them. Non-null real thermal coefficients, if present, take precedence over this assumed overlay.

## Deployed interface and expected behavior

```python
from backend.app.analytics.person_b import compute_analytics

result = compute_analytics(
    normalized_telemetry, immutable_configuration, quality_flags,
    reading_id, previous_state=None, state_policy="forward_only",
)
```

The integrated adapter is `backend.app.analytics.adapter.compute(reading, config, previous_state, policy)`. Model ID powernxt-electrical-top-oil; model version stored-reading-top-oil-1.0.1; result schema stored-reading-result-1.1.0; state schema stored-reading-state-1.0.0. Parameters and provenance are fingerprinted; supplied data are never substituted by the current/latest config. No processing clock enters computation.

For `K=sqrt(mean((I_phase/I_rated)^2))`, equilibrium is `ambient + rise*((1+R*K^2)/(1+R))^n`; exact evolution is `target+(previous_temperature-target)*exp(-dt/tau)`. **Previous** load/ambient represent the elapsed interval. Current load/ambient prepare the next interval. Subsequent measured oil is not assimilated before or after residual evaluation: residual=current measured oil minus propagated prediction.

| Situation | Expected thermal result |
|---|---|
| First eligible usable reading, no state | Store observed oil as initial condition. Prediction/residual null; reason initialized_from_measurement_prediction_not_independent; outcome partially_available. Worker status completed is legitimate. |
| Subsequent strictly advancing reading with known preceding inputs | Prediction available; residual available if current oil is usable. With full electrical channels, outcome completed. |
| Minute samples | Actual measurement dt60s, not300s. Irregular eligible intervals also use their exact elapsed seconds. |
| dt300s | Allowed by this model's continuity policy. |
| dt>300s | Invalidate thermal continuity with measurement_gap_exceeds_300_s; later good frames do not silently repair it. |
| Missing current or ambient | Bootstrap unavailable. Once initialized, preceding known interval may still predict; missing held inputs invalidate the following interval. |
| Missing oil after initialization | Prediction may continue; current residual unavailable. Returning oil never re-fits the model. |
| Equal/late/historical-only reading | No forward thermal prediction/state advancement; prior state unchanged. |
| New configuration/model/run | Different state namespace; A's worker cold-starts on identity transition and retains history/watermarks. Raw model rejects mismatched supplied state. New run starts independently. |

The300s cutoff is a versioned implementation continuity limit (`MAX_GAP_S`), not a field in ThermalParameters and not a physical time constant. Do not add max_gap_s to the configuration payload or reinterpret packets as300s. Configuration history is immutable; no update/rewrite/reprocessing of old records is part of this handoff.

Bootstrap requires all three usable RMS line currents, ambient and top-oil measurements, plus all four coefficients. Thermal propagation needs the prior held current-derived K/ambient; residual additionally needs current usable oil. Voltages are required for apparent power/capacity metrics but are not thermal inputs. Side and voltage convention remain the actual asset's settings. Genuine zeros are preserved. Producer suspect/bad/missing, nonempty ingestion flags, nonfinite numbers and model-usability bounds exclude channels. Model ranges: current0..10x rating, voltage0..2x rating, ambient-50..80C, oil-50..200C. These are transparent usability rules, not protection limits.

Unsupported PF/kW/kvar/sequence components, winding temperature, aging, health/confidence scores, forecasts and recommendations remain unavailable. Existing coefficient-free configurations continue reporting explicit missing paths; processing success does not make those quantities available.

## Exact PowerShell new-version/new-run procedure

Run at repository root in a checkout containing this reviewed handoff/helper and current main backend, with the existing Python3.12 environment and running API/worker. These commands are supplied for **Person A to execute** on their database; they were not executed against the supplied Windows IDs. No .env, migration, old config or old stream is changed. Review the new payload before the POST.

```powershell
$ErrorActionPreference = 'Stop'
$thermalPython = '.\.venv\Scripts\python.exe'
$thermalBase = 'http://127.0.0.1:8000'
$thermalAsset = 'demo-normal-85203b1018bc498c8b90873f383cc740'
$thermalBaselineVersion = 1
$thermalRun = 'thermal-' + [guid]::NewGuid().ToString('N')
$thermalOut = Join-Path 'data\generated' $thermalRun
New-Item -ItemType Directory -Path $thermalOut | Out-Null
$thermalUtf8 = [System.Text.UTF8Encoding]::new($false)
Invoke-RestMethod "$thermalBase/health/ready"

# Retrieve exactly baseline version1 through the real paginated history API.
$thermalOffset = 0
$thermalSnapshot = $null
do {
    $thermalPage = Invoke-RestMethod "$thermalBase/api/v1/assets/$thermalAsset/configurations?limit=100&offset=$thermalOffset"
    $thermalSnapshot = $thermalPage.items | Where-Object { $_.version -eq $thermalBaselineVersion } | Select-Object -First 1
    $thermalOffset += 100
} while (($null -eq $thermalSnapshot) -and ($thermalPage.items.Count -eq 100))
if ($null -eq $thermalSnapshot) { throw 'Exact baseline configuration was not found; do not substitute another asset.' }
$thermalBaselinePath = Join-Path $thermalOut 'baseline-configuration.json'
[IO.File]::WriteAllText($thermalBaselinePath, ($thermalSnapshot | ConvertTo-Json -Depth 100), $thermalUtf8)

$thermalPayloadPath = Join-Path $thermalOut 'new-configuration-payload.json'
& $thermalPython -m integration.prepare_thermal_demo --configuration-json $thermalBaselinePath --output $thermalPayloadPath
if ($LASTEXITCODE -ne 0) { throw 'Configuration preparation failed.' }
$thermalPayload = Get-Content -Raw $thermalPayloadPath
$thermalPayload  # Review ratings, side, limits and assumed provenance before POST.
```

After reviewing that concrete payload:

```powershell
$thermalNewConfig = Invoke-RestMethod -Method Post -Uri "$thermalBase/api/v1/assets/$thermalAsset/configurations" -ContentType 'application/json' -Body $thermalPayload
$thermalVersion = [int]$thermalNewConfig.version  # Capture returned value; NEVER assume2.
if (($thermalVersion -le $thermalBaselineVersion) -or ($thermalNewConfig.asset_id -ne $thermalAsset)) { throw 'Unexpected configuration reference.' }
$thermalNewConfigPath = Join-Path $thermalOut 'new-configuration-response.json'
[IO.File]::WriteAllText($thermalNewConfigPath, ($thermalNewConfig | ConvertTo-Json -Depth 100), $thermalUtf8)
$thermalSimulatorOut = Join-Path $thermalOut 'simulator'

# Synthetic demonstration timestamps; a NEW run has its own measurement watermark.
& $thermalPython -m backend.app.simulator --base-url $thermalBase generate --asset-id $thermalAsset --configuration-version $thermalVersion --run-id $thermalRun --seed 42 --start '2026-01-01T00:00:00Z' --duration-seconds 301 --interval-seconds 60 --initial-oil-temperature-c 45 --configuration-json $thermalNewConfigPath --output-dir $thermalSimulatorOut
if ($LASTEXITCODE -ne 0) { throw 'Simulator generation failed; retain the new config and inspect actual limits/ratings.' }
& $thermalPython -m backend.app.simulator --base-url $thermalBase send --input (Join-Path $thermalSimulatorOut 'telemetry.jsonl')
if ($LASTEXITCODE -ne 0) { throw 'Submission failed; retain artifacts. Retry the SAME JSONL, not regenerated identities.' }
Write-Host "asset=$thermalAsset configuration_version=$thermalVersion source=simulator run_id=$thermalRun"
```

POST is not an idempotent config-creation operation. If its response is lost/uncertain, inspect saved configuration history to recover the created version; do not blindly retry and assume a version. The generator checks actual rating consistency and load/voltage/oil envelope. Restrictive or inconsistent real settings can reject its default profile; inspect them rather than replacing ratings/limits. Saved configuration snapshot and run-metadata make this stream reproducible. Duration301 gives6 samples0..300s. No simulator/model equation is changed.

Retrieve each durable result, allowing bounded time for the already running worker:

```powershell
$thermalHistory = Invoke-RestMethod "$thermalBase/api/v1/assets/$thermalAsset/telemetry?source=simulator&run_id=$thermalRun&limit=100"
if ($thermalHistory.items.Count -ne 6) { throw 'Expected six submitted readings in the NEW run.' }
$thermalResults = @()
foreach ($thermalReading in $thermalHistory.items) {
    $thermalStatus = $null
    for ($thermalAttempt = 0; $thermalAttempt -lt 60; $thermalAttempt++) {
        $thermalStatus = Invoke-RestMethod "$thermalBase/api/v1/telemetry/$($thermalReading.id)/analytics"
        if ($thermalStatus.status -in @('completed','unavailable','failed')) { break }
        Start-Sleep -Seconds 2
    }
    if ($thermalStatus.status -ne 'completed') { throw "Reading $($thermalReading.id): $($thermalStatus.status), error=$($thermalStatus.error_code)" }
    if ($thermalStatus.configuration_version -ne $thermalVersion) { throw 'Result references the wrong immutable version.' }
    $thermalResults += $thermalStatus
}
[IO.File]::WriteAllText((Join-Path $thermalOut 'stored-analytics-results.json'), (ConvertTo-Json -InputObject $thermalResults -Depth 100), $thermalUtf8)
$thermalFirst = $thermalResults[0].result.payload.thermal_assessment
if (($null -ne $thermalFirst.predicted_top_oil_temperature_c) -or ($null -ne $thermalFirst.thermal_residual_c)) { throw 'Unexpected bootstrap behavior.' }
foreach ($thermalResult in ($thermalResults | Select-Object -Skip 1)) {
    $thermalAssessment = $thermalResult.result.payload.thermal_assessment
    if (($null -eq $thermalAssessment.predicted_top_oil_temperature_c) -or ($null -eq $thermalAssessment.thermal_residual_c) -or ($thermalAssessment.elapsed_s -ne 60)) { throw 'Subsequent thermal result unavailable; inspect its reasons/quality.' }
}
Invoke-RestMethod "$thermalBase/api/v1/assets/$thermalAsset/analytics/latest?source=simulator&run_id=$thermalRun"
```

The fixed January timestamp represents synthetic measurement time, not processing time or live measured data. New run isolation makes it safe for ordering in this demo. Latest/individual results are scoped explicitly; default device history and the original normal run are unchanged. Preserve all snapshots, POST payload, JSONL, simulator metadata and result evidence. Bootstrap being completed with null prediction/residual is expected; frames2..6 should have finite values if channels remain usable.

## Actual validation

Tested against the **deployed** `backend.app.analytics.person_b.compute_analytics`, without editing it. Python3.12, isolated PostgreSQL sentinel_test with per-test migrated schemas; no application data or supplied Windows IDs were accessed.

- `.venv/bin/python -m pytest integration/tests/test_thermal_demo.py -q --tb=short -k 'not fresh_api'`:19 passed,1 deselected (database flow deferred to full run).
- `TEST_DATABASE_URL=<isolated _test URL> .venv/bin/python -m pytest backend/tests integration/tests/test_thermal_demo.py -q --tb=short --maxfail=3`: **184 passed**, none skipped.164 current backend tests +20 thermal-demo tests. Existing Starlette/Alembic deprecation warnings remain.
- `.venv/bin/python -m integration.prepare_thermal_demo --help`: succeeded; CLI invocation also tested with saved JSON/BOM and no-overwrite behavior.
- Optional Ruff checks could not run because Ruff is not installed in this environment; no lint pass is claimed.

Coverage: actual sample schema, preservation with alternative LL/primary and LN/secondary ratings/provenance, retention of measured coefficients, invalid values, finite JSON, bootstrap, dt1/60/137/300, previous-input hold despite current load/ambient changes,301s gap latch, missing channels/coefficient reasons, run/config/model compatibility. Fresh API test creates two old configurations and a coefficient-free stored old result, captures returned new version3, generates6 packets, executes A's durable worker and retrieves persisted results; first is initialization, five subsequent predictions/residuals finite, all dt60. Old configuration and stored result remain unchanged; device stream is untouched.

Independent numerical expectation: initial55C, previous ambient30C and rated K1 with rise40C give target70C and tau10800s. At60s, prediction=`70-15*exp(-60/10800)`=**55.08310227992655C**. Observed60C gives residual **4.91689772007345C**. Current endpoint load0/ambient40 does not change that preceding interval's prediction. This verifies implementation of the analytical ODE solution, not field accuracy.

## Limits and remaining blockers

Generator equilibrium ambient+40*K² with60min tau differs from the prediction's loss-ratio/exponent equilibrium and180min tau. Its config thermal coefficients are not used by generation. Nonzero residuals—including negative residuals—are therefore expected model mismatch, not evidence of a physical fault. Short six-frame demonstrations are far shorter than either thermal time constant. No predictor tuning to generator agreement was performed.

No independent measured load/ambient/oil history, manufacturer losses, calibrated time constant or uncertainty model is available. Assumed coefficients establish usable synthetic execution only. Physical calibration and independent validation remain necessary. The actual asset ratings/limits were not supplied; the snapshot builder preserves them and the generator may require a separately reviewed compatible profile if defaults violate those limits. That is the only possible local-data-dependent execution blocker. This handoff does not deploy, alter A's database, implement new forecasts/scores/recommendations or change already stored readings/results.
