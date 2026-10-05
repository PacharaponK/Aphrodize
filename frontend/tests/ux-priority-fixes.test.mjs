import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";

const read = path => fs.readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

test("onboarding keeps one theme control in its language/theme group", () => {
  const source = read("app/onboarding/health/page.tsx");
  assert.equal((source.match(/<ThemeToggle\b/g) ?? []).length, 1);
  assert.match(source, /onboarding-controls/);
  assert.match(source, /onboarding-controls[\s\S]*?<LanguageToggle[\s\S]*?<ThemeToggle/);
});

test("daily form separates technical limitations without changing visible consent choices", () => {
  const source = read("app/clients/daily-health-tracker.tsx");
  assert.match(source, /<details className="daily-input-method">/);
  assert.match(source, /Enter your full-day drinking-water total/);
  assert.match(source, /This training range is not a drinking-water recommendation/);
  assert.match(source, /checked=\{form\.consentToStore\}/);
  assert.match(source, /checked=\{form\.modelTrainingConsent\}/);
  assert.match(source, /shared next-day models across accounts, not an account-only model/);
  assert.match(source, /This is optional and can be withdrawn/);
  assert.match(source, /No entry for today/);
  const outcomes = read("app/clients/daily-health-outcome-form.tsx");
  assert.match(outcomes, /<details className="daily-input-method">[\s\S]*?100 complete paired days[\s\S]*?Accuracy review[\s\S]*?<\/details>/);
  assert.match(outcomes, /Model training requires separate consent/);
});

test("UV route no longer locks the workflow to Thai", () => {
  const page = read("app/uv-map/page.tsx");
  const explorer = read("components/uv/uv-map-explorer.tsx");
  assert.match(page, /<UvMapHeader/);
  assert.doesNotMatch(page, /lang="th"/);
  assert.match(explorer, /useLanguage/);
  assert.match(explorer, /lang=\{language\}/);
  assert.match(explorer, /language=\{language\}/);
});
