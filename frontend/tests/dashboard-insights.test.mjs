import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { createRequire } from "node:module";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const base = new URL("../src/app/clients/", import.meta.url);
let language = "en";
function load(name) {
  const filename = new URL(name, base);
  const nativeRequire = createRequire(filename);
  const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const testModule = { exports: {} };
  new Function("require", "module", "exports", compiled)(dependency => {
    if (dependency === "next/link") return { __esModule: true, default: ({ children, ...props }) => React.createElement("a", props, children) };
    if (dependency === "./daily-health-risk-results") return load("daily-health-risk-results.tsx");
    if (dependency === "@/components/language-provider") return { useLanguage: () => ({ language }) };
    return nativeRequire(dependency);
  }, testModule, testModule.exports);
  return testModule.exports;
}
const Insights = load("dashboard-insights.tsx").default;
const render = props => renderToStaticMarkup(React.createElement(Insights, {
  loading: false, failed: false, requiresLogin: false, onRetry() {}, language, dateLabel: date => date, ...props,
}));
const unavailable = { level: null, status: "model_not_ready" };
const latest = { local_date: "2026-10-04", interpretation: {
  daily_health_summary: { level: "moderate", status: "available", headline: "ข้อความสรุปเดิม", recommendations: ["ข้อหนึ่ง", "ข้อสอง", "ข้อสาม"] },
  skin_care_attention_level: { level: "moderate", status: "available", recommendations: ["ข้อหนึ่ง", "ข้อสี่"] },
  acne_flare_signal: { level: null, status: "not_supported" },
  next_day_predictions: { low_energy_signal: unavailable, thirst_attention: { ...unavailable } },
  profile_guidance: [{ topic: "test", status: "available", message: "คำแนะนำโปรไฟล์เดิม" }],
} };

test("login, loading, failure and empty states are distinct and hide saved results", () => {
  for (const [props, copy, action] of [
    [{ requiresLogin: true, latest }, "Sign in to see insights", 'href="/login"'],
    [{ loading: true, latest }, "Loading your insights", 'role="status"'],
    [{ failed: true, latest }, "Unable to load your insights", "Retry"],
    [{}, "Record your daily health", 'href="/clients"'],
  ]) {
    const html = render(props);
    assert.ok(html.includes(copy)); assert.ok(html.includes(action));
    assert.ok(!html.includes("ข้อความสรุปเดิม"));
  }
});
test("compact summary deduplicates and limits guidance while closed details preserve everything", () => {
  const html = render({ latest });
  const beforeDetails = html.split("<details")[0];
  assert.equal((beforeDetails.match(/ข้อหนึ่ง/g) ?? []).length, 1);
  assert.ok(beforeDetails.includes("ข้อสอง"));
  assert.ok(!beforeDetails.includes("ข้อสาม"));
  assert.match(html, /<details class="home-insights-details">/);
  assert.ok(html.includes("ข้อสาม") && html.includes("ข้อสี่") && html.includes("คำแนะนำโปรไฟล์เดิม"));
  assert.ok(html.includes("3 signals not assessed"));
  assert.match(html, /datetime="2026-10-04"/i);
  assert.ok(!html.includes('<div lang="th">'));
});
test("valid zero forecast retains target, meaning and provenance; invalid values are unavailable", () => {
  const data = structuredClone(latest);
  data.interpretation.next_day_predictions.thirst_attention = {
    level: null, status: "predicted", value_0_10: 0, target: "perceived_thirst", target_date: "2026-10-05", model_id: "actual-model",
  };
  const html = render({ latest: data });
  assert.ok(html.includes("0 / 10") && html.includes("2026-10-05") && html.includes("actual-model"));
  assert.ok(html.includes("not the weight-based water formula"));
  data.interpretation.next_day_predictions.thirst_attention.value_0_10 = 12;
  assert.ok(!render({ latest: data }).includes("12 / 10"));
});
test("Thai controls render without changing stored guidance", () => {
  language = "th";
  const html = render({ latest });
  assert.ok(html.includes("ดูรายละเอียดทุกสัญญาณและวิธีประเมิน"));
  assert.ok(html.includes("ข้อความสรุปเดิม"));
  language = "en";
});
