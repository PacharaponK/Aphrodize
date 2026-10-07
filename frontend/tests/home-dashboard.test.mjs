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
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const requireLocal = (name) => {
    if (name.endsWith(".css")) return {};
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

test("overview omits product and UV guidance, with the old route redirecting to results", () => {
  const { default: legacyPage } = loadTsx(path.resolve(testDirectory, "../src/app/recommendation/page.tsx"));
  assert.throws(legacyPage, (error) => error.digest === "NEXT_REDIRECT;replace;/capture#products;307;");
  const { default: oldResultsPage } = loadTsx(path.resolve(testDirectory, "../src/app/result-detail/page.tsx"));
  assert.throws(oldResultsPage, (error) => error.digest === "NEXT_REDIRECT;replace;/capture#results;307;");
  const { UvRecommendation } = loadTsx(path.resolve(testDirectory, "../src/app/recommendation/uv-recommendation.tsx"));
  const html = renderToStaticMarkup(React.createElement(UvRecommendation));
  assert.match(html, /id="uv"/);
  assert.match(html, /aria-labelledby="uv-heading"/);
  assert.match(html, /role="status"/);
  const home = fs.readFileSync(path.resolve(testDirectory, "../src/app/page.tsx"), "utf8");
  assert.doesNotMatch(home, /UvRecommendation|recommendation\/uv\.css/);
  assert.doesNotMatch(render(), /dashboard-product-recommendations|Profile-based product recommendations/);
  const dashboard = fs.readFileSync(path.resolve(testDirectory, "../src/app/clients/daily-health-history-panel.tsx"), "utf8");
  assert.doesNotMatch(dashboard, /RecommendationPanel/);
  const profile = fs.readFileSync(path.resolve(testDirectory, "../src/app/profile/page.tsx"), "utf8");
  assert.doesNotMatch(profile, /#dashboard-product-recommendations/);
  const onboarding = fs.readFileSync(path.resolve(testDirectory, "../src/app/onboarding/health/page.tsx"), "utf8");
  assert.match(onboarding, /router\.push\(effectiveFullEdit \? "\/profile" : "\/"\)/);
});

test("personal insights precedes the secondary UV entry in every data state", () => {
  for (const state of [{}, { requiresLogin: true }, { loading: true }, { failed: true }]) {
    const html = render(state);
    assert.match(html, /aria-labelledby="home-uv-map-heading"/);
    assert.match(html, /href="\/uv-map"/);
    assert.ok(html.indexOf("Personal insights") < html.indexOf('id="home-uv-map-heading"'));
    assert.match(html, /class="secondary-button"[^>]*>Explore UV map/);
  }
});

test("home hero stays inside main with an honest decorative image and motion controls", () => {
  const filename = path.resolve(testDirectory, "../src/app/page.tsx");
  const pageText = fs.readFileSync(filename, "utf8");
  const source = ts.createSourceFile(filename, pageText, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  assert.doesNotMatch(pageText, /legacy\/home\.js/, "legacy scripts must not duplicate navbar controls");
  const heroParents = [];
  function visit(node, ancestors = []) {
    const tag = ts.isJsxElement(node) ? node.openingElement.tagName.getText(source)
      : ts.isJsxSelfClosingElement(node) ? node.tagName.getText(source) : null;
    if (tag === "HomeHero") heroParents.push(ancestors);
    ts.forEachChild(node, child => visit(child, tag ? [...ancestors, tag] : ancestors));
  }
  visit(source);
  assert.equal(heroParents.length, 1);
  assert.equal(heroParents[0].at(-1), "main");
  assert.equal(heroParents[0].includes("article"), false);
  const { HomeHero } = loadTsx(path.resolve(testDirectory, "../src/components/home-hero.tsx"));
  const html = renderToStaticMarkup(withLanguage(React.createElement(HomeHero)));
  assert.match(html, /aria-labelledby="home-hero-title"/);
  assert.match(html, /alt=""/);
  assert.match(html, /aphrodize-hero-face\.png/);
  assert.match(html, /Visual demo, not an analysis result/);
  assert.match(html, /href="\/capture"/);
  assert.match(html, /aria-pressed="false"[^>]*>Pause text animation/);
  const heroSource = fs.readFileSync(path.resolve(testDirectory, "../src/components/home-hero.tsx"), "utf8");
  assert.match(heroSource, /if \(paused \|\| reduced\) return;/);
  assert.match(heroSource, /prefers-reduced-motion: reduce/);
  assert.match(heroSource, /if \(!document\.hidden\)/);
  assert.match(heroSource, /removeEventListener\("visibilitychange", schedule\)/);
});

test("signed-in and guest visitors both retain the restored expressive hero", () => {
  const auth = loadTsx(path.resolve(testDirectory, "../src/components/auth-presentation.tsx"));
  const { HomeHero } = loadTsx(path.resolve(testDirectory, "../src/components/home-hero.tsx"));
  const original = auth.useAuthPresentation;
  try {
    auth.useAuthPresentation = () => ({ authStatus: "signed-in" });
    const html = renderToStaticMarkup(withLanguage(React.createElement(HomeHero)));
    assert.doesNotMatch(html, /home-hero-compact|Your latest records and next steps/);
    assert.match(html, /href="\/capture"/);
    assert.match(html, /Analyze skin/);
    assert.match(html, /home-hero-words/);
    assert.match(html, /Pause text animation/);
    auth.useAuthPresentation = () => ({ authStatus: "signed-out" });
    const guest = renderToStaticMarkup(withLanguage(React.createElement(HomeHero)));
    assert.doesNotMatch(guest, /home-hero-compact/);
    assert.match(guest, /home-hero-words|Analyze skin/);
    assert.equal(html, guest);
  } finally { auth.useAuthPresentation = original; }
});

test("weekly cards distinguish recorded, calculated and stored forecast provenance", () => {
  const html = render();
  assert.equal((html.match(/<article[^>]*data-evidence="calculated"/g) || []).length, 2);
  assert.equal((html.match(/<article[^>]*data-evidence="recorded"/g) || []).length, 1);
  assert.equal((html.match(/<article[^>]*data-evidence="forecast"/g) || []).length, 1);
  assert.match(html, /Recorded/);
  assert.match(html, /Calculated/);
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

test("shared navigation defaults to English with visible account controls and a mobile language menu", () => {
  const english = renderToStaticMarkup(withLanguage(React.createElement(AppNavigation, { active: "dashboard", showThemeToggle: true, showSignIn: true })));
  assert.match(english, /aria-label="Open menu"/);
  assert.match(english, />Overview</);
  assert.match(english, />Daily health</);
  assert.match(english, /href="\/login"/);
  assert.match(english, />Sign in</);
  assert.doesNotMatch(english, /href="\/portal"/);
  assert.match(english, /aria-label="เปลี่ยนภาษาเป็นไทย"/);
  assert.match(english, /aria-label="Switch to dark theme"/);
  assert.match(english, />Dark</);
  assert.match(english, /aria-controls="primary-navigation navigation-controls"/);
  assert.match(english, /id="navigation-controls"/);
  assert.match(english, /class="app-navigation-language"/);
  assert.match(english, /class="app-navigation-auth-action app-navigation-sign-in"/);
  const unchanged = renderToStaticMarkup(withLanguage(React.createElement(AppNavigation, { active: "clients" })));
  assert.match(unchanged, /aria-label="Open menu"/);
  assert.match(unchanged, /Daily health/);
  assert.match(unchanged, /aria-label="เปลี่ยนภาษาเป็นไทย"/);
  assert.equal(unchanged.includes('class="app-navigation-sign-in"'), false);
  const navigationCss = fs.readFileSync(path.resolve(testDirectory, "../src/app/design-system.css"), "utf8");
  assert.match(navigationCss, /@media\s*\(max-width:\s*1200px\)[\s\S]*?\.app-navigation\.is-motion-style \.app-navigation-controls\s*\{[^}]*display:\s*flex;/);
  assert.match(navigationCss, /\.app-navigation\.is-motion-style \.app-navigation-language\s*\{[^}]*display:\s*none;/);
  assert.match(navigationCss, /\.app-navigation\.is-motion-style\.is-open \.app-navigation-language\s*\{[^}]*display:\s*block\s*[;}]/);
});

test("the root layout owns navigation so changing pages does not remount it", () => {
  const readSource = (file) => fs.readFileSync(path.resolve(testDirectory, "../src", file), "utf8");
  assert.match(readSource("app/layout.tsx"), /<SharedNavigation\s*\/>\s*<PageTransition>\{children\}<\/PageTransition>/);
  const sourceDirectory = path.resolve(testDirectory, "../src");
  for (const file of fs.readdirSync(sourceDirectory, { recursive: true }).filter((file) => file.endsWith(".tsx"))) {
    const normalized = file.replaceAll("\\", "/");
    if (normalized === "app/layout.tsx" || normalized === "components/shared-navigation.tsx") continue;
    assert.doesNotMatch(readSource(file), /<(?:AppNavigation|SharedNavigation)\b/, `${file} must not mount another navbar`);
  }
  const source = readSource("components/shared-navigation.tsx");
  assert.match(source, /usePathname\(\)/);
  assert.match(source, /if \(!active\) return null;/, "auth and admin pages keep their own chrome");
  assert.doesNotMatch(source, /key=/, "a route key would remount the navbar");
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
  assert.doesNotMatch(navigationCss, /\.app-navigation-auth-action\s+span\s*\{\s*display:\s*none;/, "account actions keep their labels in the mobile menu");
});

test("the dashboard navbar and real data surfaces use restrained backdrop blur", () => {
  const navigationCss = fs.readFileSync(path.resolve(testDirectory, "../src/app/design-system.css"), "utf8");
  const homeCss = fs.readFileSync(path.resolve(testDirectory, "../src/app/home.css"), "utf8");
  assert.match(navigationCss, /\.app-navigation\s*\{[^}]*backdrop-filter:\s*blur\(18px\)/s);
  assert.match(homeCss, /@supports\s*\(\(backdrop-filter:[\s\S]*?\.home-dashboard-shell \.home-metric-card[\s\S]*?backdrop-filter:\s*blur\(14px\)/);
  assert.match(homeCss, /@media\s*\(prefers-reduced-transparency:\s*reduce\)[\s\S]*?backdrop-filter:\s*none;/);
});
