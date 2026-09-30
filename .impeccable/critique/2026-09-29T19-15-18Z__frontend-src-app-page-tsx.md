---
target: Home/Dashboard article sizing, typography, responsive hierarchy, and transparent full-fill navigation
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\page.tsx"
target_fingerprint: "sha256:b7641b0fa2407255d9d7c257f0da2b7beeca4123cbb1712888e2e8a7f225f223"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\page.tsx"
timestamp: 2026-09-29T19-15-18Z
slug: frontend-src-app-page-tsx
---
⚠️ DEGRADED: single-context (Assessment B’s agent hit its usage limit; detector and browser evidence were recovered in the primary context; Assessment A: /root/layout_design_a).

## Home/Dashboard review

**Design read:** Aphrodize is a personal health tracking dashboard. The supplied reference informs an editorial, video-led hero; retain Aphrodize’s palette, Libre Baskerville and Montserrat typography, and real health data.

**Design specificity:** The current page feels specific to Aphrodize: centered background video, solid health articles, coral accents, and explicit empty states fit the product. The transparent navigation and full-fill background from the new reference are not present. An opaque global navigation bar and a separate opaque title bar sit above the video.

**Automated scan:** Impeccable detector returned `[]` for `page.tsx` and `daily-health-history-panel.tsx` (0 findings). It does not scan `home.css`, which was reviewed separately. No live overlay is available because browser inspection was read-only. The fresh page rendered with genuine empty data states; no personal records were fabricated.

### Usability score

| # | Heuristic | Score | Evidence |
|---|---|---:|---|
| 1 | System status | 3/4 | Empty 0/7 and unavailable values are explicit; weekly status sits low on mobile. |
| 2 | Real-world language | 3/4 | Sleep, hydration, and records are understandable; narrow cards make explanations harder to scan. |
| 3 | User control | 3/4 | Analyze, log, and history links are present; no layout trap observed. |
| 4 | Consistency | 3/4 | Cards and typography cohere; tablet action sizing changes abruptly. |
| 5 | Error prevention | 3/4 | Missing data remains empty instead of zero; video is labeled illustrative. |
| 6 | Recognition over recall | 3/4 | Actions and notes appear in place; weekly information is far down on mobile. |
| 7 | Efficiency | 2/4 | “Log today” appears in the top area and action cards. |
| 8 | Minimalism | 2/4 | Large empty cards and vertical spacing dilute the summary. |
| 9 | Error recovery | 3/4 | Source includes retry, though failure was not reproduced live. |
| 10 | Help and documentation | 2/4 | Formula and safety notes exist, but narrow metric cards slow scanning. |
| **Total** |  | **27/40** | **Acceptable; layout-focused review** |

Cognitive load is moderate: 3 of 8 checks fail. On mobile, the intro and video take up much of the initial view before weekly status. At desktop, five navigation links are visible, but are standard destinations. The emotional journey begins calmly, then becomes a long wait for personal status; the repeated empty metric cards extend that wait.

### What works

- The video stays in the main background, with opaque articles for skin introduction and health information.
- Missing readings remain unavailable, and the weekly calendar communicates recorded days.
- Desktop navigation and the mobile hamburger provide familiar routes.

### Priority issues

1. **P1 — Give the hero a clear full-fill hierarchy.** Opaque navigation and a second full-width title card sit above the media. Place transparent navigation over the video with a contrast scrim; align the lead and weekly articles over the full-fill backdrop. Keep the coral logo, palette, and solid article surfaces. Relevant files: `frontend/src/app/page.tsx`, `frontend/src/app/home.css`, `frontend/src/components/app-navigation.tsx`.
2. **P1 — Bring weekly status up on mobile.** At 390px, navigation/title are about 222px high, followed by a 160px video gap and 273px introduction card. The seven-day card begins around y=773px and Weekly overview around y=1353px. Compact the header, shorten the video reveal to 72–96px, and tighten the intro while retaining Analyze. Target weekly status near y=600–650px.
3. **P2 — Keep tablet actions compact.** At 1000px, actions form a 318px stack of 153px cards, pushing Weekly overview to about y=885px. Make compact horizontal cards about 88–108px high or keep the pair side by side with readable copy and video lane.
4. **P2 — Improve mobile metric reading width and alignment.** At 390px, metric cards are about 168px wide with 134px for text. “Sleep duration score” wraps and its value baseline is about 22px lower than water. Below roughly 430–480px, use compact single-column rows; if retaining two columns, align heading/note space.
5. **P2 — Reduce empty metric card height.** Empty cards are about 281px each on desktop and 303–306px on mobile, including unused chart space. Shorten the unavailable state but retain formula notes and “No data yet”; reserve full chart height for real series.

**Typography direction:** Keep Libre Baskerville for page and section headings. Use Montserrat for article controls, metric labels, explanations, and tabular values. Make one headline the clear lead; current page title and intro heading are both near 34px and compete.

### Persona red flags

- **Returning user:** Can reach Log today promptly but must pass the large mobile hero to scan weekly numbers.
- **Mobile user:** Has a tappable full-width action, but weekly status starts near the bottom of the first screen.
- **Keyboard or screen-reader user:** Benefits from semantic links, headings, and date labels; narrow metric cards hinder visual comparison.

### Minor observation

The desktop 3-column grid preserves the video lane, but at tablet width it narrows to about 184px. A two-column article arrangement gives both content and background more room. The current live page had no records, so dimensions with populated history and guidance remain unverified.

### ShapeUI responsive brief

- **Job:** Let a returning user see recent health-record status quickly, then reach daily entry, trends, or skin analysis.
- **Layout:** Desktop retains solid left/right articles over a centered, full-fill video backdrop; navigation overlays media with readable contrast. Align page title with the lead article.
- **Responsive:** Tablet uses two article columns and compact actions. Mobile stacks the lead article and weekly status early, uses the existing hamburger, and shows metric details in compact rows without horizontal overflow.
- **Typography:** Libre Baskerville carries page/section hierarchy. Montserrat carries labels, values, descriptions, controls, and actions.
- **Boundaries:** Preserve Aphrodize logo, colors, routes, actual data, empty states, dark theme, and reduced-motion behavior. Do not add mock metrics or medical claims.

### Questions to consider

- Should the mobile first screen prioritize seven-day status immediately after the title, or keep the video intro first with a shorter reveal?
- Should the transparent navigation remain pinned over the video after scrolling, or only overlay the hero?
