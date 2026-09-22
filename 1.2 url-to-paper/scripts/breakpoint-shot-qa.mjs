#!/usr/bin/env node
// 1.2 self-validate: agent-authored home-768 / home-390 vs disk screenshots.
//
// Gold is capture/home-{768,390}/source-sections (and fullpage.png when
// present). Paper frames are authored from desktop — they are not live
// assembles. One pass. Fail if either frame is missing or a paired band
// is blank against a contentful clip.
//
//   node breakpoint-shot-qa.mjs --project /path/to/project --file-id <id>

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  listSourceShots,
  matchPaperSection,
  screenshotPaperSection,
  shotVerdict,
  whiteRatio,
} from "./source-shot-compare.mjs";
import { call, setFileId } from "./mcp-client.mjs";
import { mcpPayload } from "./write-paper-section.mjs";
import { landerFolderForWidth, sourceSectionsDirForWidth } from "./source-sections.mjs";
import { runWidths } from "./run-config.mjs";

export const BREAKPOINT_WIDTHS = [768, 390];

/** Sub-desktop widths this run captures (qa/run-config.json; fast = [390]). */
export function breakpointWidthsFor(projectRoot) {
  const list = runWidths(projectRoot).filter((w) => w < 1400);
  return list.length ? list : [...BREAKPOINT_WIDTHS];
}

export function requiredAuthoredFrames(boards = [], pageSlug = "home", widths = BREAKPOINT_WIDTHS) {
  const need = widths.map((w) => `${pageSlug}-${w}`);
  const have = new Set((boards || []).map((b) => b.name));
  const missing = need.filter((n) => !have.has(n));
  return { ok: missing.length === 0, missing, need };
}

export function summarizeShotQa(rows = []) {
  const failures = (rows || []).filter((r) => r.verdict);
  return {
    ok: failures.length === 0,
    failures,
    compared: rows.length,
    rows,
  };
}

export function breakpointShotQaDone(report = {}, widths = BREAKPOINT_WIDTHS) {
  return report?.ok === true
    && Array.isArray(report.frames)
    && report.frames.length >= widths.length
    && !(report.missingFrames || []).length;
}

function kidsOf(payload = {}) {
  return payload.children || payload.nodes || [];
}

async function qaOneWidth({
  call: mcp,
  fileId,
  projectRoot,
  pageSlug,
  width,
  board,
  outDir,
  log = console.error,
}) {
  const captureDir = join(projectRoot, "capture", landerFolderForWidth(pageSlug, width));
  const shotDir = sourceSectionsDirForWidth(join(projectRoot, "capture"), pageSlug, width);
  const shots = listSourceShots(shotDir);
  const rows = [];
  if (!shots.length) {
    rows.push({
      width,
      section: "(none)",
      verdict: { kind: "missing-source-shots", symptom: `no NN-*.png in ${shotDir}` },
    });
    return { width, board: board?.name, rows };
  }
  const paperKids = board?.id
    ? kidsOf(mcpPayload(await mcp("get_children", { nodeId: board.id, fileId })))
    : [];
  for (const shot of shots) {
    const section = matchPaperSection(shot, paperKids);
    const paperPath = join(outDir, `${width}-${shot.name}`);
    let paperWhite = null;
    if (section?.id) {
      await screenshotPaperSection({
        call: mcp, fileId, nodeId: section.id, outPath: paperPath, scale: 0.35,
      });
      paperWhite = whiteRatio(paperPath);
    }
    const sourceWhite = whiteRatio(shot.file);
    const verdict = !section
      ? { kind: "unmatched-shot", symptom: `no Paper band for ${shot.name}` }
      : shotVerdict({
        sourceWhite,
        paperWhite,
        paperChildCount: section.childCount,
      });
    rows.push({
      width,
      shot: shot.name,
      section: section?.name || null,
      node: section?.id || null,
      sourceWhite,
      paperWhite,
      verdict,
    });
  }
  const fullpage = join(captureDir, "fullpage.png");
  if (existsSync(fullpage) && board?.id) {
    const boardShot = join(outDir, `${width}-artboard.png`);
    await screenshotPaperSection({
      call: mcp, fileId, nodeId: board.id, outPath: boardShot, scale: 0.25,
    });
    const sourceWhite = whiteRatio(fullpage);
    const paperWhite = whiteRatio(boardShot);
    if (paperWhite != null && sourceWhite != null && paperWhite > 0.82 && sourceWhite < 0.55) {
      rows.push({
        width,
        shot: "fullpage.png",
        section: board.name,
        node: board.id,
        sourceWhite,
        paperWhite,
        verdict: {
          kind: "shot-mismatch",
          symptom: `${board.name} is ${(paperWhite * 100).toFixed(0)}% white vs fullpage ${(sourceWhite * 100).toFixed(0)}%`,
        },
      });
    }
  }
  log(`  ${width}: ${rows.filter((r) => r.verdict).length} miss(es) / ${rows.length} clip(s)`);
  return { width, board: board?.name, id: board?.id, rows };
}

export async function runBreakpointShotQa({
  projectRoot,
  fileId,
  pageSlug = "home",
  log = console.error,
} = {}) {
  const root = resolve(projectRoot || ".");
  if (fileId) setFileId(fileId);
  const info = mcpPayload(await call("get_basic_info", { ...(fileId ? { fileId } : {}) }));
  const boards = info.artboards || [];
  const widths = breakpointWidthsFor(root);
  const frames = requiredAuthoredFrames(boards, pageSlug, widths);
  const qaDir = join(root, "qa");
  const shotOut = join(qaDir, "breakpoint-shot-qa");
  mkdirSync(shotOut, { recursive: true });
  const rows = [];
  const frameReports = [];
  if (!frames.ok) {
    const report = {
      generatedFrom: "url-to-paper/breakpoint-shot-qa",
      writtenAt: new Date().toISOString(),
      ok: false,
      missingFrames: frames.missing,
      frames: [],
      failures: frames.missing.map((name) => ({
        kind: "missing-authored-frame",
        symptom: `${name} is not on Paper — author it from home-desktop, then rerun`,
      })),
      compared: 0,
    };
    writeFileSync(join(qaDir, "breakpoint-shot-qa.json"), `${JSON.stringify(report, null, 2)}\n`);
    log(`breakpoint-shot-qa FAIL — missing ${frames.missing.join(", ")}`);
    return report;
  }
  for (const width of widths) {
    const name = `${pageSlug}-${width}`;
    const board = boards.find((b) => b.name === name);
    const one = await qaOneWidth({
      call, fileId, projectRoot: root, pageSlug, width, board, outDir: shotOut, log,
    });
    frameReports.push({ width, name, id: board.id });
    rows.push(...one.rows);
  }
  const summary = summarizeShotQa(rows);
  const report = {
    generatedFrom: "url-to-paper/breakpoint-shot-qa",
    writtenAt: new Date().toISOString(),
    ok: summary.ok,
    missingFrames: [],
    frames: frameReports,
    compared: summary.compared,
    failures: summary.failures,
    rows,
  };
  writeFileSync(join(qaDir, "breakpoint-shot-qa.json"), `${JSON.stringify(report, null, 2)}\n`);
  log(`breakpoint-shot-qa ${report.ok ? "ok" : "FAIL"} · ${report.compared} clip(s)`);
  return report;
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const argv = process.argv.slice(2);
  const arg = (name) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 ? argv[i + 1] : "";
  };
  const projectRoot = resolve(arg("project") || ".");
  const fileId = arg("file-id") || process.env.PAPER_FILE_ID;
  if (!fileId) {
    console.error("breakpoint-shot-qa: --file-id is required");
    process.exit(1);
  }
  const report = await runBreakpointShotQa({
    projectRoot,
    fileId,
    pageSlug: arg("page") || "home",
    log: console.error,
  });
  if (!report.ok) process.exit(2);
}
