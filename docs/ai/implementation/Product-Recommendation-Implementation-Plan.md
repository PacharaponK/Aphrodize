# Product recommendation implementation plan

Status: planning document. Reviewed against the working tree on 2026-09-29 (Asia/Bangkok). “Done” below means code exists in this working tree; it does **not** mean it has passed PostgreSQL, HTTP, browser, clinical, or production-release verification.

## Goal and scope

Return deterministic, traceable product-category guidance for the account owner from their questionnaire and consent-authorized Daily Health reports. A released wrinkle score may add visual context to a category that is already eligible from a reported input. It must not create a product recommendation by itself or imply diagnosis, cause, treatment indication, or expected benefit.

This scope covers recommendation rules, provenance, questionnaire revisions, ownership, recommendation UI, and verification. It excludes brands, prescriptions, synthetic Daily Health predictions, guest-to-account transfer, new lifestyle-treatment rules, model calibration, and clinical validation. Sleep and water are display-only context, never treatment-effect signals.

## Current baseline: done versus remaining

| Area | Done in the working tree | Remaining before release |
| --- | --- | --- |
| Rules and safety | Safety-first category rules, deterministic item order, rule/knowledge identifiers, moisturizer and sunscreen categories, and mixed questionnaire/Daily Health sunscreen attribution | Harden malformed legacy-value handling and add boundary/contract coverage |
| Wrinkle gate | Only completed, quality-gated, explicitly released, calibrated, versioned scores can enrich an existing moisturizer item; experimental scores are excluded | Test every gate independently with real persisted analysis data; complete model/knowledge approval separately |
| Daily Health | Active `daily-health-v1` consent is checked per request; user-reported entries and reported outcomes are queried separately; selected record and consent metadata are returned | Make calendar/as-of policy explicit, add real database coverage for date/consent/ownership edges, and formalize the API response schema |
| Questionnaire | Initial create, current-revision read, full edit, safety-only edit, append-only history, base-revision checking, and row-locking code exist | Use one stable per-owner concurrency protocol for all writers; add conflict recovery UX and PostgreSQL concurrency tests |
| Ownership | Backend recommendation endpoint verifies bearer owner against the analysis; browser proxy requires account session plus signed current-analysis cookie | Exercise direct/backend/proxy/account-switch/guest behavior over real HTTP and persistence |
| UI | Safety CTA, full-edit CTA, missing-profile fallback, Thai source dates, neutral Daily Health card, outdoor labels, and no-store recommendation fetch exist | Add robust status-specific retry/recovery, verify navigation refresh, accessibility, mobile, and dark-mode behavior in a browser |
| Tests | Pure rules and direct route tests cover mixed sunscreen sources, daily source provenance, same-day tie preference, missing profile, and stale safety revision | Add disposable PostgreSQL integration and browser suites; mocked sessions are not a release gate |

Current rule version: `2026-09-28.1`. Current knowledge-base ID/version: `aphrodize-category-baseline` / `1.0.0`. Version strings do not themselves establish evidence review or release readiness.

## Released wrinkle gating

### Done

`backend/services/analysis_service.py` exposes image context only when all of these are true:

1. analysis status is `completed`;
2. `image_quality_score >= 0.8`;
3. stored `recommendation_gate.eligible` is `true`;
4. `derived_score.regions` exists;
5. calibration status is `calibrated`;
6. prediction and calibration versions are nonempty; and
7. score and ROI versions are nonempty.

When eligible, only left/right periocular numeric regions may enrich an already-created moisturizer item. Image data never triggers a category alone. Withheld or unavailable image context leaves questionnaire/Daily Health rules usable.

### Remaining plan

1. Define a typed image-context response contract that includes analysis ID, model/prediction, calibration, score, and ROI versions, and each selected region/value.
2. Normalize stored values before gating: reject booleans, non-finite values, wrong containers, and out-of-domain region scores rather than relying on Python truthiness or crashing on legacy JSON.
3. Add unit/contract cases for every individual failed gate, exact `0.8`, absent/malformed versions, experimental-only output, unfinished/rejected analysis, and valid reported-input fallback.
4. In a PostgreSQL/HTTP suite, persist analyses representing each gate and assert no unreleased score reaches the recommendation proxy or page.
5. Add a server-side feature flag/configuration gate for the wrinkle image path. It must be evaluated independently of deployed code and model-result fields, default safely to disabled until approved, and return the same non-diagnostic withheld visual-context state when disabled. Do not expose a browser-controlled switch.
6. Treat model release, calibration, feature-flag approval, and clinical knowledge approval as separate release gates; this feature must not promote a score by changing UI or rule code.

## Daily Health provenance and selection

### Done

The recommendation route authenticates and verifies analysis ownership before querying questionnaire or Daily Health data. Daily queries run only with an active consent row for the same owner, version `daily-health-v1`, and `revoked_at IS NULL`.

Eligible entries are `data_source == "user_reported"` and have dates in `[today - 30 days, today]`. The route does not query predictions or synthetic datasets. It independently selects:

- a latest lifestyle entry for sleep, water, and outdoor; and
- a latest non-null dryness candidate from entries and outcomes.

The response retains consent ID/version and returns separate nested records:

- `daily_context.lifestyle`: `source_table`, `record_id`, `observed_date`, sleep minutes, water millilitres, and outdoor choice;
- `daily_context.reported_dryness`: `source_table`, `record_id`, `observed_date`, and selected value.

This prevents an older dryness value from being labelled with a newer lifestyle date. The UI presents each value with its own Thai-formatted date and does not describe sleep or water as a treatment input.

### Explicit tie policy

Within each source table, newest date wins; source rows are ordered by date then ID. Across entry and outcome candidates, the later observed date wins. If both reports have the same date, `daily_health_outcomes` wins over `daily_health_entries`; the source name and UUID are final deterministic keys. This is source precedence, not a comparison of dryness values. A route test supplies conflicting same-day reports and asserts outcome table, UUID, date, and value.

### Remaining plan

1. Replace server-local `date.today()` semantics with an explicit recommendation calendar policy. For this release, define `Asia/Bangkok`, return `as_of_date` and `calendar_timezone`, and test midnight boundaries. Keep source `local_date`/`target_date` as recorded calendar dates rather than timezone-converting them.
2. Formalize separate availability states for dryness and lifestyle. Do not let `no_recent_reported_dryness` imply lifestyle is missing. Distinguish only what an authorized query proves; do not claim “stale” versus “absent” without evidence.
3. Define typed backend schemas for the nested response and per-item source references. Preserve actual selected values as well as IDs because daily rows can be updated in place.
4. Add PostgreSQL tests for revoked consent, re-grant, consent ownership, future rows, day -30/day -31, null newest row with older non-null row, independently selected lifestyle, synthetic entry exclusion, zero values, and same-date source precedence.
5. Add an HTTP/proxy contract test that confirms unconsented data and its record metadata are absent after revocation, including a fresh no-store request.

## Rule decision matrix and provenance

These are current application thresholds, not externally validated clinical cutoffs.

| Order | Current condition | Current result and required provenance |
| --- | --- | --- |
| 1 | Severe irritation, known allergy, high sensitivity, or incomplete/uncertain safety answers | `safety_blocked`; reason precedence is severe irritation, allergy, high sensitivity, then incomplete screening |
| 2 | Sensitivity `low`/`medium`, allergy `no`, and severe irritation `no` | Continue; legacy positive flags remain protective |
| 3 | `skin_type == "dry"` or selected Daily Health dryness `>= 6` | Fragrance-free moisturizer; source is questionnaire skin type or Daily Health dryness, respectively |
| 4 | Sunscreen frequency `never`/`sometimes` and questionnaire outdoor `>= 60` minutes or Daily Health outdoor choice `>= 3` | Broad-spectrum SPF 30+ sunscreen; sunscreen frequency is always questionnaire provenance, and Daily Health provenance is added whenever daily outdoor contributes |
| 5 | Moisturizer exists and image gate is released with eligible periocular regions | Add image source/regions/versions to that moisturizer only |
| 6 | No category after safe screening | `no_recommendation` / `no_supported_rule_inputs` |

Daily outdoor choices currently mean: 1 under one hour; 2 one to under three hours; 3 three to under four hours; 4 four hours or more. The daily threshold `>= 3` and questionnaire threshold `>= 60` minutes are deliberately different current policies. Do not convert ordinal values to invented minute values or claim equivalence. Any harmonization changes the rule version and requires evidence review.

### Remaining plan

1. Normalize every stored signal at the rule boundary. Accept only finite numeric dryness in 0–10, valid outdoor choices 1–4, and permitted questionnaire enum values; reject booleans, arrays, objects, and out-of-range values without making recommendations from them.
2. Extend the response so every emitted item has exact field-level references: source type, source ID, observed/questionnaire date, selected value, and image versions where relevant. The existing `signal_sources` list is helpful but insufficient for audit reproduction.
3. Add boundaries: dryness 5.9/6, questionnaire outdoor 59/60, daily choice 2/3, sunscreen variants, safe/unknown safety values, and malformed JSON inputs.
4. Keep sleep/water context-only in code, copy, documentation, and tests. New lifestyle treatment rules require a separately approved evidence/rule version.

## Questionnaire full edit, safety edit, and concurrency

### Done

Routes currently provide:

- `POST /questionnaires/initial` for initial full questionnaire creation;
- `GET /questionnaires/initial` for the caller’s latest revision ID and answers;
- `PUT /questionnaires/initial` for full revisions; and
- `PUT /questionnaires/initial/safety` for the three safety fields.

The UI reserves `/onboarding/health?edit=1` for safety-only edit and `/onboarding/health?edit=full` for a prefilled full edit. A missing profile falls back to full onboarding. Recommendation safety blocking directs existing profiles to safety edit; `no_recommendation` directs existing profiles to full edit so skin type, sunscreen frequency, and questionnaire outdoor can actually be changed.

PUT requests send a `base_revision_id`. The route reads the latest row using `FOR UPDATE`, checks that ID, then appends a new row. Safety edit merges only safety fields. A direct test covers merge preservation and stale-base 409 behavior.

### Remaining concurrency design

The current lock is not sufficient evidence of no lost updates: two writers can lock/read the same latest historical questionnaire row and then append independently. Implement one concurrency protocol for **all** questionnaire writers:

1. Start a transaction and lock the owner `User` row (`SELECT ... FOR UPDATE`) first.
2. In that same transaction, freshly select latest questionnaire by `created_at DESC, id DESC`.
3. For PUT, compare `base_revision_id`; on mismatch return a recoverable 409 before appending.
4. For POST, check initial-profile absence after the owner lock, then insert exactly once.
5. Append a new revision while holding the owner lock through commit. Ensure its server-owned ordering value sorts after the revision it replaces; use ID only as deterministic legacy tie-breaker.
6. Apply this protocol to user-token routes and service-authenticated `/users/{user_id}` creation, so they cannot race each other.

Add server-owned revision metadata (`schema_version`, `previous_revision_id`, `revision_kind`) or reviewed columns. Never trust these from browser payloads. Legacy rows remain legacy; do not backfill unknown answers to safe values or rewrite history.

### Remaining UX and tests

- Preserve an unsaved full/safety draft after 409, fetch the new revision, show a clear conflict state, and require the user to review/resubmit. Never automatically retry an overwrite.
- Carry a fixed, allow-listed return destination for recommendation-originated initial onboarding; initial creation currently goes to `/` while edits go to `/recommendation`.
- Verify `router.push`, browser back/forward, and route reuse fetch fresh recommendation data rather than retaining stale client state.
- Use two real PostgreSQL sessions with the same base revision: hold writer A’s owner lock, start writer B, commit A, then assert one new row, one 409, correct latest answers, and retained history. Repeat across full/safety and initial/service paths.

## Ownership and guest modes

### Done

The backend recommendation endpoint returns the same 404 for nonexistent and non-owned analyses. The frontend recommendation proxy requires an HttpOnly account session plus a signed current-analysis cookie and forwards only the bearer token to the backend. Success responses are marked private/no-store.

### Remaining plan

1. Add HTTP tests for missing/expired bearer, malformed/expired analysis cookie, different-account cookie, and proxy 401/404/5xx response caching.
2. Verify signed-in capture resolves the authenticated account and cannot silently fall back to guest when the account token expires.
3. Keep guest recommendations unavailable until there is an account-owned analysis. Signing in must not auto-transfer a pre-login guest analysis. Account history and guest migration remain separate work.
4. Ensure all direct routes derive owner from authentication, never a browser-supplied user ID; service routes require Basic credentials and independently verify their path user exists.

## UX states and acceptance behavior

### Done

The recommendation page separates category results, neutral Daily Health context, withheld-image explanation, and warning. Safety-blocked and empty states have targeted edit/onboarding actions. Daily dryness and lifestyle dates are rendered separately; outdoor is displayed as a tracker label rather than raw `3/4`.

### Remaining plan

| State | Required behavior |
| --- | --- |
| Loading | Announce progress and avoid a transient empty result |
| 401 | Offer sign-in based on status/code, not matching translated error text |
| No current or non-owned analysis | Explain the state and offer fresh capture without leaking analysis details |
| Network/5xx | Provide retry, distinguish it from valid no recommendation, and retain useful prior state only when clearly labelled stale |
| Missing questionnaire | Full onboarding, then return to the recommendation context via an allow-listed route |
| Incomplete safety screening | Safety-only edit for existing profile; do not imply it will unlock categories if true exclusions remain |
| Reported exclusion | State the actual reported reason and only offer correction if it was incorrect |
| No supported inputs | Full edit and/or Daily Health action; do not imply another photo will create a recommendation |
| Image withheld | Keep report-based categories visible and show neutral explanation |
| Ready | Show category, rationale, readable exact input sources/dates, knowledge link, and no treatment-effect claim for lifestyle data |

Browser acceptance must cover keyboard navigation, focus visibility, form validation and conflict recovery, mobile wrapping, dark mode, Thai date/unit copy, zero values, and accessibility announcements. Lint/type checks do not replace visual/browser verification.

## Knowledge governance

Current catalog links the American Academy of Dermatology dry-skin and sunscreen-selection pages. This document does not assert that they support every threshold or that they have been freshly reviewed.

Before release, record for each knowledge item: immutable ID/version, title/URL, retrieval/review date, supported category claim, limitations, linked rules, reviewer, and approval status. Keep category-support claims separate from application thresholds and safety exclusions. Do not cite the catalog as evidence for dryness `>= 6`, either outdoor threshold, wrinkle efficacy, causation, or sleep/water treatment effects unless independently supported. Knowledge meaning/reference changes need knowledge-version review; decision changes need a rule-version change. Withhold a rule if its support cannot be established.

## Acceptance criteria and verification plan

| ID | Acceptance criterion | Required verification |
| --- | --- | --- |
| A1 | Non-owner and nonexistent analysis are indistinguishable 404; missing/expired bearer is 401; no data leaks | Real HTTP + PostgreSQL |
| A2 | Revoked/missing daily consent causes no daily query/value/provenance; re-grant permits eligible retained reports only for that owner | PostgreSQL integration with query observation |
| A3 | Today and day -30 included; day -31 and future excluded; Bangkok midnight behavior is stable | Clock-controlled PostgreSQL integration |
| A4 | Latest non-null per table is selected; later date wins; same-date outcome wins; lifestyle stays independent | PostgreSQL fixtures plus response contract |
| A5 | Synthetic/predicted data never triggers a category; zero remains a valid report | Unit + integration |
| A6 | All safety exclusion/unknown permutations block correctly; legacy positive flags remain protective | Parameterized unit tests |
| A7 | Threshold and malformed-input boundaries follow the documented decision matrix | Unit/contract tests |
| A8 | Daily outdoor sunscreen result includes questionnaire sunscreen-frequency and Daily Health provenance; all selected daily IDs/dates/consent are accurate | Unit + API contract |
| A9 | Every image gate, including the independently disabled image-path feature flag, withholds appropriately; valid reported-input fallback remains usable | Unit + persisted-analysis integration |
| A10 | Questionnaire history is append-only; concurrent full/safety/initial writers have exactly one successful revision per base and a 409 conflict otherwise | Two-session PostgreSQL + HTTP |
| A11 | Guest/account switching, expired session, signed cookie, and proxy cache behavior preserve isolation | Proxy + browser integration |
| A12 | Safety edit, full edit, missing-profile onboarding, conflict recovery, and navigation refresh behave correctly | Browser integration |
| A13 | Thai copy, units, separate dates, responsive/dark/accessibility behavior pass visual and keyboard review | Browser + manual visual QA |
| A14 | Rule and knowledge versions reproduce the selected decision and only approved claims are displayed | Catalog/contract review |

## Delivery sequence

1. **Contract and normalization:** add typed response models, explicit Bangkok calendar, separate daily availability, and robust value normalization; lock the provenance contract with A3–A9 tests.
2. **Questionnaire integrity:** implement stable owner locking and server-owned revision metadata; complete A10 with real PostgreSQL contention tests.
3. **Boundary security:** complete A1, A2, and A11 through real backend/proxy persistence and authentication tests.
4. **User recovery:** implement/verify retry, 409 draft recovery, fixed return routing, and A12–A13 browser coverage.
5. **Release governance:** record knowledge approvals and run A14. Do not treat skipped integration/browser checks as passes.

Use a disposable, explicitly configured test database. Never drop or clean a developer/shared database. Finish each implementation step with focused tests, frontend lint/type checking for touched UI, `git diff --check`, and scoped diff review. Record exact commands and outcomes with the release evidence.
