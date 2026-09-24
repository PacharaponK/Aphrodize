# Aphrodize frontend

Next.js App Router workspace for the skin-tracking UI. The `/capture` and
`/result-detail` routes connect to the local API; other prototype pages still
show sample content.

```powershell
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000`. The dashboard is at `/`; the other routes are `/login`, `/capture`, `/quality-rejected`, `/result-detail`, `/trend`, `/recommendation`, `/profile`, and `/showcase`.

Start the root Compose stack first (`docker compose up -d --build`). Create
`frontend/.env.local` with server-only values matching the root `.env`:

```dotenv
BACKEND_API_URL=http://127.0.0.1:8000
BACKEND_API_USERNAME=aphrodize
BACKEND_API_PASSWORD=<API_PASSWORD from root .env>
ANALYSIS_SESSION_SECRET=<random secret of at least 32 bytes>
```

The Next.js server sends backend credentials; they are never exposed to the
browser. Users consent before upload. The original photo is removed after
processing, and private mask/overlay images are scheduled for removal after
24 hours. Results are experimental, not clinically validated. Design
references are in `design/`.
