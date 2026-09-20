// Shared inventory + HTML report for Phase 1.55 missing-elements QA.
// Inspired by prior-run / prior-run / prior-run 2026-08-16 briefs.

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { placementVerdict } from "./source-shot-compare.mjs";

export const KINDS = {
  "empty-named-section": {
    severity: "P0",
    title: "Named section is empty",
    cause: "Delete-then-write or a failed insert left childCount 0. qa-paper empty-frame is only low.",
    auto: "restore-capture",
    fix: "Insert capture HTML into the empty frame. Do not delete_nodes first. Then height: min-content.",
  },
  "hollow-section": {
    severity: "P0",
    title: "Section much shorter than live",
    cause: "Paper height is under 40% of the pre-pesticide bbox.",
    auto: "restore-capture",
    fix: "Re-insert capture HTML and hug height: min-content.",
  },
  "missing-chrome": {
    severity: "P0",
    title: "Nav / announcement not imported",
    cause: "Detector starts at the first content section. Landmarks above stay on page.",
    auto: "prepend-nav",
    fix: "Prepend semantic nav HTML (logo + links + CTA) from landmarks or a dedicated nav capture. fullpage.png is visual reference only — never write a JPEG crop as the nav layer (Pitfall #91).",
  },
  "empty-iframe": {
    severity: "P0",
    title: "Sourceless iframe (maps / embed)",
    cause: "Framer Maps iframe has no src in the serialized DOM. Paper paints an empty rectangle.",
    auto: "iframe-bitmap",
    fix: "Replace the hole with a live/source-section bitmap. Never paper-asset:// or file://.",
  },
  "dead-svg-text": {
    severity: "P0",
    title: "SVG / path text collapsed to 0×0",
    cause: "Circular or path text imports as SVG Text with an empty bbox. Icon sibling still paints.",
    auto: "svg-text-image",
    fix: "Swap the dead text for the scrape PNG (or a self-contained SVG). Do not leave 0×0 text as source of truth.",
  },
  "hidden-variant-stack": {
    severity: "P1",
    title: "Hidden breakpoint variants inflate height",
    cause: "Serializer kept display:none / 1px-wide Framer variant stacks (~thousands of px).",
    auto: "collapse-variants",
    fix: "Drop or collapse width≈1 stacks. Re-assemble from capture if flattening in Paper is safer.",
  },
  "date-chrome": {
    severity: "P1",
    title: "Date field lost native chrome",
    cause: "input[type=date] UA picker is not DOM. Placeholder serializes as Enter Text.",
    auto: "date-chrome",
    fix: "Mock dd/mm/yyyy + calendar in Paper. Keep type=date in the later HTML rebuild.",
  },
  "source-empty": {
    severity: "P1",
    title: "Empty slot is live (do not invent)",
    cause: "Framer left a title+icon card with no body. Live pesticide shows the same hole.",
    auto: "leave",
    fix: "Keep empty. Optional min-height for alignment. Do not invent marketing copy.",
  },
  "blank-source-shot": {
    severity: "P0",
    title: "Source · home shots are blank",
    cause: "write_html used paper-asset:// or file://. Paper paints A/6 badges on white rectangles.",
    auto: "reseed-source",
    fix: "Re-seed Source · {page} with data:image rows (jpeg ≤70). Never skip an existing blank board.",
  },
  "shot-mismatch": {
    severity: "P0",
    title: "Source clip has content Paper does not",
    cause: "Section screenshot vs Paper screenshot: Paper is mostly white, the live clip is not.",
    auto: "restore-from-shot",
    fix: "Restore capture HTML if the frame is empty. If a hole remains (map, badge), write the source-section crop as data:image.",
  },
  "missing-hover-state": {
    severity: "P0",
    title: "Hoverable missing on Hover States",
    cause: "Buttons, text links, or footer links were captured (or live on the section) but FRAME Hover States has no matching take.",
    auto: "leave",
    fix: "Re-run hover-reel build-paper-states for buttons and footer. Park Default | Hover on the Source row, not a new A/6 frame.",
  },
  "displaced-section": {
    severity: "P0",
    title: "Named section is off the page stack",
    cause: "Restack / prepend-nav left a leftover relative top (e.g. 3252px). Isolated get_screenshot of the node still looks full. childCount > 0 is not a pass.",
    auto: "restack-tops",
    fix: "Clear top, position: relative, height: min-content on named NN · layers. Re-check monotonic y and gaps. Do not treat a per-section white-ratio match as page-order pass.",
  },
};

export function loadJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

export function findPrePesticide(captureDir) {
  const p = join(captureDir, "pre-pesticide.json");
  return existsSync(p) ? loadJson(p) : null;
}

export function listCaptureHtml(captureDir) {
  if (!existsSync(captureDir)) return [];
  return readdirSync(captureDir)
    .filter((f) => /^\d{2}-.+\.html$/.test(f))
    .sort()
    .map((f) => join(captureDir, f));
}

export function htmlInventory(html) {
  const img = (html.match(/<img\b/gi) || []).length;
  const iframe = [...html.matchAll(/<iframe\b([^>]*)>/gi)].map((m) => m[1] || "");
  const emptyIframe = iframe.some((attrs) => !/\bsrc\s*=\s*["'][^"']+["']/i.test(attrs));
  const dateEnter = /type=["']date["'][\s\S]{0,400}Enter Text/i.test(html)
    || /Enter Text[\s\S]{0,200}type=["']date["']/i.test(html);
  const headings = (html.match(/<h[1-6]\b/gi) || []).length;
  const anchors = (html.match(/<a\b/gi) || []).length;
  const svg = (html.match(/<svg\b/gi) || []).length;
  return { img, iframe: iframe.length, emptyIframe, dateEnter, headings, anchors, svg };
}

export function slugFromName(name) {
  const m = String(name || "").match(/^\s*(\d{2})\s*·\s*(.+)$/);
  if (m) return { index: m[1], slug: m[2].trim().toLowerCase().replace(/\s+/g, "-") };
  return { index: null, slug: String(name || "").toLowerCase() };
}

export function detectFromCapture({ captureDir, pre, paperSections = [], sourceDir } = {}) {
  const findings = [];
  const files = listCaptureHtml(captureDir);
  const liveSections = pre?.sections || [];
  const liveBySlug = new Map(liveSections.map((s) => [String(s.slug || s.framerName || "").toLowerCase(), s]));

  const paperBySlug = new Map();
  for (const s of paperSections) {
    const { slug } = slugFromName(s.name);
    paperBySlug.set(slug, s);
    if (/^\d{2}/.test(s.name) && (s.childCount || 0) === 0) {
      findings.push({
        kind: "empty-named-section",
        section: s.name,
        node: s.id || null,
        symptom: `Frame ${s.name} has 0 children`,
        evidence: s.detail || `${Math.round(s.w || 0)}×${Math.round(s.h || 0)}`,
        auto: "restore-capture",
      });
    }
    if (s.w != null && s.w <= 2 && (s.h || 0) > 800) {
      findings.push({
        kind: "hidden-variant-stack",
        section: s.name,
        node: s.id || null,
        symptom: `${Math.round(s.w)}×${Math.round(s.h)} hidden variant stack`,
        evidence: s.name,
        auto: "collapse-variants",
      });
    }
    if (s.deadSvgText) {
      findings.push({
        kind: "dead-svg-text",
        section: s.name,
        node: s.id || s.deadSvgText.id || null,
        symptom: `SVG text ${s.deadSvgText.detail || "0×0"}`,
        evidence: s.deadSvgText.detail,
        auto: "svg-text-image",
      });
    }
    const live = liveBySlug.get(slug) || liveSections.find((ls) => String(ls.framerName || "").toLowerCase() === slug);
    if (live?.bbox?.h && s.h != null && s.h < live.bbox.h * 0.4 && (s.childCount || 0) === 0) {
      findings.push({
        kind: "hollow-section",
        section: s.name,
        node: s.id || null,
        symptom: `Paper ${Math.round(s.h)}px vs live ${Math.round(live.bbox.h)}px`,
        evidence: live.slug || live.framerName,
        auto: "restore-capture",
      });
    }
  }

  const chromeLandmarks = (pre?.landmarks || []).filter((l) => {
    const y = l.bbox?.y ?? l.y ?? 9999;
    const first = liveSections[0]?.bbox?.y ?? 0;
    return y < first - 8;
  });
  const hasNav = paperSections.some((s) => /nav|header|chrome/i.test(s.name || ""));
  if (chromeLandmarks.length && !hasNav && liveSections[0] && !/nav|header/i.test(liveSections[0].slug || "")) {
    findings.push({
      kind: "missing-chrome",
      section: "page chrome",
      node: null,
      symptom: `${chromeLandmarks.length} landmark(s) above first section were not imported`,
      evidence: chromeLandmarks.map((l) => l.name || l.section || "landmark").join(", "),
      auto: "prepend-nav",
    });
  }

  for (const file of files) {
    const html = readFileSync(file, "utf8");
    const inv = htmlInventory(html);
    const base = basename(file, ".html");
    if (inv.emptyIframe) {
      findings.push({
        kind: "empty-iframe",
        section: base,
        node: null,
        symptom: "iframe has no src — Paper will paint an empty rectangle",
        evidence: file,
        captureHtml: file,
        auto: "iframe-bitmap",
      });
    }
    if (inv.dateEnter) {
      findings.push({
        kind: "date-chrome",
        section: base,
        node: null,
        symptom: "Date field serializes as Enter Text",
        evidence: file,
        captureHtml: file,
        auto: "date-chrome",
      });
    }
  }

  const shotsDir = sourceDir || join(captureDir, "source-sections");
  const sourcePngs = existsSync(shotsDir)
    ? readdirSync(shotsDir).filter((f) => /^\d{2}-.+\.png$/.test(f))
    : [];
  const sourceBoards = paperSections.filter((s) => s.blankSource || /^Source\s*·/.test(s.name || ""));
  const blankBoard = sourceBoards.find((s) => s.blankSource || (s.emptyShots || 0) > 0 || (s.childCount || 0) === 0);
  if (sourcePngs.length && (blankBoard || !sourceBoards.length && paperSections.length)) {
    findings.push({
      kind: "blank-source-shot",
      section: (blankBoard || sourceBoards[0] || {}).name || "Source · home",
      node: (blankBoard || sourceBoards[0] || {}).id || null,
      symptom: blankBoard
        ? `${blankBoard.emptyShots || 0} blank shot(s) on ${blankBoard.name}`
        : `source-sections has ${sourcePngs.length} PNG(s) but Source · home is missing or empty`,
      evidence: shotsDir,
      auto: "reseed-source",
      sourceDir: shotsDir,
    });
  }

  findings.push(...detectMissingHover({ captureDir, paperSections, sourceDir: shotsDir }));
  findings.push(...placementVerdict(paperSections));

  return dedupe(findings);
}

export function findHoverManifests(captureDir) {
  const roots = [
    resolve(captureDir, "../.."),
    resolve(captureDir, ".."),
    resolve(captureDir, "../../.."),
  ];
  const found = [];
  const seen = new Set();
  for (const root of roots) {
    const comps = join(root, "source-site/components");
    if (!existsSync(comps)) continue;
    for (const page of readdirSync(comps)) {
      const pageDir = join(comps, page);
      for (const kind of ["buttons", "footer"]) {
        const man = join(pageDir, kind, "manifest.json");
        if (!existsSync(man) || seen.has(man)) continue;
        seen.add(man);
        try {
          found.push({ kind, page, path: man, manifest: loadJson(man) });
        } catch { /* skip bad json */ }
      }
    }
    if (found.length) break;
  }
  return found;
}

export function detectMissingHover({ captureDir, paperSections = [], sourceDir } = {}) {
  const findings = [];
  const manifests = findHoverManifests(captureDir);
  const sourceRows = paperSections.filter((s) => s.sourceRow || (s.onSource && /^\d{2} · /.test(s.name || "")));
  const hoverTakes = paperSections.filter((s) => s.hoverBoard || s.onHoverStates);
  const expected = new Map();
  for (const { kind, manifest } of manifests) {
    for (const st of manifest.states || []) {
      const sid = String(st.sectionId || "").padStart(2, "0");
      if (!/^\d{2}$/.test(sid)) continue;
      if (!expected.has(sid)) expected.set(sid, []);
      expected.get(sid).push({ kind, label: st.component || st.token || kind, changed: st.changed });
    }
  }
  if (!expected.size) return findings;
  if (!hoverTakes.length) return findings;

  for (const [sid, items] of expected) {
    const kinds = [...new Set(items.map((i) => i.kind))].join(" + ");
    const labels = [...new Set(items.map((i) => i.label))].join(", ");
    const take = hoverTakes.find((s) =>
      String(s.sectionId || "").padStart(2, "0") === sid
      || String(s.name || "").startsWith(`${sid} ·`)
      || String(s.hasHoverFor || "").padStart(2, "0") === sid
    );
    if (take) continue;
    const row = sourceRows.find((s) => String(s.name || "").startsWith(`${sid} ·`));
    findings.push({
      kind: "missing-hover-state",
      section: row?.name || `${sid} · (missing Hover States row)`,
      node: row?.id || null,
      symptom: `${kinds} hover captured (${labels}) but Hover States has no ${sid} take`,
      evidence: labels,
      auto: "leave",
    });
  }
  return findings;
}

function dedupe(findings) {
  const seen = new Set();
  const out = [];
  for (const f of findings) {
    const key = `${f.kind}|${f.section}|${f.symptom}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const meta = KINDS[f.kind] || {};
    out.push({
      id: `FIX-${String(out.length + 1).padStart(2, "0")}`,
      ...meta,
      ...f,
      status: f.status || "found",
    });
  }
  return out;
}

export function applyStatus(findings, applied) {
  const byId = new Map((applied || []).map((a) => [a.id, a]));
  return findings.map((f) => {
    const hit = byId.get(f.id);
    if (!hit) return f;
    return { ...f, status: hit.status, appliedNote: hit.note || hit.appliedNote };
  });
}

export function humanChecks(findings) {
  const checks = [
    { id: "walk-1600", label: "home-desktop page stack matches live order (isolated section shots can look correct while a leftover top parks a frame below the footer)" },
    { id: "walk-768", label: "home-768 is a real tablet layout, not a squeezed 1600" },
    { id: "walk-390", label: "home-390 is a real phone layout" },
    { id: "library", label: "Design Library foundations look like this site" },
    { id: "paper-comments", label: "Pin a Paper comment on every problem (clip, missing photo, wrong type, hover). Skip only if the file is clean. The next agent reads those threads before 2.0." },
  ];
  for (const f of findings) {
    if (f.kind === "empty-named-section" || f.kind === "hollow-section") {
      checks.push({ id: `see-${f.id}`, label: `${f.section} is no longer a blank frame` });
    } else if (f.kind === "empty-iframe") {
      checks.push({ id: `see-${f.id}`, label: `Map / embed in ${f.section} is a photo, not a white hole` });
    } else if (f.kind === "dead-svg-text") {
      checks.push({ id: `see-${f.id}`, label: `Badge / ring text in ${f.section} is visible` });
    } else if (f.kind === "missing-chrome") {
      checks.push({ id: `see-${f.id}`, label: "Nav / announcement is on the lander" });
    } else if (f.kind === "hidden-variant-stack") {
      checks.push({ id: `see-${f.id}`, label: `${f.section} height is near live (no 1px variant towers)` });
    } else if (f.kind === "date-chrome") {
      checks.push({ id: `see-${f.id}`, label: `Date field shows dd/mm/yyyy, not Enter Text` });
    } else if (f.kind === "source-empty") {
      checks.push({ id: `see-${f.id}`, label: `Leave ${f.section} empty — do not invent copy` });
    } else if (f.kind === "blank-source-shot") {
      checks.push({ id: `see-${f.id}`, label: "Source · home shows real section photos, not white frames" });
    } else if (f.kind === "shot-mismatch") {
      checks.push({ id: `see-${f.id}`, label: `${f.section} Paper shot now matches the source clip` });
    } else if (f.kind === "missing-hover-state") {
      checks.push({ id: `see-${f.id}`, label: `${f.section} has Default | Hover for every button / text link` });
    } else if (f.kind === "displaced-section") {
      checks.push({ id: `see-${f.id}`, label: `${f.section} sits in page order (no leftover top / mid-page hole)` });
    }
  }
  const seen = new Set();
  return checks.filter((c) => (seen.has(c.id) ? false : (seen.add(c.id), true)));
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function isSectionClipPair(p) {
  const labels = [p?.section, p?.slug].filter(Boolean).map(String);
  if (!labels.length) return false;
  if (labels.some((s) => /full stack/i.test(s) || /^home-desktop/i.test(s) || /fullpage/i.test(s))) {
    return false;
  }
  return labels.some((s) => /^\d{2}(?:-| · )/.test(s));
}

function sectionShotPairs(report) {
  return (report.shotPairs || []).filter(isSectionClipPair);
}

function shotGallery(report) {
  const pairs = sectionShotPairs(report);
  if (!pairs.length) {
    return `<p class="lead">No <code>source-sections</code> clips on this run — capture them before the 1.5 human review.</p>`;
  }
  const figs = pairs.map((p) => {
    const miss = p.verdict ? "miss" : "ok";
    const sw = p.sourceWhite == null ? "?" : p.sourceWhite.toFixed(2);
    const pw = p.paperWhite == null ? "?" : p.paperWhite.toFixed(2);
    return `<figure class="pair ${miss}">
      <figcaption><code>${esc(p.section || p.slug)}</code> · source white ${sw} / Paper white ${pw}${p.verdict ? ` · ${esc(p.verdict.symptom)}` : " · match"}</figcaption>
      <div class="pair-imgs">
        ${p.sourceRel ? `<img src="${esc(p.sourceRel)}" alt="source ${esc(p.slug)}"/>` : `<div class="empty">no source clip</div>`}
        ${p.paperRel ? `<img src="${esc(p.paperRel)}" alt="paper ${esc(p.slug)}"/>` : `<div class="empty">no Paper shot</div>`}
      </div>
    </figure>`;
  }).join("\n");
  return `<h2>Source clip vs Paper</h2>
  <p class="lead">Every run compares each <code>source-sections/NN-*.png</code> (pesticide on) to a Paper screenshot of that named section. No full-page stack. A per-section white-ratio match is not a page-order pass.</p>
  <div class="pairs">${figs}</div>`;
}

export function renderReportHtml(report) {
  const findings = report.findings || [];
  const applied = findings.filter((f) => f.status === "applied" || f.status === "left-on-purpose");
  const blocked = findings.filter((f) => f.status === "found" || f.status === "failed");
  const checks = report.checks || humanChecks(findings);
  const rows = findings.map((f) => {
    const done = f.status === "applied" || f.status === "left-on-purpose";
    const mark = done ? "✓" : f.status === "failed" ? "!" : "·";
    const cls = done ? "ok" : f.status === "failed" ? "bad" : "open";
    return `<tr class="${cls}">
      <td class="mark">${mark}</td>
      <td><code>${esc(f.id)}</code></td>
      <td>${esc(f.severity || "")}</td>
      <td>${esc(f.title || f.kind)}</td>
      <td>${esc(f.section)}</td>
      <td>${esc(f.symptom)}</td>
      <td>${esc(f.fix || "")}${f.appliedNote ? `<div class="note">${esc(f.appliedNote)}</div>` : ""}</td>
      <td class="st">${esc(f.status)}</td>
    </tr>`;
  }).join("\n");

  const checkRows = checks.map((c) => {
    const on = c.checked ? "checked" : "";
    return `<label class="check ${on}"><input type="checkbox" data-check="${esc(c.id)}" ${on ? "checked" : ""}/><span>${esc(c.label)}</span></label>`;
  }).join("\n");

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="color-scheme" content="dark" />
<meta name="theme-color" content="#050b00" />
<title>1.55 Missing-elements · ${esc(report.title || "QA")}</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
<style>
  :root {
    color-scheme: dark;
    --bg: oklch(0.137 0.036 128);
    --surface: oklch(0.175 0.040 128);
    --ink: oklch(0.966 0.020 128);
    --text: oklch(0.90 0.038 128);
    --muted: oklch(0.76 0.090 128);
    --line: oklch(0.920 0.210 128.5 / 0.20);
    --line-strong: oklch(0.920 0.210 128.5 / 0.42);
    --accent: oklch(0.920 0.210 128.5);
    --accent-soft: oklch(0.920 0.210 128.5 / 0.12);
    --accent-contrast: oklch(0.137 0.036 128);
    --human: oklch(0.84 0.14 102);
    --human-soft: oklch(0.84 0.14 102 / 0.12);
    --ok: oklch(0.82 0.16 145);
    --ok-soft: oklch(0.82 0.16 145 / 0.12);
    --bad: oklch(0.72 0.16 25);
    --bad-soft: oklch(0.72 0.16 25 / 0.12);
    --sans: "Hanken Grotesk", system-ui, sans-serif;
    --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    --radius: 2px;
    --dot-grid-size: 16px;
    --dot-grid-opacity: 0.42;
    --dot-grid-color: color-mix(in srgb, var(--accent) 28%, transparent);
  }
  *, *::before, *::after { box-sizing: border-box; }
  html, body { min-height: 100%; background: var(--bg); }
  body {
    position: relative;
    margin: 0;
    color: var(--text);
    font: 400 15px/1.5 var(--sans);
    -webkit-font-smoothing: antialiased;
  }
  body::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background-image: radial-gradient(circle, var(--dot-grid-color) 1px, transparent 1px);
    background-size: var(--dot-grid-size) var(--dot-grid-size);
    background-position: center;
    opacity: var(--dot-grid-opacity);
  }
  ::selection { background: var(--accent); color: var(--accent-contrast); }
  :focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
  a { color: var(--accent); }
  .page {
    position: relative;
    z-index: 1;
    width: min(980px, 100%);
    margin: 0 auto;
    padding: 48px 24px 80px;
  }
  .page::before, .page::after {
    content: "";
    position: absolute;
    width: 18px; height: 18px;
    pointer-events: none;
    border-color: var(--accent);
    border-style: solid;
  }
  .page::before { top: 14px; left: 14px; border-width: 1px 0 0 1px; }
  .page::after { top: 14px; right: 14px; border-width: 1px 1px 0 0; }
  .page-foot-marks {
    position: absolute; left: 14px; right: 14px; bottom: 14px; height: 18px;
    pointer-events: none;
  }
  .page-foot-marks::before, .page-foot-marks::after {
    content: "";
    position: absolute; width: 18px; height: 18px;
    border-color: var(--accent); border-style: solid;
  }
  .page-foot-marks::before { left: 0; bottom: 0; border-width: 0 0 1px 1px; }
  .page-foot-marks::after { right: 0; bottom: 0; border-width: 0 1px 1px 0; }
  .mast {
    display: flex; justify-content: space-between; align-items: center;
    gap: 16px; margin: 0 0 28px; padding-bottom: 14px;
    border-bottom: 1px solid var(--line-strong);
    color: var(--muted);
    font: 600 11px/1.2 var(--sans);
    letter-spacing: 0.14em; text-transform: uppercase;
  }
  .mast strong { color: var(--accent); font-weight: 800; letter-spacing: 0.16em; }
  .mast-tag {
    padding: 5px 9px; border: 1px solid var(--line-strong);
    color: var(--accent); font: 700 10px/1 var(--sans); letter-spacing: 0.14em;
  }
  h1 { margin: 0 0 6px; color: var(--accent); font: 800 1.8rem/1.15 var(--sans); letter-spacing: -0.03em; }
  .lead { color: var(--muted); margin: 0 0 22px; max-width: 62ch; }
  .pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 22px; }
  .pill { padding: 5px 10px; border-radius: var(--radius); font: 650 12px/1 var(--mono); }
  .pill.ok { background: var(--ok-soft); color: var(--ok); }
  .pill.open { background: var(--bad-soft); color: var(--bad); }
  .pill.human { background: var(--human-soft); color: var(--human); }
  h2 { margin: 28px 0 10px; color: var(--accent); font: 700 1.05rem/1.2 var(--sans); }
  table { width: 100%; border-collapse: collapse; background: var(--surface); border: 1px solid var(--line); border-radius: 2px; overflow: hidden; }
  th, td { text-align: left; padding: 10px 10px; border-top: 1px solid var(--line); vertical-align: top; font-size: 0.88rem; }
  th { font: 650 11px/1.2 var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; border-top: 0; }
  tr.ok { background: var(--ok-soft); }
  tr.bad { background: var(--bad-soft); }
  .mark { font: 650 16px/1 var(--sans); width: 28px; }
  tr.ok .mark { color: var(--ok); }
  tr.bad .mark { color: var(--bad); }
  .st { font: 650 11px/1 var(--mono); }
  .note { margin-top: 4px; color: var(--muted); font-size: 0.8rem; }
  code { font: 0.9em var(--mono); color: var(--ink); }
  .box { padding: 16px; border: 1px solid var(--human); border-radius: 2px; background: var(--human-soft); }
  .checks { display: grid; gap: 8px; }
  .check { display: flex; gap: 10px; align-items: flex-start; padding: 8px 10px; background: var(--surface); border-radius: 2px; border: 1px solid var(--line); }
  .check.checked { background: var(--ok-soft); border-color: var(--ok); }
  .check input { margin-top: 3px; }
  footer { margin-top: 28px; color: var(--muted); font: 400 12px/1.5 var(--mono); }
  .pairs { display: grid; gap: 16px; }
  .pair { margin: 0; padding: 10px; background: var(--surface); border: 1px solid var(--line); border-radius: 2px; }
  .pair.miss { border-color: var(--bad); background: var(--bad-soft); }
  .pair figcaption { font: 650 12px/1.4 var(--mono); color: var(--ink); margin: 0 0 8px; }
  .pair-imgs { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .pair-imgs img { width: 100%; height: auto; border-radius: 2px; background: var(--surface); }
  .pair-imgs .empty { min-height: 80px; display: grid; place-items: center; color: var(--muted); font: 12px var(--mono); background: var(--surface); border-radius: 2px; }
  .reply { margin: 0 0 12px; }
  .reply code { font: 650 14px/1.4 var(--mono); color: var(--ink); }
  .proceed { appearance: none; border: 0; border-radius: 2px; padding: 10px 14px; background: var(--accent); color: var(--accent-contrast); font: 650 13px/1 var(--sans); cursor: pointer; }
  .proceed:hover { opacity: 0.88; }
</style>
</head>
<body>
<div class="page">
  <div class="mast"><strong>WEB2HTML</strong><span class="mast-tag">QA</span></div>
  <h1>1.55 Missing-elements</h1>
  <p class="lead">${esc(report.subtitle || "Issues found, solutions already applied, then your final checks. Do not start 2.0 until the boxes below are honest.")}</p>
  <div class="pills">
    <span class="pill ok">${applied.length} applied</span>
    <span class="pill open">${blocked.length} still open</span>
    <span class="pill human">${checks.length} human checks</span>
  </div>
  ${report.paperUrl ? `<p class="lead">Paper: <a href="${esc(report.paperUrl)}">${esc(report.paperUrl)}</a>${report.liveUrl ? ` · Live: <a href="${esc(report.liveUrl)}">${esc(report.liveUrl)}</a>` : ""}</p>` : ""}
  ${shotGallery(report)}

  <h2>Issues found</h2>
  <table>
    <thead><tr><th></th><th>ID</th><th>Sev</th><th>Issue</th><th>Where</th><th>What we saw</th><th>Solution</th><th>Status</th></tr></thead>
    <tbody>
      ${rows || `<tr><td colspan="8">No missing-element defects. Still walk the final checks.</td></tr>`}
    </tbody>
  </table>

  <h2>Final checks</h2>
  <div class="box">
    <p class="lead" style="margin:0 0 12px">These ticks stay in this browser. They do not tell the agent. If anything is still wrong, pin a <strong>comment on that Paper layer</strong> — do not only type it in chat. The next agent lists open threads and fixes them before 2.0. When the file is clean, reply:</p>
    <p class="reply"><code>Paper looks right — continue</code></p>
    <button type="button" class="proceed" id="copy-proceed">Copy that reply</button>
    <div class="checks" style="margin-top:14px">${checkRows}</div>
  </div>
  <footer>Generated ${esc(report.generatedAt || "")} · ${esc(report.project || "")} · Optional diagnostic before 1.5 human sign-off</footer>
  <div class="page-foot-marks" aria-hidden="true"></div>
</div>
<script>
const key = "me-fix:" + location.pathname;
const saved = JSON.parse(localStorage.getItem(key) || "{}");
for (const input of document.querySelectorAll("input[data-check]")) {
  if (saved[input.dataset.check]) {
    input.checked = true;
    input.closest(".check").classList.add("checked");
  }
  input.addEventListener("change", () => {
    saved[input.dataset.check] = input.checked;
    localStorage.setItem(key, JSON.stringify(saved));
    input.closest(".check").classList.toggle("checked", input.checked);
  });
}
const phrase = "Paper looks right — continue";
document.getElementById("copy-proceed")?.addEventListener("click", async () => {
  const b = document.getElementById("copy-proceed");
  try {
    await navigator.clipboard.writeText(phrase);
    if (b) b.textContent = "Copied — paste it in the agent chat";
  } catch {
    if (b) b.textContent = "Copy failed — reply that phrase in chat";
  }
});
</script>
</body>
</html>`;
}

export function writeReport(outDir, report) {
  mkdirSync(outDir, { recursive: true });
  const jsonPath = join(outDir, "missing-elements-fix.json");
  const mdPath = join(outDir, "missing-elements-fix.md");
  const htmlPath = join(outDir, "missing-elements-fix.html");
  writeFileSync(jsonPath, JSON.stringify(report, null, 2));
  writeFileSync(htmlPath, renderReportHtml(report));
  const lines = [
    `# Missing-elements QA — ${report.project || report.title || ""}`,
    "",
    `**Date:** ${report.generatedAt || ""}`,
    report.paperUrl ? `**Paper:** ${report.paperUrl}` : "",
    report.liveUrl ? `**Live:** ${report.liveUrl}` : "",
    "",
    "## Issues",
    "",
    "| ID | Sev | Issue | Section | Status | Solution |",
    "|---|---|---|---|---|---|",
    ...(report.findings || []).map((f) =>
      `| ${f.id} | ${f.severity || ""} | ${f.title || f.kind} | ${f.section} | ${f.status} | ${(f.fix || "").replace(/\|/g, "/")} |`
    ),
    "",
    "## Final checks",
    "",
    ...((report.checks || []).map((c) => `- [${c.checked ? "x" : " "}] ${c.label}`)),
    "",
    "",
    "## Source clip vs Paper",
    "",
    "Every run compares each `source-sections/NN-*.png` to a Paper screenshot of that named section. No full-page stack. A white-ratio match on an isolated node is not a page-order pass.",
    ...(sectionShotPairs(report).map((p) => {
      const tag = p.verdict ? "MISS" : "ok";
      return `- ${tag} **${p.section || p.slug}** — source white ${p.sourceWhite ?? "?"} / Paper white ${p.paperWhite ?? "?"}${p.verdict ? ` — ${p.verdict.symptom}` : ""}`;
    })),
    "",
    "Open `qa/missing-elements-fix.html` in Chrome. Ticks stay in the browser. When they are true, reply in the agent chat: Paper looks right — continue.",
  ].filter(Boolean);
  writeFileSync(mdPath, lines.join("\n") + "\n");
  return { jsonPath, mdPath, htmlPath };
}
