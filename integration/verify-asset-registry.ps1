# Run from the repository root after building and migrating the backend.
# The standard-library Python check creates a unique demonstration asset and
# normally restarts db/backend; no existing records or volumes are removed.
param([string]$BaseUrl = "http://localhost:8000")
$ErrorActionPreference = "Stop"
python "$PSScriptRoot/verify_asset_registry.py" --base-url $BaseUrl
if ($LASTEXITCODE -ne 0) { throw "Asset registry verification failed" }
