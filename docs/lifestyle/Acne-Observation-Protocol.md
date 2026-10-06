# Acne observation protocol v1

Local-development collection protocol confirmed by user on 5 October 2026.

- Date is the observation day in Asia/Bangkok; no future observations. Each owner has at most one report per date, updated on correction.
- Question: “Did you notice new pimples that day?” / “วันนี้สังเกตเห็นสิวใหม่หรือไม่?” Existing lesions are not new lesions. Yes, No and Not sure are explicit choices. Skipping creates no observation, never a negative.
- Optional regions for Yes: forehead, left cheek, right cheek (person's own left/right), nose and chin. No counts, photos, medications or free-text fields.
- Separate `acne-tracking-v1` storage opt-in defaults off per account. Store only for observed history, not training. Image-analysis, annotation, daily-health and shared-training consents do not authorize acne storage.
- Retain reports until owner deletes them, withdraws this consent or account deletion cascades. Withdrawal revokes only acne consent and deletes only acne observations in the same transaction. Regrant does not restore erased observations. No acne datasets/candidates exist in this phase.
- Existing image-deletion consent revocation excludes the new acne scope so removing images does not silently withdraw acne consent without its separate purge workflow.
- Collection is deployment-gated by `ACNE_TRACKING_ENABLED` (default false). Enabled locally after user's confirmation; users still must actively grant acne consent themselves. Disabling collection does not disable deletion/withdrawal endpoints.
- API `/api/v1/acne/users/{user_id}` is bearer-authenticated and owner-matched. GET returns enabled/consent state and latest 30 reports (bounded limit 1–90). PUT `/consent` explicitly grants; DELETE `/consent` withdraws and purges. PUT `/observations` saves/corrects; DELETE `/observations/{date}` deletes one.
- Frontend uses server-only `/api/acne` proxy, signed account session, mutation origin checks and no-store responses. No private account identifiers or model probabilities displayed in observation responses.
- New `acne_observations` table is created through the repository's existing `Base.metadata.create_all` startup schema mechanism. No legacy rows are rewritten; no destructive migration is run.
- `/clients` contains optional bilingual record/history/edit/delete controls. Dashboard includes a quiet self-reported observation when active and available. Acne forecast signal remains `not_supported`, not an inferred risk grade.
- Before production rollout: review retention/deletion policy against backup behavior, exact consent wording, user comprehension and deployment approval. Phase 2 dataset, forecasting, cohort thresholds and model promotion require separate approval and are not enabled.
