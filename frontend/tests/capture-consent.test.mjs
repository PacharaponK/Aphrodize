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
    (name) => Object.hasOwn(overrides, name) ? overrides[name] : require(name), evaluated, evaluated.exports,
  );
  return evaluated.exports;
}

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
      useState(initial) {
        const index = cursor++;
        if (!(index in states)) states[index] = initial;
        return [states[index], (next) => { states[index] = typeof next === "function" ? next(states[index]) : next; }];
      },
      useEffect(effect) { if (!mounted) effects.push(effect); },
      useRef: () => ({ current: null }),
    },
    "next/navigation": { useRouter: () => ({ push() {} }) },
    "@/components/language-provider": { useLanguage: () => ({ language: "en" }) },
    "@/components/workspace-shell": { WorkspaceShell: "section" },
    "./capture.css": {},
  }).default;
  return () => {
    cursor = 0;
    const inputs = [];
    function visit(node) {
      if (Array.isArray(node)) return node.forEach(visit);
      if (!node?.props) return;
      if (node.type === "input" && node.props.type === "checkbox") inputs.push(node.props);
      visit(node.props.children);
    }
    visit(page());
    if (!mounted) { mounted = true; effects.forEach((effect) => effect()); }
    return inputs;
  };
}
const settle = () => new Promise((resolve) => setImmediate(resolve));

test("return visits restore both choices; failed withdrawal keeps consent checked", async (context) => {
  const requests = [];
  let withdrawalFails = false;
  context.mock.method(globalThis, "fetch", async (url, options) => {
    requests.push({ url, options });
    if (options?.method === "DELETE") return new Response(null, { status: withdrawalFails ? 503 : 204 });
    return Response.json({ analysis: true, annotations: true });
  });
  const render = pageHarness();
  assert.ok(render().every((input) => input.disabled && !input.checked));
  await settle();
  assert.ok(render().every((input) => input.checked && !input.disabled));
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
  assert.ok(render().every((input) => !input.checked && !input.disabled));
});
