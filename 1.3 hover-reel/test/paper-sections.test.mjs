import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(
  path.join(here, "..", "capture-extension", "content", "paper-sections.js"),
  "utf8",
);
const sandbox = { globalThis: {} };
vm.runInNewContext(src, sandbox);
const api = sandbox.globalThis.PaperCaptureSections;

const CENSUS = [
  { id: "01", slug: "hero-area", top: 0, h: 770 },
  { id: "02", slug: "stats", top: 770, h: 400 },
  { id: "03", slug: "expenses", top: 1170, h: 600 },
  { id: "04", slug: "brands", top: 1770, h: 280 },
];

test("compact nav chrome is 00; a tall Framer header is a content band", () => {
  assert.equal(api.isCompactChrome({ tagName: "NAV", getAttribute: () => "" }), true);
  assert.equal(
    api.isCompactChrome({
      tagName: "HEADER",
      getAttribute: () => "banner",
      getBoundingClientRect: () => ({ height: 72, top: 0 }),
    }),
    true,
  );
  assert.equal(
    api.isCompactChrome({
      tagName: "HEADER",
      getAttribute: () => "",
      getBoundingClientRect: () => ({ height: 770, top: 0 }),
    }),
    false,
  );
});

test("take Y maps to Paper 01 · hero, not a 00 offset", () => {
  assert.equal(api.matchCensus(-20, CENSUS).id, "00");
  assert.equal(api.matchCensus(120, CENSUS).id, "01");
  assert.equal(api.matchCensus(900, CENSUS).id, "02");
  assert.equal(api.matchCensus(1400, CENSUS).id, "03");
  assert.equal(api.matchCensus(1800, CENSUS).label, "brands");
});

test("contentBands skips only the compact bar so hero stays 01", () => {
  const nav = { tagName: "NAV", getAttribute: () => "", getBoundingClientRect: () => ({ height: 64, top: 0 }) };
  const hero = { tagName: "HEADER", getAttribute: () => "", getBoundingClientRect: () => ({ height: 770, top: 64 }) };
  const { chrome, bands } = api.contentBands([nav, hero]);
  assert.equal(chrome.length, 1);
  assert.equal(bands[0], hero);
  const take = api.assignFromBands({ parent: hero, getBoundingClientRect: () => ({ top: 200, height: 40 }) }, bands, {
    getTop: (node) => (node === hero ? 64 : 200),
  });
  assert.equal(take.id, "01");
});
