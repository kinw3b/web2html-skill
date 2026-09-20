// 1.4 post-seed check: each source-section clip vs that named Paper band.
// Catches token-bind wash, invented fill spill, system-font fallback, and exploded/collapsed frames.
// Does not replace 1.5 (human missing-elements). Pitfall #156.

import { execFileSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { shotVerdict } from "./source-shot-compare.mjs";

export const LIBRARY_SEED_MAX_PASSES = 3;

export function captureFontFaces(html) {
  const faces = new Set();
  for (const match of String(html || "").matchAll(/font-family:\s*([^;"']+)/gi)) {
    const first = match[1].split(",")[0].replace(/["']/g, "").trim();
    if (!first) continue;
    const base = first.replace(/-(Bold|Medium|Regular|Light|SemiBold|Black)$/i, "");
    if (/^(sans-serif|serif|monospace|system-ui|ui-sans-serif|system sans-serif)$/i.test(base)) continue;
    faces.add(base);
  }
  return [...faces];
}

export function isSystemFace(value) {
  return /system/i.test(String(value || ""));
}

export function fontSeedVerdict({ captureFaces = [], paperFaces = [] } = {}) {
  const captureConcrete = (captureFaces || []).filter((face) => !isSystemFace(face));
  const paperConcrete = (paperFaces || []).filter((face) => !isSystemFace(face));
  if (captureConcrete.length && paperFaces.length && !paperConcrete.length) {
    return {
      kind: "font-shift",
      symptom: `Paper fell back to a system face after seed (capture had ${captureConcrete.slice(0, 3).join(", ")})`,
    };
  }
  return null;
}

function pythonJson(pngPath, script) {
  if (!pngPath || !existsSync(pngPath)) return null;
  try {
    const out = execFileSync("python3", ["-c", script], { encoding: "utf8" }).trim();
    return JSON.parse(out);
  } catch {
    return null;
  }
}

export function pngSize(pngPath) {
  return pythonJson(pngPath, `
from PIL import Image
import json
im = Image.open(${JSON.stringify(pngPath)})
print(json.dumps({"width": im.width, "height": im.height}))
`);
}

/** Downsampled saturated-pixel stats. Screenshots are flattened RGB. */
export function saturatedPalette(pngPath) {
  return pythonJson(pngPath, `
from PIL import Image
import json
im = Image.open(${JSON.stringify(pngPath)}).convert("RGB")
im.thumbnail((180, 180))
px = list(im.getdata())
n = len(px) or 1

def sat(p):
    mx = max(p); mn = min(p)
    return 0 if mx == 0 else (mx - mn) / mx

sats = [sat(p) for p in px]
mean_sat = sum(sats) / n
hot = [p for p, s in zip(px, sats) if s >= 0.35]
if hot:
    sr = sum(p[0] for p in hot) / len(hot)
    sg = sum(p[1] for p in hot) / len(hot)
    sb = sum(p[2] for p in hot) / len(hot)
    saturated_mean = {"r": round(sr), "g": round(sg), "b": round(sb)}
    coverage = len(hot) / n
else:
    saturated_mean = None
    coverage = 0
print(json.dumps({
    "meanSat": round(mean_sat, 4),
    "coverage": round(coverage, 4),
    "saturatedMean": saturated_mean,
}))
`);
}

function colorDistRgb(a, b) {
  if (!a || !b) return Infinity;
  return Math.abs(a.r - b.r) + Math.abs(a.g - b.g) + Math.abs(a.b - b.b);
}

export function colorSeedVerdict(sourcePalette, paperPalette) {
  if (!sourcePalette || !paperPalette) {
    return { kind: "color-shift", symptom: "could not read section palettes" };
  }
  if (
    sourcePalette.meanSat >= 0.28
    && paperPalette.meanSat < Math.max(0.12, sourcePalette.meanSat * 0.45)
  ) {
    return {
      kind: "color-wash",
      symptom: `Paper saturation ${paperPalette.meanSat} vs source ${sourcePalette.meanSat}`,
    };
  }
  const sourceCov = sourcePalette.coverage ?? 0;
  const paperCov = paperPalette.coverage ?? 0;
  if (
    sourcePalette.meanSat < 0.16
    && paperPalette.meanSat >= 0.28
    && paperCov >= 0.18
    && paperCov >= sourceCov + 0.12
  ) {
    return {
      kind: "color-spill",
      symptom: `Paper gained saturated fill coverage ${paperCov} vs source ${sourceCov}`,
    };
  }
  if (
    sourcePalette.saturatedMean
    && paperPalette.saturatedMean
    && sourcePalette.meanSat >= 0.28
  ) {
    const dist = colorDistRgb(sourcePalette.saturatedMean, paperPalette.saturatedMean);
    if (dist > 90) {
      return {
        kind: "color-shift",
        symptom: `saturated mean dist ${dist}`,
      };
    }
  }
  return null;
}

export function layoutSeedVerdict({
  sourceWhite,
  paperWhite,
  paperChildCount,
  sourceH,
  paperH,
} = {}) {
  const hole = shotVerdict({ sourceWhite, paperWhite, paperChildCount });
  if (hole) {
    return { kind: "layout-shift", symptom: hole.symptom };
  }
  if (sourceH && paperH) {
    const ratio = paperH / sourceH;
    if (ratio < 0.5 || ratio > 2.5) {
      return {
        kind: "layout-shift",
        symptom: `height ratio ${ratio.toFixed(2)} (Paper ${Math.round(paperH)} vs source ${Math.round(sourceH)})`,
      };
    }
  }
  return null;
}

export function sectionSeedVerdict(input = {}) {
  return colorSeedVerdict(input.sourcePalette, input.paperPalette)
    || fontSeedVerdict(input)
    || layoutSeedVerdict(input)
    || null;
}

export function seedReportOk(report) {
  return Boolean(report?.ok) && !(report?.failures || []).length;
}

export function seedExitCode(report) {
  if (seedReportOk(report)) return 0;
  if (report?.retryable === false) return 2;
  return 1;
}

export function captureHtmlPath(captureDir, shot) {
  if (!captureDir || !shot?.id || !existsSync(captureDir)) return null;
  const files = readdirSync(captureDir).filter((f) => /^\d{2}-.+\.html$/i.test(f));
  const hit = files.find((f) => f.startsWith(`${shot.id}-`));
  return hit ? join(captureDir, hit) : null;
}
