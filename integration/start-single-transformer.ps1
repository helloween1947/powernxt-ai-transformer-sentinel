param([switch]$Stop)
$ErrorActionPreference = 'Stop'
function Check-Native { param([string]$Step) if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit $LASTEXITCODE" } }
$repoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $repoRoot
try {
  $privateDir = Join-Path $repoRoot 'data/generated/single-transformer'
  $privateEnv = Join-Path $privateDir 'private.env'
  if (-not (Test-Path -LiteralPath $privateEnv)) {
    if ($Stop) { throw 'No owned local application settings exist' }
    New-Item -ItemType Directory -Force -Path $privateDir | Out-Null
    $projectId = 'powernxt_single_' + [Guid]::NewGuid().ToString('N').Substring(0,8)
    $dbPassword = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N')
    $ports = @()
    foreach ($initialPort in @(18300,18301,18302)) {
      $candidatePort = $initialPort
      while (($ports -contains $candidatePort) -or (Get-NetTCPConnection -State Listen -LocalPort $candidatePort -ErrorAction SilentlyContinue)) { $candidatePort++ }
      $ports += $candidatePort
    }
    [IO.File]::WriteAllText($privateEnv, "COMPOSE_PROJECT_NAME=$projectId`nSINGLE_DB_PASSWORD=$dbPassword`nSINGLE_UI_PORT=$($ports[0])`nSINGLE_API_PORT=$($ports[1])`nSINGLE_DB_PORT=$($ports[2])`n")
  }
  $composeArgs = @('compose','--env-file',$privateEnv,'-f','integration/compose.single-transformer.yaml')
  $resolvedText = & docker @composeArgs config --format json
  Check-Native 'Isolated configuration'
  $resolved = $resolvedText | ConvertFrom-Json
  if ($resolved.name -notmatch '^powernxt_single_[a-zA-Z0-9_-]+$' -or $resolved.services.db.environment.POSTGRES_DB -ne 'single_transformer_app_test') { throw 'Refusing an unrecognized project/database' }
  if ($Stop) {
    & docker @composeArgs stop
    Check-Native 'Owned application shutdown'
    Write-Output 'Stopped only the owned application; database volume retained.'
    return
  }
  New-Item -ItemType Directory -Force -Path (Join-Path $privateDir 'private') | Out-Null
  & docker @composeArgs build backend frontend
  Check-Native 'Application image build'
  & docker @composeArgs up -d --no-build --wait --wait-timeout 150
  Check-Native 'Application readiness'
  foreach ($role in @('admin','operator','reader')) {
    if (-not (Test-Path -LiteralPath (Join-Path $privateDir "private/$role.txt"))) {
      & docker @composeArgs exec -T backend python -m backend.app.operators issue --name "single-app-$role" --role $role --hours 24 --token-file "/evidence/private/$role.txt"
      Check-Native 'Private local credential provisioning'
    }
  }
  & docker @composeArgs exec -T backend python -m integration.seed_single_transformer
  Check-Native 'API seed / immutable record verification'
  Write-Output ('Frontend: http://127.0.0.1:' + $resolved.services.frontend.ports[0].published)
  Write-Output ('Backend: http://127.0.0.1:' + $resolved.services.backend.ports[0].published)
  Write-Output 'Credentials are in ignored data/generated/single-transformer/private. No environment variables changed.'
} finally { Pop-Location }
