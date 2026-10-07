import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
const compiled = ts.transpileModule(fs.readFileSync("src/app/portal/page.tsx", "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
}).outputText;

function renderPortal(env = {}) {
  const exports = {};
  const load = (name) => {
    if (name.endsWith(".css")) return {};
    if (name === "@/lib/page-metadata") return { pageMetadata: () => ({}) };
    if (name === "next/link") return { default: ({ children, ...props }) => React.createElement("a", props, children) };
    return require(name);
  };
  new Function("require", "exports", "process", compiled)(load, exports, { env });
  return renderToStaticMarkup(React.createElement(exports.default));
}

test("portal uses VM proxy destinations and marks unconfigured services unavailable", () => {
  const html = renderPortal();
  for (const href of ["/", "/label-studio/", "/grafana/", "/admin"]) {
    assert.ok(html.includes(`href="${href}"`), href);
  }
  for (const href of ["http://localhost:8080", "http://localhost:5000", "http://localhost:9001", "http://localhost:3001"]) {
    assert.ok(!html.includes(`href="${href}"`), href);
  }
  assert.ok(html.includes("ยังไม่ได้ตั้งค่าทางเข้า Console"));
  assert.ok(html.includes("ยังไม่ได้เปิดทางเข้า MLflow บน VM"));
  assert.ok(html.includes("<details>"));
  assert.ok(!html.includes("<nav"));
});

test("optional service URLs accept web destinations and exclude unsafe or credential-bearing URLs", () => {
  const configured = renderPortal({
    PORTAL_MINIO_URL: "https://minio.example.org",
    PORTAL_MLFLOW_URL: "http://localhost:5000",
  });
  assert.ok(configured.includes('href="https://minio.example.org/"'));
  assert.ok(configured.includes('href="http://localhost:5000/"'));
  assert.ok(!configured.includes('class="portal-unavailable"'));
  for (const value of ["javascript:alert(1)", "not a URL", "https://user:password@example.org"]) {
    const html = renderPortal({ PORTAL_MINIO_URL: value, PORTAL_MLFLOW_URL: value });
    assert.ok(html.includes("ยังไม่ได้ตั้งค่าทางเข้า Console"));
    assert.ok(html.includes("ยังไม่ได้เปิดทางเข้า MLflow บน VM"));
    assert.ok(!html.includes(value));
  }
});

test("direct portal access has no main navigation while the main site retains it", () => {
  const source = fs.readFileSync("src/components/shared-navigation.tsx", "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  for (const pathname of ["/portal", "/"]) {
    const exports = {};
    new Function("require", "exports", code)((name) => {
      if (name === "next/navigation") return { usePathname: () => pathname };
      if (name === "./app-navigation") return { AppNavigation: () => React.createElement("nav", {}, "Main navigation") };
      return require(name);
    }, exports);
    const html = renderToStaticMarkup(React.createElement(exports.SharedNavigation));
    assert.equal(html, pathname === "/portal" ? "" : "<nav>Main navigation</nav>");
  }
});
