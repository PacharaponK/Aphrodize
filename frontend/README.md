# Aphrodize frontend

Next.js App Router workspace for the skin-tracking UI. Capture, analysis results,
daily health, and product recommendations connect to the backend API.
Recommendations use the signed-in user's profile and reviewed database catalog;
there is no frontend demo response or sample-product fallback.

```powershell
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000`. The dashboard is at `/`; the other visible routes are `/login`, `/capture`, `/quality-rejected`, `/result-detail`, `/recommendation`, and `/showcase`. `/trend` and `/profile` redirect to the dashboard while those views are hidden.

Start the root Compose stack first (`docker compose up -d --build`). Create
`frontend/.env.local` with server-only values matching the root `.env`:

```dotenv
BACKEND_API_URL=http://127.0.0.1:8000
BACKEND_API_USERNAME=aphrodize
BACKEND_API_PASSWORD=<API_PASSWORD from root .env>
ANALYSIS_SESSION_SECRET=<random secret of at least 32 bytes>
ADMIN_USERNAME=<same ADMIN_USERNAME as root .env>
ADMIN_PASSWORD=<same ADMIN_PASSWORD as root .env, at least 8 characters>
```

The Next.js server sends backend credentials; they are never exposed to the
browser. Users consent before upload. The original photo is removed after
processing, and private mask/overlay images are scheduled for removal after
24 hours. Results are experimental, not clinically validated. Design
references are in `design/`.

The admin product catalog is at `/admin/products`. Set `ADMIN_USERNAME` and
`ADMIN_PASSWORD` in both root `.env` and `frontend/.env.local` to enable it.
Catalog edits stay separate from user profiles and recommendations.
