<#!
.SYNOPSIS
Checks Aphrodize containers and their local HTTP/service readiness.

.DESCRIPTION
Runs locally from the repository root. It prints a compact table and exits with
code 1 when a required check fails. No credentials are written to the console.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$failed = $false
$results = [System.Collections.Generic.List[object]]::new()

function Add-Result {
    param([string]$Service, [string]$Status, [string]$Detail)
    $results.Add([PSCustomObject]@{ Service = $Service; Status = $Status; Detail = $Detail })
    if ($Status -ne 'ok') { $script:failed = $true }
}

function Test-HttpEndpoint {
    param([string]$Service, [string]$Uri)
    try {
        $response = Invoke-WebRequest -Uri $Uri -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
            Add-Result $Service 'ok' "HTTP $($response.StatusCode)"
        } else {
            Add-Result $Service 'failed' "HTTP $($response.StatusCode)"
        }
    } catch {
        Add-Result $Service 'failed' $_.Exception.Message
    }
}

$expectedServices = @('postgres', 'redis', 'minio', 'minio-init', 'label-studio', 'mlflow', 'api', 'inference-worker', 'trainer-worker')
$seenServices = @{}
foreach ($line in (docker compose ps --all --format json)) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $container = $line | ConvertFrom-Json
    $seenServices[$container.Service] = $container
}

foreach ($service in $expectedServices) {
    if (-not $seenServices.ContainsKey($service)) {
        Add-Result $service 'failed' 'container not created'
        continue
    }
    $container = $seenServices[$service]
    if ($service -eq 'minio-init') {
        if ($container.State -eq 'exited' -and $container.ExitCode -eq 0) {
            Add-Result $service 'ok' 'bucket initialization completed'
        } else {
            Add-Result $service 'failed' "state: $($container.State); exit: $($container.ExitCode)"
        }
    } elseif ($container.State -eq 'running') {
        $healthDetail = $container.Health
        if ([string]::IsNullOrWhiteSpace($healthDetail)) {
            $healthDetail = 'process running'
        }
        if ($healthDetail -eq 'unhealthy') {
            Add-Result $service 'failed' $healthDetail
        } elseif ($healthDetail -eq 'starting') {
            Add-Result $service 'starting' $healthDetail
        } else {
            Add-Result $service 'ok' $healthDetail
        }
    } else {
        Add-Result $service 'failed' "state: $($container.State)"
    }
}

Test-HttpEndpoint 'FastAPI' 'http://localhost:8000/api/v1/health'
Test-HttpEndpoint 'Label Studio' 'http://localhost:8080/user/login/'
Test-HttpEndpoint 'MinIO' 'http://localhost:9000/minio/health/live'
Test-HttpEndpoint 'MLflow' 'http://localhost:5000/health'

try {
    $postgresOutput = docker compose exec -T postgres /bin/sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($postgresOutput -join [Environment]::NewLine)
    }
    Add-Result 'PostgreSQL query' 'ok' 'pg_isready accepted the configured database'
} catch {
    Add-Result 'PostgreSQL query' 'failed' $_.Exception.Message
}

try {
    $redisOutput = docker compose exec -T redis /bin/sh -c 'redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping' 2>&1
    if ($LASTEXITCODE -ne 0 -or ($redisOutput -join [Environment]::NewLine) -notmatch 'PONG') {
        throw ($redisOutput -join [Environment]::NewLine)
    }
    Add-Result 'Redis query' 'ok' 'authenticated PING accepted'
} catch {
    Add-Result 'Redis query' 'failed' $_.Exception.Message
}

$results | Format-Table -AutoSize
if ($failed) { exit 1 }
