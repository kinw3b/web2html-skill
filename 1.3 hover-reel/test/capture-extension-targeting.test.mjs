import assert from "node:assert/strict";
import test from "node:test";

await import("../capture-extension/content/targeting.js");

const { targetFor, fullNavbarFor } = globalThis.PaperCaptureTargeting;

function element(name, parent = null, closest = {}) {
  return {
    name,
    parentElement: parent,
    closest(selector) { return closest[selector] || null; },
  };
}

test("manual Navbar targeting starts on the exact hovered DOM node", () => {
  const oversizedHeader = element("oversized-header");
  const section = element("content-section", oversizedHeader);
  const heading = element("heading", section, {
    "nav, header, [role='navigation']": oversizedHeader,
  });

  assert.equal(targetFor(heading, "nav", "navbar", 0), heading);
});

test("manual parent traversal is explicit and reversible", () => {
  const header = element("header");
  const nav = element("nav", header);
  const link = element("link", nav);

  assert.equal(targetFor(link, "nav", "navbar", 1), nav);
  assert.equal(targetFor(link, "nav", "navbar", 2), header);
  assert.equal(targetFor(link, "nav", "navbar", 0), link);
});

test("Auto/full-navbar selection prefers a compact nav wrapper over a page header", () => {
  const nav = element("nav");
  const link = element("link", nav, {
    "nav, [role='navigation']": nav,
    "nav, header, [role='navigation']": element("page-header"),
  });

  assert.equal(fullNavbarFor(link), nav);
});
