import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import { NextRequest } from "next/server.js";

const root = path.resolve("src");
const date = "2026-10-06";
const unavailable = { status: "not_available", level: null };
const saved = { local_date: date, prediction_target_date: "2026-10-07", prediction_status: "predicted",
  prediction_model_id: "saved-test-model", input_domain_status: "in_domain",
  input: { sleep_duration_total_minutes: 397, water_intake_ml: 1700, outdoor_exposure_choice: 1 },
  calculated: { sleep_score_0_100: 73.5 },
  predictions: { thirst_score_0_10: { value: 0, status: "calculated" }, skin_dryness_score_0_10: { value: 4.2, status: "predicted" } },
  interpretation: { daily_health_summary: unavailable, skin_care_attention_level: unavailable,
    next_day_predictions: { low_energy_signal: unavailable, thirst_attention: unavailable }, profile_guidance: [] } };

// Same SSR seam as existing tracker tests, with state retained between renders
// and mount effects executed to exercise the HTTP restore path. No real account data.
function mountTracker() {
  const modules = new Map(), states = [], refs = [], effects = [];
  let si = 0, ri = 0, first = true;
  function load(filename) {
    if (modules.has(filename)) return modules.get(filename).exports;
    const mod = { exports: {} }; modules.set(filename, mod);
    const require = createRequire(filename);
    const code = ts.transpileModule(fs.readFileSync(filename, "utf8"), { compilerOptions: {
      module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
    new Function("require", "module", "exports", code)(name => {
      if (filename.endsWith("daily-health-tracker.tsx") && name === "react") return { ...React,
        useState: initial => { const index = si++; if (!(index in states)) states[index] = typeof initial === "function" ? initial() : initial;
          return [states[index], value => { states[index] = typeof value === "function" ? value(states[index]) : value; }]; },
        useRef: initial => { const index = ri++; refs[index] ??= { current: initial }; return refs[index]; },
        useEffect: effect => { if (first) effects.push(effect); } };
      if (name.startsWith("@/") || name.startsWith(".")) {
        const base = name.startsWith("@/") ? path.join(root, name.slice(2)) : path.resolve(path.dirname(filename), name);
        if (base.endsWith("language-provider")) return { useLanguage: () => ({ language: "en" }) };
        const file = [base + ".tsx", base + ".ts"].find(fs.existsSync);
        if (file) return load(file);
      }
      return require(name);
    }, mod, mod.exports);
    return mod.exports;
  }
  const Tracker = load(path.join(root, "app/clients/daily-health-tracker.tsx")).default;
  const render = () => { si = ri = 0; return renderToStaticMarkup(React.createElement(Tracker, { initialDate: date })); };
  render(); first = false;
  for (const effect of effects) effect();
  return { render, settle: async () => { await new Promise(setImmediate); await new Promise(setImmediate); } };
}

test("refresh restores today's persisted scores without requesting a new prediction", async context => {
  context.mock.method(globalThis, "fetch", async (url, options) => {
    if (String(url).includes("/entries")) {
      const query = new URL(String(url), "http://test.local").searchParams;
      assert.equal(query.get("from_date"), date); assert.equal(query.get("to_date"), date);
      assert.equal(options.cache, "no-store");
      return Response.json({ items: [saved] });
    }
    assert.ok(String(url).endsWith("/profile"), "refresh must not invoke predict or POST");
    return Response.json({ has_session: true });
  });
  for (let refresh = 0; refresh < 2; refresh++) {
    const page = mountTracker(); await page.settle();
    const html = page.render();
    assert.match(html, /6 hr 37 min/);
    assert.match(html, /73\.5/);
    assert.match(html, /4\.2/);
    assert.match(html, /0\.0/);
    assert.doesNotMatch(html, /No entry for today/);
  }
});

test("refresh never substitutes yesterday's result for an empty today", async context => {
  context.mock.method(globalThis, "fetch", async url => Response.json(String(url).includes("/entries")
    ? { items: [{ ...saved, local_date: "2026-10-05" }] } : { has_session: true }));
  const page = mountTracker(); await page.settle();
  assert.match(page.render(), /No entry for today/);
  assert.doesNotMatch(page.render(), /6 hr 37 min/);
});

test("failed restore is not presented as missing data and offers retry", async context => {
  context.mock.method(globalThis, "fetch", async url => String(url).includes("/entries")
    ? Response.json({}, { status: 503 }) : Response.json({ has_session: true }));
  const page = mountTracker(); await page.settle();
  assert.match(page.render(), /Could not load today&#x27;s result|Could not load today's result/);
  assert.match(page.render(), /Retry loading/);
  assert.doesNotMatch(page.render(), /No entry for today/);
});

function entryApi() {
  const modules = new Map();
  function load(filename) {
    if (modules.has(filename)) return modules.get(filename).exports;
    const mod = { exports: {} }; modules.set(filename, mod);
    const require = createRequire(filename);
    const code = ts.transpileModule(fs.readFileSync(filename, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
    new Function("require", "module", "exports", code)(name => name.startsWith("@/")
      ? load(path.join(root, name.slice(2) + ".ts")) : require(name), mod, mod.exports);
    return mod.exports;
  }
  return load(path.join(root, "app/api/daily-health/entries/route.ts"));
}

test("today's GET verifies account ownership, forwards the date window and is never cached", async context => {
  const owner = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  context.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(options.cache, "no-store");
    assert.equal(options.headers.Authorization, "Bearer test-session");
    if (String(url).endsWith("/auth/profile")) return Response.json({ user_id: owner });
    const request = new URL(url);
    assert.ok(request.pathname.endsWith(`/users/${owner}/entries`));
    assert.equal(request.searchParams.get("from_date"), date);
    assert.equal(request.searchParams.get("to_date"), date);
    return Response.json({ items: [saved] });
  });
  const response = await entryApi().GET(new NextRequest(`http://test.local/api/daily-health/entries?from_date=${date}&to_date=${date}&limit=1`, { headers: { cookie: "aphrodize_session=test-session" } }));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { items: [saved] });
});

test("signed-out GET exposes no health records", async context => {
  context.mock.method(globalThis, "fetch", async () => assert.fail("No session must not access the backend"));
  const response = await entryApi().GET(new NextRequest("http://test.local/api/daily-health/entries"));
  assert.deepEqual(await response.json(), { items: [] });
  assert.equal(response.headers.get("cache-control"), "no-store");
});
