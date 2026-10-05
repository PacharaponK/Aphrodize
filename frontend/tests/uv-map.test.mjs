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
const { boundedMapOrientation } = evaluated.exports;
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

test("mission view is opt-in and its decorative depth adds no interactive provinces", () => {
  const html = render([], { missionView: true });
  assert.match(html, /uv-mission-map/);
  assert.match(html, /class="uv-map-depth" aria-hidden="true"/);
  assert.equal((html.match(/role="button"/g) ?? []).length, 77);
  assert.match(html, /ซูมเข้าจังหวัดที่เลือก/);
  assert.doesNotMatch(render([]), /uv-map-depth/);
});

test("stale values cannot appear as an available UV reading in accessible labels", () => {
  const html = render([{ ...shapes.find((p) => p.id === "bangkok"), uv_index: 7.2, status: "stale", level: "high", source: "open_meteo" }]);
  assert.match(html, /กรุงเทพมหานคร: ไม่มีข้อมูลที่พร้อมใช้/);
  assert.doesNotMatch(html, /UV 7\.2/);
});

test("orientation bounds prevent a flipped map", () => {
  assert.deepEqual(boundedMapOrientation(900, 900), { rotation: 30, tilt: 18 });
  assert.deepEqual(boundedMapOrientation(-900, -900), { rotation: -30, tilt: -12 });
  assert.deepEqual(boundedMapOrientation(4, 5), { rotation: 4, tilt: 5 });
});

test("right drag captures and releases pointer without selecting a province", () => {
  const testModule = { exports: {} };
  new Function("require", "module", "exports", compiled)(name => {
    if (name === "react") return { useId: () => "test", useState: initial => [initial, () => {}], useRef: initial => ({ current: initial }) };
    return name.endsWith(".css") ? {} : requireNative(name);
  }, testModule, testModule.exports);
  let selected = null;
  const tree = testModule.exports.ThailandUvMap({ provinces: [], selectedProvinceId: "bangkok", onSelectProvince: id => { selected = id; }, missionView: true });
  function find(node, predicate) {
    if (!node || typeof node !== "object") return null;
    if (predicate(node)) return node;
    for (const child of [node.props?.children].flat(Infinity)) { const match = find(child, predicate); if (match) return match; }
    return null;
  }
  const stage = find(tree, node => node.props?.className === "uv-map-stage");
  const properties = {};
  let capture = false;
  const target = { dataset: {}, style: { setProperty: (name, value) => { properties[name] = value; } }, setPointerCapture: () => { capture = true; }, hasPointerCapture: () => capture, releasePointerCapture: () => { capture = false; } };
  stage.props.ref.current = target;
  const event = { currentTarget: target, pointerId: 1, pointerType: "mouse", clientX: 0, clientY: 0, button: 0, buttons: 1, preventDefault() {} };
  stage.props.onPointerDown(event);
  assert.equal(capture, false);
  stage.props.onPointerDown({ ...event, button: 2, buttons: 2 });
  assert.equal(capture, true);
  stage.props.onPointerMove({ ...event, buttons: 2, clientX: 9999, clientY: -9999 });
  assert.equal(properties["--uv-rotation-offset"], "30deg");
  assert.equal(properties["--uv-tilt-offset"], "18deg");
  assert.equal(selected, null);
  stage.props.onPointerUp(event);
  assert.equal(capture, false);
  assert.equal(target.dataset.dragging, "false");
  find(tree, node => node.props?.role === "button" && node.props?.["aria-pressed"] === true).props.onClick();
  assert.equal(selected, "bangkok");
});
