import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { createRequire } from "node:module";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
const source = fs.readFileSync(new URL("../src/components/home-reveal-footer.tsx", import.meta.url), "utf8");
function load(react = React, language = "en") {
  const result = { exports: {} };
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  const overrides = {
    react,
    "./language-provider": { useLanguage: () => ({ language }) },
    "next/link": { __esModule: true, default: props => React.createElement("a", props) },
    "next/image": { __esModule: true, default: props => { const attributes = { ...props }; delete attributes.unoptimized; return React.createElement("img", attributes); } },
  };
  new Function("require", "module", "exports", compiled)(name => overrides[name] ?? require(name), result, result.exports);
  return result.exports.HomeRevealFooter;
}

test("footer retains children, real routes, both logos and bilingual disclaimer", () => {
  for (const language of ["en", "th"]) {
    const Footer = load(React, language);
    const html = renderToStaticMarkup(React.createElement(Footer, null, React.createElement("main", null, "Existing content")));
    assert.ok(html.indexOf("Existing content") < html.indexOf("<footer"));
    for (const href of ["/capture", "/clients", "/trend", "/profile", "/uv-map"]) assert.ok(html.includes(`href="${href}"`));
    assert.match(html, /aphrodize-logo-dark.svg/);
    assert.match(html, language === "en" ? /Personal tracking, not a medical diagnosis/ : /ไม่ใช่การวินิจฉัยทางการแพทย์/);
    assert.doesNotMatch(html, /data-reveal="true"/);
  }
});

test("reveal responds to reduced motion, desktop eligibility, height and cleans up", () => {
  const originalWindow = global.window;
  const originalObserver = global.ResizeObserver;
  const root = { dataset: {} };
  let height = 260;
  const footer = { getBoundingClientRect: () => ({ height }) };
  const desktop = { matches: true, addEventListener() {}, removeEventListener() {} };
  const reduced = { ...desktop, matches: false };
  let effect, update, disconnected = false, removed = false, refIndex = 0;
  global.window = { innerHeight: 900, matchMedia: query => query.includes("min-width") ? desktop : reduced, addEventListener: (_, fn) => { update = fn; }, removeEventListener: () => { removed = true; } };
  global.ResizeObserver = class { constructor(fn) { update = fn; } observe() {} disconnect() { disconnected = true; } };
  try {
    load({ ...React, useRef: () => ({ current: refIndex++ === 0 ? root : footer }), useEffect: fn => { effect = fn; } })({ children: null });
    const cleanup = effect();
    assert.equal(root.dataset.reveal, "true");
    reduced.matches = true; update(); assert.equal(root.dataset.reveal, "false");
    reduced.matches = false; desktop.matches = false; update(); assert.equal(root.dataset.reveal, "false");
    desktop.matches = true; height = 800; update(); assert.equal(root.dataset.reveal, "false");
    height = 260; update(); assert.equal(root.dataset.reveal, "true");
    cleanup(); assert.ok(disconnected && removed); assert.equal(root.dataset.reveal, undefined);
  } finally { global.window = originalWindow; global.ResizeObserver = originalObserver; }
});

test("footer is Home-only, in flow by default and returns to flow for keyboard focus", () => {
  const page = fs.readFileSync(new URL("../src/app/page.tsx", import.meta.url), "utf8");
  const layout = fs.readFileSync(new URL("../src/app/layout.tsx", import.meta.url), "utf8");
  const css = fs.readFileSync(new URL("../src/app/home.css", import.meta.url), "utf8");
  assert.match(page, /<HomeRevealFooter>/);
  assert.doesNotMatch(layout, /HomeRevealFooter/);
  assert.match(css, /home-reveal-footer:focus-within \{ position:relative/);
  assert.doesNotMatch(source, /addEventListener\("scroll"|requestAnimationFrame|setInterval/);
});
