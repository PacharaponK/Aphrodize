<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Frontend workspace

- This directory is a Next.js 16 App Router and React 19 app. Work from `frontend/`; use `pnpm` and the existing lockfile.
- Put pages and layouts in `src/app/`, browser-facing components in `src/components/`, shared helpers in `src/lib/`, and server endpoints in `src/app/api/`. Check nearby code before adding a new helper or component.
- For UI changes, read `DESIGN.md` first and follow its color, typography, spacing, component, and responsive guidelines. Reuse the existing styles in `src/app/` and `src/components/ui/` where appropriate. Keep forms and controls accessible, including labels, keyboard use, and visible focus.
- Keep backend credentials and session secrets in server-only environment variables and route handlers. Never expose them through `NEXT_PUBLIC_*`, browser code, or logs. Preserve origin checks, signed/HttpOnly cookies, and `no-store` behavior for private data.
- Image analysis requires explicit consent; annotation and model-training consent are separate choices. Treat results as experimental, not medical advice. Do not replace private API data with prototype sample data in connected flows.
- Run `pnpm lint` and `pnpm exec tsc --noEmit` for frontend changes; run `pnpm build` when changing routing, server behavior, or production configuration.
- See `README.md` for local environment setup. The generated Next.js rule block above must remain intact.
