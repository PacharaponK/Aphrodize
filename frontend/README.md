# Aphrodize frontend

Next.js 16 App Router / React 19 web client. Accounts, capture/results, Daily Health, and recommendations connect to FastAPI through server routes. No sample-product fallback is used for connected recommendation flows.

## Local setup

Use Node.js 24 and pnpm 11.19.0 (pinned in [package.json](package.json)). First start the backend from the [root guide](../README.md). Capture additionally requires the `ai` Compose profile and verified runtime weights.

Run these commands from `frontend/`:

```powershell
npm install --global pnpm@11.19.0 --ignore-scripts
pnpm install --frozen-lockfile
```

Create `.env.local` in this directory with server-only settings. Replace every placeholder:

```dotenv
BACKEND_API_URL=http://127.0.0.1:8000
BACKEND_API_USERNAME=aphrodize
BACKEND_API_PASSWORD=<API_PASSWORD from root .env>
ANALYSIS_SESSION_SECRET=<random secret generated below>
# Optional: enable administration using the same values as root .env.
ADMIN_USERNAME=<root ADMIN_USERNAME>
ADMIN_PASSWORD=<root ADMIN_PASSWORD, at least 8 characters>
# Optional public origin for canonical/Open Graph URLs.
SITE_URL=http://localhost:3000
```

Generate a session secret with:

```powershell
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"
```

Keep credentials in server-only variables; never add `NEXT_PUBLIC_` to them or commit `.env.local`. `BACKEND_API_URL` is the origin without `/api/v1`. For host development it is `127.0.0.1:8000`; inside the VM Compose network it is `http://api:8000`. Omit admin variables when administration is not needed. Model review requires admin credentials different from service credentials.

```powershell
pnpm dev
```

Open <http://localhost:3000>. Restart the dev server after configuration changes. For a production build:

```powershell
pnpm build
pnpm start
```

Set `SITE_URL` to the deployed public origin before building for deployment. When unset, canonical/Open Graph URLs are omitted. The VM Compose build supplies it automatically.

## Pages and dependencies

| Route | Purpose / dependency |
| --- | --- |
| `/` | Dashboard and Daily Health; saving records requires an account session |
| `/login`, `/signup` | Account access |
| `/capture` | Explicit consent, quality gate, queued image analysis; requires AI services |
| `/quality-rejected`, `/result-detail` | Capture rejection and analysis results |
| `/recommendation` | Reviewed catalog recommendations and city UV guidance |
| `/uv-map` | Thailand UV map; requires generated map snapshots |
| `/admin` | Product administration and model operations; requires configured admin credentials |
| `/portal` | Direct-access links to deployed tools; each tool keeps its own login |
| `/showcase` | UI reference page |

`/trend` and `/profile` currently redirect to the dashboard. The portal uses deployed proxy paths; it does not check service health. Optional server-only `PORTAL_MINIO_URL` and `PORTAL_MLFLOW_URL` enable those links. See [portal deployment](../docs/services-portal.md).

Load the local demo account and reviewed catalog using the [root fixture commands](../README.md). Named products need eligible reviewed records, verified photos/purchase links, and applicable consent/release checks. Budget filtering is per product and requires a sourced price checked within 30 days. Allergy history can withhold named products. Dated prices are not live quotes.

Guests can request profile-based recommendations by explicitly submitting the
guest questionnaire. This does not grant access to another user's analysis or
save an account profile. Account-owned records still require a verified session.

UV city forecasts and province maps have separate snapshot preparation requirements; see [city UV operations](../docs/uv-implementation.md) and the [map guide](../docs/uv-thailand-map.md). `UvMapExplorer` handles fetching and controls; `ThailandUvMap` renders controlled data. Both are in `src/components/uv/`.

## Checks

From `frontend/`:

```powershell
pnpm lint
pnpm exec tsc --noEmit
node --test tests/*.mjs
pnpm build
```

Private wellness/admin/preview pages use `noindex`; metadata must not contain personal records. Run `node tests/page-metadata.test.mjs` for the focused metadata check.

## Troubleshooting and privacy

- Backend connection errors: verify the root API health URL and `BACKEND_API_URL`. Service credentials must match root `.env`.
- Capture errors: confirm `ANALYSIS_SESSION_SECRET`, the AI profile, model files, and worker logs. Unreleased scores can be withheld even after segmentation succeeds.
- Admin unavailable: configure matching admin values in both environments, then recreate the API container and restart the frontend.
- Missing UV: generate valid snapshots; an empty/unavailable state is expected without them.

Users consent before upload. Original photos are removed after processing, with private mask/overlay cleanup scheduled after 24 hours. Analysis, annotation, and training consent remain separate. Results are experimental. Read [DESIGN.md](DESIGN.md) for implementation guidance and [design references](design/README.md) for historical wireframes.
