import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
function load(file, overrides = {}) {
  const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const exported = {};
  new Function("require", "exports", code)(name => overrides[name] ?? require(name), exported);
  return exported;
}

test("proxy creates bounded correlation ID and forwards it to the route and browser", () => {
  const { proxy } = load("src/proxy.ts");
  const { NextRequest } = require("next/server");
  const response = proxy(new NextRequest("http://localhost/api/health", {
    headers: { "x-request-id": "private@example.com" },
  }));
  const id = response.headers.get("x-request-id");
  assert.match(id, /^[0-9a-f]{32}$/);
  assert.equal(response.headers.get("x-middleware-request-x-request-id"), id);
});

test("upstream instrumentation preserves auth and correlation without private log fields", async context => {
  const logs = [];
  context.mock.method(console, "info", text => logs.push(JSON.parse(text)));
  context.mock.method(globalThis, "fetch", async (_input, init) => {
    assert.equal(init.headers.get("authorization"), "Bearer private-token");
    assert.equal(init.headers.get("x-request-id"), "e".repeat(32));
    assert.ok(init.signal);
    return new Response(null, { status: 503 });
  });
  const { backendFetch } = load("src/lib/backend-fetch.ts", {
    "next/headers": { headers: async () => new Headers({ "x-request-id": "e".repeat(32) }) },
  });
  const response = await backendFetch("http://backend/private?token=secret", {
    headers: { Authorization: "Bearer private-token" },
  });
  assert.equal(response.status, 503);
  assert.equal(logs[0].status, 503);
  assert.doesNotMatch(JSON.stringify(logs), /private|secret|token/);
});

test("upstream timeout records failure and rejects instead of leaving request hanging", async context => {
  const previous = process.env.BACKEND_TIMEOUT_MS;
  process.env.BACKEND_TIMEOUT_MS = "10";
  context.after(() => { if (previous === undefined) delete process.env.BACKEND_TIMEOUT_MS;
    else process.env.BACKEND_TIMEOUT_MS = previous; });
  const logs = [];
  context.mock.method(console, "info", text => logs.push(JSON.parse(text)));
  context.mock.method(globalThis, "fetch", (_input, init) => new Promise((_resolve, reject) => {
    init.signal.addEventListener("abort", () => reject(init.signal.reason));
    setTimeout(() => reject(new Error("Timeout test guard")), 100);
  }));
  const { backendFetch } = load("src/lib/backend-fetch.ts", {
    "next/headers": { headers: () => { throw new Error("No request context"); } },
  });
  await assert.rejects(backendFetch("http://backend"), error => error.name === "TimeoutError");
  assert.equal(logs[0].status, 502);
});
