import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { createRequire } from "node:module";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const filename = new URL("../src/components/uv/uv-sunscreens.tsx", import.meta.url);
const require = createRequire(filename);
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
}).outputText;
const catalog = [30, 50, 15].map(spf => ({ brand: "Test", name: `Screen ${spf}`, spf,
  broad_spectrum: true, target_skin_types: ["dry"], source_url: `https://example.com/${spf}`,
  water_resistant_minutes: null, image_url: spf === 50 ? "https://example.com/screen-50.jpg" : null }));
function load(language = "en") {
  const evaluated = { exports: {} };
  new Function("require", "module", "exports", compiled)(name => {
    if (name === "../language-provider") return { useLanguage: () => ({ language }) };
    if (name === "react") return { ...React, useEffect() {}, useState: initial => [initial === null ? catalog : initial, () => {}] };
    return require(name);
  }, evaluated, evaluated.exports);
  return evaluated.exports;
}

test("province/day UV selects higher SPF at eight while keeping the SPF 30 baseline", () => {
  const { suitableSunscreens } = load();
  assert.deepEqual(suitableSunscreens(catalog, 0).map(p => p.spf), [30, 50]);
  assert.deepEqual(suitableSunscreens(catalog, 7.9).map(p => p.spf), [30, 50]);
  assert.deepEqual(suitableSunscreens(catalog, 8).map(p => p.spf), [50]);
  assert.deepEqual(suitableSunscreens([catalog[0]], 12).map(p => p.spf), [30]);
  assert.deepEqual(suitableSunscreens([{ ...catalog[1], broad_spectrum: false }], 8), []);
});

test("skin and activity constraints stay mandatory even when the higher-SPF preference falls back", () => {
  const { suitableSunscreens } = load();
  const dry = { ...catalog[0], target_skin_types: ["dry"], water_resistant_minutes: 40 };
  const oily = { ...catalog[1], target_skin_types: ["oily"], water_resistant_minutes: null };
  const all = { ...catalog[1], name: "All skin sport", target_skin_types: ["all"], water_resistant_minutes: 80 };
  assert.deepEqual(suitableSunscreens([dry, oily], 12, "dry", "sports"), [dry]);
  assert.deepEqual(suitableSunscreens([dry, oily], 12, "oily", "sports"), []);
  assert.deepEqual(suitableSunscreens([all], 12, "combination", "swimming"), [all]);
  assert.deepEqual(suitableSunscreens([all], 12, "sensitive", "swimming"), []);
  assert.deepEqual(suitableSunscreens([{ ...all, suitable_for_sensitive_skin: true }], 12, "sensitive", "swimming").map(p => p.name), ["All skin sport"]);
  assert.deepEqual(suitableSunscreens([{ ...all, suitable_for_sensitive_skin: true, water_resistant_minutes: null }], 12, "sensitive", "swimming"), []);
  assert.deepEqual(suitableSunscreens([{ ...all, target_skin_types: ["sensitive"] }], 12, "sensitive", "swimming").map(p => p.name), ["All skin sport"]);
  assert.deepEqual(suitableSunscreens([dry, oily], 5, "dry", "daily"), [dry]);
  assert.deepEqual(suitableSunscreens([{ ...all, water_resistant_minutes: 20 }], 5, "unknown", "sports"), []);
  assert.deepEqual(suitableSunscreens([oily], 0, "oily", "outdoor"), [oily]);
});

test("missing UV hides product recommendations; both languages preserve label limitations", () => {
  for (const language of ["en", "th"]) {
    const { UvSunscreens } = load(language);
    const render = uv => renderToStaticMarkup(React.createElement(UvSunscreens, { provinceName: "Phuket", uv }));
    assert.doesNotMatch(render(null), /Screen 30|Screen 50/);
    const html = render(11);
    assert.match(html, /Phuket/);
    assert.match(html, /Screen 50/);
    assert.doesNotMatch(html, /Screen 30/);
    assert.match(html, language === "en" ? /Water resistance is unverified/ : /ไม่มีข้อมูลยืนยันการทนน้ำ/);
    assert.match(html, /rel="noopener noreferrer"/);
  }
});

test("recommendations include the catalog image and a missing-image fallback", () => {
  const { UvSunscreens } = load();
  const html = renderToStaticMarkup(React.createElement(UvSunscreens, { provinceName: "Phuket", uv: 11 }));
  assert.match(html, /src="https:\/\/example.com\/screen-50.jpg"/);
  assert.match(html, /alt="Test Screen 50"/);
  assert.match(html, /No product image/);
});
