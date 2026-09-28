# Implementation Plan: Tune GRU Activations and Losses

## Status

Approved by the user on 2026-09-28. Sandbox implementation and local verification are complete; production artifacts remain unchanged. The formal Review plugin workflow is still unavailable because the repository review issue-tracker setup is missing.

## Overview

Run a controlled, sandbox-only comparison of the current daily-health GRU's classification-head activation and binary loss options. The goal is to improve validation ranking and minority-class behavior without changing generated labels, altering the source dataset, touching production artifacts, or using the previously reported test users for candidate selection.

## Current Evidence

- `sandboxes/model/wellness_torch.py` uses `nn.GRU`, whose recurrent gates already use sigmoid/tanh internally, followed by a linear readout that emits logits.
- `sandboxes/model/train_wellness_torch_optuna.py` uses `BCEWithLogitsLoss` with a training-label-derived positive weight; inference applies sigmoid to logits to obtain probabilities. This is a numerically sound baseline. Do not add sigmoid before `BCEWithLogitsLoss`.
- The latest group-held-out run used 20 synthetic users. The 14 real tracker rows from one person were excluded because the real skin-dryness scale is unconfirmed. The CSV has no age field.
- The four-user test group and its results were already viewed in the prior experiment. Treat it as an exposed historical holdout; do not use it to choose activations, losses, thresholds, or checkpoints in this update.
- The synthetic dryness target is autoregressive and independent of sleep, water, thirst, and outdoor time. This optimization cannot establish a lifestyle-to-skin effect or real-population accuracy.

## Decisions

1. Keep the current GRU cell and its sigmoid/tanh gates fixed. Compare only a configurable readout-head activation: `identity` (current baseline), `ReLU`, `tanh`, and `GELU`.
2. Compare three logits-based binary losses: unweighted `BCEWithLogitsLoss`, training-only class-weighted `BCEWithLogitsLoss`, and focal loss computed directly from logits. Derive any class weights/positive fractions from each fold's training labels only.
3. Keep the output as raw logits during training. Convert with sigmoid only for metrics/predictions. Persist the selected activation/loss in the checkpoint config so prediction reconstructs the identical network.
4. Hold out the four previously exposed test users completely. Compare candidates on grouped cross-validation across the other 16 synthetic users (four user folds, two fixed random seeds); no rows from one user may cross a fold boundary.
5. Select with mean validation PR-AUC because dryness positives are rare; report fold-level accuracy, majority baseline, balanced accuracy, precision, recall, F1, and Brier score. Do not optimize raw accuracy alone. Do not claim these results represent standard adults or medical outcomes.
6. Keep all code, checkpoints, TensorBoard logs, and reports under `sandboxes/model/`; leave the CSV, app, and `models/time-series/` production artifacts unchanged.

## Task List

### Phase 1: Regression Tests and Model/Loss Interfaces

#### Task 1: Specify activation and logits-loss behavior with tests

**Description:** Add focused tests for the baseline identity head, each supported activation, raw-logit output shape, stable BCE/focal loss values and gradients, and backward-compatible loading of existing configs.

**Acceptance criteria:**
- [ ] Every supported activation builds and produces one finite logit per sequence.
- [ ] BCE and focal loss accept raw logits, remain finite for extreme logits, and produce finite gradients.
- [ ] An old config without an activation/loss field still reconstructs the existing identity-head GRU.
- [ ] Tests do not rely on production data or modify model artifacts.

**Verification:** Run the sandbox's focused `unittest` command and demonstrate that a test for the invalid sigmoid-before-logits-loss path would fail.

**Dependencies:** None.

**Files likely touched:** `sandboxes/model/wellness_torch.py`, a focused sandbox loss module if needed, and a sandbox test file.

**Estimated scope:** Medium.

#### Task 2: Add configurable activation and focal-loss support

**Description:** Extend the sandbox GRU readout with the activation choices above and add a small loss factory for unweighted BCE, training-only weighted BCE, and focal loss. Keep the model output contract as logits.

**Acceptance criteria:**
- [ ] Activation and loss are explicit config values and are serialized with the candidate.
- [ ] `BCEWithLogitsLoss` receives logits directly; no sigmoid is inserted into `forward`.
- [ ] Class weight/focal alpha are calculated from each fold's training labels only.
- [ ] Existing saved GRU configs continue to use the current identity-head behavior.

**Verification:** Focused unit tests pass; a fixed small synthetic batch shows finite loss/gradients for each option.

**Dependencies:** Task 1.

**Files likely touched:** `sandboxes/model/wellness_torch.py`, `sandboxes/model/tune_activation_loss_groupcv.py`, and optionally `sandboxes/model/losses.py`.

**Estimated scope:** Medium.

### Checkpoint: Model Contract

- [ ] Focused tests pass.
- [ ] Existing model config still loads without schema migration.
- [ ] No production or dataset file changed.

### Phase 2: Group-CV Optimization

#### Task 3: Compare activation/loss variants on fixed group folds

**Description:** Add a deterministic experiment over the 16 development users: four user-disjoint folds, two fixed seeds, identical training budgets and preprocessing fit only inside each fold's training users. Use the same features/labels and target definitions as the current sandbox.

**Acceptance criteria:**
- [ ] Prior test users are excluded from every fold and all model-selection computations.
- [ ] Fold assignments, dataset SHA-256, target prevalence, and selected config are recorded.
- [ ] Every activation/loss combination is evaluated for both targets using the same fold/seed plan.
- [ ] PR-AUC is the primary selection metric; threshold/accuracy metrics are secondary and compared with a training-majority baseline.
- [ ] Training, validation loss, validation metrics, and fold/variant identifiers are logged to TensorBoard.
- [ ] No synthetic labels or raw tracker rows are rewritten.

**Verification:** Run the deterministic group-disjointness test and the full experiment; inspect fold-level metrics and ensure the exposed test group is absent from run files.

**Dependencies:** Task 2.

**Files likely touched:** `sandboxes/model/tune_activation_loss_groupcv.py`, `sandboxes/model/output/`, and the sandbox README.

**Estimated scope:** Medium.

#### Task 4: Select and document a sandbox candidate

**Description:** Select the activation/loss by mean cross-validated PR-AUC, with balanced accuracy/F1/Brier and parameter count as tie-breakers. Train a candidate using development users only and save config, weights, fold metrics, feature-ablation explanation, and a limitations report.

**Acceptance criteria:**
- [ ] Selection uses only cross-validation results from development users.
- [ ] No metric is described as clinical, causal, or verified on standard people.
- [ ] Report explicitly states that the prior test was already exposed and is not a fresh final evaluation.
- [ ] Current best run and production artifacts remain intact.

**Verification:** Check checkpoint/config round-trip, inspect TensorBoard, and execute the updated sandbox QA notebook top-to-bottom.

**Dependencies:** Task 3.

**Files likely touched:** `sandboxes/model/output/`, `sandboxes/model/README.md`, and `sandboxes/eda/output/general_user_tuning_quality.ipynb`.

**Estimated scope:** Small.

### Checkpoint: Candidate Ready for Review

- [ ] Unit tests, grouped-CV checks, and notebook execute without errors.
- [ ] Candidate selection does not use the exposed test users.
- [ ] Review findings are recorded; no production promotion is implied.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Only 16 development synthetic users remain after excluding the previously exposed test users | Cross-validation estimates will be noisy | Report per-fold and per-seed spread; use no general-population accuracy claim |
| Focal loss may improve recall while degrading probability calibration | Risk scores could be overconfident | Track Brier score and precision/recall alongside PR-AUC; retain weighted BCE if focal does not clearly improve CV |
| Adding a head activation increases capacity | Overfitting small data | Keep the GRU cell fixed, use early stopping and identical folds; prefer identity on ties |
| Synthetic dryness is driven by prior dryness by construction | Cannot validate sleep/water effects on skin | Keep this experiment limited to proxy forecasting; require prospective real skin labels for that claim |
| The project has no `docs/agents/issue-tracker.md` review setup | The Review plugin's prescribed two-axis review cannot run as configured | Complete local tests/review; initialize the repository review setup before claiming the formal plugin review is complete |

## Open Questions

- This work is scoped to `sandboxes/model/` and will not replace the current production model.
- The Review base is the existing sandbox files before this update, as confirmed by the user. Those files are git-ignored, so the comparison will use a recorded file snapshot rather than a Git ref.
