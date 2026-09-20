import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { buildPageUrl, parseHref } from "../capture-extension/shared/session-url.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "capture-extension");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

function extensionId(key) {
  const digest = crypto.createHash("sha256").update(Buffer.from(key, "base64")).digest("hex").slice(0, 32);
  return [...digest].map((nibble) => String.fromCharCode(97 + Number.parseInt(nibble, 16))).join("");
}

test("capture extension is a side-panel MV3 package with a stable native-host identity", () => {
  const manifest = JSON.parse(read("manifest.json"));
  assert.equal(manifest.manifest_version, 3);
  assert.equal(manifest.name, "Paper Capture Tool");
  assert.equal(manifest.version, "1.2.32");
  assert.ok(manifest.content_scripts?.some((entry) => entry.js.includes("content/session-from-url.js")));
  assert.equal(manifest.side_panel.default_path, "sidepanel/panel.html");
  for (const permission of ["debugger", "nativeMessaging", "sidePanel", "scripting", "storage", "windows"]) {
    assert.ok(manifest.permissions.includes(permission), `missing ${permission}`);
  }
  assert.equal(extensionId(manifest.key), "ecicfkapebfbpdgfaiadgfcghkpgmbem");
});

test("side panel keeps navbar first, exposes four modes, and gates Done to Single", () => {
  const panel = read("sidepanel/panel.js");
  const css = read("sidepanel/panel.css");
  const html = read("sidepanel/panel.html");
  const order = ["Navbar + Dropdowns", 'title: "Hover"', 'title: "Multi-state"', 'title: "Single"'];
  let cursor = -1;
  for (const marker of order) {
    const next = panel.indexOf(marker);
    assert.ok(next > cursor, `${marker} is out of order`);
    cursor = next;
  }
  assert.doesNotMatch(panel, /title: "Tags"/);
  assert.match(panel, /item\.id === "nav" && !navbarComplete/);
  assert.match(panel, /item\.id !== "single"/);
  assert.match(panel, /✓ added to Paper/);
  assert.match(panel, /paperNodeId/);
  assert.match(panel, /applySession/);
  assert.match(panel, /maybeAutoStart/);
  assert.match(panel, /HC_SET_PAPER_SECTIONS/);
  assert.match(panel, /captureAutostart/);
  assert.match(panel, /ping\?\.session/);
  assert.match(panel, /ui\.setupError\.textContent = error\.message/);
  assert.match(css, /\.stage-dot\.complete\s*\{[^}]*box-shadow:\s*inset 0 -2px var\(--green\)/s);
  assert.doesNotMatch(css, /\.setup, \.workspace, \.complete/);
  assert.doesNotMatch(css, /\n\.complete\s*\{/);
  assert.match(html, /data-tooltip="Scans your entire page on all steps\."/);
  assert.match(html, /Capture is ready for review/);
  assert.match(html, /class="agent-cue"/);
  assert.match(html, /Ready for your Continue/);
  assert.match(html, /human-hover-done\.json/);
  assert.match(panel, /ui\.complete\.hidden = false/);
  assert.doesNotMatch(panel, /HC_CLOSE_PANEL/);
  assert.match(css, /\.auto-toggle:hover::after/);
  assert.match(css, /\.auto-toggle:focus-within::after/);
  assert.match(css, /\.record-card\s*\{[^}]*flex-direction:\s*column/s);
  assert.match(css, /\.record-button\s*\{[^}]*width:\s*100%/s);
});

test("native bridge creates only Capture Tool review frames and writes human-hover-done.json", () => {
  const host = read("bridge/host.mjs");
  assert.match(host, /\["Navigation", "Buttons", "Components"\]/);
  assert.match(host, /width: "fit-content"/);
  assert.doesNotMatch(host, /width: "1400px"/);
  assert.doesNotMatch(host, /ensureBoard\("Design Library"/);
  assert.match(host, /source-site", "components"/);
  assert.match(host, /human-hover-done\.json/);
  assert.doesNotMatch(host, /agent-pings/);
  assert.doesNotMatch(host, /1\.3-continue\.json/);
  assert.match(host, /paperNodeId/);
  assert.match(host, /readActiveSession/);
  assert.match(host, /loadPaperSections/);
  assert.match(host, /paperSections/);
  assert.match(host, /active-session\.json/);
});

test("native host installer is pinned to the manifest-derived extension ID", () => {
  const installer = read("install-native-host.command");
  assert.match(installer, /HOST_NAME="com\.kreativepro\.paper_capture"/);
  assert.match(installer, /EXTENSION_ID="ecicfkapebfbpdgfaiadgfcghkpgmbem"/);
  assert.match(installer, /allowed_origins/);
  assert.match(installer, /bridge\/semantics\.mjs/);
  assert.match(installer, /SEMANTICS_COPY/);
});

test("page-local R shortcut can arm hover-open dropdown state two without leaving the menu", () => {
  const content = read("content/capture.js");
  const panel = read("sidepanel/panel.js");
  assert.match(content, /event\.code !== "KeyR"/);
  assert.match(content, /HC_RECORDING_CHANGED/);
  assert.match(panel, /Open or change it, then capture state 2/);
});

test("service worker injects exact-DOM targeting before the capture controller", () => {
  const worker = read("service-worker.js");
  assert.match(worker, /files: \["content\/targeting\.js", "content\/nav-breakpoints\.js", "content\/component-names\.js", "content\/paper-sections\.js", "content\/tag-overlays\.js", "content\/capture\.js"\]/);
});

test("exact component serialization has no synthetic context frame and preserves outlines and SVG symbols", () => {
  const content = read("content/capture.js");
  assert.doesNotMatch(content, /layer-name=["']capture-context["']/);
  for (const property of ["outline-width", "outline-style", "outline-color", "outline-offset"]) {
    assert.match(content, new RegExp(`(?:"|')${property}(?:"|')`), `missing ${property}`);
  }
  assert.match(content, /function resolveSvgUse\(/);
  assert.match(content, /getElementById\(/);
  for (const attribute of ["stroke-linecap", "stroke-linejoin", "fill-rule", "clip-rule"]) {
    assert.match(content, new RegExp(`(?:"|')${attribute}(?:"|')`), `missing ${attribute}`);
  }
});

test("Tags Scan is gone; Done is on Single; Nav/Hover keep the 1600 lock", () => {
  const panel = read("sidepanel/panel.js");
  const content = read("content/capture.js");
  const worker = read("service-worker.js");
  assert.doesNotMatch(panel, /id: "tags"/);
  assert.doesNotMatch(panel, /"Scan"/);
  assert.doesNotMatch(panel, /HC_AUTO_TAGS/);
  assert.doesNotMatch(panel, /APPLY_SEMANTICS/);
  assert.doesNotMatch(content, /HC_AUTO_TAGS/);
  assert.doesNotMatch(content, /HC_SHOW_TAG_OUTLINES/);
  assert.match(panel, /function pageMessage\(/);
  assert.match(panel, /Receiving end does not exist/);
  assert.match(panel, /function ensureInjected\(/);
  assert.match(panel, /item\.id === "single"/);
  assert.match(worker, /HC_LOCK_DESKTOP_VIEWPORT/);
  assert.match(worker, /Emulation\.setDeviceMetricsOverride/);
  assert.match(panel, /lockDesktopViewport/);
  assert.match(panel, /1600/);
});

test("stamped page session opens the Capture Tool side panel", () => {
  const worker = read("service-worker.js");
  assert.match(worker, /HC_SESSION_FROM_PAGE/);
  assert.match(worker, /chrome\.sidePanel\.open/);
  assert.match(worker, /captureAutostart:\s*true/);
});

test("source-site query params carry this run's Paper file into the side panel", () => {
  assert.match(read("content/session-from-url.js"), /captureAutostart/);
  assert.match(read("service-worker.js"), /HC_SESSION_FROM_PAGE/);
  const session = {
    paperFileId: "01M0GPEFVQ1A4G5E078T82CNDW",
    projectRoot: path.join(path.sep, "tmp", "web2html-fixture", "kp-frilly"),
  };
  const page = buildPageUrl("https://kp-frilly.framer.website/", session);
  assert.match(page, /^https:\/\/kp-frilly\.framer\.website\//);
  assert.equal(parseHref(page).paperFileId, session.paperFileId);
  assert.equal(parseHref(page).projectRoot, session.projectRoot);
  assert.equal(
    parseHref(`https://kp-frilly.framer.website/#paperFileId=${session.paperFileId}&projectRoot=${encodeURIComponent(session.projectRoot)}`).projectRoot,
    session.projectRoot,
  );
});
