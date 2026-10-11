# Guest wrinkle analysis — 8 October 2026 (Bangkok)

Deployed the guest analysis flow at https://aphrodize.duckdns.org/capture.

- Home, capture, result/product redirect routes and image-quality recovery are public.
- Image consent remains required; human review and training are separate optional choices.
- Per-request skin and safety answers combine with the browser-owned image, without reading or saving an account profile. The backend verifies ownership with the anonymous bearer token, and the frontend requires its signed latest-analysis cookie.
- Existing image eligibility, age/sensitivity/allergy/irritation screening and reviewed-catalog filters remain in force. Account health data remains protected.

Validation: frontend image passed lint, TypeScript, 27 focused tests and production build. Backend source tests passed 29 cases. The exact API candidate passed checks for eligible image rules, transient answers, ownership rejection, safety screening and pending analysis. Both deployed services are healthy; HTTPS guest pages and result/product redirect paths passed.

Release uses the previously running images plus only the required guest-flow files. API additions include the transient-profile schema and reviewed-catalog helper absent in the deployed baseline. Existing runtime settings and other deployed changes were preserved. Previous image overrides and deployment records are retained under `.releases/guest-analysis-20261008/` for rollback.

Live API image: `sha256:3aefefabf99a1097524103c3ce6f8a2adbfdb4edc0e7b734749677eac5392ee6`.
Live frontend image: `sha256:8874570f0ca4e845799913c45e814df64dd93f826efb1f0d2493e3bf7d223c54`.

Live end-to-end evidence is recorded in `guest-analysis-2026-10-08-http.json`. The test uses only the project demo face image, without registering an account or granting annotation/training consent; no tokens, cookies or photos are written to the report.

Live HTTPS checks additionally confirmed reviewed products from transient answers without an account cookie. The POST origin check now uses the incoming Host and protocol, matching image upload validation behind the reverse proxy.

The live demo upload was accepted anonymously and entered `running`, but completion was not confirmed within 180 seconds. The inference worker heartbeat was healthy with 39 queue entries. Consequently, the live image-to-products check remains unverified; its rules and ownership behavior passed in the exact candidate image. Analysis consent for the demo session was withdrawn successfully (204); annotation and training were never granted. This release does not alter the inference worker or queue.
