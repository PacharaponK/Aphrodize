// Run: node --test tests/uv-map.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const filename = fileURLToPath(new URL("../src/components/uv/thailand-uv-map.tsx", import.meta.url));
const requireNative = createRequire(filename);
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const evaluated = { exports: {} };
new Function("require", "module", "exports", compiled)(
  (name) => name.endsWith(".css") ? {} : requireNative(name), evaluated, evaluated.exports,
);
const { ThailandUvMap } = evaluated.exports;
const shapes = JSON.parse(fs.readFileSync(path.resolve(filename, "../../../../public/assets/uv-map-provinces.json"), "utf8"));
const render = (provinces, props = {}) => renderToStaticMarkup(React.createElement(ThailandUvMap, {
  provinces, selectedProvinceId: "bangkok", onSelectProvince() {}, ...props,
}));

test("reusable map renders all provinces without fetching and keeps missing values explicit", () => {
  const html = render([]);
  assert.equal((html.match(/role="button"/g) ?? []).length, 77);
  assert.equal((html.match(/tabindex="0"/g) ?? []).length, 77);
  assert.equal((html.match(/class="uv-model-point"/g) ?? []).length, 0);
  assert.match(html, /กรุงเทพมหานคร: ไม่มีข้อมูลที่พร้อมใช้/);
  assert.doesNotMatch(html, /UV 0\.0/);
});

test("model mode exposes only its three provinces and API mode has no model markers", () => {
  const models = shapes.filter((p) => p.model_city !== null).map((p) => ({
    ...p, source: "local_model", uv_index: 11.4, status: "available", level: "extreme",
  }));
  const html = render(models, { provinceIds: models.map((p) => p.id) });
  assert.equal((html.match(/role="button"/g) ?? []).length, 3);
  assert.equal((html.match(/tabindex="0"/g) ?? []).length, 3);
  assert.equal((html.match(/class="uv-model-point"/g) ?? []).length, 3);
  assert.doesNotMatch(html, /aria-label="ภูเก็ต:/);
  const api = render(shapes.map((p) => ({
    ...p, source: "open_meteo", uv_index: 7.2, status: "available", level: "high",
  })));
  assert.equal((api.match(/role="button"/g) ?? []).length, 77);
  assert.doesNotMatch(api, /class="uv-model-point"/);
});

test("province values and source markers come from the supplied data", () => {
  const html = render(shapes.map((p) => ({
    ...p, source: p.model_city ? "local_model" : "open_meteo",
    uv_index: p.model_city ? 11.4 : 7.2,
    status: "available", level: p.model_city ? "extreme" : "high",
  })));
  assert.match(html, /กรุงเทพมหานคร: UV 11\.4 · โมเดลของเรา/);
  assert.match(html, /ภูเก็ต: UV 7\.2/);
  assert.match(html, /fill="#9762ac"/);
  assert.match(html, /fill="#ee9347"/);
  assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 1);
});
