# Run from repository root, using the Python environment with backend dependencies installed.
param([string]$BaseUrl = "http://127.0.0.1:8000")
$ErrorActionPreference = "Stop"
python -m integration.verify_normal_operation_simulator --base-url $BaseUrl
if ($LASTEXITCODE -ne 0) { throw "Normal-operation simulator verification failed" }
