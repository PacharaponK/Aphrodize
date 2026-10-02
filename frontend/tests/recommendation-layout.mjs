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
function render(language) {
  const products = ["Daily moisturizer", "A very long product name for checking responsive layouts and full ingredient disclosures", "Unscented cream"].map((name, index) => ({
    id: String(index), brand: "Layout test", name: language === "th" ? `ผลิตภัณฑ์ทดสอบ ${index + 1} สำหรับตรวจการจัดหน้าและชื่อสินค้าที่ยาว` : name,
    variant: "50 ml", image_url: index === 0 ? "/test-image.svg" : index === 1 ? "/missing-image.png" : null,
    price_satang: 49900, price_checked_at: "2026-10-02", reviewed_at: "2026-10-02", matched_claims: [], matched_skin_type: "dry",
    ingredients_inci: ["Aqua", "Glycerin", "IngredientWithoutSpaces".repeat(10)], warnings_label: "คำเตือนทดสอบ: ตรวจสูตรปัจจุบันก่อนใช้",
    source_url: "#source", purchase_url: "#product",
  }));
  const data = { status: "ready", recommendations: [{ category: "Moisturizer", rule_id: "fixture", rule_version: "1", products,
    rationale: "ข้อมูลทดสอบสำหรับตรวจ UI เท่านั้น ไม่ใช่คำแนะนำส่วนบุคคล", signal_sources: ["self_reported"],
    knowledge_source: { id: "fixture", version: "1", reference: { title: "Test reference", url: "#source" } } }],
    questionnaire_context: { status: "available" }, daily_context: {}, image_context: { status: "eligible" }, rule_version: "1",
    profile_context: { skin_type: "dry", skin_sensitivity: "medium" }, disclaimer: "ผลนี้เป็นข้อมูลทดสอบเพื่อจัดหน้าเท่านั้น" };
  let cursor = 0;
  const states = [data, "", false, "TH", null];
  const overrides = {
    react: { ...React, useState: () => [states[cursor++], () => {}], useEffect() {} },
    "@/components/language-provider": { useLanguage: () => ({ language }) },
    "@/components/allergy-ingredients": { ALLERGY_INGREDIENTS: [] },
    "next/link": ({ children, ...props }) => React.createElement("a", props, children),
    "next/image": (props) => { const imageProps = { ...props }; delete imageProps.unoptimized; return React.createElement("img", imageProps); },
    "@/components/ui/select": selectModule.exports,
  };
  const evaluated = { exports: {} };
  new Function("require", "module", "exports", source)((name) => overrides[name] ?? require(name), evaluated, evaluated.exports);
  return renderToStaticMarkup(React.createElement(evaluated.exports.RecommendationPanel));
}
const html = render("th");
assert.equal((html.match(/class="recommendation-product recommendation-product-card"/g) ?? []).length, 3);
assert.ok(!html.includes('class="rule-box'));
assert.ok(html.includes("recommendation-product-placeholder"));
assert.ok(html.includes("ส่วนผสมและแหล่งข้อมูล"));
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
    response.end(`<!doctype html><html data-theme="${url.searchParams.get("theme") === "black" ? "black" : "light"}"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>@font-face{font-family:Montserrat;src:url('/montserrat.ttf')}@font-face{font-family:NotoSansThai;src:url('/noto.ttf')}@font-face{font-family:LibreBaskerville;src:url('/libre.ttf')}:root{--font-montserrat:Montserrat;--font-noto-sans-thai:NotoSansThai;--font-libre-baskerville:LibreBaskerville}${styles}\nbody{margin:0;padding:24px}main{max-width:1240px;margin:auto;padding:0} .fixture-note{color:var(--muted);font-size:14px}</style></head><body><main class="workspace-shell"><p class="fixture-note">Isolated UI test · ข้อมูลทดสอบ ไม่ใช่ผลวิเคราะห์จริง</p><section class="page-content workspace-panel analysis-page analysis-page--face"><h2>ผลิตภัณฑ์ที่แนะนำ</h2><section class="analysis-recommendation-section">${render(url.searchParams.get("lang") === "en" ? "en" : "th")}</section></section></main><script>document.addEventListener('error',event=>{if(event.target.tagName==='IMG')event.target.hidden=true},true)</script></body></html>`);
  }).listen(3101, "127.0.0.1", () => console.log("Visual fixture: http://127.0.0.1:3101"));
}
