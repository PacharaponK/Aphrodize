import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { createRequire } from "node:module";
import ts from "typescript";
import { NextRequest } from "next/server.js";

const require = createRequire(import.meta.url);
const source = ts.transpileModule(fs.readFileSync(new URL("../src/app/api/daily-health/entries/route.ts", import.meta.url), "utf8"), {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS },
}).outputText;
const loaded = { exports: {} };
new Function("require", "module", "exports", source)(name => name === "@/lib/backend-fetch" ? { backendFetch: (...args) => globalThis.fetch(...args) } : name === "@/lib/daily-health-session" ? {
  accountSession: async () => ({ userId: "test-owner", token: "test-only" }),
  backendUrl: path => `http://backend.test${path}`,
  sameOrigin: request => request.headers.get("origin") === "http://frontend.test",
} : require(name), loaded, loaded.exports);
const body = { consent_to_store: true, local_date: "2026-10-05", sleep_duration_minutes: 420,
  water_intake_ml: 1500, outdoor_exposure_choice: 1, prediction: null, model_training_consent: true };
const request = value => new NextRequest("http://frontend.test/api/daily-health/entries", {
  method: "POST", headers: { origin: "http://frontend.test", "content-type": "application/json" },
  body: JSON.stringify(value),
});

test("old clients stay on thirst/dryness scope; only explicit v2 requests include energy", async context => {
  const saved = [];
  context.mock.method(globalThis, "fetch", async (_url, options) => {
    if (options.body) saved.push(JSON.parse(options.body));
    return Response.json({ saved: true });
  });
  assert.equal((await loaded.exports.POST(request(body))).status, 200);
  assert.equal(saved[0].model_training_consent_version, "daily-health-model-training-v1");
  assert.equal((await loaded.exports.POST(request({ ...body,
    model_training_consent_version: "daily-health-model-training-v2" }))).status, 200);
  assert.equal(saved[1].model_training_consent_version, "daily-health-model-training-v2");
});

test("unknown consent versions are rejected before contacting backend", async context => {
  context.mock.method(globalThis, "fetch", async () => { assert.fail("Invalid scope must not be forwarded"); });
  const response = await loaded.exports.POST(request({ ...body, model_training_consent_version: "unexpected" }));
  assert.equal(response.status, 400);
});

test("an unchecked v2 option stays false and does not silently grant consent", async context => {
  let saved;
  context.mock.method(globalThis, "fetch", async (_url, options) => {
    if (options.body) saved = JSON.parse(options.body);
    return Response.json({ saved: true });
  });
  const response = await loaded.exports.POST(request({ ...body,
    model_training_consent: false, model_training_consent_version: "daily-health-model-training-v2" }));
  assert.equal(response.status, 200);
  assert.equal(saved.model_training_consent, false);
});
