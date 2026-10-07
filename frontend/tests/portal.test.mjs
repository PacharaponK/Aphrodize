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

test("portal renders both languages with the Compose destinations and safe external links", () => {
  for (const language of ["th", "en"]) {
    const exports = {};
    const load = (name) => {
      if (name.endsWith(".css")) return {};
      if (name === "@/components/language-provider") return { useLanguage: () => ({ language }), LanguageToggle: () => React.createElement("button", {}, "Language") };
      if (name === "@/components/theme-toggle") return { ThemeToggle: () => React.createElement("button", {}, "Theme") };
      if (name === "next/link") return { default: ({ children, ...props }) => React.createElement("a", props, children) };
      return require(name);
    };
    new Function("require", "exports", compiled)(load, exports);
    const html = renderToStaticMarkup(React.createElement(exports.default));
    for (const href of ["/#dashboard", "/capture", "/clients", "/uv-map", "/admin", "http://localhost:8000/docs", "http://localhost:8080", "http://localhost:5000", "http://localhost:9001"]) {
      assert.ok(html.includes(`href="${href}"`), href);
    }
    for (const href of ["http://localhost:3001/d/aphrodize-system", "http://localhost:3001/alerting/notifications", "http://localhost:9090/targets"]) {
      assert.ok(html.includes(`href="${href}"`), href);
    }
    assert.equal((html.match(/target="_blank" rel="noopener noreferrer"/g) ?? []).length, 7);
    assert.ok(html.includes(language === "th" ? "ติดตามระบบและการแจ้งเตือน" : "Monitoring and alerts"));
    assert.ok(html.includes(language === "th" ? "ทุกเซอร์วิส ในที่เดียว" : "Every service. One place."));
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
