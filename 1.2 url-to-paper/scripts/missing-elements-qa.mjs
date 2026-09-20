#!/usr/bin/env node
// Phase 1.55 — inventory live pre-pesticide vs capture vs Paper.
// Writes qa/missing-elements-fix.{json,md,html}. Does not mutate Paper.

import { existsSync } from "node:fs";
import { resolve } from "node:path";
import {
  detectFromCapture,
  findPrePesticide,
  humanChecks,
  writeReport,
} from "./missing-elements-lib.mjs";

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
const paperTreePath = arg("paper-tree");

if (!existsSync(captureDir)) {
  console.error(`capture dir not found: ${captureDir}`);
  process.exit(1);
}

const pre = findPrePesticide(captureDir);
let paperSections = [];
if (paperTreePath && existsSync(paperTreePath)) {
  const tree = JSON.parse(await import("node:fs").then((fs) => fs.readFileSync(paperTreePath, "utf8")));
  paperSections = tree.sections || tree.paperSections || [];
} else if (!argv.includes("--no-paper")) {
  try {
    const { call, getFileId, setFileId } = await import("./mcp-client.mjs");
    if (arg("file-id")) setFileId(arg("file-id"));
    const fileId = arg("file-id") || process.env.PAPER_FILE_ID || getFileId();
    if (fileId) {
      paperSections = await collectPaperSections(call, arg("artboard", "home-desktop"));
    }
  } catch (err) {
    console.error("· Paper tree skipped:", String(err.message || err).split("\n")[0]);
  }
}

const findings = detectFromCapture({
  captureDir,
  pre,
  paperSections,
  sourceDir: resolve(captureDir, "source-sections"),
});
const report = {
  title: `${project || "project"} missing-elements`,
  project: project || captureDir,
  subtitle: "Issues found against pre-pesticide + capture. Solutions are applied in 1.55 before you review.",
  liveUrl,
  paperUrl,
  captureDir,
  generatedAt: new Date().toISOString(),
  findings,
  checks: humanChecks(findings),
  paperSections: paperSections.map((s) => ({ name: s.name, id: s.id, childCount: s.childCount, w: s.w, h: s.h })),
};

const paths = writeReport(outDir, report);
console.log(JSON.stringify({ findings: findings.length, ...paths, blockers: findings.filter((f) => f.severity === "P0").length }, null, 2));

async function collectPaperSections(call, artboardName) {
  const payload = (result) => {
    for (const item of result.content ?? []) {
      if (item.type === "text") {
        try { return JSON.parse(item.text); } catch { return { text: item.text }; }
      }
    }
    return {};
  };
  const info = payload(await call("get_basic_info", {}));
  const boards = (info.artboards || []).filter((a) =>
    !artboardName || a.name === artboardName || a.id === artboardName
  );
  const board = boards[0] || (info.artboards || []).find((a) => /home-desktop/i.test(a.name));
  if (!board) return [];
  const kids = payload(await call("get_children", { nodeId: board.id })).children || [];
  const sections = [];
  for (const k of kids) {
    const rec = {
      id: k.id,
      name: k.name,
      childCount: k.childCount,
      w: k.width ?? k.w,
      h: k.height ?? k.h,
      worldY: k.worldY,
      y: k.y ?? k.worldY,
      position: k.position,
      top: k.top,
    };
    try {
      const n = payload(await call("get_node_info", { nodeId: k.id }));
      rec.childCount = n.childCount ?? rec.childCount;
      rec.w = n.width ?? n.w ?? rec.w;
      rec.h = n.height ?? n.h ?? rec.h;
      rec.worldY = n.worldY ?? rec.worldY;
      rec.y = n.y ?? n.worldY ?? rec.y;
      rec.position = n.position || rec.position;
      rec.top = n.top ?? rec.top;
    } catch { /* children payload is enough */ }
    if ((k.childCount || 0) > 0) {
      try {
        const grand = payload(await call("get_children", { nodeId: k.id })).children || [];
        for (const g of grand) {
          if ((g.width === 0 || g.w === 0 || g.height === 0 || g.h === 0) && /text/i.test(`${g.component || ""} ${g.name || ""}`)) {
            rec.deadSvgText = { id: g.id, detail: `${g.name} 0×0` };
          }
          if ((g.width ?? g.w ?? 99) <= 2 && (g.height ?? g.h ?? 0) > 800) {
            sections.push({
              id: g.id,
              name: `${k.name} / ${g.name}`,
              childCount: g.childCount,
              w: g.width ?? g.w,
              h: g.height ?? g.h,
            });
          }
        }
      } catch { /* shallow is enough */ }
    }
    sections.push(rec);
  }
  const sourceBoards = (info.artboards || []).filter((a) => /^Source\s*·/.test(a.name || ""));
  for (const sb of sourceBoards) {
    const rows = payload(await call("get_children", { nodeId: sb.id })).children || [];
    let emptyShots = 0;
    for (const row of rows) {
      let kids = [row];
      try {
        kids = payload(await call("get_children", { nodeId: row.id })).children || [row];
      } catch { /* row itself */ }
      let hasHoverStates = false;
      for (const g of kids) {
        const kind = `${g.component || ""} ${g.type || ""} ${g.name || ""}`;
        const isImg = /image|img|rectangle/i.test(kind) && !/badge/i.test(kind);
        const w = g.width ?? g.w ?? 0;
        const hasPaint = Boolean(g.fill || g.src || g.imageHash || (g.fills && g.fills.length));
        if (isImg && w > 80 && !hasPaint) emptyShots += 1;
        if (/^(Hover States|States \+ hover|Button|Text link|Pill|Social icon)$/i.test(g.name || "")) {
          const count = g.childCount ?? 0;
          if (count > 0 || /^(Button|Text link|Pill|Social icon)$/i.test(g.name || "")) hasHoverStates = true;
          if (g.name === "Hover States" || g.name === "States + hover") {
            try {
              const inner = payload(await call("get_children", { nodeId: g.id })).children || [];
              if (inner.length) hasHoverStates = true;
            } catch { /* name is enough if childCount set */ }
            if ((g.childCount || 0) > 0) hasHoverStates = true;
          }
        }
      }
      if (/^\d{2} · /.test(row.name || "")) {
        sections.push({
          id: row.id,
          name: row.name,
          childCount: kids.length,
          sourceRow: true,
          hasHoverStates,
          hoverNames: kids.map((g) => g.name),
        });
      }
    }
    sections.push({
      id: sb.id,
      name: sb.name,
      childCount: rows.length,
      w: sb.width ?? sb.w,
      h: sb.height ?? sb.h,
      blankSource: emptyShots > 0 || rows.length === 0,
      emptyShots,
    });
  }
  return sections;
}
