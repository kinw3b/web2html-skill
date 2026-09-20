import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = path.resolve(here, "..", "capture-extension");
const read = (file) => fs.readFileSync(path.join(extensionRoot, file), "utf8");

await import("../capture-extension/content/nav-breakpoints.js");

const { breakpointSpecs, fingerprintNav, pickNavCandidate } = globalThis.PaperCaptureNavBreakpoints;

test("Navigation background capture is limited to tablet and mobile widths", () => {
  assert.deepEqual(breakpointSpecs(), [
    { name: "tablet", width: 768, height: 1024 },
    { name: "mobile", width: 390, height: 844 },
  ]);
});

test("desktop Navbar fingerprint relocates its responsive navigation wrapper", () => {
  const desktop = fingerprintNav({
    tag: "header",
    framerName: "Navigation",
    role: "banner",
    classes: ["framer-nav"],
    text: "Lawyer Home About Contact",
  });
  const picked = pickNavCandidate([
    {
      id: "hero-shell", tag: "section", framerName: "Hero-section",
      classes: ["framer-hero"], text: "High quality legal services",
      rect: { top: 0, width: 390, height: 844 }, viewport: { width: 390, height: 844 },
    },
    {
      id: "promo", tag: "div", framerName: "Announcement",
      classes: ["promo"], text: "Browse templates",
      rect: { top: 0, width: 390, height: 44 }, viewport: { width: 390, height: 844 },
      interactiveCount: 1, navLinkCount: 1,
    },
    {
      id: "mobile-nav", tag: "header", framerName: "Navigation", role: "banner",
      classes: ["framer-nav"], text: "Lawyer Menu",
      rect: { top: 44, width: 390, height: 76 }, viewport: { width: 390, height: 844 },
      hasLogo: true, hasMenuButton: true, interactiveCount: 2, navLinkCount: 0,
    },
  ], desktop);

  assert.equal(picked.id, "mobile-nav");
});

test("Auto rejects an announcement link and selects the smallest parent with Navbar evidence", () => {
  const picked = pickNavCandidate([
    {
      id: "announcement", tag: "div", text: "Browse 15 templates",
      rect: { top: 0, width: 1600, height: 56 }, viewport: { width: 1600, height: 1000 },
      navLinkCount: 1, interactiveCount: 1,
    },
    {
      id: "navbar", tag: "nav", role: "navigation", text: "Lawyer Home About Contact Free Consultation",
      rect: { top: 56, width: 1600, height: 92 }, viewport: { width: 1600, height: 1000 },
      hasLogo: true, navLinkCount: 5, hasCta: true, hasDropdown: false, interactiveCount: 6,
    },
    {
      id: "hero-shell", tag: "section", text: "Lawyer Home High quality legal services",
      rect: { top: 0, width: 1600, height: 780 }, viewport: { width: 1600, height: 1000 },
      hasLogo: true, navLinkCount: 5, hasCta: true, interactiveCount: 8,
    },
  ], {});
  assert.equal(picked.id, "navbar");
});

test("Auto accepts a compact Framer bar without a named logo if it has menu links plus a CTA", () => {
  const picked = pickNavCandidate([
    {
      id: "frilly-nav", tag: "div", text: "Frilly All Pages Pricing Integration Sign In Get Started Now",
      rect: { top: 0, width: 1440, height: 72 }, viewport: { width: 1440, height: 900 },
      hasLogo: false, navLinkCount: 4, hasCta: true, hasDropdown: true, interactiveCount: 6,
    },
    {
      id: "hero-shell", tag: "header", text: "Create your workspace",
      rect: { top: 0, width: 1440, height: 820 }, viewport: { width: 1440, height: 900 },
      hasLogo: false, navLinkCount: 4, hasCta: true, interactiveCount: 8,
    },
  ], {});
  assert.equal(picked.id, "frilly-nav");
});

test("Auto still rejects an announcement strip with one link", () => {
  const picked = pickNavCandidate([
    {
      id: "announcement", tag: "div", text: "Browse 15 templates",
      rect: { top: 0, width: 1600, height: 40 }, viewport: { width: 1600, height: 1000 },
      hasLogo: false, navLinkCount: 1, hasCta: false, interactiveCount: 1,
    },
  ], {});
  assert.equal(picked, null);
});

test("responsive rematch uses the collapsed logo+menu bar when the desktop link row is gone", () => {
  const desktop = fingerprintNav({
    tag: "div",
    classes: ["framer-linkrow"],
    text: "All Pages Pricing Integration Sign In Get Started Now",
  });
  const picked = pickNavCandidate([
    {
      id: "mobile-nav", tag: "div", classes: ["framer-navbar"], text: "Frilly",
      rect: { top: 0, width: 390, height: 64 }, viewport: { width: 390, height: 844 },
      hasLogo: true, hasMenuButton: true, interactiveCount: 2, navLinkCount: 0,
    },
    {
      id: "hero", tag: "section", classes: ["framer-hero"], text: "Create your workspace",
      rect: { top: 0, width: 390, height: 760 }, viewport: { width: 390, height: 844 },
      hasLogo: true, hasMenuButton: true, interactiveCount: 4, navLinkCount: 0,
    },
  ], desktop);
  assert.equal(picked.id, "mobile-nav");
});

test("responsive rematching rejects a full-page hero shell", () => {
  const picked = pickNavCandidate([{
    id: "hero-shell", tag: "section", framerName: "Navigation Hero-section",
    rect: { top: 0, width: 768, height: 1024 }, viewport: { width: 768, height: 1024 },
  }], fingerprintNav({ tag: "header", framerName: "Navigation" }));

  assert.equal(picked, null);
});

test("Navbar captures carry a desktop fingerprint and background tabs can request a responsive serialize", () => {
  const content = read("content/capture.js");
  assert.match(content, /navFingerprint:.*fingerprintNav\(element\)/);
  assert.match(content, /HC_CAPTURE_NAV_BREAKPOINT/);
  assert.match(content, /pickNavCandidate/);
  assert.match(content, /function autoNavbarTarget\(/);
  assert.match(content, /function navbarCandidateRows\(/);
  assert.match(content, /function hasMenuControl\(/);
  assert.match(content, /data-framer-name='Phone'/);
  assert.match(content, /page \$\{innerWidth\}/);
});

test("Framer Phone and Tablet bars match at hamburger widths without desktop links", () => {
  const desktop = fingerprintNav({
    tag: "div",
    text: "All Pages Pricing Integration Sign In Get Started Now",
  });
  const picked = pickNavCandidate([
    {
      id: "phone", tag: "div", framerName: "Phone", text: "Get Started Now",
      rect: { top: 0, width: 335, height: 80 }, viewport: { width: 390, height: 844 },
      hasLogo: true, hasMenuButton: true, hasCta: true, navLinkCount: 0, interactiveCount: 3,
    },
    {
      id: "hero", tag: "header", framerName: "hero-area", text: "Create your workspace",
      rect: { top: 0, width: 375, height: 913 }, viewport: { width: 390, height: 844 },
      hasLogo: true, hasMenuButton: true, hasCta: true, navLinkCount: 0, interactiveCount: 4,
    },
  ], desktop);
  assert.equal(picked.id, "phone");
});

test("service worker captures 768 and 390 Navbar states in sized popup windows", () => {
  const worker = read("service-worker.js");
  assert.match(worker, /HC_CAPTURE_NAV_BREAKPOINTS/);
  assert.match(worker, /chrome\.windows\.create/);
  assert.match(worker, /lockViewport/);
  assert.match(worker, /mobile:\s*spec\.width <= 768/);
  assert.match(worker, /type:\s*"popup"/);
  assert.match(worker, /HC_CAPTURE_NAV_BREAKPOINT/);
  assert.match(worker, /content\/nav-breakpoints\.js/);
});

test("desktop Navbar receipt automatically commits tablet and mobile results to Paper", () => {
  const panel = read("sidepanel/panel.js");
  const html = read("sidepanel/panel.html");
  assert.match(panel, /HC_CAPTURE_NAV_BREAKPOINTS/);
  assert.match(panel, /capture\.navFingerprint/);
  assert.match(panel, /for \(const responsive of result\.captures/);
  assert.match(panel, /hasAllNavbarReceipts/);
  assert.doesNotMatch(html, /viewport-picker|breakpoint-switch/);
});

test("responsive Navbar does not report complete when a Paper commit fails", () => {
  const panel = read("sidepanel/panel.js");
  assert.match(panel, /paperFailures/);
  assert.match(panel, /responsiveCommits\.filter\(\(take\) => take\.status !== "success"\)/);
});

test("locked Continue explains Navbar progress until all three Paper receipts arrive", () => {
  const panel = read("sidepanel/panel.js");
  const html = read("sidepanel/panel.html");
  const css = read("sidepanel/panel.css");
  const worker = read("service-worker.js");
  assert.match(html, /id="navProgress"/);
  assert.match(html, /role="progressbar"/);
  assert.match(html, /Desktop/);
  assert.match(html, /Tablet/);
  assert.match(html, /Mobile/);
  assert.match(panel, /function renderNavbarProgress\(/);
  assert.match(panel, /Waiting for Paper/);
  assert.match(panel, /Confirming/);
  assert.match(panel, /HC_NAV_BREAKPOINT_PROGRESS/);
  assert.match(worker, /HC_NAV_BREAKPOINT_PROGRESS/);
  assert.match(css, /nav-progress/);
  assert.match(css, /@keyframes spin/);
});

test("Navbar progress stays hidden until the desktop Navbar has been manually captured", () => {
  const panel = read("sidepanel/panel.js");
  assert.match(panel, /const desktopStarted = takes\.some/);
  assert.match(panel, /stage\(\)\.id === "nav" && desktopStarted/);
});
