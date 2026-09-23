# Aphrodize client

The Aphrodize client is a Next.js App Router application using Tailwind CSS and shadcn/ui. It is deliberately independent from the Docker Compose services so interface development can run with fast refresh.

## Requirements

- Node.js 20.9 or later
- pnpm 11 (the version is pinned in `package.json`)

## Run the client

From this directory:

```powershell
Copy-Item .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). The client assumes the backend is available at `http://localhost:8000`; change `NEXT_PUBLIC_API_BASE_URL` in `.env.local` when needed. Values beginning with `NEXT_PUBLIC_` are visible to the browser, so do not place credentials or private API keys in this file.

To build and run the production client locally:

```powershell
pnpm build
pnpm start
```

## UI foundation

- Next.js App Router and TypeScript
- Tailwind CSS 4
- shadcn/ui with the `base-nova` preset
- shadcn configuration: `components.json`
- First generated shadcn component: `src/components/ui/button.tsx`

Add further components with the local CLI:

```powershell
.\node_modules\.bin\shadcn.cmd add card dialog input
```

Run client linting with `pnpm lint`.
