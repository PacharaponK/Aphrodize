---
target: Face analysis result after analysis display like attached image
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\capture\\analysis-result.tsx"
target_fingerprint: "sha256:a6ce04d8fe94013fb7c56caac5e475ccee29adcc7baa21a43b97f82ecd352753"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\capture\\analysis-result.tsx"
timestamp: 2026-10-02T10-05-15Z
slug: frontend-src-app-capture-analysis-result-tsx
---
Method: dual-agent (A: /root/assessment_a · B: /root/assessment_b)

## UX critique — Face-analysis results

**Design health score: 27/40 — Acceptable; improve the hierarchy before broad release.**

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 3/4 | Queued/running, analysis time, and artifact expiry are represented; no progress estimate. |
| 2 | Match System / Real World | 2/4 | Pixel area is explained, but summary wording and Low/Moderate/Elevated badges can read like a skin grade. |
| 3 | User Control and Freedom | 3/4 | New analysis, home navigation, overlay/mask selection, zoom, and stages are available. |
| 4 | Consistency and Standards | 3/4 | Shared theme/navigation remain, but the desktop column ratio differs from DESIGN.md. |
| 5 | Error Prevention | 3/4 | Rejected, failed, no-score, and expired-artifact states are handled. |
| 6 | Recognition Rather Than Recall | 3/4 | Bars and image legend have labels; formula details are disclosed separately. |
| 7 | Flexibility and Efficiency | 3/4 | Stage navigation and image zoom support result review. |
| 8 | Aesthetic and Minimalist Design | 2/4 | Equal-weight KPIs and every regional card compete with the face image. |
| 9 | Error Recovery | 2/4 | Some errors provide next steps, but load failure relies on page reload and processing failure is generic. |
| 10 | Help and Documentation | 3/4 | Inline metric explanations and a formula disclosure clarify the output. |
| **Total** | | **27/40** | **Acceptable (67.5%)** |

### Design specificity

The product-specific direction is strong: the brief defines data limits, states, layout, and responsive behavior. The current UI diverges from its own spec: result-detail.css gives the results column more width than the image on desktop, while analysis-result.tsx displays all regions instead of limiting the initial view to four.

The deterministic scan found 0 issues in analysis-result.tsx; no false positives were reported. A fresh browser tab could not connect to localhost:3000/capture#results (ERR_CONNECTION_REFUSED), so visual review and overlay injection were unavailable. This assessment is based on source and DESIGN.md, not a live screenshot.

### Overall impression

The analyzed image and its explanation are a solid foundation. The largest opportunity is to make the page clearly say “what the model marked in this photo” and keep the image-area percentage prominent, without looking like a diagnosis.

### What's working

- The user's analyzed image, overlay/mask, zoom, and legend make the result inspectable.
- Marked-area percentage is distinguished from the experimental score, with meaning and formula explained.
- Important states include queued/running, rejected, failed, no score, and expired artifact.

### Priority issues

1. **[P1] Image-first hierarchy is reversed.** The desktop grid is 1fr:1.12fr, so the results side is wider than the image; both KPIs also have similar emphasis.  
   **Fix:** target about 56% image / 44% results; lead with marked-area percentage, subordinate the experimental score, and avoid a score ring that looks like a skin grade.  
   **Suggested command:** /impeccable layout.

2. **[P1] Level badges can imply clinical severity.** “Overall Assessment Summary” and colored Low/Moderate/Elevated labels can create a skin-health judgment despite the disclaimer.  
   **Fix:** use neutral model-output wording; avoid severity colors unless their meaning and thresholds are defined and validated.  
   **Suggested command:** /impeccable clarify.

3. **[P2] Regional detail creates excess scrolling.** All scored regions currently appear as cards, with score and percentage repeated.  
   **Fix:** show up to four high-salience region bars first; place the rest and pixel counts in a disclosure.  
   **Suggested command:** /impeccable distill.

4. **[P2] Recommendations are separated from the reference-like result view.** Products currently live in the #products stage.  
   **Fix:** optionally show a compact preview only when the API returns eligible recommendations, with a link to the full product stage; otherwise keep the current flow and do not invent examples.  
   **Suggested command:** /impeccable shape.

5. **[P2] Privacy copy may disagree with actual artifact expiry.** The fixed “auto-deleted within 24h” badge sits alongside a dynamic expiration value.  
   **Fix:** show retention only when supported by current policy/API data and verify load/expiry recovery states.  
   **Suggested command:** /impeccable harden.

### Persona red flags

- **Concerned skincare user:** may read “Elevated” or a red badge as a health warning, although the output is experimental.
- **Screen-reader or color-blind user:** needs region labels and numeric values to carry meaning without relying on badge color.
- **Mobile user:** the full region list lengthens scrolling before reaching methods or next steps.

### Minor observations

- resultIntro is defined but appears unused.
- The privacy badge is fixed to 24 hours while artifact expiry is dynamic.
- /result-detail redirects; the true result target is /capture#results.
- Do not copy the reference's example rings, texture/firmness/evenness/radiance/redness/pores, face wireframe, AI Doctor, appointment widget, or sample percentages unless Aphrodize's API actually supports them.

### Proposed implementation plan

1. Keep the results surface at /capture#results; retain shared navigation, theme, language, and capture stepper rather than adding a duplicate route or sidebar.
2. On desktop, make the real face image and overlay/mask the wider left column (about 56%). On the right, show marked-area percentage first, experimental score second, then factual region bars.
3. Initially show no more than four regions with measurable values. Put additional regions, method, and pixel counts in a collapsed disclosure.
4. If a result-stage recommendation preview is desired, render it only from actual API recommendations when the recommendation gate permits it; keep full product selection in #products.
5. Preserve and verify queued, running, rejected, failed, no-score, expired, and artifact-load-error states. Use API/policy-backed expiry rather than a fixed privacy claim.
6. At tablet/mobile widths, stack image before measurements, preserve uncropped overlays, support Thai/English and dark/light themes, keep controls at least 44px, and prevent horizontal overflow.
7. Validate real payloads and edge states, responsive layouts, accessibility, lint, typecheck, build, and relevant frontend tests.

Questions to resolve: What can a user safely conclude from one marked-area percentage? Should eligible recommendations be previewed in results or remain entirely in the separate #products step?
