---
target: View details history UI
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\clients\\daily-health-history-panel.tsx"
target_fingerprint: "sha256:f24a2de8e8d4a7297a99b588992a9dc40b6a08e9304d38662b9b590f275f3b0f"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\clients\\daily-health-history-panel.tsx"
timestamp: 2026-10-05T11-38-02Z
slug: pp-clients-daily-health-history-panel-tsx-5078680d
---
Method: dual-agent (A: /root/view_details_design · B: /root/insights_design_a)

# View details — Health history critique

Target: frontend/src/app/clients/daily-health-history-panel.tsx; history-specific disclosure on /trend. Evaluation only; no UI edits.

## Design specificity and evidence

Aphrodize's warm outer card is coherent, but the expanded generic risk-card report does not prioritize the date-specific question: what mattered and what can I do? Assessment A used source review and a fresh signed-out live tab, where populated details were unavailable. Independent B inspected populated desktop details in an existing authenticated Chrome session without logging in or altering records. Mobile layout is source-reviewed only.

Detector: 0 findings, JSON []; no false positives. Clean markup scan does not certify UX or shared CSS. Supported evaluate is read-only, so no detector injection, live server or visible overlay exists.

## Heuristic scores

| Heuristic | /4 | Main observation |
|---|---:|---|
| System status | 3 | Date and availability count; reasons require expansion |
| Real-world match | 3 | Familiar inputs; technical provenance competes with guidance |
| Control | 3 | Native reversible disclosure and date reset |
| Consistency | 2 | Nested legacy card vocabulary and mixed languages |
| Error prevention | 3 | Honest unavailable states and constrained dates |
| Recognition | 2 | Generic label does not preview content |
| Efficiency | 3 | Three recent days; expanded reports lengthen scanning |
| Minimalism | 2 | Repeated guidance and full unavailable cards |
| Recovery | 2 | Signed-out history reads empty instead of requesting sign-in |
| Help | 3 | Provenance and scope retained but verbose |
| Total | 26/40 | Acceptable; hierarchy needs redesign |

## Strengths

Native details retain focus and announce expanded state. Controls include the record date in accessible labels, have a 44px minimum height and visible focus. Three recent days with 30-day search limits initial load. Recorded inputs, target dates and unavailable statuses remain distinct.

## Priority issues

1. [P1] Full report inside each date repeats overview/dryness guidance. Replace history-specific content with inline Reasons, Guidance and Next-day outlook sections. Deduplicate presentation, not saved records. Commands: distill/layout.
2. [P2] Unavailable energy/thirst occupy full cards with duplicate actions. Group truthful availability statuses quietly, using a single shared action only when destinations/purposes match. Never confuse model_not_ready with insufficient_history. Commands: clarify/distill.
3. [P2] Generic View details label does not communicate value or change after opening. Use Reasons & guidance, visible open/close affordance and Hide details while preserving native semantics, date accessible label, focus and 44px targets. Commands: clarify/polish.

Runtime B also observed blank horizontal space beside narrower cards. Use the history panel width deliberately rather than reusing the daily-results grid unchanged.

## Cognitive load and personas

Collapsed view is manageable. Expansion introduces four signal blocks plus profile guidance and disclaimer: more reading branches, not a demonstrated excess of primary actions. First-timers can mistake system model readiness for insufficient account records; returning mobile users must scan a long stack; English users encounter saved Thai guidance, which must remain faithfully preserved and properly tagged.

## Minor observations and direction

Do not claim tiny tap targets or broken keyboard semantics: current source/browser evidence supports those foundations. Secondary metadata belongs in a provenance disclosure; keep forecast date, value and experimental meaning visible. Signed-out history state is a separate follow-up, not evidence of empty account history. Recommend a compact inline panel over a modal/drawer to preserve comparison between dates. Keep theme, palette, three-day list and 30-day search unchanged.

Questions: inline compact panel versus date-detail drawer? Scope history-only versus also Dashboard details?
