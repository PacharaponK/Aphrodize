import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const filename = fileURLToPath(new URL("../src/components/analysis/analysis-loader.tsx", import.meta.url));
const nativeRequire = createRequire(filename);
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const evaluated = { exports: {} };
new Function("require", "module", "exports", compiled)(name => name.endsWith(".css") ? {} : nativeRequire(name), evaluated, evaluated.exports);
const { AnalysisLoader } = evaluated.exports;

test("loader uses actual brand paths and preserves a single honest status", () => {
  const paths = nativeRequire("./brand-logo-paths.json");
  const original = fs.readFileSync(new URL("../public/assets/aphrodize-logo.svg", import.meta.url), "utf8");
  for (const d of paths) assert.ok(original.includes(`d="${d}"`));
  const html = renderToStaticMarkup(React.createElement(AnalysisLoader, { message: "Queued for processing", language: "en" }));
  assert.equal((html.match(/<path /g) ?? []).length, paths.length * 2);
  assert.equal((html.match(/role="status"/g) ?? []).length, 1);
  assert.match(html, /Queued for processing/);
  assert.match(html, /Pause animation/);
  assert.doesNotMatch(html, /%|progressbar/);
});

test("Thai waiting state and controls are localized", () => {
  const html = renderToStaticMarkup(React.createElement(AnalysisLoader, { message: "กำลังประมวลผลภาพ", language: "th" }));
  assert.match(html, /กำลังประมวลผลภาพ/);
  assert.match(html, /หยุดภาพเคลื่อนไหว/);
  assert.match(html, /ไม่ใช่ความคืบหน้าหรือผลวิเคราะห์/);
});
