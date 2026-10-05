---
target: all frontend routes then page transitions
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\layout.tsx"
target_fingerprint: "sha256:54b82bf769f74a918f2e3e88343e7429cb61152ca97fc476d4ea35fcf70bd57d"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\layout.tsx"
timestamp: 2026-10-05T12-20-44Z
slug: frontend-src-app-layout-tsx
---
Method: dual-agent (A: view_details_design · B: insights_design_a)

# Frontend-wide UX critique, 5 October 2026

Target: shared frontend rooted at frontend/src/app/layout.tsx. Assessment before page-transition implementation; score is a bounded expert judgment, not production certification.

## Design specificity and impression

Aphrodize feels authored: face-led Home, Libre Baskerville display, Montserrat UI, coffee ink and coral/blush. The biggest opportunity is consistency and task density, not additional decoration. Home is expressive while information pages are calmer.

## Heuristics

| Heuristic | /4 | Key evidence |
|---|---:|---|
| System status | 3 | States represented; restored analysis deep links temporarily show preparation |
| Real-world match | 3 | Familiar health labels; profile raw fallback keys |
| Control/freedom | 3 | Reversible disclosures, stages and map reset |
| Consistency | 2 | English preference not reflected in UV; duplicated onboarding theme |
| Error prevention | 3 | Consent, input bounds, disabled prerequisite stages |
| Recognition | 3 | Labels, navigation, stepper and dated records |
| Efficiency | 3 | Three recent days and date search |
| Minimalism | 2 | Sparse wide data containers and many map controls |
| Error recovery | 3 | Retry, expiry, rejection covered in source, not all exercised |
| Help/documentation | 3 | Provenance and limits clear; some technical copy burdens daily tasks |
| Total | 28/40 | Solid foundation; consistency and density need improvement |

## Strengths

- Recognizable Home art direction with calm information pages.
- Required image consent distinct from optional human review; retention is explained.
- Results distinguish marked-area measurements from experimental scores; unavailable products are not fabricated. History now uses compact Reasons & guidance and date search.

## Priority issues

1. [P1] UV remains Thai in English mode. Verified navigation/content mismatch impedes English readers. Localize its interface through the existing provider, preserving province/source meaning. Suggested command: /impeccable clarify.
2. [P2] Onboarding has two theme controls. Verified source and accessibility tree. Keep one controls group to reduce confusion and duplicate focus stops. Suggested command: /impeccable distill.
3. [P2] Profile fallback displays internal keys and empty values, including allergy ingredients. Verified DOM. Use explicit supported-field labels, meaningful array formatting and missing-value treatment; retain safety information. Suggested command: /impeccable clarify.
4. [P2] Everyday tasks occupy large sparse containers and daily-health flows expose long training protocol copy. Verified desktop/source. Tighten route-specific reading columns and empty states; move technical detail to disclosure without removing informed-consent substance. Suggested commands: /impeccable layout, /impeccable distill.
5. [P2] UV source/day/province plus many view controls compete with unavailable-data status. Verified desktop/DOM. Keep primary data controls prominent; group secondary view controls while retaining keyboard/mobile alternatives and semantic colors. Suggested commands: /impeccable adapt, /impeccable distill.

## Cognitive load and emotional journey

UV has more than four visible view decisions. Daily check-in has more reading and internal scrolling than its basic sleep/water/outdoor task requires. Home provides a strong entry, capture consent reassures, but language inconsistency and raw profile fields interrupt confidence. Restored deep-link stage flicker may appear like failed navigation before restoration completes.

## Persona flags

- English first-timer: cannot follow the Thai UV workflow after an English link.
- Returning daily tracker: secondary training explanations and long empty-state spacing delay the primary action.
- Motion-sensitive user: preserve existing pause/reduced-motion behavior and avoid hidden-page fades or automatic map rotation.

## Minor observations

Deep links to results/products show preparation before saved stage restoration. Empty product-match state lacks an adjacent reset-filter action. Admin currently displays a configuration-not-ready message. DESIGN.md retains superseded clauses that may confuse later maintenance. Profile header/body alignment and the old View details label are already fixed, not current findings.

## Detector and verification limits

One scan of frontend/src/app: 12 warnings, 9 stylistic and 3 quality. side-tab 6 (clients/clients.css:1,48,81; clients/daily-health-forecast.css:13; design-system.css:323; recommendation/uv.css:18); layout-transition 3 (design-system.css:385; result-detail/result-detail.css:532,683); overused-font 1 (prototype.css:1); gradient-text 2 (prototype.css:18,34). Inter is overridden by the actual self-hosted font. Legacy gradient/redirect CSS needs runtime confirmation; semantic caution sidebars are not automatically usability defects. No live overlay because browser evaluate is read-only.

Fresh representative browser/source coverage of Home, Capture/results/products, Clients, Trend, Profile, UV, Login, Signup and Onboarding. Admin was unavailable; showcase/quality-rejected source-only. No account mutations, submissions, uploads, real analysis execution, forced error, full keyboard/contrast or dark-mode audit. Narrow signup effective viewport 488x1055 had no overflow; broad mobile verification not established.

## Page-transition direction

Persistent pathname-only, entry-only opacity settling; Home240ms, information160ms, content always visible. Stable navigation, no keyed children/template, transforms, exit delay, scroll/focus interception or hash/query replay. Honor reduced motion and interruption. This addresses the separately requested motion scope only; it does not resolve the priority findings above.

## Questions to consider

Which should follow: language/onboarding consistency, profile/day-entry density, or UV control hierarchy? Should the follow-up cover the top three findings or all five?
