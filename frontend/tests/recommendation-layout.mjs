// Run: node tests/recommendation-layout.mjs; add --serve for an isolated visual fixture.
import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const source = ts.transpileModule(read("../src/app/recommendation/recommendation-panel.tsx"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const selectSource = ts.transpileModule(read("../src/components/ui/select.tsx"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const selectModule = { exports: {} };
new Function("require", "module", "exports", selectSource)(require, selectModule, selectModule.exports);
let translate;
function render(language, count = 3, overridesData = {}, error = "") {
  const products = ["Daily moisturizer", "A very long product name for checking responsive layouts and full ingredient disclosures", "Unscented cream"].map((name, index) => ({
    id: String(index), brand: "Layout test", name: language === "th" ? `ผลิตภัณฑ์ทดสอบ ${index + 1} สำหรับตรวจการจัดหน้าและชื่อสินค้าที่ยาว` : name,
    variant: "50 ml", image_url: index === 0 ? "/test-image.svg" : index === 1 ? "/missing-image.png" : null,
    price_satang: 49900, price_checked_at: "2026-10-02", reviewed_at: "2026-10-02", matched_claims: ["fragrance-free", "lightweight"], matched_skin_type: "dry",
    ingredients_inci: ["Aqua", "Glycerin", "IngredientWithoutSpaces".repeat(10)], warnings_label: "คำเตือนทดสอบ: ตรวจสูตรปัจจุบันก่อนใช้",
    source_url: "#source", purchase_url: "#product",
  })).slice(0, count);
  const data = { status: "ready", recommendations: [{ category: "lightweight moisturizer for combination skin", rule_id: "fixture", rule_version: "1", products,
    rationale: "You reported combination skin. Consider a lightweight moisturizer for dry areas and avoid applying it to areas that feel oily. Released wrinkle regions are shown as visual context only. They do not identify a cause, predict product effects, or authorize use near the eyes.", signal_sources: ["self_reported"],
    wrinkle_region_scores: [{ region: "forehead", score: 15 }],
    wrinkle_area_measurements: [{ region: "forehead", wrinkle_area_ratio: 0.018, visible_area_band: "medium", near_boundary: true }],
    knowledge_source: { id: "fixture", version: "1", reference: { title: "Test reference", url: "#source" } } }],
    questionnaire_context: { status: "available" }, daily_context: {}, image_context: { status: "eligible" }, rule_version: "1",
    profile_context: { skin_type: "dry", skin_sensitivity: "medium" }, disclaimer: "General skin-care product information based on reported inputs and reviewed labels. A catalog match is not a guarantee against allergy. It is not a diagnosis, treatment advice, or evidence that a product will change a wrinkle score. Check the full ingredient list and stop use if irritation occurs.", ...overridesData };
  let cursor = 0;
  const states = [data, error, false, "TH", null];
  const overrides = {
    react: { ...React, useState: () => [states[cursor++], () => {}], useEffect() {} },
    "@/components/language-provider": { useLanguage: () => ({ language }) },
    "@/components/allergy-ingredients": { ALLERGY_INGREDIENTS: [] },
    "next/link": ({ children, ...props }) => React.createElement("a", props, children),
    "next/image": (props) => { const imageProps = { ...props }; delete imageProps.unoptimized; return React.createElement("img", imageProps); },
    "@/components/ui/select": selectModule.exports,
  };
  const evaluated = { exports: {} };
  new Function("require", "module", "exports", `${source}\nmodule.exports.translate = localizeGuidance;`)((name) => overrides[name] ?? require(name), evaluated, evaluated.exports);
  translate = evaluated.exports.translate;
  return renderToStaticMarkup(React.createElement(evaluated.exports.RecommendationPanel));
}
const html = render("th");
assert.equal((html.match(/class="recommendation-product recommendation-product-card"/g) ?? []).length, 3);
assert.ok(!html.includes('class="rule-box'));
assert.ok(html.includes("recommendation-product-placeholder"));
assert.ok(html.includes("ส่วนผสมและแหล่งข้อมูล"));
assert.ok(html.indexOf('class="recommendation-warning"') < html.indexOf('class="product-inci-details"'), "product cautions stay visible outside collapsed details");
for (const count of [1, 2, 3]) {
  assert.equal((render("th", count).match(/class="recommendation-product recommendation-product-card"/g) ?? []).length, count);
}
for (const language of ["th", "en"]) {
  const empty = render(language, 0);
  assert.ok(!empty.includes('class="recommendation-card recommendation-group"'));
  assert.ok(empty.includes(language === "th" ? "ยังไม่มีผลิตภัณฑ์ที่ตรวจทานแล้วตรงกับเงื่อนไขที่เลือก" : "No reviewed products match your selected criteria yet."));
  assert.ok(!empty.includes('/onboarding/health?edit=full'), "no catalog match must not request missing profile data");
  const mixed = render(language, 1, { recommendations: [
    { rule_id: "missing", category: "Hidden missing products" },
    { rule_id: "empty", category: "Hidden empty products", products: [] },
    { rule_id: "matched", category: "Visible matched products", rationale: "Test", signal_sources: [],
      knowledge_source: { id: "test", version: "1", reference: { title: "Test", url: "#source" } },
      products: [{ id: "1", brand: "Test", name: "Test", variant: "", matched_skin_type: "dry", matched_claims: [], ingredients_inci: [], source_url: "#source" }] },
  ] });
  assert.ok(mixed.includes("Visible matched products"));
  assert.ok(!mixed.includes("Hidden missing products"));
  assert.ok(!mixed.includes("Hidden empty products"));
}
const allergy = render("en", 0, { allergy_context: { reported: true, details: "Test allergy" }, product_context: { status: "allergy_review_required" } });
assert.ok(allergy.includes("Named products are withheld"), "allergy information remains visible when product groups are hidden");
assert.ok(render("en", 0, { status: "safety_blocked", blocked_reason: "reported_severe_irritation" }).includes("You reported severe irritation"));
assert.ok(html.includes('lang="th"'));
assert.ok(html.includes("มอยส์เจอไรเซอร์เนื้อบางเบาสำหรับผิวผสม"));
assert.ok(html.includes("ข้อมูลนี้ไม่ได้ระบุสาเหตุ"));
assert.ok(html.includes("ข้อมูลนี้ไม่ใช่การวินิจฉัย"));
assert.ok(html.includes("คะแนนริ้วรอย 15.0"));
assert.ok(html.includes("ระดับพื้นที่ริ้วรอยที่ตรวจพบ"));
assert.ok(html.includes("1.80%"));
assert.ok(html.includes("ใกล้จุดแบ่งระดับ"));
assert.ok(html.includes("เกณฑ์ทดลอง"));
assert.ok(html.includes("ปราศจากน้ำหอม, เนื้อบางเบา"));
assert.ok(!html.includes("You reported combination skin"));
const english = render("en");
assert.ok(english.includes('lang="en"'));
assert.ok(english.includes("You reported combination skin"));
assert.ok(english.includes("They do not identify a cause"));
assert.ok(english.includes("Guidance rules v1"));
assert.ok(english.includes("original language"));
assert.ok(english.includes("คำเตือนทดสอบ"), "source label cautions must not be removed or guessed");
assert.ok(render("en", 1, {}, "กรุณาเข้าสู่ระบบเพื่อดูคำแนะนำส่วนบุคคล").includes("Sign in to view"));
assert.ok(render("th", 1, {}, "Invalid product budget").includes("งบประมาณสินค้าไม่ถูกต้อง"));
assert.ok(render("en", 1, {}, "ยังเชื่อมต่อบริการคำแนะนำไม่ได้").includes("Could not connect"));
assert.ok(render("th", 1, { status: "pending" }).includes("รอวิเคราะห์ภาพ"));
assert.ok(render("en", 1, { status: "pending" }).includes("after image analysis completes"));
assert.ok(render("th", 1, { recommendations: [], blocked_reason: "safety_screening_incomplete" }).includes("กรุณาบันทึกข้อมูลความไว"));
assert.ok(render("en", 1, { recommendations: [], blocked_reason: "safety_screening_incomplete" }).includes("Complete the skin-sensitivity"));
// Check the actual API copy, including youth, daily dryness and image-context branches.
const backendCopy = read("../../backend/services/analysis_service.py").replace(/"\s*\r?\n\s*"/g, "");
const paragraphs = [...backendCopy.matchAll(/"((?:You (?:reported|recently|are)|The (?:American|approved)|General skin-care| Released wrinkle).*?)"/g)].map((match) => match[1].trim());
assert.ok(paragraphs.length >= 10);
for (const paragraph of paragraphs) {
  for (const sentence of paragraph.split(/(?<=\.) /)) {
    assert.notEqual(translate(sentence, "th"), sentence, `Untranslated API copy: ${sentence}`);
  }
  assert.equal(translate(paragraph, "en"), paragraph);
}
assert.equal(translate("Unrecognized future guidance.", "th"), "Unrecognized future guidance.");
console.log("Recommendation layout fixture checks passed.");
if (process.argv.includes("--serve")) {
  const styles = ["prototype.css", "design-system.css", "result-detail/result-detail.css"].map((path) => read(`../src/app/${path}`)).join("\n");
  const image = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="220"><rect x="25" y="40" width="70" height="150" rx="10" fill="#fbe1e3"/><rect x="30" y="20" width="60" height="25" rx="4" fill="#b63240"/><text x="60" y="115" text-anchor="middle" font-size="14">TEST</text></svg>';
  http.createServer((request, response) => {
    const url = new URL(request.url, "http://127.0.0.1:3101");
    const fonts = { "/montserrat.ttf": "Montserrat", "/noto.ttf": "NotoSansThai", "/libre.ttf": "LibreBaskerville" };
    if (fonts[url.pathname]) { response.setHeader("Content-Type", "font/ttf"); response.end(fs.readFileSync(new URL(`../src/app/fonts/${fonts[url.pathname]}-Variable.ttf`, import.meta.url))); return; }
    if (url.pathname === "/test-image.svg") { response.setHeader("Content-Type", "image/svg+xml"); response.end(image); return; }
    if (url.pathname === "/missing-image.png") { response.writeHead(404); response.end(); return; }
    response.setHeader("Content-Type", "text/html; charset=utf-8");
    response.end(`<!doctype html><html data-theme="${url.searchParams.get("theme") === "black" ? "black" : "light"}"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>@font-face{font-family:Montserrat;src:url('/montserrat.ttf')}@font-face{font-family:NotoSansThai;src:url('/noto.ttf')}@font-face{font-family:LibreBaskerville;src:url('/libre.ttf')}:root{--font-montserrat:Montserrat;--font-noto-sans-thai:NotoSansThai;--font-libre-baskerville:LibreBaskerville}${styles}\nbody{margin:0;padding:24px}main{max-width:1240px;margin:auto;padding:0} .fixture-note{color:var(--muted);font-size:14px}</style></head><body><main class="workspace-shell"><p class="fixture-note">Isolated UI test · ข้อมูลทดสอบ ไม่ใช่ผลวิเคราะห์จริง</p><section class="page-content workspace-panel analysis-page analysis-page--face"><h2>ผลิตภัณฑ์ที่แนะนำ</h2><section class="analysis-recommendation-section">${render(url.searchParams.get("lang") === "en" ? "en" : "th", Number(url.searchParams.get("count")) || 3)}</section></section></main><script>document.addEventListener('error',event=>{if(event.target.tagName==='IMG')event.target.hidden=true},true)</script></body></html>`);
  }).listen(3101, "127.0.0.1", () => console.log("Visual fixture: http://127.0.0.1:3101"));
}
