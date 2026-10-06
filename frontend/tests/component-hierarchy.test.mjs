import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import postcss from "postcss";

const read = (path) => fs.readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const hierarchy = postcss.parse(read("src/app/component-hierarchy.css"));
const design = postcss.parse(read("src/app/design-system.css"));

function palette(theme) {
  const tokens = {};
  for (const sheet of [design, hierarchy]) sheet.walkRules((rule) => {
    if (rule.selector !== ":root" && !(theme === "black" && rule.selector === 'html[data-theme="black"]')) return;
    rule.walkDecls((d) => { if (d.prop.startsWith("--")) tokens[d.prop] = d.value; });
  });
  const resolve = (value) => value.startsWith("var(") ? resolve(tokens[value.slice(4, -1)]) : value;
  return Object.fromEntries(Object.entries(tokens).filter(([, value]) => /^#|^var\(--(?:surface|primary|ink|muted)/.test(value)).map(([name, value]) => [name, resolve(value)]));
}

function luminance(hex) {
  let raw = hex.slice(1);
  if (raw.length === 3) raw = [...raw].map((c) => c + c).join("");
  const channels = raw.match(/../g).map((c) => parseInt(c, 16) / 255).map((c) => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4);
  return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
}
function contrast(a, b) {
  const [lighter, darker] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (lighter + .05) / (darker + .05);
}

for (const theme of ["pastel", "black"]) {
  test(`${theme}: hierarchy text, controls and status tokens reach 4.5:1`, () => {
    const p = palette(theme);
    const pairs = [
      ["--ink", "--surface-prominent"], ["--muted", "--surface-supporting"],
      ["--muted", "--surface-context"], ["--ink-soft", "--surface-supporting"],
      ["--primary-foreground", "--primary"], ["--primary-foreground", "--primary-hover"],
      ["--primary-deep", "--primary-soft"], ["--danger", "--surface-prominent"],
      ["--danger", "--danger-surface"], ["--success-ink", "--success-surface"],
      ["--success-ink", "--surface-prominent"],
    ];
    for (const [foreground, background] of pairs) {
      const ratio = contrast(p[foreground], p[background]);
      assert.ok(ratio >= 4.5, `${foreground} on ${background}: ${ratio.toFixed(2)}:1`);
    }
  });
}

test("the layout loads shared hierarchy once and the persistent boundary covers routes", () => {
  assert.equal(read("src/app/layout.tsx").match(/import "\.\/component-hierarchy\.css";/g)?.length, 1);
  assert.match(read("src/components/page-transition.tsx"), /data-color-system="hierarchical"/);
  assert.doesNotMatch(read("src/components/page-transition.tsx"), /key=\{pathname\}/);
});

test("all route families have deliberate color roles without layout or metric mutations", () => {
  const css = hierarchy.toString();
  for (const route of ["home-dashboard-shell", "clients-page", "trend-page", "profile-panel", "auth-card", "onboarding-card", "capture-image-area", "analysis-page--face", "recommendation-filters", "uv-map-detail", "admin-products-page", "quality-panel", "showcase-grid"]) assert.ok(css.includes(`.${route}`), route);
  hierarchy.walkDecls((decl) => {
    assert.equal(decl.important, undefined, "avoid !important cascade patches");
    assert.ok(!["width", "height", "display", "position", "transform", "animation", "fill", "stroke", "font-size"].includes(decl.prop), `outside color scope: ${decl.prop}`);
  });
  assert.doesNotMatch(css, /\.health-signal-(low|moderate|high)\s|\.uv-map-legend\s|path\[role/);
});

test("selected UV and forecast alerts consume defined theme-aware tokens", () => {
  const rules = [];
  hierarchy.walkRules((r) => rules.push(r));
  const selected = rules.find((r) => r.selector.includes(".uv-map-source") && r.selector.includes('[aria-pressed="true"]'));
  const values = Object.fromEntries(selected.nodes.filter((n) => n.type === "decl").map((d) => [d.prop, d.value]));
  assert.equal(values.color, "var(--primary-deep)");
  assert.equal(values.background, "var(--primary-soft)");
  for (const theme of ["pastel", "black"]) assert.ok(palette(theme)["--danger"]);
  assert.match(hierarchy.toString(), /\.form-message\.success \{ color: var\(--success-ink\); \}/);
});
