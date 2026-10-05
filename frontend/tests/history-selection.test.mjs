import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createRequire } from "node:module";

function compile(path, overrides = {}) {
  const filename = new URL(path, import.meta.url);
  const nativeRequire = createRequire(filename);
  const source = fs.readFileSync(filename, "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } }).outputText;
  const evaluated = { exports: {} };
  new Function("require", "module", "exports", compiled)(name => {
    if (name in overrides) return overrides[name];
    if (name.startsWith(".")) {
      const dependency = new URL(`${name}.tsx`, filename);
      if (fs.existsSync(dependency)) return compile(dependency, overrides);
    }
    return nativeRequire(name);
  }, evaluated, evaluated.exports);
  return evaluated.exports;
}
const { selectHistoryDays } = compile("../src/lib/history-selection.ts");
const row = local_date => ({ local_date });

test("latest view sorts without mutating and limits to three actual days in an inclusive 30-day window", () => {
  const items = ["2026-10-01", "2026-09-06", "2026-10-05", "2026-10-06", "2026-10-03", "2026-09-05"].map(row);
  const original = [...items];
  assert.deepEqual(selectHistoryDays(items, "2026-09-06", "2026-10-05").map(item => item.local_date),
    ["2026-10-05", "2026-10-03", "2026-10-01"]);
  assert.deepEqual(items, original);
  assert.equal(selectHistoryDays(items, "2026-09-06", "2026-10-05", "2026-09-06").length, 1);
});

test("date search finds older records and never substitutes missing, out-of-window or future dates", () => {
  const items = ["2026-09-05", "2026-09-12", "2026-10-05", "2026-10-06"].map(row);
  assert.deepEqual(selectHistoryDays(items, "2026-09-06", "2026-10-05", "2026-09-12"), [row("2026-09-12")]);
  for (const date of ["2026-09-05", "2026-10-06", "2026-09-13"]) {
    assert.deepEqual(selectHistoryDays(items, "2026-09-06", "2026-10-05", date), []);
  }
  assert.deepEqual(selectHistoryDays([], "2026-09-06", "2026-10-05"), []);
});

const absent = { level: null, status: "insufficient_history" };
const available = { level: "moderate", status: "available", recommendations: ["Recorded advice"] };
const item = { local_date: "2026-10-04", prediction_target_date: "2026-10-05",
  input: { sleep_duration_total_minutes: 397, water_intake_ml: 0, outdoor_exposure_choice: 1 },
  calculated: { sleep_score_0_100: 80 },
  predictions: { thirst_score_0_10: { status: "not_available", value: null }, skin_dryness_score_0_10: { status: "not_available", value: null } },
  interpretation: { daily_health_summary: available, skin_care_attention_level: available,
    acne_flare_signal: absent, next_day_predictions: { low_energy_signal: absent, thirst_attention: absent }, profile_guidance: [] } };

function renderHistory({ selected = "", search = "", language = "en", view = "trend" } = {}) {
  let index = 0;
  const states = [{ items: [item] }, false, false, 0, search, selected, "2026-10-05"];
  const exports = compile("../src/app/clients/daily-health-history-panel.tsx", {
    react: { ...React, useEffect: () => {}, useState: initial => [index < states.length ? states[index++] : typeof initial === "function" ? initial() : initial, () => {}] },
    "next/link": { __esModule: true, default: ({ children, ...props }) => React.createElement("a", props, children) },
    "@/components/language-provider": { useLanguage: () => ({ language }) },
    "@/lib/history-selection": { selectHistoryDays },
    "./daily-health-risk-results": { __esModule: true, default: () => React.createElement("p", null, "Full recorded results") },
  });
  return renderToStaticMarkup(React.createElement(exports.default, { view }));
}

test("trend renders bounded date controls, closed details, real zero and prediction target", () => {
  const html = renderHistory();
  assert.match(html, /min="2026-09-06"/);
  assert.match(html, /max="2026-10-05"/);
  assert.match(html, /Back to latest/);
  assert.match(html, /<details class="daily-history-details">/);
  assert.doesNotMatch(html, /<details[^>]*open/);
  assert.match(html, /3 signals not assessed/);
  assert.match(html, /0 ml/);
  assert.match(html, /Forecast signals for/);
  assert.match(html, /Full recorded results/);
});

test("missing date has a localized empty state, not the latest record", () => {
  const html = renderHistory({ selected: "2026-09-12", search: "2026-09-12", language: "th" });
  assert.match(html, /ไม่มีบันทึกวันที่/);
  assert.match(html, /กลับวันล่าสุด/);
  assert.doesNotMatch(html, /Full recorded results/);
});

test("weekly overview keeps full results and no trend search", () => {
  const html = renderHistory({ view: "overview" });
  assert.doesNotMatch(html, /history-search-date|daily-history-details/);
  assert.match(html, /Full recorded results/);
});
