// Pair capture/home-{desktop,768,390}/source-sections/NN-*.png with Paper
// section screenshots. White-ratio is how we notice a blank Paper frame that
// the live clip still has content in — the reason those shots exist.

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";

export function listSourceShots(sourceDir) {
  const abs = resolve(sourceDir);
  if (!existsSync(abs)) return [];
  return readdirSync(abs)
    .filter((f) => /^\d{2}-.+\.png$/i.test(f))
    .sort()
    .map((f) => {
      const m = f.match(/^(\d{2})-(.+)\.png$/i);
      return {
        file: join(abs, f),
        id: m?.[1] || "",
        slug: (m?.[2] || "").toLowerCase(),
        name: f,
      };
    });
}

export function whiteRatio(pngPath) {
  if (!pngPath || !existsSync(pngPath)) return null;
  const py = `
from PIL import Image
im = Image.open(${JSON.stringify(pngPath)}).convert("RGB")
im.thumbnail((240, 240))
px = list(im.getdata())
n = len(px) or 1
white = sum(1 for r,g,b in px if r > 248 and g > 248 and b > 248)
print(f"{white/n:.4f}")
`;
  try {
    const out = execFileSync("python3", ["-c", py], { encoding: "utf8" }).trim();
    const n = Number(out);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

export function matchPaperSection(shot, paperSections = []) {
  const slug = shot.slug.replace(/-/g, " ");
  return paperSections.find((s) => {
    const name = String(s.name || "").toLowerCase();
    if (name.startsWith(`${shot.id} ·`) || name.startsWith(`${shot.id}·`)) return true;
    if (name.includes(shot.slug)) return true;
    if (name.includes(slug)) return true;
    return false;
  }) || null;
}

export async function screenshotPaperSection({ call, fileId, nodeId, outPath, scale = 0.4 }) {
  mkdirSync(resolve(outPath, ".."), { recursive: true });
  const result = await call("get_screenshot", {
    ...(fileId ? { fileId } : {}),
    nodeId,
    scale,
  });
  for (const c of result.content || []) {
    if (c.type === "image" && c.data) {
      writeFileSync(outPath, Buffer.from(c.data, "base64"));
      return outPath;
    }
  }
  return null;
}

export function namedIndex(name) {
  const m = String(name || "").match(/^\s*(\d{2})\s*·/);
  return m ? Number(m[1]) : null;
}

export function sectionY(s) {
  const y = s.worldY ?? s.y;
  return Number.isFinite(y) ? y : null;
}

export function leftoverTopPx(s) {
  const raw = s.top ?? s.styleTop;
  if (raw == null || raw === "" || raw === "auto") return 0;
  const n = typeof raw === "number" ? raw : parseFloat(String(raw));
  return Number.isFinite(n) ? n : 0;
}

/** Named NN · layers must stack in name order with no leftover relative top
 *  and no gap larger than ~1 section. childCount > 0 is not a pass —
 *  prior-run 05 kept 2 kids and a leftover top:3252px below the footer. */
export function placementVerdict(sections = [], { gapFactor = 1.15, minGap = 400 } = {}) {
  const named = (sections || [])
    .filter((s) => !s.sourceRow && namedIndex(s.name) != null)
    .filter((s) => s.position !== "absolute" && s.position !== "fixed")
    .map((s) => ({
      ...s,
      index: namedIndex(s.name),
      y: sectionY(s),
      leftover: leftoverTopPx(s),
    }));
  const findings = [];
  for (const s of named) {
    if (s.leftover > 80) {
      findings.push({
        kind: "displaced-section",
        section: s.name,
        node: s.id || null,
        symptom: `leftover top ${Math.round(s.leftover)}px (children ${s.childCount ?? "?"})`,
        evidence: `position ${s.position || "relative"}; top ${s.leftover}`,
        auto: "restack-tops",
        leftover: s.leftover,
      });
    }
  }
  const byName = [...named].sort((a, b) => a.index - b.index || String(a.name).localeCompare(b.name));
  const byY = [...named].filter((s) => s.y != null).sort((a, b) => a.y - b.y);
  if (byY.length >= 2) {
    const nameOrder = byName.map((s) => s.id || s.name).join("|");
    const yOrder = byY.map((s) => s.id || s.name).join("|");
    if (nameOrder !== yOrder) {
      const last = byY[byY.length - 1];
      findings.push({
        kind: "displaced-section",
        section: last.name,
        node: last.id || null,
        symptom: `named order ${byName.map((s) => s.name).join(" → ")} vs y order ${byY.map((s) => s.name).join(" → ")}`,
        evidence: "monotonic y vs NN · name",
        auto: "restack-tops",
      });
    }
    for (let i = 1; i < byY.length; i++) {
      const prev = byY[i - 1];
      const cur = byY[i];
      const h = prev.h;
      if (h == null || !Number.isFinite(h) || h <= 0) continue;
      const gap = Math.round(cur.y - (prev.y + h));
      const limit = Math.max(minGap, h * gapFactor);
      if (gap > limit) {
        findings.push({
          kind: "displaced-section",
          section: cur.name,
          node: cur.id || null,
          symptom: `${gap}px hole after ${prev.name} (limit ${Math.round(limit)}px)`,
          evidence: `${prev.name} y=${Math.round(prev.y)} h=${Math.round(h)} → ${cur.name} y=${Math.round(cur.y)}`,
          auto: "restack-tops",
          gap,
        });
      }
    }
  }
  return findings;
}

export function shotVerdict({ sourceWhite, paperWhite, paperChildCount }) {
  // Children do not prove placement. Empty-frame still needs childCount 0.
  // White-ratio can still fire when the isolated shot is a hole.
  if ((paperChildCount ?? 1) === 0 && sourceWhite != null && sourceWhite < 0.75) {
    return { kind: "empty-named-section", symptom: "Paper frame is empty; source clip has content" };
  }
  if (paperWhite != null && sourceWhite != null && paperWhite > 0.82 && sourceWhite < 0.55) {
    return { kind: "shot-mismatch", symptom: `Paper is ${(paperWhite * 100).toFixed(0)}% white vs source ${(sourceWhite * 100).toFixed(0)}%` };
  }
  return null;
}

export function boardShotVerdict({ sourceWhite, paperWhite }) {
  if (paperWhite != null && sourceWhite != null && paperWhite > 0.72 && sourceWhite < 0.50) {
    return {
      kind: "displaced-section",
      symptom: `home-desktop stack is ${(paperWhite * 100).toFixed(0)}% white vs fullpage ${(sourceWhite * 100).toFixed(0)}%`,
    };
  }
  return null;
}

export function dataImageSrc(absPath, { jpeg = true } = {}) {
  const abs = resolve(absPath);
  if (!existsSync(abs)) return "";
  if (jpeg) {
    try {
      const out = join("/tmp", `me-shot-${basename(abs).replace(/\W+/g, "-")}.jpg`);
      execFileSync("sips", ["-s", "format", "jpeg", "-s", "formatOptions", "72", abs, "--out", out]);
      if (existsSync(out)) {
        return `data:image/jpeg;base64,${readFileSync(out).toString("base64")}`;
      }
    } catch { /* png fallback */ }
  }
  const buf = readFileSync(abs);
  const mime = buf[0] === 0xff ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${buf.toString("base64")}`;
}
