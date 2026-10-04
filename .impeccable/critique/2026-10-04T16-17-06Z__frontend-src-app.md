---
target: current frontend design
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app"
timestamp: 2026-10-04T16-17-06Z
slug: frontend-src-app
---
Method: dual-agent (A: /root/design_review_now · B: /root/detector_review_now)

# Current frontend critique

Target: frontend/src/app, localhost:3000. Desktop 1266-1280 x 720; mobile390 x844. Signed-out read-only inspection of Home, Capture, Login, Signup, Daily Health, Profile, Trends. No account submissions, uploads or consent changes. Viewport restored. No code changes.

## Design specificity and overall impression
Product-authored coral/coffee palette, editorial serif and portrait establish coherent Aphrodize identity. Expressive Home and quieter operational surfaces follow the approved Oct3 revision. Biggest opportunity: make signed-out state and task entry as deliberate as the brand. Embedded non-wrinkle condition labels in the hero undermine cautious product claims.

## Design Health Score
| # | Heuristic | Score | Key issue |
|---|---|---|---|
|1|Visibility of system status|3|Signed out vs no records ambiguous|
|2|Match real world|2|Unsupported-looking hero labels and vague consent|
|3|Control and freedom|3|Back/Pause present, credential recovery unclear|
|4|Consistency|2|Sign in route inconsistency; mixed-language Trends|
|5|Error prevention|3|Upload validation and separate consent good|
|6|Recognition|3|Visible steps; account entry disappears|
|7|Efficiency|2|Mobile upload below large empty frame|
|8|Aesthetic minimalism|3|Coherent brand, excessive empty spacing|
|9|Error recovery|2|No visible forgot-credential path|
|10|Help and documentation|2|Capture tips useful; signup terms unexplained|
|Total||25/40|Acceptable|

## Strengths
- Coral/coffee, serif headings, text-only nav underline form a coherent identity.
- Three-stage capture flow with explicit required analysis vs optional annotation consent.
- Accessible labels, motion pause/reduced-motion source, and explicit profile auth gate are useful foundations, not a certification.

## Priority issues
1. P1 Auth and empty states. shared-navigation.tsx:22 exposes Sign in only on Home; app-navigation.tsx:61 returns null otherwise. Home shows0/7 and empty metrics without clear sign-in distinction; Capture/Clients lose auth entry. Keep common Sign in and explicit account-backed auth states. Commands: harden, clarify.
2. P1 Signup consent. signup/page.tsx:173 requires vague consent terms without detail/link. Explain account storage purpose and where independent image consent occurs; don't merge privacy choices. Commands: clarify, onboard.
3. P2 Mobile upload hierarchy. capture/capture.css:25,91 empty frame occupies~300px; at390x844 Choose image begins near y770. Compact empty upload zone with early action; expand only with preview. Commands: adapt, layout.
4. P2 Hero trust. home-hero.tsx imagery has Dark Circles/Redness/Blemish labels, while home.css:28 demo label10px near bottom. Make illustrative demo apparent before unsupported condition labels, or replace labels in asset with permitted user approval. Preserve approved identity/motion. Commands: clarify, distill.
5. P2 Diary dialog and language consistency. Daily Health dialog observed x0y0w650h648 at1280x720; center constrain and allow appropriate scrolling. Trends Risk History remains Thai while selected page is English. Translate full surface. Commands: layout, adapt, clarify.

## Detector and browser evidence
12 raw warnings, detector exit0: side-tab6, layout-transition3, gradient-text2, overused-font1. Locations: clients/clients.css:1,48,81; clients/daily-health-forecast.css:13; design-system.css:320,374; prototype.css:1,18,34; recommendation/uv.css:18; result-detail/result-detail.css:532,683.
Legacy Inter overridden by font-ui; auth gradient overridden by design-system.css:351. Semantic caveat callouts are legitimate, not six automatic defects. Width transitions are a P3 performance check, not observed jank. No injected overlay: browser evaluation supports read-only DOM, so no mutable script preflight/server performed. Manual DOM/AX/screenshots used.

## Cognitive load and emotional journey
Moderate load: five nav entries plus controls grouped reasonably; mobile empty capture frame, repeated preparation text and multiple empty metric cards add extraneous load. Aspirational Home to calm consent flow works; losing auth entry and empty-record ambiguity create emotional valleys. Populated result ending not assessed.

## Personas
- Jordan first-timer: may expect dark circles/redness analysis from hero; signup consent opaque.
- Casey mobile: scrolling to upload and consent; no overflow on inspected routes390px.
- Sam accessibility-dependent: labels/pause useful;10px demo text needs measured contrast/zoom check. No WCAG failure asserted from screenshot alone.

## Minor observations and limits
Capture initial heading was not occluded in this live pass. No visible password recovery route on Login; only expose supported recovery, not a fake reset action. Old superseded DESIGN clauses can drift future implementation. Dark mode, screenreader,200%zoom, slow network, authenticated charts/private result/product state not tested. No new test accounts or data.

## Questions to consider
Priority: auth+consent, mobile capture+dialog, or hero trust wording?
Scope: top3 issues or all5? Preserve existing palette and approved Home identity.
