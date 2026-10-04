import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const source = fs.readFileSync(new URL("../src/app/clients/daily-health-risk-results.tsx", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
} }).outputText;
const loaded = { exports: {} };
new Function("require", "module", "exports", compiled)(name => name === "@/components/language-provider"
  ? { useLanguage: () => ({ language: "en" }) } : require(name), loaded, loaded.exports);
const absent = { level: null, status: "model_not_ready" };
const prediction = { level: null, status: "predicted", value_0_10: 6.2,
  target_date: "2026-10-06", model_id: "review-approved-test-model", target: "perceived_thirst" };
function render(signal = prediction) {
  return renderToStaticMarkup(React.createElement(loaded.exports.default, { interpretation: {
    daily_health_summary: absent, skin_care_attention_level: absent,
    acne_flare_signal: { level: null, status: "not_supported" },
    next_day_predictions: { low_energy_signal: absent, thirst_attention: signal },
    profile_guidance: [],
  } }));
}
test("observed forecast renders value, target day and source without fabricated risk grade", () => {
  const html = render();
  assert.match(html, /6\.2 \/ 10/);
  assert.match(html, /dateTime="2026-10-06"/i);
  assert.match(html, /review-approved-test-model/);
  assert.match(html, /not the weight-based water formula/);
  assert.match(html, /Experimental estimate/);
  assert.doesNotMatch(html, /health-signal-high/);
});
test("unsupported acne is distinct from undeployed energy and thirst models", () => {
  const html = render(absent);
  assert.match(html, /Not supported yet/);
  assert.match(html, /Model not ready/);
  assert.doesNotMatch(html, /Not enough self-reported/);
  assert.match(html, /Record observed outcomes/);
});
