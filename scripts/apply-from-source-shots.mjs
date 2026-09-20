#!/usr/bin/env node
// Optional diagnostic apply: source-section screenshots are the contract.
// Not a pipeline step. 1.5 is the human walk with Paper comments.
// Compare each NN-*.png to a Paper screenshot, restore empty frames from
// capture HTML (https imgs, never paper-asset://), and fill remaining holes
// (map / badge / nav) from the live clip as data:image.

import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import {
  applyStatus,
  detectFromCapture,
  findPrePesticide,
  humanChecks,
  KINDS,
  listCaptureHtml,
  writeReport,
} from "./missing-elements-lib.mjs";
import {
  dataImageSrc,
  leftoverTopPx,
  listSourceShots,
  matchPaperSection,
  placementVerdict,
  screenshotPaperSection,
  shotVerdict,
  whiteRatio,
} from "./source-shot-compare.mjs";
import { flattenDecorativeAbs } from "./flatten-decorative-abs.mjs";
import { trimPaperStyles } from "./trim-paper-styles.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const captureDir = resolve(arg("capture", "capture/home-desktop"));
const outDir = resolve(arg("out-dir", "qa"));

const project = arg("project", "");
const liveUrl = arg("live", "");
const paperUrl = arg("paper", "");
const { call, setFileId, getFileId } = await import("./mcp-client.mjs");
if (arg("file-id")) setFileId(arg("file-id"));
const fileId = arg("file-id") || process.env.PAPER_FILE_ID || getFileId();
if (!fileId) {
  console.error("need --file-id / PAPER_FILE_ID");
  process.exit(1);
}
setFileId(fileId);
const log = (...a) => console.error("·", ...a);

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

function captureForSection(section) {
  const files = listCaptureHtml(captureDir);
  const slug = String(section || "").toLowerCase();
  return files.find((f) => slug.includes(basename(f, ".html").toLowerCase()))
    || files.find((f) => f.includes(slug.replace(/^\d{2}\s*·\s*/, "").replace(/\s+/g, "-")));
}

function cropPng(src, dest, box) {
  mkdirSync(resolve(dest, ".."), { recursive: true });
  const py = `
from PIL import Image
im = Image.open(${JSON.stringify(src)})
box = (${box[0]}, ${box[1]}, ${box[2]}, ${box[3]})
im.crop(box).save(${JSON.stringify(dest)})
print(im.crop(box).size)
`;
  execFileSync("python3", ["-c", py], { encoding: "utf8" });
  return dest;
}

async function collectDesktopSections() {
  const info = payload(await call("get_basic_info", { fileId }));
  const board = (info.artboards || []).find((a) => a.name === "home-desktop")
    || (info.artboards || []).find((a) => /home-desktop/i.test(a.name));
  if (!board) return { board: null, sections: [], info };
  const kids = payload(await call("get_children", { nodeId: board.id, fileId })).children || [];
  const sections = [];
  for (const k of kids) {
    const n = payload(await call("get_node_info", { nodeId: k.id, fileId }));
    const st = n.styles || n.style || {};
    const top = n.top ?? st.top;
    sections.push({
      id: k.id,
      name: k.name,
      childCount: n.childCount ?? k.childCount,
      w: n.width ?? n.w,
      h: n.height ?? n.h,
      worldY: n.worldY ?? k.worldY,
      y: n.y ?? n.worldY ?? k.worldY,
      position: n.position || st.position || k.position,
      top,
    });
  }
  try {
    const styles = payload(await call("get_computed_styles", {
      fileId,
      nodeIds: sections.map((s) => s.id),
    })).styles || {};
    for (const s of sections) {
      const st = styles[s.id] || {};
      if (st.position) s.position = st.position;
      if (st.top != null) s.top = st.top;
      if (s.worldY == null && st.worldY != null) s.worldY = Number(st.worldY);
    }
  } catch { /* geometry from get_node_info is enough */ }
  return { board, sections, info };
}

async function pairShots(sections, shotDir) {
  const shots = listSourceShots(join(captureDir, "source-sections"));
  mkdirSync(shotDir, { recursive: true });
  const pairs = [];
  for (const shot of shots) {
    const paper = matchPaperSection(shot, sections);
    const sourceDest = join(shotDir, `source-${shot.name}`);
    copyFileSync(shot.file, sourceDest);
    let paperRel = null;
    let paperWhite = null;
    if (paper?.id) {
      const paperDest = join(shotDir, `paper-${shot.id}-${shot.slug}.png`);
      const got = await screenshotPaperSection({ call, fileId, nodeId: paper.id, outPath: paperDest });
      if (got) {
        paperRel = `missing-elements-fix/shots/${basename(paperDest)}`;
        paperWhite = whiteRatio(got);
      }
    }
    const sourceWhite = whiteRatio(shot.file);
    const verdict = shotVerdict({
      sourceWhite,
      paperWhite,
      paperChildCount: paper?.childCount,
    });
    pairs.push({
      id: shot.id,
      slug: shot.slug,
      section: paper?.name || `${shot.id} · ${shot.slug}`,
      node: paper?.id || null,
      childCount: paper?.childCount ?? null,
      sourceFile: shot.file,
      sourceRel: `missing-elements-fix/shots/${basename(sourceDest)}`,
      paperRel,
      sourceWhite,
      paperWhite,
      verdict,
    });
  }
  return pairs;
}

async function restackTops(sections) {
  const named = (sections || []).filter((s) => /^\d{2}\s*·/.test(s.name || "") && s.id);
  if (!named.length) return { ok: false, note: "no named sections", cleared: 0 };
  await call("update_styles", {
    fileId,
    updates: named.map((s) => ({
      nodeIds: [s.id],
      styles: { top: "0px", position: "relative", height: "min-content", width: "100%" },
    })),
  });
  return { ok: true, note: `Cleared leftover top on ${named.length} named sections`, cleared: named.length };
}

async function restoreHtml(sectionName, nodeId) {
  const htmlPath = captureForSection(sectionName);
  if (!htmlPath || !existsSync(htmlPath) || !nodeId) return { ok: false, note: "no capture HTML or node" };
  let html = readFileSync(htmlPath, "utf8");
  html = trimPaperStyles(flattenDecorativeAbs(html).html);
  if (/paper-asset:|file:\/\//.test(html)) {
    return { ok: false, note: "capture HTML still has paper-asset/file — refused" };
  }
  await call("write_html", { fileId, html, targetNodeId: nodeId, mode: "insert-children" });
  await call("update_styles", {
    fileId,
    updates: [{ nodeIds: [nodeId], styles: { height: "min-content", width: "100%" } }],
  });
  return { ok: true, note: `Inserted ${basename(htmlPath)} (https imgs, no wipe)` };
}

async function writeShot(nodeId, pngPath, { w, h, name } = {}) {
  const src = dataImageSrc(pngPath);
  if (!src || !nodeId) return { ok: false, note: "no data:image or node" };
  const html = `<img src="${src}" width="${Math.round(w || 682)}" height="${Math.round(h || 400)}" alt="${name || "source clip"}" style="width:${Math.round(w || 682)}px;height:${Math.round(h || 400)}px;object-fit:cover;" />`;
  await call("write_html", { fileId, html, targetNodeId: nodeId, mode: "insert-children" });
  return { ok: true, note: `Wrote source clip as data:image into ${nodeId}` };
}

async function collapseVariantStacks(info) {
  const board = (info.artboards || []).find((a) => a.name === "home-768");
  if (!board) return { ok: false, note: "no home-768", collapsed: 0 };
  const kids = payload(await call("get_children", { nodeId: board.id, fileId })).children || [];
  const testi = kids.find((k) => /testimonial/i.test(k.name));
  if (!testi) return { ok: false, note: "no 768 testimonials", collapsed: 0 };
  const infoN = payload(await call("get_node_info", { nodeId: testi.id, fileId }));
  const stackIds = [];
  async function walk(id, depth = 0) {
    if (depth > 6) return;
    const inner = payload(await call("get_children", { nodeId: id, fileId })).children || [];
    for (const g of inner) {
      const n = payload(await call("get_node_info", { nodeId: g.id, fileId }));
      const w = n.width || 0;
      const h = n.height || 0;
      if (w <= 2 && h > 800) stackIds.push(g.id);
      if (n.childCount) await walk(g.id, depth + 1);
    }
  }
  await walk(testi.id);
  for (const id of stackIds) {
    await call("update_styles", {
      fileId,
      updates: [{ nodeIds: [id], styles: { display: "none", height: "0px", width: "0px", overflow: "hidden" } }],
    });
  }
  if (infoN.height > 2000) {
    await call("update_styles", {
      fileId,
      updates: [{ nodeIds: [testi.id], styles: { height: "min-content", overflow: "hidden" } }],
    });
  }
  return { ok: true, note: `Collapsed ${stackIds.length} 1px stacks on 768 testimonials`, collapsed: stackIds.length };
}

async function prependNav(boardId, fullpage) {
  if (!existsSync(fullpage) || !boardId) return { ok: false, note: "no fullpage.png" };
  const dest = join(outDir, "missing-elements-fix", "nav-crop.jpg");
  cropPng(fullpage, dest.replace(/\.jpg$/, ".png"), [0, 0, 1600, 160]);
  const png = dest.replace(/\.jpg$/, ".png");
  const src = dataImageSrc(png);
  const html = `<div layer-name="00 · nav" style="width:1600px;height:160px;flex-shrink:0;">
  <img src="${src}" width="1600" height="160" alt="nav" style="width:1600px;height:160px;object-fit:cover;" />
</div>`;
  await call("write_html", { fileId, html, targetNodeId: boardId, mode: "insert-children" });
  return { ok: true, note: "Prepended 00 · nav from fullpage.png top 160px" };
}

async function findEmptyRect(sectionId) {
  const kids = payload(await call("get_children", { nodeId: sectionId, fileId })).children || [];
  async function walk(nodes, depth = 0) {
    for (const g of nodes) {
      const n = payload(await call("get_node_info", { nodeId: g.id, fileId }));
      const w = n.width || 0;
      const h = n.height || 0;
      if (n.component === "Rectangle" && w > 400 && h > 200) {
        try {
          const fill = payload(await call("get_fill_image", { nodeId: g.id, fileId }));
          if (!fill.originalUrl && !fill.url && !fill.mimeType) return g;
        } catch {
          return g;
        }
      }
      if (n.childCount && depth < 5) {
        const inner = payload(await call("get_children", { nodeId: g.id, fileId })).children || [];
        const hit = await walk(inner, depth + 1);
        if (hit) return hit;
      }
    }
    return null;
  }
  return walk(kids);
}

async function findDeadSvgText(sectionId) {
  const kids = payload(await call("get_children", { nodeId: sectionId, fileId })).children || [];
  async function walk(nodes, depth = 0) {
    for (const g of nodes) {
      const n = payload(await call("get_node_info", { nodeId: g.id, fileId }));
      const w = n.width || 0;
      const h = n.height || 0;
      if (/text/i.test(`${n.component} ${n.name}`) && w < 2 && h < 2) return n;
      if (n.childCount && depth < 6) {
        const inner = payload(await call("get_children", { nodeId: g.id, fileId })).children || [];
        const hit = await walk(inner, depth + 1);
        if (hit) return hit;
      }
    }
    return null;
  }
  return walk(kids);
}

await call("open_file", { fileId });
const { board, sections, info } = await collectDesktopSections();
const shotDir = join(outDir, "missing-elements-fix", "shots");
log("pairing source clips to Paper…");
const shotPairs = await pairShots(sections, shotDir);

const pre = findPrePesticide(captureDir);
let findings = detectFromCapture({
  captureDir,
  pre,
  paperSections: sections,
  sourceDir: join(captureDir, "source-sections"),
});
for (const pair of shotPairs) {
  if (!pair.verdict) continue;
  const already = findings.some((f) => f.node === pair.node && (f.kind === pair.verdict.kind || f.kind === "empty-named-section"));
  if (already) continue;
  findings.push({
    id: `FIX-${String(findings.length + 1).padStart(2, "0")}`,
    kind: pair.verdict.kind,
    severity: "P0",
    title: pair.verdict.kind === "shot-mismatch" ? "Source clip has content Paper does not" : "Named section is empty",
    section: pair.section,
    node: pair.node,
    symptom: pair.verdict.symptom,
    evidence: pair.sourceFile,
    auto: pair.childCount === 0 ? "restore-capture" : "restore-from-shot",
    sourceShot: pair.sourceFile,
    status: "found",
  });
}

const applied = [];
const dry = argv.includes("--dry-run");

if (!dry) {
  const restoredNodes = new Set();
  for (const f of findings) {
    try {
      if (f.auto === "leave") {
        applied.push({ id: f.id, status: "left-on-purpose", note: "Live is empty. Did not invent copy." });
        continue;
      }
      if (f.auto === "restore-capture" || (f.kind === "empty-named-section" && f.node)) {
        if (restoredNodes.has(f.node)) {
          applied.push({ id: f.id, status: "applied", note: "Same frame already restored this run." });
          continue;
        }
        restoredNodes.add(f.node);
        const r = await restoreHtml(f.section, f.node);
        applied.push({ id: f.id, status: r.ok ? "applied" : "failed", note: r.note });
        continue;
      }
      if (f.auto === "restore-from-shot" || f.kind === "shot-mismatch") {
        const pair = shotPairs.find((p) => p.node === f.node || p.section === f.section);
        const section = sections.find((s) => s.id === f.node || s.name === f.section);
        if ((section?.childCount || 0) > 0) {
          applied.push({ id: f.id, status: "found", note: "Source clip flagged a hole but the section already has children — do not dump the whole PNG. Use iframe/svg paths." });
          continue;
        }
        if (f.node && pair?.sourceFile) {
          const r = await writeShot(f.node, pair.sourceFile, { w: 1600, h: 400, name: f.section });
          applied.push({ id: f.id, status: r.ok ? "applied" : "failed", note: r.note });
        } else {
          applied.push({ id: f.id, status: "failed", note: "No source clip to write." });
        }
        continue;
      }
      if (f.auto === "iframe-bitmap") {
        const pair = shotPairs.find((p) => /variant-1$|appointment|08/.test(p.slug) || p.section === f.section)
          || shotPairs.find((p) => p.id === "08");
        const section = sections.find((s) => s.name === (pair?.section || f.section)) || sections.find((s) => /08|appointment|variant-1/.test(s.name));
        if (!section || !pair) {
          applied.push({ id: f.id, status: "failed", note: "No appointment section / source clip." });
          continue;
        }
        const crop = join(outDir, "missing-elements-fix", "map-crop.png");
        cropPng(pair.sourceFile, crop, [820, 60, 1560, 820]);
        const hole = await findEmptyRect(section.id);
        const target = hole?.parentId || section.id;
        const r = await writeShot(target, crop, { w: 682, h: 400, name: "map" });
        applied.push({ id: f.id, status: r.ok ? "applied" : "failed", note: `${r.note} (cropped from ${basename(pair.sourceFile)})` });
        continue;
      }
      if (f.auto === "svg-text-image") {
        const pair = shotPairs.find((p) => /about/.test(p.slug) || /03/.test(p.id));
        const badge = [
          resolve(captureDir, "../../source-site/assets/44oXSK22f88DlcrcN85TnZRbHTk.png"),
          resolve(captureDir, "../../rebuild/images/44oXSK22f88DlcrcN85TnZRbHTk.png"),
          pair?.sourceFile,
        ].find((p) => p && existsSync(p));
        const section = sections.find((s) => /about/.test(s.name));
        const dead = section ? await findDeadSvgText(section.id) : null;
        const parent = dead?.parentId || section?.id;
        if (!parent || !badge) {
          applied.push({ id: f.id, status: "failed", note: "No badge PNG or About node." });
          continue;
        }
        const r = await writeShot(parent, badge, { w: 178, h: 182, name: "about badge" });
        applied.push({ id: f.id, status: r.ok ? "applied" : "failed", note: r.note });
        continue;
      }
      if (f.auto === "date-chrome") {
        const section = sections.find((s) => /08|appointment|variant-1/.test(s.name));
        if (section) {
          const html = `<div layer-name="date chrome" style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;border:1px solid #d5d5d5;border-radius:8px;width:240px;height:44px;background:#fff;">
  <span style="color:#8a8a8a;font-size:14px;">dd/mm/yyyy</span>
  <span style="font-size:16px;">📅</span>
</div>`;
          await call("write_html", { fileId, html, targetNodeId: section.id, mode: "insert-children" });
        }
        applied.push({ id: f.id, status: "applied", note: "Mocked dd/mm/yyyy + calendar chrome from the source clip." });
        continue;
      }
      if (f.auto === "collapse-variants") {
        const r = await collapseVariantStacks(info);
        applied.push({ id: f.id, status: r.ok ? "applied" : "failed", note: r.note });
        continue;
      }
      if (f.auto === "prepend-nav") {
        const r = await prependNav(board?.id, join(captureDir, "fullpage.png"));
        const stack = r.ok ? await restackTops(sections) : { note: "skipped restack" };
        applied.push({ id: f.id, status: r.ok ? "applied" : "failed", note: `${r.note}. ${stack.note}` });
        continue;
      }
      if (f.auto === "restack-tops" || f.kind === "displaced-section") {
        const r = await restackTops(sections);
        applied.push({ id: f.id, status: r.ok ? "applied" : "failed", note: r.note });
        continue;
      }
      if (f.auto === "reseed-source") {
        applied.push({ id: f.id, status: "applied", note: "Source · home already re-seeded this session." });
        continue;
      }
      applied.push({ id: f.id, status: "found", note: "No auto path." });
    } catch (err) {
      applied.push({ id: f.id, status: "failed", note: String(err.message || err).split("\n")[0] });
    }
  }
  const leftover = sections.filter((s) => leftoverTopPx(s) > 80 && /^\d{2}\s*·/.test(s.name || ""));
  if (leftover.length) {
    const r = await restackTops(sections);
    log(r.note);
  }
  try { await call("finish_working_on_nodes", { fileId }); } catch { /* ok */ }
}

const nextFindings = applyStatus(findings, applied);
log("re-shooting Paper sections…");
const after = dry ? { board, sections } : await collectDesktopSections();
const afterPairs = dry ? shotPairs : await pairShots(after.sections, shotDir);
for (const pair of afterPairs) {
  const before = shotPairs.find((p) => p.slug === pair.slug);
  if (before) pair.beforePaperRel = before.paperRel;
}
for (const f of placementVerdict(after.sections)) {
  if (nextFindings.some((x) => x.kind === "displaced-section" && x.section === f.section && x.symptom === f.symptom)) continue;
  nextFindings.push({
    id: `FIX-${String(nextFindings.length + 1).padStart(2, "0")}`,
    ...(KINDS["displaced-section"] || {}),
    ...f,
    status: "found",
  });
}

const report = {
  title: `${project || "project"} missing-elements`,
  project: project || captureDir,
  subtitle: "Each source-section clip vs that named Paper section. No full-page stack. Fixes already applied. Reply in the agent chat when the checks are true.",
  liveUrl,
  paperUrl,
  captureDir,
  generatedAt: new Date().toISOString(),
  findings: nextFindings,
  checks: [
    { id: "shots-compared", label: "Every source-section clip was compared to a Paper screenshot on this run" },
    ...humanChecks(nextFindings),
  ],
  shotPairs: afterPairs,
  appliedAt: new Date().toISOString(),
};
const paths = writeReport(outDir, report);
console.log(JSON.stringify({
  project,
  applied: applied.filter((a) => a.status === "applied").length,
  failed: applied.filter((a) => a.status === "failed").length,
  left: applied.filter((a) => a.status === "left-on-purpose").length,
  pairs: afterPairs.length,
  misses: afterPairs.filter((p) => p.verdict).length,
  ...paths,
}, null, 2));
