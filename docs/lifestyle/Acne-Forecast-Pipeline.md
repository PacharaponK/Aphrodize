# Acne forecasting — removed

Removed at the user's request on 5 October 2026.

- Offline training, readiness service and pilot runner are removed.
- New health predictions omit `acne_flare_signal`; UI ignores that field in historical payloads.
- Dashboard and History unassessed counts exclude acne.
- Observation form and Dashboard history summary are also removed. Existing observations and consent records are not deleted; backend history and cleanup APIs remain.
- New acne training opt-in is unavailable (HTTP 410). Withdrawal of legacy research consent remains available.
- Thirst, energy and personal sleep/water forecasting are unchanged.
