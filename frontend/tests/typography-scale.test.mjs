import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = path => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const css = read("../src/app/design-system.css");

test("shared reading roles are rem-based and data headings stay 24–28px", () => {
  for (const token of ["--text-body: 1rem", "--text-secondary: .875rem", "--text-meta: .8125rem", "--text-chart: .75rem"]) {
    assert.ok(css.includes(token));
  }
  assert.match(css, /--text-section: clamp\(1\.5rem, 1\.4vw, 1\.75rem\)/);
  assert.match(css, /\.profile-info-section h2/);
  assert.match(css, /\.personal-forecast-panel-heading h2/);
  assert.match(css, /\.capture-permissions-heading h2/);
});

test("navigation changes layout rather than shrinking labels", () => {
  assert.match(css, /@media\(min-width:1201px\)/);
  assert.match(css, /\.app-navigation-links \.nav-link\{[^}]*font-size:var\(--text-body\)/);
  assert.doesNotMatch(css, /\.nav-link\{font-size:11px/);
});

test("consent and essential chart labels use reading roles", () => {
  assert.doesNotMatch(css, /\.signup-consent[^}]*12px\s*!important/);
  assert.match(css, /:root \.personal-forecast-legend \{ font-size: var\(--text-secondary\)/);
  assert.match(css, /:root \.uv-map-legend small \{ font-size: var\(--text-meta\)/);
  assert.match(css, /\.capture-consent-copy, \.capture-privacy, \.auth-privacy/);
});

test("forecast dates do not scale down with the SVG", () => {
  const chart = read("../src/app/clients/daily-health-forecast-trend.tsx");
  assert.match(chart, /className="personal-forecast-axis-dates"/);
  assert.doesNotMatch(chart, /<text className="personal-forecast-axis-label"/);
  assert.match(chart, /data-series="actual"/);
  assert.match(chart, /data-series="forecast"/);
  assert.match(css, /\.personal-forecast-axis-dates \{[^}]*font-size: var\(--text-chart\)/);
});
