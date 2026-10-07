import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const { NextRequest } = require("next/server");
const { unstable_doesMiddlewareMatch } = require("next/experimental/testing/server");
function load(relative, overrides = {}) {
  const loaded = { exports: {} };
  const source = ts.transpileModule(fs.readFileSync(new URL(relative, import.meta.url), "utf8"), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  new Function("require", "module", "exports", source)(name => {
    if (Object.hasOwn(overrides, name)) return overrides[name];
    if (name === "@/lib/daily-health-session") return load("../src/lib/daily-health-session.ts");
    return require(name);
  }, loaded, loaded.exports);
  return loaded.exports;
}
const { proxy, config } = load("../src/proxy.ts");
const recommendations = load("../src/app/api/analysis/recommendations/route.ts");
const request = (path, cookie, init = {}) => new NextRequest(`http://localhost:3000${path}`, {
  ...init, headers: { ...init.headers, ...(cookie ? { cookie } : {}) },
});

test("login returns to the requested page and rejects external redirect destinations", async t => {
  const savedFetch = global.fetch;
  const savedWindow = global.window;
  const savedFormData = global.FormData;
  t.after(() => {
    global.fetch = savedFetch;
    global.FormData = savedFormData;
    if (savedWindow === undefined) delete global.window;
    else global.window = savedWindow;
  });
  global.fetch = async () => Response.json({ signed_in: true });
  global.FormData = class { get(name) { return name === "email" ? "test@example.com" : "test-password"; } };
  const destinations = [];
  let refreshes = 0;
  const Login = load("../src/app/login/page.tsx", {
    react: { useState: value => [value, () => {}] },
    "next/navigation": { useRouter: () => ({ replace: value => destinations.push(value), refresh: () => refreshes++ }) },
    "@/components/language-provider": { useLanguage: () => ({ language: "en" }), LanguageToggle: () => null },
    "@/components/theme-toggle": { ThemeToggle: () => null },
    "@/components/auth-intro-video": { AuthIntroVideo: () => null },
  }).default;
  function findForm(node) {
    if (Array.isArray(node)) return node.map(findForm).find(Boolean);
    if (node?.type === "form") return node;
    return node?.props ? findForm(node.props.children) : undefined;
  }
  for (const [next, expected] of [["/onboarding/health?edit=1", "/onboarding/health?edit=1"],
    ["https://outside.test", "/"], ["//outside.test", "/"], ["/\\outside.test", "/"],
    ["javascript:alert(1)", "/"], ["http://[", "/"]]) {
    global.window = { location: { origin: "http://localhost:3000", search: `?${new URLSearchParams({ next })}` } };
    await findForm(Login()).props.onSubmit({ preventDefault() {}, currentTarget: { checkValidity: () => true } });
    assert.equal(destinations.at(-1), expected, next);
  }
  assert.equal(refreshes, 6);
});

test("only capture and sign-in flows allow guests; member pages and APIs verify sessions", async t => {
  const savedFetch = global.fetch;
  t.after(() => { global.fetch = savedFetch; });
  let calls = 0;
  global.fetch = async () => { calls++; throw new Error("Guests must not contact the backend"); };
  for (const path of ["/capture", "/capture/", "/capture#products", "/login", "/signup",
    "/api/analysis", "/api/analysis/recommendations", "/api/auth/login", "/api/auth/signup",
    "/api/auth/logout", "/admin/products", "/api/admin/session", "/api/admin/products"]) {
    assert.equal((await proxy(request(path))).headers.get("x-middleware-next"), "1", path);
  }
  for (const path of ["/", "/clients", "/trend", "/profile", "/onboarding/health?edit=1",
    "/portal", "/uv-map", "/showcase", "/quality-rejected", "/recommendation", "/result-detail",
    "/capture-extra", "/capture/private", "/future-member-page"]) {
    const response = await proxy(request(path));
    const login = new URL(response.headers.get("location"));
    assert.equal(response.status, 307, path);
    assert.equal(login.pathname, "/login");
    assert.equal(login.searchParams.get("next"), path);
    assert.equal(response.headers.get("cache-control"), "no-store");
  }
  for (const path of ["/api/daily-health/predict", "/api/uv/map", "/api/uv/recommendation",
    "/api/daily-health/entries", "/api/profile", "/api/onboarding/health", "/api/analysis/private"]) {
    const response = await proxy(request(path));
    assert.equal(response.status, 401, path);
    assert.equal(response.headers.get("location"), null);
  }
  assert.equal(calls, 0);
  // Anonymous analysis and admin sessions cannot stand in for a member session.
  assert.equal((await proxy(request("/profile", "aphrodize_anonymous=guest; aphrodize_admin=admin"))).status, 307);

  for (const status of [401, 403]) {
    global.fetch = async () => new Response(null, { status });
    assert.equal((await proxy(request("/clients", "aphrodize_session=expired-or-forged"))).status, 307);
    assert.equal((await proxy(request("/api/daily-health/predict", "aphrodize_session=expired-or-forged"))).status, 401);
  }
  global.fetch = async (_url, init) => {
    assert.equal(init.headers.Authorization, "Bearer member-token");
    return Response.json({ user_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" });
  };
  assert.equal((await proxy(request("/profile", "aphrodize_session=member-token"))).headers.get("x-middleware-next"), "1");
  global.fetch = async () => Response.json({ user_id: "invalid-identity" });
  assert.equal((await proxy(request("/profile", "aphrodize_session=member-token"))).status, 503);
  global.fetch = async () => { throw new Error("Service unavailable"); };
  assert.equal((await proxy(request("/profile", "aphrodize_session=member-token"))).status, 503);
});

test("matcher protects pages and APIs while allowing capture static assets", () => {
  for (const path of ["/", "/capture", "/profile", "/api/daily-health/predict", "/assets-private", "/_next/image-private"]) {
    assert.equal(unstable_doesMiddlewareMatch({ config, nextConfig: {}, url: path }), true, path);
  }
  for (const path of ["/_next/static/chunks/app.js", "/_next/image?url=test", "/assets/aphrodize-logo.svg", "/legacy/theme.js", "/favicon.ico"]) {
    assert.equal(unstable_doesMiddlewareMatch({ config, nextConfig: {}, url: path }), false, path);
  }
});

test("guest product recommendations use transient answers and never require an account cookie", async t => {
  const savedFetch = global.fetch;
  const savedUsername = process.env.BACKEND_API_USERNAME;
  const savedPassword = process.env.BACKEND_API_PASSWORD;
  process.env.BACKEND_API_USERNAME = "test-service";
  process.env.BACKEND_API_PASSWORD = "test-password";
  t.after(() => {
    global.fetch = savedFetch;
    if (savedUsername === undefined) delete process.env.BACKEND_API_USERNAME;
    else process.env.BACKEND_API_USERNAME = savedUsername;
    if (savedPassword === undefined) delete process.env.BACKEND_API_PASSWORD;
    else process.env.BACKEND_API_PASSWORD = savedPassword;
  });
  const answers = { skin_type: "dry", skin_sensitivity: "low", known_product_allergy: "no",
    severe_irritation: "no", age_group: "25_34" };
  global.fetch = async (url, init) => {
    assert.ok(String(url).includes("/analyses/recommendations/guest?"));
    assert.deepEqual(JSON.parse(init.body), answers);
    return Response.json({ status: "ready", recommendations: [{ products: [{ id: "reviewed-product" }] }] });
  };
  assert.deepEqual(await (await recommendations.GET(request("/api/analysis/recommendations"))).json(), { guest_profile_required: true });
  const response = await recommendations.POST(request("/api/analysis/recommendations?market=TH", null, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(answers),
  }));
  assert.equal(response.status, 200);
  assert.equal((await response.json()).recommendations[0].products[0].id, "reviewed-product");
});
