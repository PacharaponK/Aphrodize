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
  target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
} }).outputText;
let language = "en";
const loaded = { exports: {} };
new Function("require", "module", "exports", compiled)(name => name === "@/components/language-provider"
  ? { useLanguage: () => ({ language }) } : require(name), loaded, loaded.exports);
const absent = { level: null, status: "model_not_ready" };
const prediction = { level: null, status: "predicted", value_0_10: 6.2,
  target_date: "2026-10-06", model_id: "review-approved-test-model", target: "perceived_thirst" };
function render(signal = prediction, acneReadiness) {
  return renderToStaticMarkup(React.createElement(loaded.exports.default, { interpretation: {
    daily_health_summary: absent, skin_care_attention_level: absent,
    acne_flare_signal: { level: null, status: "not_supported" },
    next_day_predictions: { low_energy_signal: absent, thirst_attention: signal },
    profile_guidance: [],
  }, ...(acneReadiness ? { acneReadiness } : {}) }));
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

test("removed acne signal stays hidden for legacy historical responses", () => {
  const html = render(absent);
  assert.doesNotMatch(html, /Acne signal|Forecast model not enabled|Current account data readiness|acne-observation-title/);
  assert.match(html, /Next-day energy/);
  assert.match(html, /Next-day thirst/);
});

test("current assessment and outlook are separate; unavailable outcomes have one honest action", () => {
  const html = render(absent);
  assert.match(html, /daily-risk-current/);
  assert.match(html, /daily-risk-outlook/);
  assert.equal((html.match(/<article /g) ?? []).length, 2);
  assert.equal((html.match(/Record observed outcomes/g) ?? []).length, 1);
  assert.match(html, /review and approval are still required/);
  const invalid = render({ ...prediction, value_0_10: 11 });
  assert.doesNotMatch(invalid, /11 \/ 10|Experimental estimate/);
  assert.match(invalid, /Unavailable/);
});

test("guidance is unique and preserves references in closed disclosures", () => {
  const html = renderToStaticMarkup(React.createElement(loaded.exports.default, {
    date: "2026-10-06", guidance: ["คำแนะนำซ้ำ", "คำแนะนำอื่น"], interpretation: {
      daily_health_summary: { ...absent, recommendations: ["คำแนะนำซ้ำ"] },
      skin_care_attention_level: { ...absent, recommendations: ["คำแนะนำซ้ำ"] },
      next_day_predictions: { low_energy_signal: { ...prediction, target: "perceived_energy", value_0_10: 0 }, thirst_attention: prediction },
      profile_guidance: [{ topic: "skin", message: "คำแนะนำซ้ำ", reference_url: "https://example.org/source", reference_label: "Source" }],
    },
  }));
  assert.equal((html.match(/คำแนะนำซ้ำ/g) ?? []).length, 1);
  assert.match(html, /คำแนะนำอื่น/);
  assert.match(html, /href="https:\/\/example.org\/source"/);
  assert.match(html, /0 \/ 10/);
  assert.match(html, /higher means more energy/);
  assert.match(html, /<details class="daily-risk-guidance">/);
  assert.match(html, /<details class="daily-risk-provenance">/);
  assert.doesNotMatch(html, /<details[^>]* open/);
});

test("Thai grouping and resilient headers retain readable controls", () => {
  language = "th";
  const html = render(absent);
  assert.match(html, /จากบันทึกของคุณ/);
  assert.match(html, /แนวโน้มวันถัดไป/);
  language = "en";
  const css = fs.readFileSync(new URL("../src/app/clients/clients.css", import.meta.url), "utf8");
  assert.match(css, /\.clients-page \.health-signal-heading \{[^}]*flex-wrap: wrap/);
  assert.match(css, /\.clients-page \.health-signal-heading \.health-signal-level \{[^}]*white-space: normal/);
  assert.match(css, /daily-risk-provenance\) summary \{[^}]*min-height: 44px/);
});
