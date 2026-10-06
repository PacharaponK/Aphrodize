# Observed-outcome forecasts and acne design

## Shipped connection

- Thirst and energy cards display numeric **experimental perceived-outcome estimates** only from a manually approved, intact candidate trained on opted-in real self-reports. Include D+1, model ID and method. Never turn the estimate into unvalidated low/moderate/high clinical categories.
- The current-day, weight-based hydration formula remains a separate calculated metric. It is not the model's thirst output and cannot populate the next-day thirst card.
- New inference results carry a two-hour signed receipt bound to the input day, sleep minutes, water and outdoor choice. Storage verifies the receipt rather than trusting submitted forecast numbers. Verified next-day outputs are kept separately in `daily_health_entries.next_day_forecasts`; historical rows are not recomputed or relabeled. Outcomes remain separate training labels.
- If no real candidate is deployed, show `model_not_ready`, not a claim that this account's history was checked. Acne cards, collection UI and forecast pipeline have been removed; the acne sections below are archived design proposals, not current features. OOD inference abstains from next-day forecasts, including test-only OOD mode.

## Energy pipeline

- Support two-target thirst/dryness and extended `[reported_thirst_level_0_10, reported_dryness_level_0_10, reported_energy_level_0_10]` candidates. The complete cohort must independently reach 100 matched days from five actively consenting users. Missing energy is excluded, never inferred; zero is valid. Older artifacts without the safety-policy and consent-version manifest markers must be rebuilt before promotion or serving.
- Pair only the same user's `user_reported` lifestyle inputs on D with observed outcomes on D+1. Imported fixtures, synthetic rows and prior predictions are excluded. Energy direction is **higher means more perceived energy**, not a low-energy risk score.
- A candidate remains review-only. Retain participant-disjoint validation/test; additionally fit a separate chronological evaluation model using dates strictly before the last 20% of distinct dates. Mean baselines use training labels only. Publish per-target MAE/RMSE/R², participant test mean baseline, temporal test and temporal mean baseline. These are two separate evaluation views, not a claim of a joint participant/time split.
- Every target, including thirst and dryness in two-target candidates, requires finite, nonnegative MAE strictly better than its mean baseline in both participant and chronological holdouts, plus explicit administrator review. Missing, equal, invalid or worse metrics block promotion. If temporal coverage is insufficient, promotion is blocked. This engineering gate is not clinical validation.
- Consent withdrawal during training invalidates the snapshot; existing candidate/deployment revocation logic remains in force. Never auto-promote a candidate or manufacture labels to meet the cohort threshold.

## Input availability and training consent

- Both `created_at` and `updated_at` must be timezone-aware, ordered, and strictly before midnight at the start of target day D+1 in `Asia/Bangkok`. Late corrections, backfills and missing or naive timestamps are excluded from training. Records remain stored unchanged; there are no historical feature snapshots from which to reconstruct pre-edit values.
- Refresh database rows when checking the consent-filtered training snapshot. Fingerprints and candidate manifests include `created-and-updated-before-target-bangkok-day-v1`, preventing reuse of a pre-policy snapshot as a safe candidate.
- Legacy `daily-health-model-training-v1` permits thirst/dryness only. Expanded `daily-health-model-training-v2` explicitly covers recorded history and self-reported thirst, dryness and energy for shared next-day models across accounts. Energy training requires active v2 consent; v1 is never silently upgraded.
- The current form offers an unchecked v2 opt-in to users with only v1 consent and retains withdrawal controls. Legacy API clients default to v1; unknown versions are rejected. Withdrawal revokes both scopes without deleting daily-health history.
- These guards address mutable input availability, not immutable historical versions of outcome labels, and do not constitute clinical validation or automatically enable a deployed model.

## Acne: proposed collection form, not yet implemented

The requested acne work is a design specification. Do not collect new acne data or display a forecast until the protocol and separate consent are approved.

Proposed optional **Observed breakouts** form:

1. Observation date (today or past only, user's local day).
2. “Did you notice new pimples today?”: Yes / No / Not sure. Missing or Not sure is unknown, not No.
3. Optional number of newly noticed lesions, only when Yes; the pilot must define counting instructions and validation limits before shipping. Do not treat the count as a medical severity scale.
4. Optional affected regions selected by the user. Do not infer acne from the wrinkle model, landmarks, skin-type answers or hydration formula.
5. Optional recent skincare/medication change, with explicit purpose and minimization; do not require names or free-text sensitive details in the initial pilot.
6. A separate acne-tracking storage opt-in; shared model-training consent remains independent and off by default. Users can skip, correct and delete reports. Do not use analysis/annotation consent as acne consent.

Store dated self-reports in a separate, versioned outcome schema with provenance and consent version. Never modify existing daily-health or wrinkle predictions into acne labels. Show recorded observations distinctly from predictions.

## Acne model: proposed pilot

- Candidate target: **any user-reported new breakout in D+1 through D+7**, not a diagnosis or inferred severity. Seven days with explicit observations are needed to classify a negative window; absent reports make the label unknown. A confirmed positive observation can establish a positive label only under the finalized protocol.
- Candidate features: consented baseline acne reports and recorded lifestyle history available by D. Do not assert sleep or water causally determines acne. Additional skincare or medication features require separate approved collection and purpose.
- Start with a transparent prevalence/last-observation baseline and regularized classifier. Class imbalance, cohort size, minimum positive/negative labels and participant coverage must be assessed from a real pilot before setting a defensible release threshold; the energy cohort floor must not be copied as evidence of acne adequacy.
- Hold out users and future time periods; embargo at least the seven-day target horizon so overlapping windows cannot leak labels. Do not choose thresholds on the test set.
- Report PR-AUC, ROC-AUC, Brier score, calibration, missing-label coverage and participant-level bootstrap uncertainty. Evaluate cold-start and known-history users separately. Open only after improvement versus baselines, calibration review, appropriate consent and explicit approval; until then show `not_supported` or an honest pilot status without probabilities.
- Form usability checks: users can distinguish “new today” from existing lesions; skipping and uncertainty do not silently create negatives; keyboard/mobile and Thai/English support; no photos required and no clinical claims.

## Acceptance checks

Real three-target test output must display thirst and energy, preserve target date/model provenance, and remain independent of the hydration formula. Two-target candidates display thirst without inventing energy. Synthetic, OOD, tampered or input-mismatched receipts must not produce saved next-day signals. Historical records keep original values. No automatic promotion or new acne data collection is part of this change.
