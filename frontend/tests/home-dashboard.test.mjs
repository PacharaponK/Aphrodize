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
const tsxModuleCache = new Map();

// Compile the real TSX in memory; no extra test runner or generated files.
function loadTsx(filename) {
  filename = path.resolve(filename);
  if (tsxModuleCache.has(filename)) return tsxModuleCache.get(filename).exports;
  const evaluatedModule = { exports: {} };
  tsxModuleCache.set(filename, evaluatedModule);
  const nativeRequire = createRequire(filename);
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const requireLocal = (name) => {
    const localBase = name.startsWith("@/")
      ? path.resolve(testDirectory, "../src", name.slice(2))
      : name.startsWith(".")
        ? path.resolve(path.dirname(filename), name)
        : null;
    if (localBase) {
      const local = [localBase, `${localBase}.tsx`, `${localBase}.ts`, path.join(localBase, "index.tsx")]
        .find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
      if (local) return loadTsx(local);
    }
    return nativeRequire(name);
  };
  new Function("require", "module", "exports", source)(requireLocal, evaluatedModule, evaluatedModule.exports);
  return evaluatedModule.exports;
}
const { DashboardHistory } = loadTsx(path.resolve(testDirectory, "../src/app/clients/daily-health-history-panel.tsx"));
const { AppNavigation, AuthNavigationAction } = loadTsx(path.resolve(testDirectory, "../src/components/app-navigation.tsx"));
const { LanguageProvider } = loadTsx(path.resolve(testDirectory, "../src/components/language-provider.tsx"));
const withLanguage = (node) => React.createElement(LanguageProvider, null, node);
const render = (props = {}) => renderToStaticMarkup(withLanguage(React.createElement(DashboardHistory, {
  items: [], loading: false, failed: false, requiresLogin: false, onRetry() {}, ...props,
})));

test("the looping decorative video belongs to main, not an article", () => {
  const filename = path.resolve(testDirectory, "../src/app/page.tsx");
  const source = ts.createSourceFile(filename, fs.readFileSync(filename, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const pageText = fs.readFileSync(filename, "utf8");
  assert.doesNotMatch(pageText, /legacy\/home\.js/, "the stale legacy script must not inject duplicate navbar controls");
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
  const english = renderToStaticMarkup(withLanguage(React.createElement(AppNavigation, { active: "dashboard", showThemeToggle: true, showSignIn: true })));
  assert.match(english, /aria-label="Open menu"/);
  assert.match(english, />Overview</);
  assert.match(english, />Daily health</);
  assert.match(english, /href="\/login"/);
  assert.match(english, />Sign in</);
  assert.match(english, /aria-label="เปลี่ยนภาษาเป็นไทย"/);
  const unchanged = renderToStaticMarkup(withLanguage(React.createElement(AppNavigation, { active: "clients" })));
  assert.match(unchanged, /aria-label="Open menu"/);
  assert.match(unchanged, /Daily health/);
  assert.match(unchanged, /aria-label="เปลี่ยนภาษาเป็นไทย"/);
  assert.equal(unchanged.includes('class="app-navigation-sign-in"'), false);
  const homeCss = fs.readFileSync(path.resolve(testDirectory, "../src/app/home.css"), "utf8");
  assert.match(homeCss, /app-navigation-sign-in\s*\{[^}]*width:\s*44px;[^}]*min-width:\s*44px;[^}]*height:\s*44px;/s);
  assert.match(homeCss, /app-navigation-sign-in span\s*\{\s*display:\s*none;/);
  const navigationCss = fs.readFileSync(path.resolve(testDirectory, "../src/app/design-system.css"), "utf8");
  assert.match(navigationCss, /@media\s*\(max-width:\s*480px\)[\s\S]*?\.app-navigation-controls\s*\{[^}]*grid-row:\s*2;/);
});

test("the navbar switches from sign in to sign out with the authenticated session", () => {
  const signInHtml = renderToStaticMarkup(withLanguage(React.createElement(AuthNavigationAction, {
    language: "en", authStatus: "signed-out", showSignIn: true, signingOut: false, onSignOut() {},
  })));
  assert.match(signInHtml, /href="\/login"/);
  assert.match(signInHtml, /aria-label="Sign in"/);
  assert.match(signInHtml, />Sign in</);
  assert.doesNotMatch(signInHtml, />Log out</);

  const signOutHtml = renderToStaticMarkup(withLanguage(React.createElement(AuthNavigationAction, {
    language: "en", authStatus: "signed-in", showSignIn: true, signingOut: false, onSignOut() {},
  })));
  assert.match(signOutHtml, /<button[^>]*aria-label="Log out"/);
  assert.match(signOutHtml, />Log out</);
  assert.doesNotMatch(signOutHtml, /href="\/login"/);

  const thaiSignOutHtml = renderToStaticMarkup(withLanguage(React.createElement(AuthNavigationAction, {
    language: "th", authStatus: "signed-in", showSignIn: true, signingOut: false, onSignOut() {},
  })));
  assert.match(thaiSignOutHtml, /aria-label="ออกจากระบบ"/);
  assert.match(thaiSignOutHtml, />ออกจากระบบ</);

  const navigationCss = fs.readFileSync(path.resolve(testDirectory, "../src/app/design-system.css"), "utf8");
  assert.match(navigationCss, /app-navigation-auth-action\s*\{[^}]*min-width:\s*44px;[^}]*min-height:\s*44px;/s);
  assert.match(navigationCss, /@media\s*\(max-width:\s*900px\)[\s\S]*?\.app-navigation-auth-action\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;/);
  assert.match(navigationCss, /\.app-navigation-auth-action\s+span\s*\{\s*display:\s*none;/);
});

test("the dashboard navbar and real data surfaces use restrained backdrop blur", () => {
  const navigationCss = fs.readFileSync(path.resolve(testDirectory, "../src/app/design-system.css"), "utf8");
  const homeCss = fs.readFileSync(path.resolve(testDirectory, "../src/app/home.css"), "utf8");
  assert.match(navigationCss, /\.app-navigation\s*\{[^}]*backdrop-filter:\s*blur\(18px\)/s);
  assert.match(homeCss, /@supports\s*\(\(backdrop-filter:[\s\S]*?\.home-dashboard-shell \.home-metric-card[\s\S]*?backdrop-filter:\s*blur\(14px\)/);
  assert.match(homeCss, /@media\s*\(prefers-reduced-transparency:\s*reduce\)[\s\S]*?backdrop-filter:\s*none;/);
});
