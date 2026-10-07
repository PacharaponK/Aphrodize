<# Checks the selected Compose deployment without printing its resolved environment. #>
[CmdletBinding()]
param([string[]]$ComposeFiles = @('compose.yml'), [string[]]$Profiles = @())
$ErrorActionPreference = 'Stop'
$composeArgs = @('compose')
foreach ($file in $ComposeFiles) { $composeArgs += @('-f', $file) }
foreach ($profile in $Profiles) { $composeArgs += @('--profile', $profile) }
$rawConfig = & docker @composeArgs config --format json
if ($LASTEXITCODE -ne 0) { throw 'Cannot read the selected Compose configuration' }
$config = ($rawConfig -join "`n") | ConvertFrom-Json
$rawState = & docker @composeArgs ps --all --format json
if ($LASTEXITCODE -ne 0) { throw 'Cannot read container state' }
$seen = @{}
foreach ($line in $rawState) {
    if (-not [string]::IsNullOrWhiteSpace($line)) {
        foreach ($container in ($line | ConvertFrom-Json)) { $seen[$container.Service] = $container }
    }
}
$failed = $false
$results = foreach ($entry in $config.services.PSObject.Properties) {
    $service = $entry.Name
    $requiredProfiles = @($entry.Value.profiles)
    if ($requiredProfiles.Count -and $requiredProfiles[0] -and
        -not ($requiredProfiles | Where-Object { $_ -in $Profiles })) { continue }
    $container = $seen[$service]
    $ok = $false
    $detail = 'container not created'
    if ($container) {
        if ($service -in @('minio-init', 'fixture')) {
            $ok = $container.State -eq 'exited' -and $container.ExitCode -eq 0
            $detail = "one-shot state: $($container.State); exit: $($container.ExitCode)"
        } else {
            $ok = $container.State -eq 'running' -and $container.Health -notin @('unhealthy', 'starting')
            $detail = if ($container.Health) { $container.Health } else { $container.State }
        }
    }
    if (-not $ok) { $failed = $true }
    [PSCustomObject]@{ Service = $service; Status = $(if ($ok) { 'ok' } else { 'failed' }); Detail = $detail }
}
$results | Format-Table -AutoSize
if ($seen['api'] -and $seen['api'].State -eq 'running') {
    $probeCode = @'
import base64, json, os, sys
from urllib.request import Request, urlopen
try:
    credentials = os.environ['API_USERNAME'] + ':' + os.environ['API_PASSWORD']
    request = Request('http://127.0.0.1:8000/api/v1/monitoring/ready', headers={
        'Authorization': 'Basic ' + base64.b64encode(credentials.encode()).decode()})
    with urlopen(request, timeout=5) as response:
        status = json.load(response)['status']
    print('API readiness: ' + status)
    sys.exit(0 if status == 'ready' else 1)
except Exception:
    print('API readiness: unavailable')
    sys.exit(1)
'@
    & docker @composeArgs exec -T api python -c $probeCode
    if ($LASTEXITCODE -ne 0) { $failed = $true }
}
if ($failed) { exit 1 }
