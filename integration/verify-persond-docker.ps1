param(
    [Parameter(Mandatory=$true)][string]$Python,
    [int]$DatabasePort = 15447,
    [int]$ApiPort = 15448
)
$ErrorActionPreference = 'Stop'
function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Verification command failed: $Executable (exit $LASTEXITCODE)" }
}
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$taskOriginalLocation = Get-Location
$taskVariables = @('PERSOND_TEST_PASSWORD','PERSOND_TEST_DATABASE','PERSOND_DB_PORT','PERSOND_API_PORT')
$taskSaved = @{}
foreach ($taskVariable in $taskVariables) { $taskSaved[$taskVariable] = [Environment]::GetEnvironmentVariable($taskVariable,'Process') }
$taskProject = 'persond_review_' + [guid]::NewGuid().ToString('N')
$taskCompose = @('compose','--project-name',$taskProject,'--file',(Join-Path $PSScriptRoot 'compose.persond-review.yaml'))
$taskStarted = $false
$taskIssued = $false
$taskPrivate = $null
try {
    Set-Location -LiteralPath $taskRoot
    # Preflight never starts Docker Desktop or an existing service.
    Invoke-Checked 'docker' @('info','--format','{{.ServerVersion}}')
    if ($DatabasePort -lt 1024 -or $ApiPort -lt 1024 -or $DatabasePort -eq $ApiPort -or
        $DatabasePort -in @(5432,5433,55432) -or $ApiPort -in @(8000,8001,18001,18002)) {
        throw 'Dedicated non-development ports required'
    }
    foreach ($taskPort in @($DatabasePort,$ApiPort)) {
        if (Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue) { throw "Port $taskPort is already occupied" }
    }
    $env:PERSOND_TEST_PASSWORD = [guid]::NewGuid().ToString('N')
    $env:PERSOND_TEST_DATABASE = $taskProject + '_test'
    $env:PERSOND_DB_PORT = [string]$DatabasePort
    $env:PERSOND_API_PORT = [string]$ApiPort
    $taskUrl = "postgresql+psycopg://sentinel:$($env:PERSOND_TEST_PASSWORD)@127.0.0.1:$DatabasePort/$($env:PERSOND_TEST_DATABASE)"
    $taskBase = "http://127.0.0.1:$ApiPort"
    $taskEvidence = Join-Path $taskRoot ('.venv/' + $taskProject)
    New-Item -ItemType Directory -Path $taskEvidence | Out-Null
    $taskPrivate = Join-Path $env:TEMP ($taskProject + '_private')
    New-Item -ItemType Directory -Path $taskPrivate | Out-Null
    $taskIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    Invoke-Checked 'icacls' @($taskPrivate,'/inheritance:r','/grant:r',"${taskIdentity}:(OI)(CI)F")
    $taskToken = Join-Path $taskPrivate 'admin.txt'
    Invoke-Checked 'docker' ($taskCompose + @('config','--quiet'))
    Invoke-Checked 'docker' ($taskCompose + @('build','backend','worker'))
    $taskStarted = $true
    Invoke-Checked 'docker' ($taskCompose + @('up','-d','--wait','db'))
    Invoke-Checked $Python @('-m','integration.verify_combined_records','--database-url',$taskUrl,'--mode','seed','--evidence-file',"$taskEvidence/migration.json")
    # Apply the actual populated upgrade using the normal backend image.
    Invoke-Checked 'docker' ($taskCompose + @('run','--rm','--no-deps','backend','python','-m','alembic','-c','backend/alembic.ini','upgrade','head'))
    Invoke-Checked 'docker' ($taskCompose + @('run','--rm','--no-deps','backend','python','-m','alembic','-c','backend/alembic.ini','check'))
    Invoke-Checked $Python @('-m','integration.verify_combined_records','--database-url',$taskUrl,'--mode','preserve','--evidence-file',"$taskEvidence/migration.json")
    Invoke-Checked 'docker' ($taskCompose + @('up','-d','backend'))
    function Wait-ReviewApi {
        for ($taskAttempt=0; $taskAttempt -lt 60; $taskAttempt++) {
            try { if ((Invoke-WebRequest "$taskBase/health/ready" -TimeoutSec 2).StatusCode -eq 200) { return } } catch {}
            Start-Sleep -Seconds 1
        }
        throw 'Isolated API readiness timed out'
    }
    Wait-ReviewApi
    # Credential file is private and outside Git. Container never receives its plaintext.
    $taskSavedUrl = $env:DATABASE_URL
    try {
        $env:DATABASE_URL = $taskUrl
        Invoke-Checked $Python @('-m','backend.app.operators','issue','--name','d-docker-review-admin','--role','admin','--token-file',$taskToken)
        $taskIssued = $true
    } finally { $env:DATABASE_URL = $taskSavedUrl }
    Invoke-Checked $Python @('-m','integration.verify_incident_maintenance','--base-url',$taskBase,'--database-url',$taskUrl,'--token-file',$taskToken,'--state-file',"$taskEvidence/tasks.json")
    Invoke-Checked $Python @('-m','integration.verify_what_if','--base-url',$taskBase,'--database-url',$taskUrl,'--output',"$taskEvidence/what-if.json")
    Invoke-Checked $Python @('-m','integration.verify_combined_records','--database-url',$taskUrl,'--mode','capture','--evidence-file',"$taskEvidence/retained.json")
    # Verifiers run the fenced worker synchronously. Boot the normal background worker
    # afterward to avoid racing their deliberately deterministic run_once assertions.
    Invoke-Checked 'docker' ($taskCompose + @('up','-d','worker'))
    Start-Sleep -Seconds 3
    $taskWorkerId = & docker @taskCompose ps -q worker
    if (-not $taskWorkerId -or (& docker inspect --format '{{.State.Running}}' $taskWorkerId) -ne 'true') { throw 'Normal worker did not remain running' }
    Invoke-Checked 'docker' ($taskCompose + @('restart','backend','worker'))
    Wait-ReviewApi
    Invoke-Checked $Python @('-m','integration.verify_incident_maintenance','--base-url',$taskBase,'--database-url',$taskUrl,'--token-file',$taskToken,'--state-file',"$taskEvidence/tasks.json",'--resume')
    Invoke-Checked $Python @('-m','integration.verify_combined_records','--database-url',$taskUrl,'--mode','verify','--evidence-file',"$taskEvidence/retained.json")
    $taskImages = & docker @taskCompose images --format json
    @{source=(& git rev-parse HEAD); project=$taskProject; database=$env:PERSOND_TEST_DATABASE;
      images=$taskImages; checks=@('normal images built','populated D004 upgrade','sole D006 and metadata','live incident tasks','live What-if','worker running','API/worker restart','exact retained sample/analytics/incident/snapshot records');
      limitations=@('synthetic worker inputs','local admin credential','no genuine UI E2E','no development deployment','no model1.0.2 adoption')} |
      ConvertTo-Json -Depth 5 | Set-Content "$taskEvidence/result.json"
    Write-Output "PASS isolated Docker review; evidence=$taskEvidence; retained volume=$taskProject`_review_data"
} finally {
    try {
        if ($taskIssued) {
            $taskSavedUrl = $env:DATABASE_URL
            try { $env:DATABASE_URL = $taskUrl; Invoke-Checked $Python @('-m','backend.app.operators','revoke','--name','d-docker-review-admin') }
            finally { $env:DATABASE_URL = $taskSavedUrl }
        }
    } finally {
        if ($taskStarted) { & docker @taskCompose stop }
        # Never down -v, rm, prune, or delete data/credential files.
        foreach ($taskVariable in $taskVariables) { [Environment]::SetEnvironmentVariable($taskVariable,$taskSaved[$taskVariable],'Process') }
        Set-Location -LiteralPath $taskOriginalLocation
    }
}
