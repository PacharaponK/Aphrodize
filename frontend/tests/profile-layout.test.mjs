import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { createRequire } from "node:module";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
const source = fs.readFileSync(new URL("../src/app/profile/page.tsx", import.meta.url), "utf8");

function renderProfile(profile, language = "en", requiresLogin = false) {
  let stateIndex = 0;
  const pageStates = [profile, "", false, requiresLogin];
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const evaluated = { exports: {} };
  const overrides = {
    react: { ...React, useEffect: () => {}, useState: initial => [stateIndex < 4 ? pageStates[stateIndex++] : typeof initial === "function" ? initial() : initial, () => {}] },
    "@/components/language-provider": { useLanguage: () => ({ language }) },
    "@/components/workspace-shell": { WorkspaceShell: ({ children }) => React.createElement("main", null, children) },
    "next/link": { default: ({ children, ...props }) => React.createElement("a", props, children), __esModule: true },
  };
  new Function("require", "module", "exports", compiled)(name => name.endsWith(".css") ? {} : overrides[name] ?? require(name), evaluated, evaluated.exports);
  return renderToStaticMarkup(React.createElement(evaluated.exports.default));
}

const account = { display_name: "Test Account", email: "profile@example.test", profile: null,
  answers: { skin_type: "oily", skin_sensitivity: "medium", allergy_details: "Long ingredient name", age_years: 25,
    age_group: "18_29", sleep_hours: 0, wellness_goal: "hydration", height_cm: 9999, weight_kg: 9999,
    guardian_consent: "private", custom_answer: "Preserved answer" } };

test("profile groups real answers in skin, signup and baseline order without losing unknown fields", () => {
  const html = renderProfile(account);
  assert.ok(html.indexOf("profile-skin-title") < html.indexOf("profile-signup-title"));
  assert.ok(html.indexOf("profile-signup-title") < html.indexOf("profile-habits-title"));
  assert.match(html, /Oily/);
  assert.match(html, /Moderate/);
  assert.match(html, /Long ingredient name/);
  assert.match(html, /0 hours/);
  assert.match(html, /not today&#x27;s readings/);
  assert.match(html, /Preserved answer/);
  assert.doesNotMatch(html, /9999|guardian_consent|18_29/);
  assert.equal((html.match(/Edit wellness information/g) ?? []).length, 1);
});

test("profile keeps Thai labels and separates missing values from zero", () => {
  const html = renderProfile({ ...account, answers: { skin_type: null, sleep_hours: 0 } }, "th");
  assert.match(html, /ข้อมูลผิวและข้อควรระวัง/);
  assert.match(html, /ยังไม่ได้บันทึก/);
  assert.match(html, /0 ชั่วโมง/);
});

test("signed-out profile shows the login gate without private account sections", () => {
  const html = renderProfile(null, "en", true);
  assert.match(html, /Sign in to view your profile/);
  assert.doesNotMatch(html, /profile-layout|profile-signup-title|profile-skin-title/);
});

test("saved measurements still require active consent and private uncached APIs", () => {
  assert.match(source, /height_profile_consent_active === true && profile\.height_cm != null/);
  assert.match(source, /weight_profile_consent_active === true && profile\.weight_kg != null/);
  assert.match(source, /fetch\("\/api\/daily-health\/profile", \{ cache: "no-store" \}\)/);
  assert.match(source, /fetch\("\/api\/profile", \{ cache: "no-store" \}\)/);
});

test("account card uses actual identity and tracking goal, not reference portrait or invented metrics", () => {
  const html = renderProfile({ ...account, display_name: "Tester", email: "tester@example.test" });
  const card = html.match(/<aside class="profile-identity"[\s\S]*?<\/aside>/)?.[0] ?? "";
  assert.match(card, /aria-labelledby="profile-account-name"/);
  assert.match(card, /profile-monogram" aria-hidden="true">T<\/span>/);
  assert.match(card, /id="profile-account-name">Tester/);
  assert.match(card, /tester@example.test/);
  assert.match(card, /profile-goal-tag">Hydration/);
  assert.doesNotMatch(card, /<img|Followers|Sessions|Angela|Videos/);
});

test("account card preserves long strings and localizes missing goal without invented data", () => {
  const name = "ชื่อผู้ใช้ที่มีความยาวมากสำหรับตรวจการแสดงผล";
  const email = "very-long-email-address-for-profile-layout@example.test";
  const html = renderProfile({ ...account, display_name: name, email, answers: {} }, "th");
  assert.ok(html.includes(name));
  assert.ok(html.includes(email));
  assert.match(html, /profile-goal-tag">ยังไม่ได้บันทึก/);
  assert.match(html, /profile-monogram" aria-hidden="true">ช<\/span>/);
});
