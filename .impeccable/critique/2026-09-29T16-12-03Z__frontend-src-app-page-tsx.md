---
target: Home/Dashboard reference layout
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\page.tsx"
target_fingerprint: "sha256:fd894d3a1fa6a7e2f5909946729b5fcd913f9a1eeeeb2725debc4323377d2383"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\page.tsx"
timestamp: 2026-09-29T16-12-03Z
slug: frontend-src-app-page-tsx
---
Method: dual-agent (A: /root/home_ux_design · B: /root/home_ux_evidence)

# Home/Dashboard UX review — 29 September 2026

Scope: frontend/src/app/page.tsx and its dashboard history view. Home/Dashboard only; existing brand, navigation, APIs and models retained.

## Design Health Score

These are the initial assessment scores before the four fixes, not a post-fix rescore or a whole-system score.

| # | Heuristic | Score /4 | Initial observation |
|---|---|---:|---|
| 1 | Visibility of System Status | 2 | Dashboard 401 could be masked by loading. |
| 2 | Match System / Real World | 3 | Real score provenance and recorded data are distinguished. |
| 3 | User Control and Freedom | 3 | Direct recording and trend links. |
| 4 | Consistency and Standards | 2 | English mode left dashboard headings in Thai. |
| 5 | Error Prevention | 3 | No fictional personal metrics. |
| 6 | Recognition Rather Than Recall | 3 | Summary/history exist; chart dates and values needed local access. |
| 7 | Flexibility and Efficiency | 2 | Daily logging was too far down on mobile. |
| 8 | Aesthetic and Minimalist Design | 3 | Reference-aligned card hierarchy. |
| 9 | Error Recovery | 2 | Authentication recovery needed a clear state. |
| 10 | Help and Documentation | 2 | Small explanatory notes and chart interpretation remain important. |
| Total | Acceptable, initial assessment | 25/40 | No fabricated post-fix score. |

## Design Specificity and Overall Impression

Reference-inspired bento layout is adapted to Aphrodize's existing coral palette, logo, fonts, user video and actual daily-health data. The largest opportunity was making daily logging as prominent as decorative media. No invented aggregate health percentage, doctor/chat feature, appointment, or face score is added.

The deterministic scan returned [] with exit 0: zero findings and no false positives to adjudicate. Assessment B ran it once against the page and history-panel markup. Browser evaluation is read-only, so mutable injection and live overlay were not available; no user-visible overlay is claimed. Browser inspection found no horizontal overflow at desktop and mobile widths, no console errors, and two development Fast Refresh warnings.

## What's Working

- Actual seven-day records drive calendar, averages and charts; missing values are not represented as zero.
- Decorative media is explicitly distinguished from analysis results; sample identity and sample scores were removed from Home.
- Existing horizontal navigation/mobile hamburger, dark theme and reduced-motion behavior are retained.

## Priority Issues and Resolution

1. **P1 — Authentication masked by loading.** Users could wait indefinitely instead of seeing how to sign in. Fix: prioritize requiresLogin, clear stale history on dashboard 401. Suggested command: /impeccable harden. **Resolved**; source and SSR regression test cover simultaneous login/loading.
2. **P1 — Partial English mode.** Thai headings persisted after language switching. Fix: bilingual new dashboard headings/actions/states/metric notes and localized dates; stored Thai guidance has an explicit language notice rather than an invented medical translation. Suggested command: /impeccable clarify. **Resolved** in source and live review.
3. **P2 — Mobile daily logging too deep.** The action followed the large media card. Fix: add a visible Record today link near the top, with a 44px target. Suggested command: /impeccable adapt. **Resolved** in mobile browser capture.
4. **P2 — Chart dates and values inaccessible.** Users could not read daily values at the chart. Fix: visible dates, accessible seven-day labels and a local disclosure list of values; missing days remain gaps and zero remains zero. Suggested command: /impeccable clarify. **Resolved** in source, SSR regression and captures.

Independent finish review: ship for this four-fix scope; all four resolved. This is not a declaration that the entire application is flawless.

## Cognitive Load and Emotional Journey

Initial cognitive load was moderate: two of eight checklist checks required attention, especially mobile action placement and five main navigation choices. The seven calendar cells are data, not seven decision options. Neutral empty states and explanatory score provenance avoid a falsely reassuring health percentage. Loading/authentication clarity was the main emotional valley addressed in this pass.

## Persona Red Flags

- **Alex:** Daily logging originally required scrolling below the media card. A top action now provides a direct route.
- **Sam:** Partial English mode, inaccessible chart values and low-visibility dark home icon were risks. New labels, local value lists, language annotations and dark icon treatment address them. No full screen-reader or 200% zoom certification is claimed.
- **Casey:** Mobile action placement is improved. Small explanatory copy and media prominence should still be checked with real users; no full authenticated form journey was run in this scope.

## Minor Observations and Limits

- Existing shared navigation has some Thai accessibility labels in English mode; no whole-app language rewrite was undertaken.
- Guidance remains the stored Thai guidance and existing risk component.
- The user's MP4 contains baked visual annotations/checkerboard-like areas; it was retained without modifying its contents.
- Live browser verification covered empty data, desktop/mobile, English and dark mode. Populated history and an actual protected 401 were validated from code/SSR fixtures, not an authenticated end-to-end session.
- Lint, TypeScript checking, production build and two Node regression tests passed. Tests exercise missing/zero/status behavior, not clinical accuracy.
- DESIGN.md and PRODUCT.md match this scope; the score wording was narrowed to distinguish the duration formula from thirst/dryness direction.

## Questions to Consider

Should decorative media become less prominent once a user has recorded history? This is an optional future design decision, not a change made in this scope.
