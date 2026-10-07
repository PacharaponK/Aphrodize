// Run: node --test tests/personal-forecast-api.test.mjs (from frontend/).
import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectDirectory = path.resolve(testDirectory, "..");
const moduleCache = new Map();

function loadTypeScript(filename) {
  filename = path.resolve(filename);
  if (moduleCache.has(filename)) return moduleCache.get(filename).exports;
  const loaded = { exports: {} };
  moduleCache.set(filename, loaded);
  const nativeRequire = createRequire(filename);
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const localRequire = (name) => {
    if (name.startsWith("@/")) {
      const base = path.resolve(projectDirectory, "src", name.slice(2));
      const localPath = [`${base}.ts`, `${base}.tsx`].find((candidate) => fs.existsSync(candidate));
      if (localPath) return loadTypeScript(localPath);
    }
    return nativeRequire(name);
  };
  new Function("require", "module", "exports", source)(localRequire, loaded, loaded.exports);
  return loaded.exports;
}

const { NextRequest } = createRequire(import.meta.url)("next/server");
const { GET, PUT } = loadTypeScript(
  path.resolve(projectDirectory, "src/app/api/daily-health/personal-forecast/route.ts"),
);

test("personal forecast API is scoped to the signed-in account and never cached", async (t) => {
  const previousFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = previousFetch; });
  const accountId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  const calls = [];
  globalThis.fetch = async (input, init = {}) => {
    const url = String(input);
    calls.push({ url, init });
    if (url.endsWith("/api/v1/auth/profile")) {
      return Response.json({ user_id: accountId });
    }
    return Response.json({ enabled: true, status: "forecasted" });
  };

  const response = await GET(new NextRequest("http://localhost:3000/api/daily-health/personal-forecast", {
    headers: { cookie: "aphrodize_session=private-session-token" },
  }));

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(calls[1].url, `http://127.0.0.1:8000/api/v1/daily-health/users/${accountId}/personal-forecast`);
  assert.equal(new Headers(calls[1].init.headers).get("authorization"), "Bearer private-session-token");
});

test("personal forecast consent changes reject cross-origin requests before session lookup", async (t) => {
  const previousFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = previousFetch; });
  let fetchCalls = 0;
  globalThis.fetch = async () => {
    fetchCalls += 1;
    return Response.json({});
  };

  const response = await PUT(new NextRequest("http://localhost:3000/api/daily-health/personal-forecast", {
    method: "PUT",
    headers: {
      cookie: "aphrodize_session=private-session-token",
      host: "localhost:3000",
      origin: "https://untrusted.example",
    },
  }));

  assert.equal(response.status, 403);
  assert.equal(fetchCalls, 0);
});
