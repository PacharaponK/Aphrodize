---
target: Health risks and signals layout
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\clients\\daily-health-risk-results.tsx"
target_fingerprint: "sha256:d82e20332a0835b6634d4495b536a14c67c6d0251c090e372c094e00a4dec5f9"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\clients\\daily-health-risk-results.tsx"
timestamp: 2026-10-06T10-24-42Z
slug: app-clients-daily-health-risk-results-tsx-8eae03e0
---
Method: dual-agent (A: health_layout_design · B: health_layout_detector)

# Health risks and signals layout critique

Target: frontend/src/app/clients/daily-health-risk-results.tsx (Daily Health, Operate/Read).
Source/CSS-based provisional critique. Independent new browser tabs inherited authentication; reviewers stopped and closed them. Private records were excluded. Result-card visual verification, mobile/zoom overflow and image-based contrast remain unverified. No overlay: evaluate is read-only.

## Design specificity and overall impression
Aphrodize-specific domains, experimental status and profile guidance are honest and useful. The generic bordered-card grid does not distinguish current assessments, next-day estimates and unavailable models strongly enough. Main opportunity: grouped time horizons and progressive disclosure rather than additional color.

## Heuristics
| Heuristic | Score /4 | Key issue |
|---|---:|---|
| Visibility of system status |3|Explicit availability/experimental states|
| Match with real world |2|Model IDs and mixed languages|
| User control and freedom |3|Native links and disclosure|
| Consistency and standards |2|Live/restored wrappers differ|
| Error prevention |3|Missing is not low; validates forecasts|
| Recognition rather than recall |3|Names/date present, time grouping absent|
| Flexibility and efficiency |2|Repeated guidance/actions|
| Aesthetic and minimalist design |2|Unavailable and metadata overemphasized|
| Error recovery |2|Observation action cannot remedy deployment readiness|
| Help and documentation |3|Scope, scale and references|
| Total |25/40|Acceptable|

## Strengths
Explicit text status avoids color-only meaning; numeric forecasts preserve target date and scale direction; no fabricated missing results and non-diagnostic limitations retained.

## Priority issues
1. P1: Today and tomorrow mixed in one grid. risk-results.tsx:5-10; clients.css:161 final auto-fit override. Group current wellness/dryness and next-day energy/thirst. Preserve dates, truth and absence. Command: layout.
2. P2: Unavailable signals receive full cards and duplicated links. risk-results.tsx:72,92-95. Use compact unavailable-outlook group with distinct reasons and one action; do not imply observation submission resolves missing deployment. Command: distill.
3. P2: Recommendations repeat across signal cards, profile guidance and Today's guidance. risk-results.tsx:73-79,98-108; dashboard.tsx:11-16,25-34. Deduplication currently excludes profile duplicates only. Consolidate unique advice with accessible detail disclosure. Command: distill.
4. P2: Heading/badge rigidity and technical density. clients.css:38,40,82; risk-results.tsx:57-64. Heading lacks wrapping; badge flex:none/nowrap can crowd titles on narrow layouts, but actual overflow unverified. Add responsive wrapping; keep scale/date next to value and model provenance in a secondary disclosure. Commands: adapt/clarify.

## Cognitive load and emotional journey
Moderate, higher when guidance populated. No >4-option decision point inside component; cards are information chunks, not choices. Current severity, model availability and forecast value require mental sorting. Repeated unavailability stalls the ending; concise current summary followed by quieter outlook would feel resolved.

## Persona red flags
Jordan: badge position suggests risk level and experimental estimate are comparable.
Sam/mobile: nonwrapping badges need approved mobile and 200% zoom inspection; no observed overflow claimed.
Alex: repeated advice slows scanning; restored path omits live wrapper additional guidance (tracker.tsx:774-779).

## Detector and minor observations
CLI detect --json returned [] / exit0, count0, no rule names or locations or false positives. Source evidence still supports hierarchy review. Home has heading wrap accommodation not present in clients. The live wrapper combines daily-health-dashboard/personalized-guidance roles; verify matching surfaces after refresh. English mode marks Thai text but only supplemental daily guidance explains language limitation. Disclaimer remains small. No source edits.

## Questions to consider
Should current assessment be one short lead? Should unavailable next-day models be grouped? Preserve underlying facts and consent regardless.
