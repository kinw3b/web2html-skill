#!/usr/bin/env node
// 1.4 post-seed check: each 1600 / 768 / 390 source-section clip vs that
// named Paper band. Repair is rebind, never write_html. Pitfall #156.

import {
  existsSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  captureFontFaces,
  captureHtmlPath,
  colorSeedVerdict,
  fontSeedVerdict,
  layoutSeedVerdict,
  pngSize,
  saturatedPalette,
  seedExitCode,
} from "./library-seed-compare.mjs";
import {
  listSourceShots,
  matchPaperSection,
  placementVerdict,
  screenshotPaperSection,
  whiteRatio,
} from "./source-shot-compare.mjs";

export const SEED_LANDERS = [
  { key: "desktop", lander: "home-desktop", dir: "home-desktop" },
  { key: "768", lander: "home-768", dir: "home-768" },
  { key: "390", lander: "home-390", dir: "home-390" },
];

function payload(result) {
  for (const item of result?.content || []) {
    if (item.type !== "text") continue;
    try { return JSON.parse(item.text); } catch { return { text: item.text }; }
  }
  return {};
}

function requiredArg(argv, name) {
  const i = argv.indexOf(`--${name}`);
  const value = i >= 0 ? argv[i + 1] : "";
  if (!value || value.startsWith("--")) {
    throw new Error(`validate-library-seed.mjs requires --${name}`);
  }
  return value;
}

function optionalArg(argv, name, fallback = "") {
  const i = argv.indexOf(`--${name}`);
  const value = i >= 0 ? argv[i + 1] : "";
  if (!value || value.startsWith("--")) return fallback;
  return value;
}

function fail({ kind, symptom, retryable, section = null, node = null }) {
  return { kind, symptom, retryable, section, node };
}

export async function collectPaperFaces(call, fileId, rootId, { depth = 4, cap = 48 } = {}) {
  const faces = new Set();
  if (!rootId) return [];
  const ids = [rootId];
  let frontier = [rootId];
  for (let d = 0; d < depth && ids.length < cap; d++) {
    const next = [];
    for (const pid of frontier) {
      const kids = payload(await call("get_children", { nodeId: pid, fileId })).children || [];
      for (const k of kids) {
        ids.push(k.id);
        next.push(k.id);
        if (ids.length >= cap) break;
      }
      if (ids.length >= cap) break;
    }
    frontier = next;
  }
  try {
    const styles = payload(await call("get_computed_styles", { fileId, nodeIds: ids })).styles || {};
    for (const st of Object.values(styles)) {
      const raw = st?.fontFamily;
      if (!raw) continue;
      const first = String(raw).split(",")[0].replace(/["']/g, "").trim();
      if (first) faces.add(first);
    }
  } catch { /* font check is skip-if-unread */ }
  return [...faces];
}

async function landerSections(call, fileId, info, landerName) {
  const board = (info.artboards || []).find((a) => a.name === landerName)
    || (info.artboards || []).find((a) => new RegExp(landerName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i").test(String(a?.name || "")));
  if (!board) return { board: null, sections: [] };
  const kids = payload(await call("get_children", { nodeId: board.id, fileId })).children || [];
  const sections = kids.map((k) => ({
    id: k.id,
    name: k.name,
    childCount: k.childCount,
    w: k.width ?? k.w,
    h: k.height ?? k.h,
    worldY: k.worldY ?? k.y,
    y: k.y ?? k.worldY,
    position: k.position,
    top: k.top,
  }));
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
  } catch { /* names are enough to pair */ }
  for (const s of sections) {
    if (s.childCount == null) {
      const inner = payload(await call("get_children", { nodeId: s.id, fileId })).children || [];
      s.childCount = inner.length;
    }
  }
  return { board, sections };
}

export async function validateLibrarySeed({
  projectRoot,
  fileId,
  expectFile = "",
  paperCall,
  screenshot = screenshotPaperSection,
  log = console.error,
  scale = 1,
} = {}) {
  const root = resolve(projectRoot);
  const jsonOut = join(root, "qa", "library-seed-qa.json");
  const failures = [];
  const sectionsOut = [];
  const info = payload(await paperCall("get_basic_info", { fileId }));

  if (expectFile && info?.fileName && !String(info.fileName).includes(expectFile)) {
    failures.push(fail({
      kind: "wrong-file",
      symptom: `Active file is "${info.fileName}" but --expect-file "${expectFile}" was required`,
      retryable: false,
    }));
  }

  for (const lander of SEED_LANDERS) {
    const captureDir = join(root, "capture", lander.dir);
    const shotDir = join(captureDir, "source-sections");
    const shots = listSourceShots(shotDir);
    if (!shots.length) {
      failures.push(fail({
        kind: "missing-source-sections",
        symptom: `capture/${lander.dir}/source-sections has no NN-*.png clips`,
        retryable: false,
        section: lander.lander,
      }));
      continue;
    }

    const { board, sections } = await landerSections(paperCall, fileId, info, lander.lander);
    if (!board) {
      failures.push(fail({
        kind: "missing-lander",
        symptom: `${lander.lander} is missing after the Design Library seed`,
        retryable: false,
        section: lander.lander,
      }));
      continue;
    }

    for (const hit of placementVerdict(sections)) {
      failures.push(fail({
        kind: "layout-shift",
        symptom: `${lander.key}: ${hit.symptom}`,
        retryable: true,
        section: hit.section,
        node: hit.node,
      }));
    }

    const outDir = join(root, "qa", "library-seed", lander.key);
    mkdirSync(outDir, { recursive: true });
    for (const shot of shots) {
      const paper = matchPaperSection(shot, sections);
      if (!paper) {
        failures.push(fail({
          kind: "unmatched-section",
          symptom: `no ${lander.lander} ${shot.id} · band for ${shot.name}`,
          retryable: false,
          section: shot.name,
        }));
        sectionsOut.push({ lander: lander.key, shot: shot.name, paper: null, ok: false });
        continue;
      }

      log(`[1.4] seed ${lander.key} ${shot.name} ↔ ${paper.name}`);
      const paperPng = join(outDir, `${shot.id}-${shot.slug}-paper.png`);
      const shotPath = await screenshot({
        call: paperCall,
        fileId,
        nodeId: paper.id,
        outPath: paperPng,
        scale,
      });
      if (!shotPath || !existsSync(shotPath)) {
        failures.push(fail({
          kind: "color-shift",
          symptom: `could not screenshot ${lander.lander} ${paper.name}`,
          retryable: true,
          section: paper.name,
          node: paper.id,
        }));
        sectionsOut.push({ lander: lander.key, shot: shot.name, paper: paper.name, node: paper.id, ok: false });
        continue;
      }

      const htmlPath = captureHtmlPath(captureDir, shot);
      const captureFaces = htmlPath && existsSync(htmlPath)
        ? captureFontFaces(readFileSync(htmlPath, "utf8"))
        : [];
      const paperFaces = await collectPaperFaces(paperCall, fileId, paper.id);
      const sourcePalette = saturatedPalette(shot.file);
      const paperPalette = saturatedPalette(shotPath);
      const sourceSize = pngSize(shot.file);
      const paperSize = pngSize(shotPath);
      const verdict = colorSeedVerdict(sourcePalette, paperPalette)
        || fontSeedVerdict({ captureFaces, paperFaces })
        || layoutSeedVerdict({
          sourceWhite: whiteRatio(shot.file),
          paperWhite: whiteRatio(shotPath),
          paperChildCount: paper.childCount,
          sourceH: sourceSize?.height,
          paperH: paperSize?.height,
        });

      const row = {
        lander: lander.key,
        shot: shot.name,
        paper: paper.name,
        node: paper.id,
        captureFaces,
        paperFaces,
        sourcePalette,
        paperPalette,
        ok: !verdict,
        verdict,
      };
      sectionsOut.push(row);
      if (verdict) {
        failures.push(fail({
          kind: verdict.kind,
          symptom: `${lander.lander} ${paper.name}: ${verdict.symptom}`,
          retryable: verdict.kind !== "color-spill",
          section: paper.name,
          node: paper.id,
        }));
      }
    }
  }

  const retryable = failures.length > 0 && failures.every((f) => f.retryable !== false);
  const report = {
    ok: failures.length === 0,
    retryable: failures.length === 0 ? true : retryable,
    failures,
    sections: sectionsOut,
  };
  mkdirSync(dirname(jsonOut), { recursive: true });
  writeFileSync(jsonOut, JSON.stringify(report, null, 2), "utf8");
  return report;
}

const invoked = process.argv[1]
  && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(resolve(process.argv[1]));

if (invoked) {
  try {
    const argv = process.argv.slice(2);
    const projectRoot = requiredArg(argv, "project");
    const fileId = requiredArg(argv, "file-id");
    const expectFile = optionalArg(argv, "expect-file");
    const { call, setFileId } = await import("./mcp-client.mjs");
    setFileId(fileId);
    const report = await validateLibrarySeed({
      projectRoot,
      fileId,
      expectFile,
      paperCall: call,
    });
    const jsonOut = optionalArg(argv, "json");
    if (jsonOut) {
      mkdirSync(dirname(resolve(jsonOut)), { recursive: true });
      writeFileSync(resolve(jsonOut), JSON.stringify(report, null, 2), "utf8");
    }
    console.log(JSON.stringify({ ok: report.ok, retryable: report.retryable, failures: report.failures }, null, 2));
    process.exitCode = seedExitCode(report);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 2;
  }
}
