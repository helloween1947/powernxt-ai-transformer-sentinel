# Run from the repository root with Python 3.12 and migrated Compose services.
param([string]$BaseUrl = "http://127.0.0.1:8000")
$ErrorActionPreference = "Stop"
python "$PSScriptRoot/verify_telemetry_ingestion.py" --base-url $BaseUrl
if ($LASTEXITCODE -ne 0) { throw "Telemetry ingestion verification failed" }
