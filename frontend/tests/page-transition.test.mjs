import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import ts from "typescript";

function harness({ reduced = false, hidden = false, supported = true } = {}) {
  const source = ts.transpileModule(fs.readFileSync(new URL("../src/components/page-transition.tsx", import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  let pathname = "/";
  const refs = [];
  let index = 0;
  let effect;
  let cleanup;
  let lastDependency;
  let cancels = 0;
  const animations = [];
  const preferenceListeners = new Set();
  const visibilityListeners = new Set();
  const preference = {
    matches: reduced,
    addEventListener: (_, callback) => preferenceListeners.add(callback),
    removeEventListener: (_, callback) => preferenceListeners.delete(callback),
  };
  const document = {
    hidden,
    addEventListener: (_, callback) => visibilityListeners.add(callback),
    removeEventListener: (_, callback) => visibilityListeners.delete(callback),
  };
  const main = supported ? { animate(frames, options) {
    animations.push({ frames, options });
    return { cancel() { cancels++; } };
  } } : {};
  const container = { querySelector(selector) { assert.equal(selector, "main"); return main; } };
  const exported = {};
  const requireMock = (name) => {
    if (name === "react") return {
      useRef(value) { const position = index++; return refs[position] ??= { current: value }; },
      useEffect(callback, dependencies) { if (lastDependency !== dependencies[0]) effect = callback; },
    };
    if (name === "next/navigation") return { usePathname: () => pathname };
    if (name === "react/jsx-runtime") return { jsx: (type, props) => ({ type, props }) };
    throw new Error(`Unexpected import ${name}`);
  };
  new Function("require", "exports", "window", "document", source)(requireMock, exported,
    { matchMedia: () => preference }, document);
  return {
    animations, preferenceListeners, visibilityListeners,
    render(path) {
      pathname = path;
      index = 0;
      effect = undefined;
      const child = { unchanged: true };
      const element = exported.PageTransition({ children: child });
      assert.equal(element.props.children, child);
      assert.equal(element.props.style.display, "contents");
      assert.equal(element.props.key, undefined);
      refs[1].current = container;
      if (effect) { cleanup?.(); cleanup = effect(); lastDependency = pathname; }
    },
    reduce() { preference.matches = true; for (const listener of preferenceListeners) listener(); },
    hide() { document.hidden = true; for (const listener of visibilityListeners) listener(); },
    cleanup() { cleanup?.(); },
    get cancels() { return cancels; },
  };
}

test("route entry is short, visible, layout-neutral, and does not remount children", () => {
  const h = harness();
  h.render("/");
  assert.equal(h.animations.length, 0, "initial load stays unanimated");
  h.render("/clients");
  assert.deepEqual(h.animations[0].frames, [{ opacity: 0.96 }, { opacity: 1 }]);
  assert.equal(h.animations[0].options.duration, 160);
  assert.equal(h.animations[0].options.fill, undefined);
  h.render("/clients");
  assert.equal(h.animations.length, 1, "same pathname updates do not replay");
  h.render("/");
  assert.equal(h.animations[1].options.duration, 240);
  assert.equal(h.animations[1].frames[0].opacity, 0.9);
  h.cleanup();
  assert.equal(h.cancels, 2);
  assert.equal(h.preferenceListeners.size + h.visibilityListeners.size, 0);
});

test("reduced motion, hidden tabs and missing animation support stay static", () => {
  for (const options of [{ reduced: true }, { hidden: true }, { supported: false }]) {
    const h = harness(options);
    h.render("/"); h.render("/capture");
    assert.equal(h.animations.length, 0);
  }
});

test("motion preference and visibility changes cancel an active entry", () => {
  for (const event of ["reduce", "hide"]) {
    const h = harness();
    h.render("/"); h.render("/profile");
    h[event]();
    assert.equal(h.cancels, 1);
    h.cleanup();
    assert.equal(h.preferenceListeners.size + h.visibilityListeners.size, 0);
  }
});
