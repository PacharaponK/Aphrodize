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

This is local log collection only. It does not deploy an observability platform or send logs to any external service.
