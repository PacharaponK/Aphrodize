---
target: "Health risk history: too much display"
total_score: 21
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\clients\\daily-health-history-panel.tsx"
target_fingerprint: "sha256:06d1ad2280fb27d5a6be7679e3b7d4eac4f5dad31cd7171ffe78d7060085fcec"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\clients\\daily-health-history-panel.tsx"
timestamp: 2026-10-04T17-12-11Z
slug: pp-clients-daily-health-history-panel-tsx-5078680d
---
Method: dual-agent (A: history_ux_a · B: history_ux_b)

Health risk history: 21/40. History should support fast date comparison, not repeat complete reports.

| Heuristic | Score /4 | Issue |
|---|---:|---|
| Visibility of system status | 3 | Loading, retry and unavailable states exist. |
| Match with real world | 2 | Mixed language and next-day signals inside historical entries. |
| User control and freedom | 2 | No per-date disclosure. |
| Consistency and standards | 3 | Consistent cards, wrong density for history. |
| Error prevention | 3 | Unavailable is not presented as low risk. |
| Recognition rather than recall | 2 | Long reports hinder date comparison. |
| Flexibility and efficiency | 1 | No compact scan view. |
| Aesthetic and minimalist design | 1 | Repeated rating, advice and disclaimers. |
| Error recovery | 2 | Retry exists; missing-data recovery is unclear. |
| Help and documentation | 2 | Advice and references exist but repeat. |
| Total | 21/40 | Significant density improvements needed. |

Design specificity: categories are specific to Aphrodize, but history composition is a generic full-results dump rather than a date-comparison surface.

Priority issues:
1. P1: Every date renders five full signal cards; up to 30 entries permits 150 cards. Use compact date summaries with explicit accessible disclosure.
2. P1: Three unavailable results compete with assessed results. Use a quiet count, preserve each original unavailable reason inside details, never replace missing results with low risk.
3. P2: Overall rating repeats and the supplied example repeats moisturizer guidance. Display overall once in summary and deduplicate identical advice within expanded details.
4. P2: Profile education and disclaimer repeat per date. Use a section-level disclaimer and optional profile guidance, preserving dated/changed guidance and references.
5. P2: Mixed Thai/English chrome increases interpretation effort. Localize chrome consistently; identify the original language of stored advice.

Suggested collapsed entry:
4 ต.ค. 2569 — ภาพรวม: ปานกลาง
นอน 6 ชม. 37 นาที · น้ำ 1,700 มล. · กลางแจ้ง < 1 ชม.
ผิวแห้ง: ปานกลาง · ยังประเมินไม่ได้ 3 สัญญาณ
ดูรายละเอียด

Details retain factors, deduplicated advice, individual unavailable reasons, profile guidance and references. Forecasts retain target date and provenance separate from recorded values.

Strengths: explicit missing states; recorded date and input context; text accompanies risk colors. Cognitive load failures: focus, chunking, hierarchy, one thing at a time and progressive disclosure. Five cards are information categories, not five competing actions. Emotional journey repeats warnings and shortfalls before ending in lengthy education. Persona concerns: Alex cannot compare quickly, Sam encounters repetitive linear reading, Casey sees five stacked cards per date.

Evidence: daily-health-history-panel.tsx DailyHistoryEntry renders full DailyHealthRiskResults; risk-results defines all five signals plus guidance and disclaimer. Both agents independently opened fresh /trend tabs; signed-out/empty state prevented populated live/mobile verification. User's pasted entry supports actual duplicate moisturizer wording. Detector ran once against history-panel markup: exit 0, findings [], count 0, rules [], locations []. A narrow clean scan does not test dynamic content density. Read-only browser API prevented injection; no overlay or temporary server was created. No app code or account data changed.

Questions for next step: collapsed summary rows (recommended) versus latest day expanded; history-only scope (recommended) versus also applying compact results to Daily Health/Home.
