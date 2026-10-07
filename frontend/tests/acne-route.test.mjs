import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const filename = new URL("../src/app/api/acne/route.ts", import.meta.url);
const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS },
}).outputText;
let session = { userId: "verified-owner", token: "test-only" };
let calls = [];
const testModule = { exports: {} };
class ResponseStub {
  constructor(body, init = {}) { this.body = body; this.status = init.status ?? 200; this.headers = init.headers; }
  static json(body, init) { return new ResponseStub(body, init); }
}
new Function("require", "module", "exports", source)(name => {
  if (name === "@/lib/backend-fetch") return { backendFetch: (...args) => globalThis.fetch(...args) };
  if (name === "next/server") return { NextResponse: ResponseStub };
  if (name === "@/lib/daily-health-session") return {
    accountSession: async () => session,
    sameOrigin: request => request.originValid,
    backendUrl: path => `http://backend.test${path}`,
  };
  throw new Error(`Unexpected dependency ${name}`);
}, testModule, testModule.exports);
function request(query = "", payload = {}, originValid = true) {
  return { originValid, nextUrl: new URL(`http://frontend.test/api/acne${query}`),
    text: async () => typeof payload === "string" ? payload : JSON.stringify(payload) };
}

test("private training consent proxy and security boundaries", async () => {
  const savedFetch = global.fetch;
  global.fetch = async (url, options) => {
    calls.push({ url, options });
    return { status: 200, ok: true, json: async () => ({ training_consent_active: true }) };
  };
  try {
    const response = await testModule.exports.PUT(request("?scope=training", { consent_to_train_acne: true }));
    assert.equal(response.status, 410);
    assert.equal(response.headers["Cache-Control"], "no-store");
    assert.equal(calls.length, 0);
    await testModule.exports.DELETE(request("?scope=training"));
    assert.equal(calls[0].options.method, "DELETE");
    calls = [];
    assert.equal((await testModule.exports.PUT(request("?scope=training", {}, false))).status, 403);
    assert.equal((await testModule.exports.DELETE(request("?scope=training&date=2026-01-01"))).status, 400);
    assert.equal((await testModule.exports.PUT(request("?scope=unexpected"))).status, 400);
    assert.equal((await testModule.exports.POST(request("?scope=training"))).status, 400);
    assert.equal((await testModule.exports.PUT(request("?scope=training", "ก".repeat(2000)))).status, 410);
    session = null;
    assert.equal((await testModule.exports.PUT(request("?scope=training"))).status, 401);
    assert.equal(calls.length, 0);
  } finally { global.fetch = savedFetch; }
});
