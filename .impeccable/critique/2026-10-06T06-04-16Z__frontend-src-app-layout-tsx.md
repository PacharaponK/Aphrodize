---
target: check font size all page
total_score: 16
max_score: 28
na_heuristics: 2,3,9
p0_count: 0
p1_count: 0
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\layout.tsx"
target_fingerprint: "sha256:54b82bf769f74a918f2e3e88343e7429cb61152ca97fc476d4ea35fcf70bd57d"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\layout.tsx"
timestamp: 2026-10-06T06-04-16Z
slug: frontend-src-app-layout-tsx
---
Method: dual-agent (A: design_review_now · B: insights_design_a)

# All-page typography critique

Scope: source across all routes; rendered desktop 1920px and mobile 390px. Home, clients, trend, capture, profile, UV, login, signup, onboarding/health, quality-rejected, showcase and gated admin inspected. Result-detail/recommendation redirect into Capture without a current result; populated analysis regional metrics reviewed in source only. No application UI changes, uploads, submissions or account writes.

## Design specificity and overall impression

Aphrodize's editorial serif headlines, Montserrat/Noto Sans Thai reading layer and warm palette feel authored for the product. Main headings and metric values work; essential interpretation text is too small relative to the widened page frame. Improve the reading layer, not every heading.

## Nielsen typography-only score

| # | Heuristic | /4 | Evidence |
|---|---|---|---|
|1|Visibility of status|3|Small supporting status/data labels|
|2|Real-world match|n/a|Model terminology outside scope|
|3|Control/freedom|n/a|Workflow behavior not tested|
|4|Consistency|2|Independent hard-coded reading scales|
|5|Error prevention|2|Consent and limits visually underweighted|
|6|Recognition|2|Small nav/legend labels|
|7|Efficiency|2|Repeated scanning needs effort|
|8|Minimalism/aesthetics|3|Strong primary hierarchy|
|9|Recovery|n/a|Error recovery not tested|
|10|Help/documentation|2|Much guidance at12–13px|
|Total||16/28|Typography scope only|

## Strengths

- Home hero84px desktop /39.375px mobile with clear editorial identity; preserve its distinct role.
- Auth inputs16px; Profile key/value14px with1.6 leading.
- Capture consent13px already has1.75 leading and constrained reading measure.

## Priority findings

1. **P2 Essential chart/data captions too small.** Forecast ticks10px, legends/values11px, <=380 legend10px; Home dates/captions11px; UV legend10.4px measured desktop/mobile. Regional definitions10px,units/caption11px in source. Raise ticks12–13, legends/rows13–14; reduce tick density instead of shrinking. Evidence: clients/daily-health-forecast.css29–43; home.css137–138; result-detail/result-detail.css1469–1486. Suggested typeset + adapt. No minimum-font WCAG violation asserted.
2. **P2 Consent/interpretation underweighted.** Signup consent12px!important; login privacy11px; Home visual-demo disclaimer10px; capture consent13px, required/optional11px. Raise consent14–15, short privacy13–14; retain full substance and generous leading. Evidence: design-system.css372; capture/capture.css65–67; browser measurements. Suggested typeset.
3. **P2 Primary navbar labels too small.** Desktop12px, open390px mobile menu11px measured.44px targets do not compensate for small text. Recommend desktop14px/mobile14–16px, resolve desktop fit by collapse/spacing. Evidence: design-system.css588,602. Suggested typeset + adapt.
4. **P3 No consistent reading and section role scale.** Daily health section40px desktop vs trend21/profile20/capture18,24,28. Practical help often12–13px. Establish body15–16,secondary14,metadata12–13,data section24–28; retain Home hero exception and semantic differences. Evidence: design-system.css1186–1188; daily-health-forecast.css4–5; profile/profile.css42; capture/capture.css23,51,86. Suggested typeset + document.

## Cognitive and emotional assessment

Page structure easy to recognize; reading dates, units and limitations has moderate cognitive cost. Initial impression premium/calm; confidence-related details feel like fine print. No new >4-choice decision cluster attributed to typography.

## Persona red flags

- Sam: UV ranges, consent and legends may require zoom.
- Alex: tiny dates/units slow repeated comparison.
- Casey: mobile vertical nav11px unnecessarily small; reflow instead of shrink.

## Minor findings and limitations

Onboarding numeric inputs14px measured mobile vs Auth16; verify Safari/iPhone before asserting zoom behavior. No horizontal overflow in observed390px states. Populated results, Thai200%zoom, contrast and complete keyboard audit untested. Admin editor configuration-gated. Declared font stack is not a glyph-by-glyph fallback audit.

## Detector evidence

One scan on frontend/src/app:12warnings (9stylistic,3quality).
- side-tab6: clients/clients.css1,48,81; clients/daily-health-forecast.css13; design-system.css324; recommendation/uv.css18.
- layout-transition3: design-system.css386; result-detail/result-detail.css532,683.
- overused-font1: prototype.css1.
- gradient-text2: prototype.css18,34.

These rules do not measure font size. Inter finding is not evidence of the actual Capture font (Montserrat/Noto Sans Thai with Libre Baskerville headings). Legacy/prototype rules need import/cascade qualification. Browser readonly evaluation does not support mutation; no injected overlay, detector browser console output or visualization server.
