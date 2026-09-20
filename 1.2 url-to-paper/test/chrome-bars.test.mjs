import test from "node:test";
import assert from "node:assert/strict";
import {
  combineChromeHtml,
  desktopLanderHasNavbar,
  isCompactBar,
  isPhoneLeafText,
  nodeLooksLikeNavbar,
} from "../scripts/chrome-bars.mjs";

test("compact bars reject the page shell", () => {
  assert.equal(isCompactBar({
    width: 1600, height: 45, top: 0, viewportWidth: 1600, viewportHeight: 900,
  }), true);
  assert.equal(isCompactBar({
    width: 1600, height: 104, top: 45, viewportWidth: 1600, viewportHeight: 900,
  }), true);
  assert.equal(isCompactBar({
    width: 1600, height: 6838, top: 0, viewportWidth: 1600, viewportHeight: 900,
  }), false);
});

test("phone leaf is a short tel, not page copy", () => {
  assert.equal(isPhoneLeafText("(310) 555-0142"), true);
  assert.equal(isPhoneLeafText("Book a table tonight at KP Cuisine"), false);
});

test("combine stacks header + nav in relative flow", () => {
  const header = '<div style="position: fixed; top: 0px; width: 1600px">top</div>';
  const nav = '<div style="position: sticky; top: 45px; width: 1600px">menu</div>';
  const html = combineChromeHtml(header, nav);
  assert.match(html, /layer-name="Navbar"/);
  assert.match(html, /position: relative/);
  assert.doesNotMatch(html, /position:\s*fixed/i);
  assert.doesNotMatch(html, /position:\s*sticky/i);
  assert.match(html, /top/);
  assert.match(html, /menu/);
});

test("desktop lander navbar is compact chrome, not the hero", () => {
  assert.equal(nodeLooksLikeNavbar({ name: "01 · hero-area", height: 900 }), false);
  assert.equal(nodeLooksLikeNavbar({ name: "00-header" }), true);
  assert.equal(nodeLooksLikeNavbar({ name: "pc-0a-0" }), true);
  assert.equal(nodeLooksLikeNavbar({ name: "Navbar" }), true);
  assert.equal(desktopLanderHasNavbar([
    { name: "01 · hero-area", height: 820 },
    { name: "02 · menu", height: 640 },
  ]), false);
  assert.equal(desktopLanderHasNavbar([
    { name: "00 · header", height: 48 },
    { name: "01 · hero-area", height: 820 },
  ]), true);
});

test("combine with one fragment still rewrites to relative", () => {
  const html = combineChromeHtml("", '<nav style="position: fixed; left: 0px">bar</nav>');
  assert.match(html, /position: relative/);
  assert.match(html, /<nav/);
});
