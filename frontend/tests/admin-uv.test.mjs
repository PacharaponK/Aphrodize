// Run: node --test tests/admin-uv.test.mjs
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
let states = [];
let index = 0;
function load(relative) {
  const filename = path.resolve(relative);
  const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const exports = {};
  new Function("require", "exports", compiled)((name) => {
    if (name.endsWith(".css")) return {};
    if (name === "react") return { ...React, useEffect() {}, useState: () => [states[index++], () => {}] };
    if (name === "@/components/ui/button") return { Button: ({ variant, ...props }) => React.createElement("button", { ...props, "data-variant": variant }) };
    if (name.startsWith("@/")) return load(`src/${name.slice(2)}.ts`);
    return require(name);
  }, exports);
  return exports;
}
const { UvModelPanel } = load("src/app/admin/uv-model-panel.tsx");
const { GET, POST } = load("src/app/api/admin/uv/route.ts");
const { adminSessionValue } = load("src/lib/admin-auth.ts");
const { NextRequest } = require("next/server");

const score = { n: 14, mae: 0.2, bias: 0.1, undercalls: { 8: 0, 11: 0 } };
const comparison = { candidate: score, incumbent: score, persistence: score, passed: true };
const overview = {
  active: "uv-current", previous: "uv-previous", history: [], data_dates: {}, active_manifest: null,
  forecast_generated_at: null, monitoring: null, pipeline: { status: "awaiting_review", at: "2026-10-20T00:00:00Z" },
  candidate: { version: "uv-candidate", can_promote: true, issue: null, tracking: null, evaluation: null,
    gate: { base_version: "uv-current", cities: Object.fromEntries(["bangkok", "songkhla", "chiang_mai"].map(c => [c, { h1: comparison, h2: comparison }])) } },
};
function render(data, error = "") {
  states = [data, false, error, ""]; index = 0;
  return renderToStaticMarkup(React.createElement(UvModelPanel));
}

test("UV panel shows every city/horizon, missing dates and disables approval on errors", () => {
  const html = render(overview);
  assert.equal((html.match(/<td>ผ่าน<\/td>/g) ?? []).length, 6);
  assert.match(html, /MAE ใหม่/);
  assert.match(html, /พลาด ≥11/);
  assert.match(html, /ยังไม่มีข้อมูล/);
  assert.doesNotMatch(html, /<button disabled="">.*อนุมัติใช้ candidate นี้/);
  assert.match(render(overview, "Session หมดอายุ"), /<button disabled="">.*อนุมัติใช้ candidate นี้/);
  assert.match(render({ ...overview, candidate: null }), /ยังไม่มี candidate ให้ตรวจ/);
});

test("UV proxy requires signed session and matching origin before forwarding", async (t) => {
  const previous = { username: process.env.ADMIN_USERNAME, password: process.env.ADMIN_PASSWORD, fetch: globalThis.fetch };
  process.env.ADMIN_USERNAME = "uv-test"; process.env.ADMIN_PASSWORD = "test-only-password";
  t.after(() => {
    if (previous.username === undefined) delete process.env.ADMIN_USERNAME; else process.env.ADMIN_USERNAME = previous.username;
    if (previous.password === undefined) delete process.env.ADMIN_PASSWORD; else process.env.ADMIN_PASSWORD = previous.password;
    globalThis.fetch = previous.fetch;
  });
  let calls = 0;
  globalThis.fetch = async () => { calls++; return Response.json({ active: "uv-current" }); };
  assert.equal((await GET(new NextRequest("http://localhost:3000/api/admin/uv"))).status, 401);
  const headers = { cookie: `aphrodize_admin=${adminSessionValue()}`, host: "localhost:3000", "content-type": "application/json" };
  for (const origin of [undefined, "https://untrusted.example"]) {
    assert.equal((await POST(new NextRequest("http://localhost:3000/api/admin/uv", {
      method: "POST", headers: { ...headers, ...(origin ? { origin } : {}) }, body: "{}",
    }))).status, 403);
  }
  assert.equal(calls, 0);
  const response = await GET(new NextRequest("http://localhost:3000/api/admin/uv", { headers }));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(calls, 1);
});
