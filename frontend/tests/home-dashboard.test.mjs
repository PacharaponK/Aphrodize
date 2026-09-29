// Run: node --test tests/home-dashboard.test.mjs (from frontend/).
import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
const testDirectory = path.dirname(fileURLToPath(import.meta.url));

// Compile the real TSX in memory; no extra test runner or generated files.
function loadTsx(filename) {
  const evaluatedModule = { exports: {} };
  const nativeRequire = createRequire(filename);
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const requireLocal = (name) => {
    const local = path.resolve(path.dirname(filename), `${name}.tsx`);
    return name.startsWith(".") && fs.existsSync(local) ? loadTsx(local) : nativeRequire(name);
  };
  new Function("require", "module", "exports", source)(requireLocal, evaluatedModule, evaluatedModule.exports);
  return evaluatedModule.exports;
}
const { DashboardHistory } = loadTsx(path.resolve(testDirectory, "../src/app/clients/daily-health-history-panel.tsx"));
const { AppNavigation } = loadTsx(path.resolve(testDirectory, "../src/components/app-navigation.tsx"));
const render = (props = {}) => renderToStaticMarkup(React.createElement(DashboardHistory, {
  items: [], loading: false, failed: false, requiresLogin: false, onRetry() {}, ...props,
}));

test("the looping decorative video belongs to main, not an article", () => {
  const filename = path.resolve(testDirectory, "../src/app/page.tsx");
  const source = ts.createSourceFile(filename, fs.readFileSync(filename, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const videoParents = [];
  function visit(node, ancestors = []) {
    const tag = ts.isJsxElement(node) ? node.openingElement.tagName.getText(source)
      : ts.isJsxSelfClosingElement(node) ? node.tagName.getText(source) : null;
    if (tag === "HomeMotionVideo") videoParents.push(ancestors);
    ts.forEachChild(node, (child) => visit(child, tag ? [...ancestors, tag] : ancestors));
  }
  visit(source);
  assert.equal(videoParents.length, 1);
  assert.deepEqual(videoParents[0].slice(-2), ["main", "figure"]);
  assert.equal(videoParents[0].includes("article"), false);
  const videoSource = fs.readFileSync(path.resolve(testDirectory, "../src/components/home-motion-video.tsx"), "utf8");
  assert.match(videoSource, /\n\s+loop\n/);
  assert.match(videoSource, /\n\s+muted\n/);
  assert.match(videoSource, /\n\s+playsInline\n/);
});

test("logged-out, loading and error states do not fabricate scores or records", () => {
  for (const state of [{ requiresLogin: true }, { loading: true }, { failed: true }]) {
    const html = render(state);
    assert.equal((html.match(/class="home-metric-card"/g) || []).length, 4);
    assert.equal(html.includes("home-metric-chart"), false);
    assert.equal(html.includes("is-recorded"), false);
  }
  assert.match(render({ requiresLogin: true, loading: true }), /href="\/login"/);
  assert.match(render({ failed: true }), /Retry/);
});

test("zero is valid, unavailable predictions are excluded, and missing days remain gaps", () => {
  const date = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Bangkok" }).format(new Date());
  const absent = { level: null, status: "not_available" };
  const item = {
    local_date: date, prediction_target_date: null, input: { sleep_duration_total_minutes: 480, water_intake_ml: 1000, outdoor_exposure_choice: 1 },
    calculated: { sleep_score_0_100: 0 },
    predictions: { thirst_score_0_10: { status: "not_available", value: 9 }, skin_dryness_score_0_10: { status: "predicted", value: 0 } },
    interpretation: { daily_health_summary: absent, skin_care_attention_level: absent, acne_flare_signal: absent, next_day_predictions: { low_energy_signal: absent, thirst_attention: absent }, profile_guidance: [] },
  };
  const html = render({ items: [item] });
  assert.equal((html.match(/home-day is-recorded/g) || []).length, 1);
  assert.equal((html.match(/class="home-metric-chart"/g) || []).length, 3);
  assert.match(html, /0\.0 <span>\/ 100/);
  assert.match(html, /0\.0 <span>\/ 10/);
  assert.match(html, /1\/7 days with data/);
  assert.equal((html.match(/<rect /g) || []).length, 3);
});

test("dashboard chrome defaults to English without inventing personal content", () => {
  const html = render();
  for (const label of ["Your last 7 days", "Weekly overview", "Log today", "Personal insights", "No data yet"]) assert.ok(html.includes(label));
  assert.match(html, /lang="en"/);
  assert.equal(/[\u0E00-\u0E7F]/u.test(html), false);
});

test("Home navigation starts in English without changing other pages' default", () => {
  const english = renderToStaticMarkup(React.createElement(AppNavigation, { active: "dashboard", initialLanguage: "en" }));
  assert.match(english, /aria-label="Open menu"/);
  assert.match(english, />Overview</);
  assert.match(english, />Daily health</);
  assert.equal(/[\u0E00-\u0E7F]/u.test(english), false);
  const unchanged = renderToStaticMarkup(React.createElement(AppNavigation, { active: "clients" }));
  assert.match(unchanged, /aria-label="เปิดเมนู"/);
  assert.match(unchanged, /สุขภาพรายวัน/);
});
