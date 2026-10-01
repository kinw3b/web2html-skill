// Paper Snapshot 0.4.4 serializer deltas: valid-nesting scope, percentage
// <img> pinning, and appearance:none checkbox/radio boxes.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import { launchOptions } from "../scripts/chrome-path.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const serializerSrc = readFileSync(join(__dir, "../scripts/serializer.js"), "utf8");
const GIF = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

const FIXTURE = `<!doctype html><html><body style="margin:0">
<section id="root" style="width:600px">
  <p id="para" class="dot">Intro</p>
  <a id="outer" href="/a" style="display:block">Outer</a>
  <button id="btn">Btn</button>
  <div id="shrink" style="display:inline-block"><img src="${GIF}" style="width:50%;height:20px"></div>
  <div id="fixed" style="width:300px"><img src="${GIF}" style="width:50%;height:20px"></div>
  <label><input class="cb" type="checkbox" style="appearance:none;width:16px;height:16px"> check</label>
</section>
<style>.dot::before{content:"•"} .cb::before{content:"✓";display:block}</style>
</body></html>`;

async function capture() {
  const browser = await chromium.launch(launchOptions({ visible: false }));
  try {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    await page.setContent(FIXTURE, { waitUntil: "load" });
    // The HTML parser would repair these; script-built DOM keeps them.
    await page.evaluate(() => {
      const mk = (tag, text) => Object.assign(document.createElement(tag), { textContent: text });
      document.querySelector("#para").append(mk("div", "div in p"), mk("h3", "h3 in p"));
      document.querySelector("#outer").append(Object.assign(mk("a", "nested a"), { href: "/b" }));
      const inner = mk("p", "p in button");
      inner.append(mk("div", "div in p in button"));
      document.querySelector("#btn").append(mk("button", "nested button"), inner);
    });
    return await page.evaluate(`(async () => {
      ${serializerSrc}
      return await fe("#root");
    })()`);
  } finally {
    await browser.close();
  }
}

const result = await capture();
const html = String(result.html || "").replace(/ style="[^"]*"/g, "");

test("capture succeeded", () => {
  assert.equal(result.status, "success");
});

test("block tags inside <p> emit as <span> with the original tag", () => {
  assert.match(html, /<span paper-snapshot-original-tag="DIV">div in p<\/span>/);
  assert.match(html, /<span paper-snapshot-original-tag="H3">h3 in p<\/span>/);
});

test("::before inside a <p> is wrapped in <span>", () => {
  assert.match(html, /<p[^>]*><span>•<\/span>Intro/);
});

test("nested <a> and <button> emit as <span>", () => {
  assert.match(html, /<span paper-snapshot-original-tag="A">nested a<\/span>/);
  assert.match(html, /<span paper-snapshot-original-tag="BUTTON">nested button<\/span>/);
});

test("<button> resets the paragraph scope, a <p> inside it starts a new one", () => {
  assert.match(html, /<p[^>]*>p in button<span paper-snapshot-original-tag="DIV">div in p in button<\/span><\/p>/);
});

test("percentage <img> width is pinned only when the parent shrink-wraps it", () => {
  const widths = [...String(result.html).matchAll(/<img [^>]*style="([^"]*)"/g)]
    .map((m) => (m[1].match(/(?:^|; )width: ([^;]+)/) || [])[1]);
  assert.equal(widths.length, 2);
  assert.match(widths[0], /px$/, `shrink-wrapped img should be px, got ${widths[0]}`);
  assert.equal(widths[1], "50%");
});

test("appearance:none checkbox with a pseudo tick emits as <div>", () => {
  assert.match(html, /<div [^>]*type="checkbox"[^>]*paper-snapshot-original-tag="INPUT"><div>✓<\/div><\/div>/);
});
