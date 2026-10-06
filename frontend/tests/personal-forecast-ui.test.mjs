// Run: node --test tests/personal-forecast-ui.test.mjs (from frontend/).
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
const moduleCache = new Map();

function loadTsx(filename) {
  filename = path.resolve(filename);
  if (moduleCache.has(filename)) return moduleCache.get(filename).exports;
  const loaded = { exports: {} };
  moduleCache.set(filename, loaded);
  const nativeRequire = createRequire(filename);
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const localRequire = (name) => {
    if (name.startsWith("@/")) {
      const base = path.resolve(testDirectory, "../src", name.slice(2));
      const localPath = [`${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate));
      if (localPath) return loadTsx(localPath);
    }
    if (name.startsWith(".")) {
      const base = path.resolve(path.dirname(filename), name);
      const localPath = [`${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate));
      if (localPath) return loadTsx(localPath);
    }
    return nativeRequire(name);
  };
  new Function("require", "module", "exports", source)(localRequire, loaded, loaded.exports);
  return loaded.exports;
}

const { ForecastLineChart } = loadTsx(
  path.resolve(testDirectory, "../src/app/clients/daily-health-forecast-trend.tsx"),
);

test("forecast graph separates actual sleep readings from the next-day estimate", () => {
  const html = renderToStaticMarkup(React.createElement(ForecastLineChart, {
    metric: "sleep_duration_minutes",
    language: "en",
    actual: [
      { local_date: "2026-09-24", sleep_duration_minutes: 360, water_intake_ml: 1200 },
      { local_date: "2026-09-25", sleep_duration_minutes: 390, water_intake_ml: 1300 },
      { local_date: "2026-09-26", sleep_duration_minutes: 420, water_intake_ml: 1400 },
      { local_date: "2026-09-27", sleep_duration_minutes: null, water_intake_ml: null },
      { local_date: "2026-09-28", sleep_duration_minutes: 450, water_intake_ml: 1500 },
      { local_date: "2026-09-29", sleep_duration_minutes: 480, water_intake_ml: 1600 },
      { local_date: "2026-09-30", sleep_duration_minutes: 510, water_intake_ml: 1700 },
    ],
    targetDate: "2026-10-01",
    forecastValue: 540,
  }));

  assert.match(html, /role="img"/);
  assert.match(html, /Actual/);
  assert.match(html, /Next-day forecast/);
  assert.match(html, /class="personal-forecast-actual-line"/);
  assert.match(html, /class="personal-forecast-next-line"/);
  assert.match(html, /data-evidence="recorded"/);
  assert.match(html, /data-evidence="forecast"/);
  assert.match(html, /personal-forecast-next-summary/);
  assert.match(html, /data-series="forecast"/);
  assert.match(html, /7\.5/);
  assert.match(html, /2026-10-01/);
});
