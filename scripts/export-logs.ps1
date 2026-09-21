<#!
.SYNOPSIS
Exports local Docker Compose logs from every Aphrodize service.

.DESCRIPTION
Writes a timestamped, Git-ignored snapshot to logs/. Use -Follow for a live,
all-service stream instead of creating a snapshot.
#>

[CmdletBinding()]
param(
    [ValidateRange(1, 100000)]
    [int]$Tail = 500,
    [switch]$Follow
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$logDirectory = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

if ($Follow) {
    docker compose logs --follow --timestamps --tail $Tail
    exit $LASTEXITCODE
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$snapshot = Join-Path $logDirectory "docker-compose-$timestamp.log"
$latest = Join-Path $logDirectory 'latest.log'
$output = docker compose logs --no-color --timestamps --tail $Tail 2>&1

if ($LASTEXITCODE -ne 0) {
    throw ($output -join [Environment]::NewLine)
}

$output | Set-Content -Path $snapshot -Encoding utf8
Copy-Item -Path $snapshot -Destination $latest -Force
Write-Host "Saved all-service log snapshot: $snapshot"
