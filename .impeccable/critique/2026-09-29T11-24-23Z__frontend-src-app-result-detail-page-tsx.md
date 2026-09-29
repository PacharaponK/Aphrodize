---
target: Aphrodize facial-analysis result page compared with attached reference
total_score: 23
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\result-detail\\page.tsx"
target_fingerprint: "sha256:600a159b5a5e227a63dc89cdbede295f9319e368d89970ba29fef00ea752feaf"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\result-detail\\page.tsx"
timestamp: 2026-09-29T11-24-23Z
slug: frontend-src-app-result-detail-page-tsx
---
# UX critique: Aphrodize face analysis results

Method: dual-agent (A: `/root/design_review` · B: `/root/detector_review`)

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of system status | 3/4 | Loading and error states exist; the empty state has a recovery action. |
| 2 | Match between system and real world | 2/4 | “Score 0–100” and “pixels” may still be misinterpreted. |
| 3 | User control and freedom | 3/4 | Overlay/mask switching and restart/navigation options are available. |
| 4 | Consistency and standards | 2/4 | The navy summary panel conflicts with the light surfaces and violet accent in DESIGN.md. |
| 5 | Error prevention | 2/4 | Expiry checks presence only; “deleted within 24 hours” is hard-coded. |
| 6 | Recognition rather than recall | 3/4 | Controls have text and scores are numeric. |
| 7 | Flexibility and efficiency | 2/4 | Core flow works, but there is no prior-result history on this page. |
| 8 | Aesthetic and minimalist design | 2/4 | Summary and formula precede the image; regional details can be long. |
| 9 | Error recovery | 2/4 | Restart is available, but quality flags may be technical codes. |
| 10 | Help and documentation | 2/4 | Formula and caveat exist, but score meaning should be adjacent to the score. |
| **Total** | | **23/40** | **Acceptable** |

## Design specificity verdict

The attached reference includes multiple metrics and product recommendations that Aphrodize does not currently have evidence to support. It should not be copied literally. The updated `frontend/DESIGN.md` is better aligned with the product: it preserves the existing navigation and limits the result to overlay/mask, experimental wrinkle-area score, detected-area ratio, and regional results. The current implementation still places the summary and formula before the image, so it does not yet follow the reference's image-led hierarchy.

The Impeccable detector exited successfully and returned `[]` (0 issues); there are no detector false positives to assess. A fresh browser tab loaded `/result-detail` but showed only the no-analysis empty state, so the completed-state appearance was reviewed from source/CSS. Browser overlay injection was unavailable because CUA exposes no page-evaluation or DOM-mutation API. No overlay is visible in the browser.

## Overall impression

The page has useful safeguards and truthful measurements, but presents the explanation and summary before the visual evidence. Make the image and the meaning of its score immediately clear.

## What's working

- It does not invent metrics that the backend does not provide.
- It exposes the score formula and pixel counts and describes the result as experimental.
- It supports queued/running/rejected/failed states and provides overlay/mask selection.

## Priority issues

1. **[P1] Score meaning can be mistaken for a skin-health rating.** Place an explanation next to the score: it reflects pixels marked by the model, not skin health or diagnosis, and state the direction clearly. Suggested command: `/impeccable clarify`.
2. **[P1] The main image is pushed below the summary and formula.** Use an image-led desktop split with compact summary and regional results beside it; keep Aphrodize navigation and move calculation detail below. Suggested command: `/impeccable layout`.
3. **[P2] Regional details are dense.** Up to eight regions may each show score, ratio, and pixel counts. Show essential values first and disclose pixel detail on demand. Suggested command: `/impeccable distill`.
4. **[P2] Expired-image and image-load-error states are not distinct.** Compare expiry with the current time, separate expired from failed loading, and translate quality flags into actionable user language. Suggested command: `/impeccable harden`.

## Cognitive load

Three checklist failures: score grouping when up to eight regions are visible; hierarchy because summary/formula precede the image; and progressive disclosure because all formula detail appears immediately. Overall cognitive load is moderate.

## Emotional journey

Users arrive wanting to see the image and understand the result. They may encounter numbers before the interpretation that would keep an experimental score from sounding diagnostic. Explain beside the score that a higher value means more pixels were marked, not a higher skin-health score.

## Persona red flags

- **Jordan, first timer:** may not know what the score means; the empty state does not explain how to find a prior result.
- **Sam, keyboard or screen-reader user:** artifact buttons expose `aria-pressed`, but their group lacks `role="group"`; image-load failure should announce status clearly.
- **Casey, mobile user:** eight region rows plus formula may make the page long, with navigation actions at the bottom.

## Minor observations

- Unknown region keys can appear as raw snake_case.
- The progress bar has adjacent numeric text, so information is not color-only.
- Motion should be restrained for this operational page: brief transitions for overlay/mask and result-state changes only, with `prefers-reduced-motion` support. Avoid scroll pinning, autoplay, and decorative motion.
