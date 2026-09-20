// 1.2.b — live DOM semantic multiset vs layer-ids.json.
//
// Tags Scan is not the census. Optional invisible QA only — not a 1.2 gate.
// h1–h6 / p / a / img / button. 768 / 390 do not run it.
//
//   node scripts/layer-ids-census.mjs --ids capture/home-desktop/layer-ids.json \
//     --live capture/home-desktop/layer-ids-live.json \
//     --out capture/home-desktop/layer-ids-census.json

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const SEMANTIC_TAGS = new Set([
  "h1", "h2", "h3", "h4", "h5", "h6", "p", "a", "img", "button",
]);

export function censusKey(tag, text) {
  const t = String(tag || "").toLowerCase();
  let body = String(text || "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u2018\u2019]/g, "'");
  if (t === "img") return "img|img";
  return `${t}|${body.slice(0, 48)}`;
}

export function sidecarKeys(ids = {}) {
  const keys = [];
  for (const row of Object.values(ids)) {
    const tag = String(row?.tag || "").toLowerCase();
    if (!SEMANTIC_TAGS.has(tag)) continue;
    let text = row.text || row.alt || "";
    // Serializer stores textContent. Empty social/icon <a>s have no copy;
    // live + sidecar both count them as "<A>" so the multiset joins.
    if (tag === "a" && !String(text).trim()) text = "<A>";
    keys.push(censusKey(tag, text));
  }
  return keys;
}

function counts(keys) {
  const map = new Map();
  for (const key of keys) map.set(key, (map.get(key) || 0) + 1);
  return map;
}

export function compareCensus(liveKeys = [], sideKeys = []) {
  const live = counts(liveKeys);
  const side = counts(sideKeys);
  const missing = [];
  for (const [key, n] of live) {
    const have = side.get(key) || 0;
    if (have < n) missing.push({ key, live: n, sidecar: have });
  }
  return {
    ok: missing.length === 0,
    missing,
    live: liveKeys.length,
    sidecar: sideKeys.length,
  };
}

/** Playwright `page.evaluate` body — visible semantic nodes only. */
export function collectLiveSemanticRows() {
  const skip = (el) => {
    if (el.closest("x-paper-prepesticide, x-paper-overlay, [class*='x-paper-']")) return true;
    const href = el.getAttribute?.("href") || "";
    if (/^https?:\/\/(www\.)?framer\.com(\/|$)/i.test(href)) return true;
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return true;
    if (Number(s.opacity || 1) === 0) return true;
    const r = el.getBoundingClientRect();
    return r.width < 1 || r.height < 1;
  };
  const rows = [];
  for (const el of document.querySelectorAll("h1,h2,h3,h4,h5,h6,p,a,img,button")) {
    if (skip(el)) continue;
    const tag = el.tagName.toLowerCase();
    // Same string as serializer.js (textContent, not innerText). Block
    // children inside a card <a> concatenate without a space; innerText
    // inserts one and the multiset misses a row that is already in the sidecar.
    let text = (el.textContent || "").replace(/\s+/g, " ").trim();
    if (tag === "img") text = "img";
    if (tag === "a" && !text) text = "<A>";
    rows.push({ tag, text });
  }
  return rows;
}

export function writeCensus(outFile, report) {
  const payload = {
    generatedFrom: "url-to-paper/layer-ids-census",
    writtenAt: new Date().toISOString(),
    ...report,
  };
  writeFileSync(outFile, JSON.stringify(payload, null, 2));
  return payload;
}

export async function censusLivePage(page, ids, outFile) {
  const rows = await page.evaluate(collectLiveSemanticRows);
  const liveKeys = (rows || []).map((row) => censusKey(row.tag, row.text));
  const compared = compareCensus(liveKeys, sidecarKeys(ids));
  return writeCensus(outFile, compared);
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const argv = process.argv.slice(2);
  const arg = (name) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 ? argv[i + 1] : "";
  };
  const idsPath = resolve(arg("ids") || "capture/home-desktop/layer-ids.json");
  const livePath = arg("live") ? resolve(arg("live")) : "";
  const outPath = resolve(arg("out") || `${dirname(idsPath)}/layer-ids-census.json`);
  const ids = JSON.parse(readFileSync(idsPath, "utf8")).ids || {};
  const live = livePath ? JSON.parse(readFileSync(livePath, "utf8")) : [];
  const liveKeys = Array.isArray(live) ? live : live.keys || [];
  const report = writeCensus(outPath, compareCensus(liveKeys, sidecarKeys(ids)));
  console.log(`layer-ids-census: ${report.ok ? "ok" : "FAIL"} · live ${report.live} · sidecar ${report.sidecar} · missing ${report.missing.length}`);
  if (!report.ok) process.exit(2);
}
