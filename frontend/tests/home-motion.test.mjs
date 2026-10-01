// Run: node --test tests/home-motion.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import ts from "typescript";

test("overview motion targets current cards, respects reduced motion and cleans up", () => {
  const source = ts.transpileModule(fs.readFileSync(new URL("../src/components/home-scroll-motion.tsx", import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText;
  const selectors = [".home-topbar", ".home-overview-card", ".home-wellness-card", ".home-action-card", ".home-metric-card", ".home-insights-card"];
  const cards = selectors.map((selector) => ({ matches: (value) => value === selector }));
  const dashboard = { querySelector: () => null };
  let reducedMotion = false;
  let cleanup;
  let reverts = 0;
  const animations = [];
  const gsap = {
    registerPlugin() {},
    matchMedia(scope) {
      assert.equal(scope, dashboard);
      return {
        add(query, callback) {
          assert.equal(query, "(prefers-reduced-motion: no-preference)");
          if (!reducedMotion) callback();
        },
        revert() { reverts++; },
      };
    },
    utils: { toArray(selector, scope) {
      assert.deepEqual(selector.split(", "), selectors);
      assert.equal(scope, dashboard);
      return cards;
    } },
    fromTo(target, from, to) { animations.push({ target, from, to }); },
  };
  const evaluatedModule = { exports: {} };
  const requireMock = (name) => {
    if (name === "react") return { useEffect: (callback) => { cleanup = callback(); } };
    if (name === "gsap") return { gsap };
    if (name === "gsap/ScrollTrigger") return { ScrollTrigger: {} };
    throw new Error(`Unexpected import: ${name}`);
  };
  new Function("require", "exports", "document", source)(requireMock, evaluatedModule.exports, {
    querySelector: () => dashboard,
  });
  evaluatedModule.exports.HomeScrollMotion();
  assert.deepEqual(animations.map(({ target }) => target), cards);
  assert.equal(animations[1].from.x, -40);
  assert.equal(animations[2].from.x, 40);
  for (const { from, to } of animations) {
    assert.ok((from.opacity ?? 1) > 0, "content remains visible during motion");
    assert.equal(to.scrollTrigger.toggleActions, "restart none restart reverse");
    assert.ok(to.duration + (to.delay ?? 0) <= 1.2);
    assert.equal(to.x, 0);
    assert.equal(to.y, 0);
    assert.equal(to.opacity, 1);
  }
  cleanup();
  assert.equal(reverts, 1);
  reducedMotion = true;
  animations.length = 0;
  evaluatedModule.exports.HomeScrollMotion();
  assert.equal(animations.length, 0);
  cleanup();
  assert.equal(reverts, 2);
});
