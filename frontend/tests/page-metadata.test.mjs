import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import ts from "typescript";

const app = path.resolve("src/app");
const source = fs.readFileSync("src/lib/page-metadata.ts", "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;

function loadMetadata(SITE_URL) {
  const exports = {};
  new Function("exports", "process", compiled)(exports, { env: { SITE_URL } });
  return exports;
}

function metadataArguments(filename) {
  const file = ts.createSourceFile(filename, fs.readFileSync(filename, "utf8"), ts.ScriptTarget.Latest, true);
  let args;
  function visit(node) {
    if (ts.isCallExpression(node) && node.expression.getText(file) === "pageMetadata") {
      args = node.arguments.map((argument) => JSON.parse(argument.getText(file)));
    }
    ts.forEachChild(node, visit);
  }
  visit(file);
  return args;
}

test("every page has matching share metadata, indexing policy and canonical URLs", () => {
  const configured = loadMetadata("https://aphrodize.example");
  const unconfigured = loadMetadata();
  const publicRoutes = new Set(["/login", "/signup", "/uv-map"]);
  const titles = new Set();
  const pages = fs.readdirSync(app, { recursive: true }).filter((file) => path.basename(file) === "page.tsx");

  assert.ok(pages.length > 0);
  for (const page of pages) {
    const filename = path.join(app, page);
    const layout = path.join(path.dirname(filename), "layout.tsx");
    const args = metadataArguments(filename) ?? (fs.existsSync(layout) ? metadataArguments(layout) : undefined);
    assert.ok(args, `${page} must define server metadata`);
    const route = `/${path.dirname(page).split(path.sep).filter((part) => part !== ".").join("/")}`;
    const metadata = configured.pageMetadata(...args);
    const canonicalPath = ["/recommendation", "/result-detail"].includes(route) ? "/capture" : route;

    assert.equal(args[2], canonicalPath, page);
    assert.equal(metadata.title, `${args[0]} | Aphrodize`);
    assert.ok(metadata.title.length <= 30, `${page} needs a short tab title`);
    assert.ok(!titles.has(metadata.title), `${page} needs a unique title`);
    titles.add(metadata.title);
    assert.ok(metadata.description.length >= 50, `${page} needs a useful description`);
    assert.equal(metadata.openGraph.title, metadata.title);
    assert.equal(metadata.twitter.title, metadata.title);
    assert.equal(metadata.openGraph.description, metadata.description);
    assert.equal(metadata.twitter.description, metadata.description);
    assert.equal(metadata.openGraph.locale, args[4] ?? "en_US");
    assert.equal(metadata.robots.index, publicRoutes.has(route), page);
    assert.equal(metadata.alternates.canonical, `https://aphrodize.example${canonicalPath}`);
    assert.equal(metadata.openGraph.url, metadata.alternates.canonical);
    assert.equal(unconfigured.pageMetadata(...args).alternates, undefined);
    assert.equal(unconfigured.pageMetadata(...args).openGraph.url, undefined);
  }
});
