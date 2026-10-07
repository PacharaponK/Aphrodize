# Aphrodize frontend

Next.js App Router workspace for the skin-tracking UI. Capture, analysis results,
daily health, and product recommendations connect to the backend API.
Recommendations use the signed-in user's profile and reviewed database catalog;
there is no frontend demo response or sample-product fallback.
Product cards render real catalog photos, reference THB prices, and direct retailer
purchase links from the API. The current Thai shopping snapshot covers eight exact
Watsons variants; Shopee links may be added through the reviewed admin catalog when
the exact listing is verified. Budget filtering applies per product and requires a
sourced price checked within 30 days. Reported allergies still withhold named products.

```powershell
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000`. The dashboard is at `/`; the other visible routes are `/login`, `/capture`, `/quality-rejected`, `/result-detail`, `/recommendation`, and `/showcase`. `/trend` and `/profile` redirect to the dashboard while those views are hidden.

The service portal is at `/portal`, accessible by direct URL without a navbar link.
It links to the application, product administration, FastAPI Docs, Label Studio,
MLflow and MinIO Console. External links use the local Compose ports and open in
new tabs; they work on the computer running Docker. Start the relevant services
first (`docker compose --profile ai up -d --build`); each tool keeps its own login.
The portal is a directory and does not check service health.

Every page has a dedicated title, description, Open Graph and Twitter summary.
Metadata follows the default rendered language (English, or Thai for Thai-only pages).
Personal wellness pages, admin tools and UI previews use `noindex`; sign-in,
sign-up and the UV map are indexable. Metadata never includes personal records.
Set the server-only `SITE_URL` to your deployed public origin (for example,
`https://your-domain.example`) to enable canonical and Open Graph URLs.
When it is unset, these URLs are omitted instead of pointing to localhost.
After changing `SITE_URL`, rebuild the frontend. Check metadata with
`node tests/page-metadata.test.mjs`.

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

The admin product catalog is at `/admin`. Set `ADMIN_USERNAME` and
`ADMIN_PASSWORD` in both root `.env` and `frontend/.env.local` to enable it.
Catalog edits stay separate from user profiles and recommendations.

Thailand's clear-sky UV map is at `/uv-map`, linked from the dashboard UV section.
`UvMapExplorer` provides fetching, date selection and province details;
`ThailandUvMap` accepts province data and controlled selection props without fetching.
Both live in `src/components/uv/`. See [the map guide](../docs/uv-thailand-map.md)
for refresh setup, data sources, reuse examples and map-data licences.
