// Run: node tests/capture-consent.test.mjs (from frontend/).
import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { createRequire } from "node:module";
import { createHmac } from "node:crypto";
import ts from "typescript";
import { NextRequest } from "next/server.js";

const require = createRequire(import.meta.url);
function load(file, overrides) {
  const source = ts.transpileModule(fs.readFileSync(new URL(file, import.meta.url), "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2017, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const evaluated = { exports: {} };
  new Function("require", "module", "exports", source)(
    (name) => name === "@/lib/backend-fetch" ? { backendFetch: (...args) => globalThis.fetch(...args) }
      : Object.hasOwn(overrides, name) ? overrides[name] : require(name), evaluated, evaluated.exports,
  );
  return evaluated.exports;
}

test("recommendations always require a session and forward backend data, even with demo=1", async (context) => {
  const route = load("../src/app/api/analysis/recommendations/route.ts", {});
  const url = "http://localhost/api/analysis/recommendations?scope=profile&demo=1";
  const calls = [];
  const backendBody = { status: "pending", recommendations: [], marker: "backend-response" };
  context.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push({ url, options });
    return Response.json(backendBody);
  });
  const signedOut = await route.GET(new NextRequest(url));
  assert.equal(signedOut.status, 401);
  assert.equal(calls.length, 0);
  const request = new NextRequest(url, { headers: { cookie: "aphrodize_session=test-token" } });
  const response = await route.GET(request);
  assert.deepEqual(await response.json(), backendBody);
  assert.equal(response.headers.get("cache-control"), "private, no-store");
  assert.ok(calls[0].url.endsWith("/api/v1/analyses/recommendations?market=TH"));
  assert.equal(new Headers(calls[0].options.headers).get("authorization"), "Bearer test-token");
  assert.equal(calls[0].options.cache, "no-store");
  context.mock.method(globalThis, "fetch", async () => { throw new Error("Backend unavailable"); });
  const failed = await route.GET(request);
  assert.equal(failed.status, 502);
  assert.equal(Object.hasOwn(await failed.json(), "recommendations"), false);
});

test("recommendation filters forward satang unchanged and reject invalid inputs", async (context) => {
  const route = load("../src/app/api/analysis/recommendations/route.ts", {});
  const calls = [];
  context.mock.method(globalThis, "fetch", async (url) => { calls.push(url); return Response.json({ status: "ready" }); });
  const request = (query) => new NextRequest(`http://localhost/api/analysis/recommendations?scope=profile&${query}`, {
    headers: { cookie: "aphrodize_session=test-token" },
  });
  assert.equal((await route.GET(request("market=TH&max_price_satang=49900"))).status, 200);
  assert.ok(calls[0].endsWith("?market=TH&max_price_satang=49900"));
  for (const query of ["market=XX", "max_price_satang=-1", "max_price_satang=0.5", "max_price_satang=100000001"]) {
    assert.equal((await route.GET(request(query))).status, 400);
  }
  assert.equal(calls.length, 1);
});

test("product cards render shopping media and convert valid budget numbers to satang", (context) => {
  const product = { id: "catalog-product", brand: "CeraVe", name: "Cream", variant: "50 g",
    price_satang: 17900, price_checked_at: "2026-09-30T17:00:00Z",
    reviewed_at: "2026-09-30T17:00:00Z", matched_claims: [], matched_skin_type: "dry",
    ingredients_inci: ["Aqua"], warnings_label: "", source_url: "https://www.cerave.co.th/",
    image_url: "https://medias.watsons.co.th/publishing/verified.jpg",
    purchase_url: "https://www.watsons.co.th/en/verified/p/BP_275377" };
  const values = [{ status: "ready", recommendations: [{ category: "moisturizer", rule_id: "test", products: [product] }],
    questionnaire_context: { status: "available" }, daily_context: {}, disclaimer: "" }, "", false, "TH", null];
  let index = 0;
  const changes = [];
  const panel = load("../src/app/recommendation/recommendation-panel.tsx", {
    react: { useState: () => { const slot = index++; return [values[slot], (value) => changes.push([slot, value])]; }, useEffect: () => {} },
    "@/components/language-provider": { useLanguage: () => ({ language: "en" }) },
    "@/components/allergy-ingredients": { ALLERGY_INGREDIENTS: [] },
    "@/components/ui/select": { Select: "select" }, "next/image": "img",
  }).RecommendationPanel;
  const nodes = [], texts = [];
  function visit(node) {
    if (Array.isArray(node)) return node.forEach(visit);
    if (typeof node === "string" || typeof node === "number") { texts.push(String(node)); return; }
    if (!node?.props) return;
    nodes.push(node); visit(node.props.children);
  }
  visit(panel({ compact: true }));
  assert.ok(nodes.some(node => node.type === "img" && node.props.src === product.image_url && node.props.alt.includes("50 g")));
  assert.ok(nodes.some(node => node.type === "a" && node.props.href === product.purchase_url && node.props.rel.includes("noreferrer")));
  assert.ok(texts.join(" ").includes("179.00"));
  assert.ok(texts.join(" ").includes("1 Oct 2026"));
  let budget = "1.2e2";
  const nativeFormData = globalThis.FormData;
  context.after(() => { globalThis.FormData = nativeFormData; });
  globalThis.FormData = class { get(name) { return name === "market" ? "TH" : budget; } };
  const form = nodes.find(node => node.type === "form");
  form.props.onSubmit({ preventDefault() {}, currentTarget: {} });
  assert.ok(changes.some(([slot, value]) => slot === 4 && value === 12000));
  changes.length = 0; budget = "0.29";
  form.props.onSubmit({ preventDefault() {}, currentTarget: {} });
  assert.ok(changes.some(([slot, value]) => slot === 4 && value === 29));
  changes.length = 0; budget = "";
  form.props.onSubmit({ preventDefault() {}, currentTarget: {} });
  assert.equal(changes.length, 0); // Reapplying unchanged filters must not leave loading stuck.
});

test("saved consent uses the current account without a latest-analysis cookie; withdrawal is scoped", async (context) => {
  const owner = { userId: "d4e251fd-0f48-42b1-89df-42cf727cd43d", token: "test-token" };
  const route = load("../src/app/api/analysis/route.ts", {
    "@/lib/daily-health-session": { accountSession: async () => owner },
  });
  const calls = [];
  context.mock.method(globalThis, "fetch", async (url, options) => {
    calls.push({ url, options });
    return options.method === "DELETE"
      ? new Response(null, { status: 204 })
      : Response.json({ analysis: true, annotations: true });
  });
  const response = await route.GET(new NextRequest("http://localhost/api/analysis?consents=1"));
  assert.deepEqual(await response.json(), { analysis: true, annotations: true });
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.ok(calls[0].url.endsWith(`/consents/users/${owner.userId}`));
  assert.deepEqual(calls[0].options.headers, { Authorization: `Bearer ${owner.token}` });
  for (const scope of ["analysis", "annotations"]) {
    const result = await route.DELETE(new NextRequest(`http://localhost/api/analysis?scope=${scope}`, { method: "DELETE" }));
    assert.equal(result.status, 204);
    assert.ok(calls.at(-1).url.endsWith(`/consents/users/${owner.userId}/${scope}`));
  }
  const forbidden = await route.DELETE(new NextRequest("http://localhost/api/analysis?scope=analysis", {
    method: "DELETE", headers: { origin: "http://elsewhere", host: "localhost" },
  }));
  assert.equal(forbidden.status, 403);
  assert.equal(calls.length, 3);
});

test("new visitors have no implicit consent", async () => {
  const route = load("../src/app/api/analysis/route.ts", {
    "@/lib/daily-health-session": { accountSession: async () => null },
  });
  const response = await route.GET(new NextRequest("http://localhost/api/analysis?consents=1"));
  assert.deepEqual(await response.json(), { analysis: false, annotations: false });
});

test("repeated review consent does not fill the browser's 50-user limit", async (context) => {
  const owner = { userId: "d4e251fd-0f48-42b1-89df-42cf727cd43d", token: "test-token" };
  const secret = "consent-regression-test";
  const previous = process.env.ANALYSIS_SESSION_SECRET;
  process.env.ANALYSIS_SESSION_SECRET = secret;
  context.after(() => {
    if (previous === undefined) delete process.env.ANALYSIS_SESSION_SECRET;
    else process.env.ANALYSIS_SESSION_SECRET = previous;
  });
  const route = load("../src/app/api/analysis/route.ts", {
    "@/lib/daily-health-session": { accountSession: async () => owner },
  });
  context.mock.method(globalThis, "fetch", async () => Response.json({ id: owner.userId }));
  const encoded = Buffer.from(Array(50).fill(owner.userId).join(",")).toString("base64url");
  const payload = `${encoded}.${Date.now() + 60_000}`;
  const mac = createHmac("sha256", secret).update(payload).digest("hex");
  const body = new FormData();
  body.set("image", new File(["test-image"], "image.jpg", { type: "image/jpeg" }));
  body.set("consent", "yes");
  body.set("annotation_consent", "yes");
  const response = await route.POST(new NextRequest("http://localhost/api/analysis", {
    method: "POST", body, headers: { cookie: `aphrodize_annotations=${payload}.${mac}` },
  }));
  assert.equal(response.status, 202);
  const cookie = response.cookies.get("aphrodize_annotations").value.split(".")[0];
  assert.equal(Buffer.from(cookie, "base64url").toString("utf8"), owner.userId);
});

// Exercise the actual page's handlers/effects with a small hook harness.
function pageHarness() {
  const states = [];
  const effects = [];
  let cursor = 0;
  let mounted = false;
  const page = load("../src/app/capture/page.tsx", {
    react: {
      startTransition: (callback) => callback(),
      useState(initial) {
        const index = cursor++;
        if (!(index in states)) states[index] = initial;
        return [states[index], (next) => { states[index] = typeof next === "function" ? next(states[index]) : next; }];
      },
      useEffect(effect) { if (!mounted) effects.push(effect); },
      useRef: () => ({ current: null }),
    },
    "./analysis-result": { __esModule: true, default: "analysis-result" },
    "@/components/language-provider": { useLanguage: () => ({ language: "en" }) },
    "@/components/workspace-shell": { WorkspaceShell: "section" },
    "./capture.css": {},
  }).default;
  return () => {
    cursor = 0;
    const inputs = [];
    const nodes = [];
    function visit(node) {
      if (Array.isArray(node)) return node.forEach(visit);
      if (!node?.props) return;
      nodes.push(node);
      if (node.type === "input" && node.props.type === "checkbox") inputs.push(node.props);
      visit(node.props.children);
    }
    visit(page());
    inputs.nodes = nodes;
    if (!mounted) { mounted = true; effects.forEach((effect) => effect()); }
    return inputs;
  };
}
const settle = () => new Promise((resolve) => setImmediate(resolve));

function resultHarness(analysis) {
  const states = [analysis, "", false, "overlay", false, 0, false, 1, 0, 0];
  let cursor = 0;
  let pollEffect;
  const Component = load("../src/app/capture/analysis-result.tsx", {
    react: {
      useState(initial) {
        const index = cursor++;
        if (!(index in states)) states[index] = initial;
        return [states[index], (value) => {
          states[index] = typeof value === "function" ? value(states[index]) : value;
        }];
      },
      useRef: () => ({ current: null }),
      useEffect(effect, dependencies) {
        if (dependencies?.length === 1 && typeof dependencies[0] === "number") pollEffect = effect;
      },
    },
    "@/components/language-provider": { useLanguage: () => ({ language: "en" }) },
    "@/app/recommendation/recommendation-panel": { RecommendationPanel: "recommendation-panel" },
    "../result-detail/result-detail.css": {}, "next/image": "img",
    "@/components/analysis/analysis-loader": { AnalysisLoader: ({ message }) => message },
  }).default;
  return {
    render() {
      cursor = 0;
      const nodes = [], texts = [];
      function visit(node) {
        if (Array.isArray(node)) return node.forEach(visit);
        if (typeof node === "string" || typeof node === "number") { texts.push(String(node)); return; }
        if (!node?.props) return;
        if (typeof node.type === "function") return visit(node.type(node.props));
        nodes.push(node);
        visit(node.props.children);
      }
      visit(Component({ view: "results", onReady() {}, onNewAnalysis() {} }));
      return { nodes, text: texts.join(" ") };
    },
    poll: () => pollEffect(),
  };
}

function completedResult(regions = {}) {
  return { id: "result-ui-test", status: "completed", quality_flags: [], error_category: null,
    result: { artifacts_expires_at: new Date(Date.now() + 3_600_000).toISOString(),
      derived_score: { overall: { score: 10, wrinkle_area_ratio: 0.005, wrinkle_pixels: 5, evaluated_pixels: 1000 },
        regions, formula: "min(100, proportion * 2000)", disclaimer: "Experimental" } } };
}

test("personal outline uses a private artifact and falls back honestly on image failure", () => {
  const result = completedResult({ forehead: { score: 2, wrinkle_area_ratio: .01, wrinkle_pixels: 1, evaluated_pixels: 100 } });
  result.result.model_output = { personalized_outline_available: true };
  const harness = resultHarness(result);
  const image = harness.render().nodes.find(node => node.type === "img" && node.props.src === "/api/analysis?artifact=outline");
  assert.ok(image);
  image.props.onError();
  const fallback = harness.render();
  assert.ok(fallback.text.includes("Standard face diagram"));
  assert.equal(fallback.nodes.some(node => node.type === "img" && node.props.src === "/api/analysis?artifact=outline"), false);
  result.result.artifacts_expires_at = new Date(Date.now() - 60_000).toISOString();
  assert.equal(resultHarness(result).render().nodes.some(node => node.type === "img" && node.props.src === "/api/analysis?artifact=outline"), false);
});

test("result shows every region outside collapsed technical details and distinguishes missing measurements", () => {
  const regions = Object.fromEntries(["forehead", "glabella", "nasolabial", "perioral", "image_left_cheek", "image_right_cheek"]
    .map((name, index) => [name, { score: index * 10, wrinkle_area_ratio: index / 100, wrinkle_pixels: index, evaluated_pixels: 100 }]));
  regions.image_left_periocular = { score: 0, wrinkle_area_ratio: 0, wrinkle_pixels: 0, evaluated_pixels: 0 };
  const { nodes, text } = resultHarness(completedResult(regions)).render();
  const bars = nodes.filter(node => node.props.role === "meter");
  assert.equal(bars.length, 6);
  assert.deepEqual(bars.map(node => node.props["aria-valuenow"]), [5, 4, 3, 2, 1, 0]);
  assert.equal(nodes.filter(node => node.props.className === "analysis-region-detail").length, 8);
  assert.equal(nodes.find(node => node.type === "details").props.open, undefined);
  assert.ok(text.includes("Skin analysis overview"));
  assert.ok(text.includes("Standard face diagram, not your face shape"));
  assert.ok(text.includes("not severity or exact pixels"));
  assert.ok(text.includes("overlay/mask for exact marks"));
  assert.ok(text.includes("not a skin grade or diagnosis"));
  assert.ok(text.includes("not better or worse skin"));
  assert.ok(text.includes("Not clinically validated"));
  assert.equal(nodes.filter(node => node.props.className === "face-map-zone is-marked").length, 5);
  assert.ok(text.includes("Not scored") || text.includes("not enough evaluated pixels"));
  assert.equal(/Low detection|Moderate detection|Prominent detection|Overall Assessment/.test(text), false);
  assert.equal(text.includes("Auto-deleted within 24h"), false);
});

test("face schematic never highlights zero, unmeasurable or unknown region locations", () => {
  const area = (ratio, pixels = 100) => ({ score: 5, wrinkle_area_ratio: ratio, wrinkle_pixels: 5, evaluated_pixels: pixels });
  const { nodes, text } = resultHarness(completedResult({ forehead: area(.01), glabella: area(0), unknown_region: area(.02), perioral: area(.03, 0) })).render();
  const highlighted = nodes.filter(node => node.props.className === "face-map-zone is-marked");
  assert.deepEqual(highlighted.map(node => node.props["data-face-region"]), ["forehead"]);
  assert.ok(text.includes("unknown_region"), "unmapped measurements remain available as text");
  assert.equal(text.includes("Texture"), false);
  assert.equal(text.includes("Redness"), false);
});

test("landmark results use a labelled SVG summary without fetching the private regions image", () => {
  const result = completedResult({ forehead: { score: 2, wrinkle_area_ratio: .001, wrinkle_pixels: 1, evaluated_pixels: 1000 } });
  result.result.derived_score.roi_version = "mediapipe-landmark-skin-roi-v1";
  result.result.model_output = { regional_geometry_status: "available" };
  const view = resultHarness(result).render();
  assert.equal(view.nodes.some(node => node.type === "img" && node.props.src === "/api/analysis?artifact=regions"), false);
  assert.deepEqual(view.nodes.filter(node => node.props["data-face-region"]).map(node => node.props["data-face-region"]), ["forehead"]);
  assert.ok(view.text.includes("Standard face diagram"));
  result.result.model_output.regional_geometry_status = "unavailable";
  result.result.derived_score.regions = {};
  const absent = resultHarness(result).render();
  assert.ok(absent.text.includes("This result has no facial landmark data"));
  assert.equal(absent.nodes.some(node => node.props["data-face-region"]), false);
  assert.equal(absent.nodes.filter(node => node.props.className === "analysis-region analysis-region-card is-unscorable").length, 8);
  assert.equal(absent.nodes.filter(node => node.props.role === "meter").length, 0);
  assert.ok(absent.text.includes("Forehead") && absent.text.includes("Perioral area"));
});

test("zero-detection regional summary shows an unshaded face rather than disappearing", () => {
  const result = completedResult({ forehead: { score: 0, wrinkle_area_ratio: 0, wrinkle_pixels: 0, evaluated_pixels: 1000 } });
  const { nodes } = resultHarness(result).render();
  assert.ok(nodes.some(node => node.type === "svg" && node.props.role === "img"));
  assert.equal(nodes.filter(node => node.props["data-face-region"]).length, 0);
});

test("artifact failure offers an image retry without losing measurements; expired images offer a new analysis", () => {
  const harness = resultHarness(completedResult());
  const first = harness.render().nodes.find(node => node.type === "img");
  first.props.onError();
  const failed = harness.render();
  const retry = failed.nodes.find(node => node.type === "button" && node.props.children === "Retry image");
  assert.ok(retry);
  assert.ok(failed.text.includes("0.50"));
  retry.props.onClick();
  const reloaded = harness.render().nodes.find(node => node.type === "img");
  assert.notEqual(reloaded.props.src, first.props.src);
  const expired = completedResult();
  expired.result.artifacts_expires_at = new Date(Date.now() - 60_000).toISOString();
  const expiredView = resultHarness(expired).render();
  assert.equal(expiredView.nodes.some(node => node.type === "img"), false);
  assert.ok(expiredView.text.includes("has expired"));
  assert.ok(expiredView.nodes.some(node => node.type === "button" && node.props.children === "Analyze a new image"));
  assert.ok(expiredView.text.includes("0.50"));
});

test("result load retry fetches again in place and replaces the error with the current result", async (context) => {
  let calls = 0;
  context.mock.method(globalThis, "fetch", async () => {
    calls += 1;
    if (calls === 1) throw new Error("temporarily unavailable");
    return Response.json(completedResult());
  });
  const harness = resultHarness(null);
  harness.render();
  let stop = harness.poll();
  await settle();
  const failure = harness.render();
  const retry = failure.nodes.find(node => node.type === "button" && node.props.children === "Try loading again");
  assert.ok(retry);
  stop();
  retry.props.onClick();
  assert.ok(harness.render().text.includes("Loading analysis"));
  stop = harness.poll();
  await settle();
  const restored = harness.render();
  stop();
  assert.equal(calls, 2);
  assert.ok(restored.text.includes("Skin analysis overview"));
  assert.equal(restored.text.includes("Could not load analysis"), false);
});

test("analysis gates products on completion and separates product and result content", () => {
  for (const status of ["queued", "running", "rejected", "failed", "completed"]) {
    for (const view of ["results", "products"]) {
      let cursor = 0;
      let ready;
      const onReady = (value) => { ready = value; };
      const area = { score: 10, wrinkle_area_ratio: 0.01, wrinkle_pixels: 1, evaluated_pixels: 100 };
      const states = [{ id: "test", status, quality_flags: [], error_category: null,
        result: { derived_score: { overall: area, regions: {}, formula: "test", disclaimer: "Experimental" } } },
        "", false, "overlay", false, 0, false, 1];
      const Component = load("../src/app/capture/analysis-result.tsx", {
        react: { useState: () => [states[cursor++], () => {}], useRef: () => ({ current: null }), useEffect(effect, dependencies) {
          if (dependencies?.includes(onReady)) effect();
        } },
        "@/components/language-provider": { useLanguage: () => ({ language: "en" }) },
        "@/app/recommendation/recommendation-panel": { RecommendationPanel: "recommendation-panel" },
        "../result-detail/result-detail.css": {}, "next/image": "img",
    "@/components/analysis/analysis-loader": { AnalysisLoader: ({ message }) => message },
      }).default;
      const visible = [];
      function visit(node, hidden = false) {
        if (Array.isArray(node)) return node.forEach((child) => visit(child, hidden));
        if (!node?.props) return;
        hidden ||= node.props.hidden === true;
        if (!hidden) visible.push(node);
        visit(node.props.children, hidden);
      }
      visit(Component({ view, onReady, onNewAnalysis() {} }));
      assert.equal(ready, status === "completed");
      assert.equal(visible.some((node) => node.type === "recommendation-panel"), status === "completed" && view === "products");
      assert.equal(visible.some((node) => node.props.className === "analysis-result-grid"), status === "completed" && view === "results");
    }
  }
});

test("capture keeps upload errors, results and another analysis on the same page", async (context) => {
  const originalWindow = globalThis.window;
  const paths = [];
  const listeners = new Map();
  globalThis.window = { location: { hash: "", pathname: "/capture", search: "" },
    addEventListener(name, callback) { listeners.set(name, callback); }, removeEventListener() {},
    history: { state: {}, pushState(_state, _title, path) { paths.push(path); } } };
  context.after(() => { if (originalWindow === undefined) delete globalThis.window; else globalThis.window = originalWindow; });
  context.mock.method(URL, "createObjectURL", () => "blob:test-image");
  let uploadFails = true;
  context.mock.method(globalThis, "fetch", async (_url, options) => options?.method === "POST"
    ? Response.json(uploadFails ? { detail: "Upload failed" } : { status: "queued" }, { status: uploadFails ? 503 : 202 })
    : Response.json({ analysis: false, annotations: false }));
  const render = pageHarness();
  render();
  await settle();
  render().nodes.find((node) => node.type === "input" && node.props.type === "file").props.onChange({
    target: { files: [new File(["image"], "face.png", { type: "image/png" })] },
  });
  render()[0].onChange({ target: { checked: true } });
  const submit = () => render().nodes.find((node) => node.props["aria-describedby"] === "capture-submit-hint").props.onClick();
  await submit();
  assert.ok(render().nodes.some((node) => node.props.role === "alert"));
  assert.equal(paths.length, 0);
  uploadFails = false;
  await submit();
  const result = render().nodes.find((node) => node.type === "analysis-result");
  assert.ok(result);
  assert.ok(render().nodes.some((node) => node.props.className === "capture-studio" && node.props.hidden), "image preparation is hidden in stage 2");
  assert.ok(render().nodes.some((node) => node.props.id === "results"), "results have a scroll target");
  assert.deepEqual(paths, ["/capture#results"]);
  const productsButton = () => render().nodes.find((node) => node.type === "button" && node.props.children?.[0] === "View recommended products");
  assert.equal(productsButton().props.disabled, true, "products wait for completed analysis");
  result.props.onReady(true);
  assert.equal(productsButton().props.disabled, false);
  productsButton().props.onClick();
  assert.equal(paths.at(-1), "/capture#products");
  assert.equal(render().nodes.find((node) => node.type === "analysis-result").props.view, "products");
  globalThis.window.location.hash = "#results";
  listeners.get("popstate")();
  assert.equal(render().nodes.find((node) => node.type === "analysis-result").props.view, "results");
  globalThis.window.location.hash = "#products";
  listeners.get("popstate")();
  assert.equal(render().nodes.find((node) => node.type === "analysis-result").props.view, "products");
  render().nodes.find((node) => node.type === "button" && node.props.children === "Back to results").props.onClick();
  assert.equal(render().nodes.find((node) => node.type === "analysis-result").props.view, "results");
  result.props.onNewAnalysis();
  assert.equal(paths.at(-1), "/capture");
  assert.ok(render().nodes.some((node) => node.props["aria-describedby"] === "capture-submit-hint" && !node.props.disabled));
  assert.ok(render().nodes.some((node) => node.type === "img" && node.props.src === "blob:test-image"), "the selected photo survives stage changes");
  globalThis.window.location.hash = "#results";
  const deepLink = pageHarness();
  deepLink();
  assert.ok(deepLink().nodes.some((node) => node.type === "analysis-result"));
  globalThis.window.location.hash = "#products";
  const productLink = pageHarness();
  productLink();
  const linkedResult = productLink().nodes.find((node) => node.type === "analysis-result");
  assert.equal(linkedResult.props.view, "results", "a product deep link checks analysis first");
  linkedResult.props.onReady(true);
  assert.equal(productLink().nodes.find((node) => node.type === "analysis-result").props.view, "products");
});

test("return visits restore three choices; failed withdrawal keeps consent checked", async (context) => {
  const requests = [];
  let withdrawalFails = false;
  context.mock.method(globalThis, "fetch", async (url, options) => {
    requests.push({ url, options });
    if (options?.method === "DELETE") return new Response(null, { status: withdrawalFails ? 503 : 204 });
    return Response.json({ analysis: true, annotations: true, training: true });
  });
  const render = pageHarness();
  assert.ok(render().every((input) => input.disabled && !input.checked));
  await settle();
  assert.ok(render().every((input) => input.checked && !input.disabled));
  withdrawalFails = true;
  render()[2].onChange({ target: { checked: false } });
  await settle();
  assert.equal(render()[2].checked, true);
  assert.equal(requests.at(-1).url, "/api/analysis?scope=training");
  withdrawalFails = false;
  render()[2].onChange({ target: { checked: false } });
  await settle();
  assert.equal(render()[2].checked, false);
  assert.equal(render()[1].checked, true);
  render()[0].onChange({ target: { checked: false } });
  await settle();
  assert.equal(render()[0].checked, false);
  assert.equal(render()[1].checked, true);
  assert.equal(requests.at(-1).url, "/api/analysis?scope=analysis");
  withdrawalFails = true;
  render()[1].onChange({ target: { checked: false } });
  await settle();
  assert.equal(render()[1].checked, true);
  withdrawalFails = false;
  render()[1].onChange({ target: { checked: false } });
  await settle();
  assert.equal(render()[1].checked, false);
});

test("unverified saved consent remains unchecked", async (context) => {
  context.mock.method(globalThis, "fetch", async () => new Response(null, { status: 502 }));
  const render = pageHarness();
  render();
  await settle();
  const choices = render();
  assert.ok(choices.every((input) => !input.checked));
  assert.ok(choices.slice(0, 2).every((input) => !input.disabled));
  assert.equal(choices[2].disabled, true, "training requires a separate review choice");
});
