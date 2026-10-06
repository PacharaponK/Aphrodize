import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import { NextRequest } from "next/server.js";

const root = fileURLToPath(new URL("../", import.meta.url));

// Follow the repository's React SSR harness; keep local UI components real.
function trackerHarness(sex, personalizationConsent = true, language = "en") {
  const cache = new Map();
  let submit;
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const loaded = { exports: {} };
    cache.set(filename, loaded);
    const nativeRequire = createRequire(filename);
    const isTracker = filename.endsWith("daily-health-tracker.tsx");
    const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    function localRequire(name) {
      if (isTracker && name === "react") return { ...React, useEffect: () => {},
        useState: initial => {
          let value = typeof initial === "function" ? initial() : initial;
          if (value && typeof value === "object" && "menstruationChoice" in value) {
            value = { ...value, date: "2026-10-06", sleepHours: "7", sleepMinutes: "0",
              waterIntakeMl: "1500", outdoorChoice: "under_1_hour", consentToStore: true,
              personalizationConsent, menstruationChoice: "yes" };
          } else if (value && typeof value === "object" && "has_session" in value) {
            value = { ...value, has_session: true, sex };
          }
          return [value, () => {}];
        } };
      if (isTracker && name === "react/jsx-runtime") {
        const runtime = nativeRequire(name);
        const wrap = method => (type, props, key) => {
          if (type === "form") submit = props.onSubmit;
          return runtime[method](type, props, key);
        };
        return { ...runtime, jsx: wrap("jsx"), jsxs: wrap("jsxs") };
      }
      if (name.endsWith(".css")) return {};
      if (name.startsWith("@/") || name.startsWith(".")) {
        const base = name.startsWith("@/") ? path.join(root, "src", name.slice(2))
          : path.resolve(path.dirname(filename), name);
        const resolved = [base + ".ts", base + ".tsx", path.join(base, "index.ts")]
          .find(candidate => fs.existsSync(candidate));
        if (resolved) return load(resolved);
      }
      return nativeRequire(name);
    }
    new Function("require", "module", "exports", compiled)(localRequire, loaded, loaded.exports);
    return loaded.exports;
  }
  // Only localization is replaced; the form and its submitted HTTP payload are real.
  const languageFile = path.join(root, "src/components/language-provider.tsx");
  cache.set(languageFile, { exports: { useLanguage: () => ({ language }) } });
  const Tracker = load(path.join(root, "src/app/clients/daily-health-tracker.tsx")).default;
  const html = renderToStaticMarkup(React.createElement(Tracker, { initialDate: "2026-10-06" }));
  return { html, submit: () => submit({ preventDefault() {} }) };
}

test("male daily health form does not ask about periods even with personalization enabled", () => {
  const { html } = trackerHarness("male");
  assert.doesNotMatch(html, /Are you menstruating today|name="period-checkin"|menstrual check-ins/);
  assert.match(html, /Smoking status/);
});

test("male form submits null menstrual context to prediction and storage despite a stale choice", async context => {
  const requests = [];
  context.mock.method(globalThis, "fetch", async (url, options = {}) => {
    if (options.body) requests.push({ url, body: JSON.parse(options.body) });
    return Response.json({}, { status: String(url).endsWith("/predict") ? 503 : 200 });
  });
  await trackerHarness("male").submit();
  assert.equal(requests.find(item => item.url.endsWith("/predict")).body.personal_context.currently_menstruating, null);
  assert.equal(requests.find(item => item.url.endsWith("/entries")).body.currently_menstruating, null);
});

test("female form retains optional menstrual check-in and submits the selected answer", async context => {
  const requests = [];
  context.mock.method(globalThis, "fetch", async (url, options = {}) => {
    if (options.body) requests.push({ url, body: JSON.parse(options.body) });
    return Response.json({}, { status: String(url).endsWith("/predict") ? 503 : 200 });
  });
  const form = trackerHarness("female");
  assert.match(form.html, /Are you menstruating today/);
  await form.submit();
  assert.equal(requests.find(item => item.url.endsWith("/predict")).body.personal_context.currently_menstruating, true);
  assert.equal(requests.find(item => item.url.endsWith("/entries")).body.currently_menstruating, true);
});

function loadRoute(relativePath) {
  const cache = new Map();
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const loaded = { exports: {} };
    cache.set(filename, loaded);
    const nativeRequire = createRequire(filename);
    const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    new Function("require", "module", "exports", compiled)(name => {
      if (name.startsWith("@/")) return load(path.join(root, "src", name.slice(2) + ".ts"));
      return nativeRequire(name);
    }, loaded, loaded.exports);
    return loaded.exports;
  }
  return load(path.join(root, "src", relativePath));
}

test("daily health profile forwards sex from the authenticated account profile", async context => {
  context.mock.method(globalThis, "fetch", async url => Response.json(
    String(url).endsWith("/auth/profile")
      ? { user_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", profile: { sex: "male" } }
      : { consent_active: true, sex: "female" },
  ));
  const { GET } = loadRoute("app/api/daily-health/profile/route.ts");
  const response = await GET(new NextRequest("http://localhost:3000/api/daily-health/profile", {
    headers: { cookie: "aphrodize_session=test-session" },
  }));
  assert.equal(response.status, 200);
  assert.equal((await response.json()).sex, "male");
});
