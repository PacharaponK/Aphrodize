import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import ts from "typescript";
import { NextRequest } from "next/server.js";

const require = createRequire(import.meta.url);
const source = ts.transpileModule(fs.readFileSync(new URL("../src/app/api/analysis/recommendations/route.ts", import.meta.url), "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true },
}).outputText;
const evaluated = { exports: {} };
new Function("require", "module", "exports", source)(name => name === "@/lib/backend-fetch" ? { backendFetch: (...args) => globalThis.fetch(...args) } : require(name), evaluated, evaluated.exports);
const { GET, POST } = evaluated.exports;
const url = "http://localhost/api/analysis/recommendations";
const initial = await GET(new NextRequest(url));
assert.equal(initial.status, 200);
assert.equal((await initial.json()).guest_profile_required, true);
assert.equal(initial.headers.get("cache-control"), "no-store");
const answers = { skin_type: "dry", skin_sensitivity: "low", known_product_allergy: "no", severe_irritation: "no", age_group: "25_34", sunscreen_frequency: "every_day" };
process.env.BACKEND_API_USERNAME = "test-service";
process.env.BACKEND_API_PASSWORD = "test-password";
process.env.BACKEND_API_URL = "http://backend.test";
let calls = 0;
globalThis.fetch = async (target, init) => {
  calls++;
  assert.equal(target, "http://backend.test/api/v1/analyses/recommendations/guest?market=TH&max_price_satang=50000");
  assert.equal(init.method, "POST");
  assert.deepEqual(JSON.parse(init.body), answers);
  assert.ok(init.headers.Authorization.startsWith("Basic "));
  assert.equal(init.cache, "no-store");
  return Response.json({ status: "ready", recommendations: [] });
};
const request = (query = "?market=TH&max_price_satang=50000", body = JSON.stringify(answers), origin = "http://localhost") => new NextRequest(url + query, {
  method: "POST", body, headers: { "Content-Type": "application/json", origin, host: "localhost" },
});
const result = await POST(request());
assert.equal(result.status, 200);
assert.equal(result.headers.get("cache-control"), "private, no-store");
assert.equal((await POST(request("", "{}", "http://other.test"))).status, 403);
assert.equal((await POST(request("", "bad json"))).status, 400);
assert.equal((await POST(request("?max_price_satang=-1"))).status, 400);
assert.equal((await POST(request("?market=invalid"))).status, 400);
assert.equal((await POST(request("", "x".repeat(4097)))).status, 413);
assert.equal(calls, 1);
console.log("Guest recommendations: anonymous access, forwarding, filters and validation passed");

// Per-request skin answers must retain the private image context for guests.
const { createHmac } = require("node:crypto");
process.env.ANALYSIS_SESSION_SECRET = "test-analysis-secret";
const analysisId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const expiry = String(Date.now() + 60_000);
const mac = createHmac("sha256", process.env.ANALYSIS_SESSION_SECRET).update(`${analysisId}.${expiry}`).digest("hex");
const cookie = `aphrodize_analysis=${analysisId}.${expiry}.${mac}; aphrodize_anonymous=${analysisId}:guest-token`;
globalThis.fetch = async (target, init) => {
  assert.equal(target, `http://backend.test/api/v1/analyses/${analysisId}/recommendations?market=TH`);
  assert.equal(init.headers.Authorization, "Bearer guest-token");
  assert.deepEqual(JSON.parse(init.body), answers);
  return Response.json({ status: "ready", image_context: { status: "eligible" } });
};
const imageRequest = (cookies) => new NextRequest(url + "?scope=analysis", {
  method: "POST", body: JSON.stringify(answers), headers: { cookie: cookies, origin: "http://localhost", host: "localhost" },
});
assert.equal((await POST(imageRequest(cookie))).status, 200);
assert.equal((await POST(imageRequest(""))).status, 401);
assert.equal((await POST(imageRequest(cookie.replace(mac, "0".repeat(64))))).status, 401);
console.log("Guest image recommendations: signed image and owner token required");
