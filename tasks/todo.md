# Activation/Loss Tuning Checklist

Approved on 2026-09-28. Sandbox work is complete; formal Review plugin setup remains blocked as noted below.

## Phase 1 — Regression tests and model/loss interfaces

- [x] Test identity, ReLU, tanh, and GELU readout activations.
- [x] Test unbounded logits output shape, finite BCE/focal loss, and finite gradients, including extreme logits.
- [x] Test that legacy configs still load as the identity-head model.
- [x] Add configurable activation and logits-based loss options without changing production artifacts.
- [x] Run focused sandbox tests and confirm no sigmoid is applied before `BCEWithLogitsLoss`.

## Phase 2 — Grouped tuning

- [x] Snapshot the pre-update ignored sandbox files as the review baseline under `sandboxes/model/output/activation_loss_preupdate_20260928/`.
- [x] Verify and freeze the previously exposed four-user test group; exclude it from all tuning and candidate selection.
- [x] Add deterministic four-fold user-group cross-validation over the remaining development users, using two fixed seeds.
- [x] Compare every activation/loss combination with fold-local preprocessing and training-only class weighting.
- [x] Log train/validation loss and validation metrics to TensorBoard; record dataset hash, fold assignments, and target prevalence.
- [x] Select candidates by mean validation PR-AUC, using balanced accuracy, F1, Brier score, and parameter count as secondary considerations.
- [x] Train and save the chosen sandbox candidates using development users only.
- [x] Run focused tests, grouped-split checks, checkpoint/config round-trip, predictor smoke test, and the executed QA notebook.
- [x] Document results, per-fold variability, synthetic-label limitations, and the exposed historical holdout.

## Review gate

- [x] Compare changed sandbox code and configuration against the recorded pre-update snapshot; confirm prior training/prediction scripts are unchanged.
- [x] Resolve the smoke-test, candidate-selection, artifact-naming, and report-metadata issues found during local review.
- [ ] Complete the formal Review plugin's two-axis review; blocked because `docs/agents/issue-tracker.md` is not present. No review setup files were created without approval.
- [x] Do not imply production promotion or clinical validation.
