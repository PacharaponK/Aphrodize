import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";

const read = path => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const shared = read("../src/app/design-system.css");
const home = read("../src/app/home.css");
const health = read("../src/app/clients/clients.css");
const capture = read("../src/app/capture/capture.css");

test("navbar, Home and workspace share one frame and responsive gutter", () => {
  assert.match(shared, /--page-frame-max: 1920px/);
  assert.match(shared, /scrollbar-gutter: stable/);
  assert.match(shared, /width: calc\(min\(100%, var\(--page-frame-max\)\) - 2 \* var\(--responsive-page-gutter\)\)/);
  assert.match(shared, /max-width: var\(--page-frame-max\)/);
  assert.match(shared, /--responsive-page-gutter: 18px/);
  assert.match(shared, /--responsive-page-gutter: 14px/);
  assert.match(home, /padding: 28px var\(--responsive-page-gutter\) 48px/);
  assert.match(home, /width:min\(100%,var\(--page-frame-max\)\)/);
  assert.doesNotMatch(shared, /max-width:1504px/);
});

test("health section frames share full width in sparse and populated states", () => {
  assert.doesNotMatch(shared, /--reading-panel-max/);
  assert.doesNotMatch(health, /var\(--reading-panel-max\)/);
  assert.match(health, /tracker-results:not\(:has\(\.tracker-metric-grid\)\)/);
  assert.match(health, /personal-forecast-panel:not\(:has\(\.personal-forecast-chart-grid\)\)/);
  assert.match(health, /padding: clamp\(28px, 3vw, 56px\) 0 48px/);
  assert.match(health, /daily-entry-card \{ flex-direction: column; align-items: stretch/);
});

test("compact empty chooser keeps real previews contained and expandable", () => {
  assert.match(capture, /\.capture-image-frame \{[^}]*min-height: 200px/);
  assert.match(capture, /\.capture-image-frame.has-image \{ min-height: clamp\(320px, 33vw, 520px\)/);
  assert.match(capture, /object-fit: contain/);
  assert.doesNotMatch(capture, /\.capture-image-frame, \.capture-image-frame img/);
});

test("recovery, Profile, Auth, onboarding, UV and admin share the page frame", () => {
  assert.match(shared, /\.workspace-panel.quality-panel \{ width: 100%; max-width: none/);
  assert.match(shared, /\.quality-workspace \.workspace-topbar \{ width: 100%/);
  assert.match(read("../src/app/quality-rejected/page.tsx"), /className="quality-workspace"/);
  assert.match(shared, /\.profile-panel \{\s*width: 100%;\s*max-width: none/);
  assert.match(shared, /\.auth-card > \* \{ width: 100%; max-width: 70ch/);
  assert.match(shared, /\.auth-page,\s*main.onboarding-page,\s*main.admin-products-page \{\s*width: min\(100%, var\(--page-frame-max\)\)/);
  assert.match(read("../src/app/profile/profile.css"), /workspace-topbar \{\s*width: 100%;\s*max-width: none/);
  assert.match(read("../src/components/uv/uv-map.css"), /\.uv-map-page \{ width: min\(100%, var\(--page-frame-max\)\)/);
  assert.match(read("../src/app/admin/products/products.css"), /\.admin-products-container \{ width: 100%; max-width: none/);
});
