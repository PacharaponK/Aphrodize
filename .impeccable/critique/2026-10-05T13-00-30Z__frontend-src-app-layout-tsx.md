---
target: all page size width
total_score: 13
max_score: 20
na_heuristics: 1,3,5,9,10
p0_count: 0
p1_count: 0
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\layout.tsx"
target_fingerprint: "sha256:54b82bf769f74a918f2e3e88343e7429cb61152ca97fc476d4ea35fcf70bd57d"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\layout.tsx"
timestamp: 2026-10-05T13-00-30Z
slug: frontend-src-app-layout-tsx
---
Method: dual-agent (A: /root/design_review_now · B: /root/insights_design_a)

# All-page width review

Scope: current source across all frontend routes; parent measured 12 main routes at desktop 2400 CSS px and exact 390 CSS px; independent agents visually reviewed 1920 CSS px desktop representatives. No UI edits, submissions, uploads, consent changes or account writes. /result-detail and /recommendation redirect to /capture#results and /capture#products. Admin editor is configuration-gated; only its unavailable state was inspected. No full populated results, all dialog states, 320px, 200% zoom or theme switching certification.

## Verdict and width inventory

Responsive behavior works in the inspected states: document scrollWidth equals clientWidth at exact 390px on all 12 main routes. Different inner widths serve different tasks; the problem is inconsistent outer grids and overextended sparse task surfaces, not a global failure to scale.

| Region | Current cap/policy |
|---|---|
| Home, Capture, Daily health, Trends | 1920px, differing gutters/padding |
| Shared navbar | 1504px |
| Profile | 1240px heading and panel aligned; preserve explicit approval |
| UV map | 1280px |
| Login/signup | full available shell; actual form content 520px |
| Onboarding | 760px card |
| Quality rejected/showcase | 1920px workspace, wide inner panel |
| Admin | runtime unavailable state only; editor unverified |

## Heuristic score, width-only

| # | Heuristic | Score | Width finding |
|---|---|---|---|
| 1 | System status | n/a | Async behavior outside scope |
| 2 | Match real world | 3 | Focused forms good; recovery surface oversized |
| 3 | User control | n/a | Not behavior review |
| 4 | Consistency | 2 | Independent outer caps and gutters |
| 5 | Error prevention | n/a | Validation outside scope |
| 6 | Recognition | 3 | Empty capture pushes upload action down |
| 7 | Efficiency | 3 | Responsive grids, wasted empty space |
| 8 | Minimalism | 2 | Wide single-task panels |
| 9 | Error recovery | n/a | Recovery composition only, behavior not tested |
| 10 | Help/documentation | n/a | Outside scope |
| Total | | 13/20 | Acceptable, 65%; not site-wide UX score |

## Priority issues

1. [P2] Navbar and workspace have unrelated outer edges. At actual1920, navbar1504 x198.5 versus Capture/Trends inner workspace1770.5 x65.3: roughly133px per side mismatch. Define a shared outer grid or align task headers to the floating navbar grid while allowing wider media/data below. Preserve narrower approved Profile1240. Evidence design-system.css:582,1142–1147,1154–1165. Suggested /impeccable layout.
2. [P2] Daily health/Trends mix full-width sparse text with compounded gutters. Daily entry card is1684px at1920; outer simple-page gutter plus page-content padding plus inner panel padding narrows mobile usable area. Split broad graphs from720–800px reading regions within a1200–1280 task container where appropriate, and give one layer ownership of page gutters. Do not arbitrarily narrow image-led Capture or discard data. Evidence clients/page.tsx,trend/page.tsx,design-system.css:1154–1165,1225–1244. Suggested layout/adapt.
3. [P2] Capture empty preview expands like a populated diagnostic image. At1920 image column1096px, placeholder up to520px high; mobile empty preview300px. Make the empty chooser180–240px with action nearby, expand after an image exists, preserve contain mode/consent/real results. Evidence capture/capture.css:21,25–28,91. Suggested adapt/layout.
4. [P2] Quality-rejected panel is dashboard-sized for a single recovery decision. Actual panel1770px, copy640px and list440px leave huge blank margins; header and reading path are separated. Use680–800px recovery panel with aligned header; Showcase can remain a medium multi-link grid. Evidence design-system.css:305–307,quality-rejected/page.tsx:11–20. Suggested distill/layout.

## Strengths and persona/cognitive notes

- Profile heading/body both1240px and same left edge; intentional approved design, not a defect.
- Auth form controls cap520px: shell expansion does not mean unreadable input width. Onboarding760 and UV1280 are defensible task tiers.
- Shrink-safe minmax grids and mobile stacking work in measured states, no390px horizontal overflow.
- Alex desktop must re-anchor eyes between unrelated outer frames and sparse recovery panel. Casey mobile loses usable width to nested padding and scrolls past empty capture area. Sam zoom is not certified; source minimum320px should be tested separately rather than claiming390px failure.
- Cognitive burden is moderate spatial reorientation and task-action separation, not an options-count failure. Expressive Home and calm data pages fit Aphrodize; preserve brand while fixing geometry.

## Detector and limitations

One detect --json frontend/src/app run:12 warnings (9 stylistic,3 quality). side-tab6 at clients/clients.css:1,48,81;clients/daily-health-forecast.css:13;design-system.css:323;recommendation/uv.css:18. layout-transition3 at design-system.css:385;result-detail/result-detail.css:532,683. overused-font1 prototype.css:1. gradient-text2 prototype.css:18,34. None directly identifies container-width/overflow. Legacy override and redirect relevance must be checked; do not redesign width based on these warnings. No reliable injected overlay: evaluate is read-only; no visualization server started.

## Minor observations

Home footer inner1600 differs from hero/daily grid1789 at1920. Home earlier1600 cap is overridden by later1920 rule; clarify container ownership in a future edit. Exact390px all-route check covered current available states, not every authenticated result/form/error state. No P0/P1 width blocker confirmed.

## Questions to consider

Choose shared outer navbar/workspace grid versus preserve1504 floating navbar and align headers only. Choose top3 width fixes versus all4 with shared tokens, retaining Profile1240 and form520. No layout changes authorized by this critique-only request.
