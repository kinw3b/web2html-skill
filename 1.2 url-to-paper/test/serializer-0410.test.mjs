// Paper Snapshot 0.4.10 serializer deltas: shadow-rooted style probe,
// root-only text-align reset, form-control sizes, empty colspan padding,
// and Elementor .elementor-invisible lifted during capture.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import { launchOptions } from "../scripts/chrome-path.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const serializerSrc = readFileSync(join(__dir, "../scripts/serializer.js"), "utf8");

const FIXTURE = `<!doctype html><html><head><style>
  /* Page CSS that used to leak into the <link> probe. */
  link { padding-left: 37px !important; }
  #root link { letter-spacing: 9px; }
</style></head><body style="margin:0">
<section id="root" style="width:600px;text-align:center">
  <div id="probe-victim">Plain</div>
  <p id="centered">Inherits center</p>
  <input id="field" type="text" size="20">
  <textarea id="area" rows="3" cols="20"></textarea>
  <select id="pick"><option>One</option></select>
  <table><tr><td id="span3" colspan="3"></td></tr><tr><td>a</td><td>b</td><td>c</td></tr>
    <tr><td id="span2full" colspan="2">full</td><td>z</td></tr></table>
  <div id="ewidget" class="elementor-invisible">Elementor widget</div>
</section>
</body></html>`;

async function capture() {
  const browser = await chromium.launch(launchOptions({ visible: false }));
  try {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    await page.setContent(FIXTURE, { waitUntil: "load" });
    await page.addStyleTag({ content: ".elementor-invisible{visibility:hidden}" });
    const result = await page.evaluate(`(async () => {
      ${serializerSrc}
      return await fe("#root");
    })()`);
    const after = await page.evaluate(() => ({
      elementorRestored: document.querySelector("#ewidget").classList.contains("elementor-invisible"),
      leftovers: document.querySelectorAll("x-paper-style-reference").length,
    }));
    return { result, after };
  } finally {
    await browser.close();
  }
}

const { result, after } = await capture();
const html = String(result.html || "");

test("capture succeeded", () => {
  assert.equal(result.status, "success");
});

test("page CSS targeting <link> does not leak into emitted styles", () => {
  // With the old light-DOM probe, padding-left:37px would be in the baseline
  // and real padding-left:0 would be emitted as a diff.
  assert.doesNotMatch(html, /padding-left:\s*0px/);
  assert.doesNotMatch(html, /letter-spacing/);
});

test("probe host is removed after capture", () => {
  assert.equal(after.leftovers, 0);
});

test("text-align is not repeated on descendants that inherit it", () => {
  const centered = (html.match(/text-align:\s*center/g) || []).length;
  assert.equal(centered, 1, html.slice(0, 400));
});

test("input/textarea/select pin their used width/height when sized by default", () => {
  // No author width/height: the computed-style diff alone emits nothing,
  // so 0.4.10 copies the used px size in.
  for (const tag of ["input", "textarea", "select"]) {
    const m = html.match(new RegExp(`<${tag}[^>]*style="([^"]*)"`));
    assert.ok(m, `${tag} emitted with style`);
    assert.match(m[1], /(^|;\s*)width:\s*[\d.]+px/, `${tag} width`);
    assert.match(m[1], /(^|;\s*)height:\s*[\d.]+px/, `${tag} height`);
  }
});

test("empty colspan>1 cell pads its row with table-cell siblings", () => {
  const pads = html.match(/<div paper-snapshot-original-tag="TD" style="display: table-cell;"><\/div>/g) || [];
  assert.equal(pads.length, 2, "colspan=3 empty cell gets 2 pads; filled colspan=2 gets none");
});

test("elementor-invisible is lifted for capture and restored after", () => {
  assert.match(html, /Elementor widget/);
  assert.doesNotMatch(html, /visibility:\s*hidden/);
  assert.equal(after.elementorRestored, true);
});
