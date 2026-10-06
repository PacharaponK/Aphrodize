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

const { ForecastLineChart, forecastAxis } = loadTsx(
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

test("Y axes use displayed units and cover actual plus forecast extremes", () => {
  const sleep = forecastAxis("sleep_duration_minutes", [240, 360, 480, 600]);
  assert.ok(sleep.lower <= 4 && sleep.upper >= 10);
  assert.ok(sleep.ticks.includes(6) && sleep.ticks.includes(8));
  assert.equal(sleep.pointPosition(360), sleep.position(6));
  const water = forecastAxis("water_intake_ml", [1000, 1500, 2000]);
  assert.ok(water.ticks.includes(1000) && water.ticks.includes(1500) && water.ticks.includes(2000));
  assert.ok(water.lower <= 1000 && water.upper >= 2000);
  for (const metric of ["sleep_duration_minutes", "water_intake_ml"]) {
    for (const values of [[], [0, 0], [300, 300], [0, 20000]]) {
      const axis = forecastAxis(metric, values);
      assert.ok(axis.upper > axis.lower);
      assert.ok(axis.ticks.length >= 2 && axis.ticks.length <= 9);
      assert.ok(Number.isFinite(axis.pointPosition(0)));
    }
  }
});

test("point values are HTML labels, preserve zero and gaps, and distinguish the forecast", () => {
  const actual = Array.from({ length: 7 }, (_, i) => ({ local_date: `2026-09-${24 + i}`, sleep_duration_minutes: i === 3 ? null : 360, water_intake_ml: i === 3 ? null : i === 0 ? 0 : 1500 }));
  const html = renderToStaticMarkup(React.createElement(ForecastLineChart, {
    metric: "water_intake_ml", language: "en", actual, targetDate: "2026-10-01", forecastValue: 2000,
  }));
  assert.match(html, /personal-forecast-y-axis/);
  assert.match(html, /personal-forecast-y-unit">ml/);
  assert.match(html, /personal-forecast-y-tick[^>]*>1,000/);
  assert.equal((html.match(/class="personal-forecast-grid-line"/g) ?? []).length, (html.match(/class="personal-forecast-y-tick"/g) ?? []).length);
  assert.equal((html.match(/class="personal-forecast-point-value"/g) ?? []).length, 6);
  assert.match(html, /class="personal-forecast-point-value"[^>]*>0<\/span>/);
  assert.match(html, /class="personal-forecast-point-value is-forecast"[^>]*>2,000<\/span>/);
  assert.equal((html.match(/class="personal-forecast-actual-line"/g) ?? []).length, 4);
  assert.match(html, /tabindex="0" role="region"/);
  assert.doesNotMatch(html, /<svg[^]*?<text/);
});

test("Thai sleep labels convert minutes to hours without inventing a missing forecast", () => {
  const html = renderToStaticMarkup(React.createElement(ForecastLineChart, {
    metric: "sleep_duration_minutes", language: "th",
    actual: [{ local_date: "2026-09-24", sleep_duration_minutes: 450, water_intake_ml: null }],
    targetDate: "2026-09-25", forecastValue: null,
  }));
  assert.match(html, /personal-forecast-y-unit">ชั่วโมง/);
  assert.match(html, /class="personal-forecast-point-value"[^>]*>7\.5<\/span>/);
  assert.doesNotMatch(html, /personal-forecast-point-value is-forecast/);
  assert.doesNotMatch(html, /class="personal-forecast-next-line"/);
  assert.match(html, /ยังไม่มีค่าพยากรณ์/);
});
