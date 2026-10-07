# Run in the Windows folder containing the running worker's compose.gpu.yml.
[CmdletBinding()]
param(
    [string]$VmAddress = "aphrodize@172.30.81.237",
    [string]$RuntimeDir = (Get-Location).Path
)
$ErrorActionPreference = "Stop"
Set-Location $RuntimeDir
if (!(Test-Path .env.gpu) -or !(Test-Path compose.gpu.yml)) {
    throw "Run this script in the existing GPU runtime folder with .env.gpu and compose.gpu.yml."
}
$tempConfig = Join-Path $RuntimeDir (".env.annotation.download-" + [guid]::NewGuid())
try {
    & scp "${VmAddress}:~/Aphrodize/.env.annotation.gpu" $tempConfig
    if ($LASTEXITCODE -ne 0) { throw "Could not download annotation configuration from the VM." }
    $config = @{}
    foreach ($line in [IO.File]::ReadAllLines($tempConfig)) {
        if ($line -match '^(LABEL_STUDIO_URL|LABEL_STUDIO_API_KEY|LABEL_STUDIO_PROJECT_ID)=(.+)$') {
            $config[$Matches[1]] = $Matches[2]
        }
    }
    if ($config.Count -ne 3 -or [int]$config['LABEL_STUDIO_PROJECT_ID'] -lt 1) {
        throw "Annotation configuration is incomplete."
    }
    $existing = [IO.File]::ReadAllLines((Join-Path $RuntimeDir '.env.gpu'))
    $updated = @($existing | Where-Object { $_ -notmatch '^LABEL_STUDIO_(URL|API_KEY|PROJECT_ID)=' })
    foreach ($key in @('LABEL_STUDIO_URL', 'LABEL_STUDIO_API_KEY', 'LABEL_STUDIO_PROJECT_ID')) {
        $updated += $key + '=' + $config[$key]
    }
    # Preserve model paths and data-service credentials; change only review settings.
    $encoding = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllLines((Join-Path $RuntimeDir '.env.gpu'), [string[]]$updated, $encoding)
    $compose = [IO.File]::ReadAllLines((Join-Path $RuntimeDir 'compose.gpu.yml'))
    $compose = @($compose | Where-Object { $_ -notmatch '^\s+LABEL_STUDIO_(URL|API_KEY|PROJECT_ID):' })
    [IO.File]::WriteAllLines((Join-Path $RuntimeDir 'compose.gpu.yml'), [string[]]$compose, $encoding)
    & docker compose --env-file .env.gpu -f compose.gpu.yml config --quiet
    if ($LASTEXITCODE -ne 0) { throw "Worker Compose configuration is invalid." }
    & docker compose --env-file .env.gpu -f compose.gpu.yml up -d --no-deps --force-recreate inference-worker
    if ($LASTEXITCODE -ne 0) { throw "Worker restart failed." }
    $probe = @'
from backend.core.config import settings
from backend.libs.labelstudio_client import get_label_studio_client
assert settings.label_studio_api_key and settings.label_studio_project_id > 0
client = get_label_studio_client()
project = client.projects.get(id=settings.label_studio_project_id)
assert project.title == "Aphrodize wrinkle mask review"
print("GPU worker -> Label Studio: OK")
'@
    $probe | & docker compose --env-file .env.gpu -f compose.gpu.yml exec -T inference-worker python -
    if ($LASTEXITCODE -ne 0) { throw "Worker cannot access the review project." }
    Write-Host "Annotation enabled. Report: GPU worker -> Label Studio: OK"
} finally {
    if (Test-Path $tempConfig) { Remove-Item $tempConfig -Force }
}
