---
target: Aphrodize dashboard / frontend/src/app/page.tsx
total_score: 24
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\page.tsx"
target_fingerprint: "sha256:feb9ecde47ac344278aca9906993029d0355124be03532f9d5e80e36f753720c"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\page.tsx"
timestamp: 2026-09-29T15-00-25Z
slug: frontend-src-app-page-tsx
---
# Aphrodize dashboard design recheck

Method: dual-agent (A: /root/design_assessment · B: /root/detector_assessment)

## Scope and design specificity

Target: dashboard at `http://localhost:3000/#dashboard`, primarily `frontend/src/app/page.tsx` and its related home styles/components. The dashboard-specific design brief is missing. The existing `DESIGN.md` is for the face-analysis result-detail page, so its brand and safety principles were used as context, not as a dashboard specification.

Product-specificity verdict: **Partly product-specific.** Aphrodize’s logo, blush-and-white palette, skin-analysis imagery, and daily-health summary establish the product category. The fixed/sample details and generic AI-skincare hero treatment make the dashboard feel more like a mockup than a clearly personal tracker.

## Overall impression

The desktop dashboard is calm and reasonably scannable, with useful labelled navigation and a constructive 7-day empty state. The main improvements are trust and hierarchy: make demo versus user data consistent across the whole page, and make the actual result/status more prominent than decorative motion.

## Heuristic scores

| # | Heuristic | Score | Evidence |
|---|---|---:|---|
| 1 | Visibility of system status | 2/4 | The weekly no-data state is clear, but nearby latest-result metadata looks personal while some data is sample. |
| 2 | Match between system and real world | 2/4 | Thai copy is mixed with unexplained English terms such as “confidence,” “Skin profile,” and “safety check.” |
| 3 | User control and freedom | 3/4 | Navigation, theme/language controls, links, and video controls are available. |
| 4 | Consistency and standards | 2/4 | A second Home control duplicates the active Home nav item; language is mixed across the page. |
| 5 | Error prevention | 2/4 | A caution notice and honest empty state help, but demo/personal status is inconsistent. |
| 6 | Recognition rather than recall | 3/4 | Navigation labels and the health-entry CTA are visible; “confidence” and score meaning need in-place explanation. |
| 7 | Flexibility and efficiency | 2/4 | Key result and health actions require scrolling past the dominant media. |
| 8 | Aesthetic and minimalist design | 3/4 | The restrained palette and card grouping work; video dominates and the detail panel has unused space. |
| 9 | Help users recognize, diagnose, and recover from errors | 3/4 | The health-history panel includes useful empty and retry states. |
| 10 | Help and documentation | 2/4 | The disclaimer helps, but score/confidence values have little immediate explanation. |
| **Total** |  | **24/40** | **Acceptable — trust and hierarchy fixes remain.** |

## Cognitive load

**3 of 8 checklist failures — moderate load.**

- **Single focus:** Face results, a new-image action, weekly health summary, and rule-based guidance compete in the page flow.
- **Immediate hierarchy:** The face video dominates the first viewport; the 37/100 example score sits below it and starts off-screen.
- **Choice count:** Five top-level navigation items exceed the four-choice checklist target, and the separate Home action repeats one.

Grouping is otherwise useful: related face findings are carded, and the weekly no-data state is visually distinct.

## Emotional journey

The greeting and soft palette feel welcoming; the caution banner reassures. Fixed-looking date/confidence metadata can then make sample data feel personal, while the main score is below the fold. The weekly empty state is honest and provides a useful logging path. The recommendation dialog’s hard-coded personal rationale risks undermining trust.

## What is working

- White/blush palette, Aphrodize mark, and restrained accent colors feel calm and coherent.
- The desktop two-column layout uses readable labels; result status is not conveyed through color alone.
- The 7-day empty state explains the lack of history and gives a clear path to record daily health.

## Priority issues

1. **[P1] Demo and personal data are visually mixed.** In the inspected state, the 37/100 score is labelled as a sample, but the neighboring fixed date, “Ink” greeting, confidence values, and “quality passed” status appear like current personal results; the header also offers sign-in. **Fix:** Apply one explicit demo state to every sample card, or show a real no-result state until the user has data. Remove fixed names/dates from the personal dashboard. Suggested command: `/impeccable clarify`.

2. **[P1] The hero video overstates measurements and pushes the result down.** The face-analysis media includes HUD labels for hydration, elasticity, firmness/radiance, and wrinkle depth that imply metrics not established in the dashboard, and it occupies the dominant first-viewport area while the key score is below it. **Fix:** Remove metric-like HUD elements or mark the clip as decorative; place the result/status above or beside a shorter media treatment. Suggested command: `/impeccable layout`.

3. **[P1] Recommendation copy asserts personal health inputs without evidence.** The inspected dialog rationale says the user reported dry skin, high UV exposure, and inconsistent sunscreen use. **Fix:** Render personal rationale only from verified inputs; otherwise present generic educational guidance clearly as such or omit it. Suggested command: `/impeccable harden`.

4. **[P2] Localization and navigation are inconsistent.** Thai UI is mixed with “Skin profile,” “WEEKLY HEALTH OVERVIEW,” “confidence,” and “safety check.” A top-bar Home control duplicates the active Home navigation item, and the language switch leaves the daily-health panel in Thai while other copy changes. **Fix:** Localize dashboard copy through one consistent mechanism and remove the redundant Home control. Suggested command: `/impeccable clarify`.

## Persona red flags

- **Alex (Power User):** Wants the weekly signal quickly. The video pushes the score below the first viewport and the weekly summary/action farther down the page.
- **Sam (Accessibility-dependent):** Navigation has labels and result status has text, but “confidence 0.86” is unexplained jargon, embedded video HUD content has no text alternative, and small eyebrow/metadata text may be hard to read. Contrast was not measured.

## Minor observations

- The right-side detail card stretches alongside a tall media card and leaves considerable unused space below three result rows.
- The displayed 20 Sep 2026 date is nine days old relative to this review on 29 Sep 2026; use a live timestamp or an unmistakable demo label.
- The scroll-motion component checks `prefers-reduced-motion`; preserve that behavior in any hierarchy change.

## Detector and browser evidence

- Deterministic CLI check: `impeccable.cmd detect --json frontend/src/app/page.tsx` exited 0 and returned `[]` (0 findings). Human visual concerns remain despite no automated rule hits.
- Fresh browser tab at `http://localhost:3000/#dashboard` confirmed the desktop dashboard: nav items, sign-in button, yellow non-diagnostic disclaimer, two-column face result, weekly 7-day empty state and CTA, and rule-based recommendation section below the fold.
- The browser connector provides screenshots/accessibility state and UI input, but no mutable page evaluation or script injection; mutation preflight and detector overlay were unavailable. No overlay is claimed.
- The connector also has no console/log capture method. Ctrl+Shift+J did not open developer tools, so browser-console health is **unverified**, not clean.
- No files were edited as part of the critique.

## Questions to consider

- Should a signed-out visitor see any face result, or a clearly labelled demo preview instead?
- Can the result be the first thing users see, with motion serving as supporting context rather than the hero?
- What verified evidence must be present before the recommendation dialog says “คุณรายงาน” and gives personal guidance?
