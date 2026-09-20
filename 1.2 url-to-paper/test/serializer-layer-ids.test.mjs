// Lean 1.2: Paper layer-name is the scrape name (or omitted).
// Never stamp pc-<section>-<child-index-path> onto imported nodes.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import { launchOptions } from "../scripts/chrome-path.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const serializerSrc = readFileSync(join(__dir, "../scripts/serializer.js"), "utf8");

const PC_PATH = /^pc-[a-z0-9]+(?:-[0-9.ab~]+)*$/i;

const FIXTURE = `<!doctype html><html><body style="margin:0">
<section id="root" style="display:flex;flex-direction:column;width:600px">
  <h1 class="framer-text framer-styles-preset-abc123 extra" data-framer-name="Headline" role="heading" style="font-size:20px">Headline</h1>
  <div style="display:none">dropped, but still consumes its index</div>
  <p style="font-size:14px">Body copy</p>
  <a href="/pricing" style="display:flex">Get Started Now</a>
  <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
       alt="Logo" style="width:40px;height:40px">
  <div style="display:contents"><span style="font-size:12px">unwrapped parent</span></div>
  <div class="pseudo" style="width:50px;height:50px;background:#eee"></div>
  <svg width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#0a0"></circle></svg>
  <div id="icon-host" style="width:27px;height:27px"><svg id="sprite-icon" width="27" height="27"><use href="https://site.test/#icon-plus"></use></svg></div>
  <svg style="position:absolute;width:0;height:0;overflow:hidden"><symbol id="icon-plus" viewBox="0 0 24 24" preserveAspectRatio="xMidYMid meet"><path d="M12 4v16M4 12h16" fill="currentColor"></path></symbol></svg>
</section>
<style>.pseudo::before{content:"before";display:block}.pseudo::after{content:"after";display:block}</style>
</body></html>`;

function layerNames(html) {
  return [...String(html || "").matchAll(/\blayer-name="([^"]+)"/g)].map((m) => m[1]);
}

async function capture(idPrefix, selector = "#root") {
  const browser = await chromium.launch(launchOptions({ visible: false }));
  try {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    await page.setContent(FIXTURE, { waitUntil: "load" });
    return await page.evaluate(`(async () => {
      ${serializerSrc}
      return await fe(${JSON.stringify(selector)}, ${JSON.stringify({ idPrefix })});
    })()`);
  } finally {
    await browser.close();
  }
}

const result = await capture("01-");
const stamps = layerNames(result.html);

test("capture succeeded", () => {
  assert.equal(result.status, "success");
  assert.ok(result.html.length > 0);
});

test("Paper layer-name is never a pc-path tree", () => {
  for (const name of stamps) {
    assert.equal(
      PC_PATH.test(name),
      false,
      `layer-name="${name}" is a generated path id`,
    );
  }
  assert.equal(
    [...result.html.matchAll(/\blayer-name="(pc-[^"]+)"/g)].length,
    0,
  );
});

test("scrape data-framer-name survives as layer-name", () => {
  assert.ok(
    stamps.includes("Headline"),
    `expected Headline from data-framer-name, got: ${stamps.join(", ")}`,
  );
});

test("unnamed nodes do not invent a path id", () => {
  const p = result.ids.find((row) => row.tag === "p");
  const img = result.ids.find((row) => row.tag === "img");
  const a = result.ids.find((row) => row.tag === "a");
  assert.ok(p && img && a, "optional sidecar should still describe source tags");
  assert.ok(!result.html.includes(`layer-name="${p.pcId}"`));
  assert.ok(!result.html.includes(`layer-name="${img.pcId}"`));
  assert.ok(!result.html.includes(`layer-name="${a.pcId}"`));
});

test("<a> keeps its href and text", () => {
  const a = result.ids.find((row) => row.tag === "a");
  assert.equal(a.href, "/pricing");
  assert.equal(a.text, "Get Started Now");
});

test("pseudo elements are not stamped with pc-path names", () => {
  const owner = result.ids.find((row) => row.path === "0.6");
  assert.ok(owner, "pseudo owner missing from optional sidecar");
  assert.ok(!stamps.includes(`${owner.pcId}b`));
  assert.ok(!stamps.includes(`${owner.pcId}a`));
});

test("svg interiors are not named with a path id", () => {
  assert.ok(!/<circle[^>]*layer-name/.test(result.html));
});

test("sprite SVG selections promote to their HTML host and inline a full URL fragment", async () => {
  const sprite = await capture("sprite-", "#sprite-icon");
  assert.equal(sprite.status, "success");
  assert.match(sprite.html, /<div\b/);
  assert.match(sprite.html, /width: 27px/);
  assert.match(sprite.html, /viewBox="0 0 24 24"/);
  assert.match(sprite.html, /<path[^>]*d="M12 4v16M4 12h16"/);
  assert.doesNotMatch(sprite.html, /<use\b/);
  assert.doesNotMatch(sprite.html, /fill="currentColor"/i);
});

test("sprite lookup walks open shadow roots", async () => {
  const browser = await chromium.launch(launchOptions({ visible: false }));
  try {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    await page.setContent(
      `<!doctype html><html><body><div id="icon-host" style="width:27px;height:27px"></div></body></html>`,
      { waitUntil: "load" },
    );
    await page.evaluate(() => {
      const host = document.getElementById("icon-host");
      const root = host.attachShadow({ mode: "open" });
      root.innerHTML = `<svg id="sprite-icon" width="27" height="27"><use href="https://site.test/#icon-plus"></use></svg>
        <svg style="position:absolute;width:0;height:0;overflow:hidden"><symbol id="icon-plus" viewBox="0 0 24 24"><path d="M1 1h10" fill="currentColor"></path></symbol></svg>`;
    });
    const sprite = await page.evaluate(`(async () => {
      ${serializerSrc}
      return await fe("#icon-host", { idPrefix: "sh-" });
    })()`);
    assert.equal(sprite.status, "success");
    assert.match(sprite.html, /viewBox="0 0 24 24"/);
    assert.match(sprite.html, /<path[^>]*d="M1 1h10"/);
    assert.doesNotMatch(sprite.html, /<use\b/);
  } finally {
    await browser.close();
  }
});

test("optional sidecar records live identity without writing it onto Paper", () => {
  const h1 = result.ids.find((row) => row.tag === "h1");
  assert.ok(h1, "no h1 in optional sidecar");
  assert.equal(h1.class, "framer-text framer-styles-preset-abc123 extra");
  assert.deepEqual(h1.classes, ["framer-text", "framer-styles-preset-abc123"]);
  assert.equal(h1.role, "heading");
  assert.equal(h1["data-framer-name"], "Headline");
  assert.ok(h1.pcId.startsWith("pc-"), "internal sidecar key may still be a pc-id");
  assert.ok(!stamps.includes(h1.pcId), "internal pc-id must not become layer-name");
});
