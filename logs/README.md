# Local service logs

This directory contains local snapshots of the Docker Compose logs for every Aphrodize service. Log output stays local and is ignored by Git.

## Export a snapshot

From the repository root in PowerShell:

```powershell
.\scripts\export-logs.ps1
```

The command writes a timestamped `docker-compose-*.log` file and replaces `latest.log`. By default it exports the latest 500 lines from every service. Use `-Tail 2000` for more lines.

## Follow all services live

```powershell
.\scripts\export-logs.ps1 -Follow
```

Press `Ctrl+C` to stop following. This is equivalent to `docker compose logs --follow`, with timestamps and all services included.

## Retention and safety

Docker uses its local log driver with a 10 MB maximum file size and five retained files per container. Do not commit exported logs or add passwords, `.env` values, image payloads, personal data, or access tokens to application log messages.

The export script captures local logs only. The optional [observability stack](../docs/observability.md) collects allowlisted JSON records from instrumented services into Loki and exposes dashboards/Discord alerts.

## Inspect one service or another deployment

Run from the repository root with Docker running:

```powershell
docker compose logs --tail 100 api
docker compose --profile ai logs --tail 100 inference-worker trainer-worker
```

The export script uses the default Compose selection. To inspect a VM or another
configuration, use its documented file/environment selection directly, for example
`docker compose -f compose.vm.yml logs --tail 100 api`. A snapshot contains only
logs still retained by Docker; it cannot recover rotated or deleted records.
Exported snapshots have no automatic retention policy. Remove obsolete local
snapshots deliberately after keeping any needed troubleshooting evidence.
