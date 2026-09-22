// qa/run-config.json reader — the 2.24.0 intake (source / checkpoints / speed).
// Mirrors 1.0 - web2html/scripts/run_config.py. Never throws: a missing or
// malformed file reads as the full run (1600 / 768 / 390, human checkpoints).

import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

export const GENERATED_FROM = "web2html/run-config/v1";
export const FULL_WIDTHS = [1600, 768, 390];
export const FAST_WIDTHS = [1600, 390];

export function runConfigPath(projectRoot) {
  return join(resolve(projectRoot), "qa", "run-config.json");
}

export function defaultRunConfig() {
  return {
    generatedFrom: GENERATED_FROM,
    source: { kind: "none", path: null, dir: null, indexHtml: null },
    checkpoints: "human",
    speed: "full",
    widths: [...FULL_WIDTHS],
    designLibrary: true,
    designSystem: true,
    rawDump: true,
    recordedAt: null,
  };
}

export function normalizeWidths(raw) {
  const out = [];
  if (Array.isArray(raw)) {
    for (const item of raw) {
      const width = Number.parseInt(item, 10);
      if (Number.isFinite(width) && width > 0 && !out.includes(width)) out.push(width);
    }
  }
  out.sort((a, b) => b - a);
  return out.length ? out : [...FULL_WIDTHS];
}

export function loadRunConfig(projectRoot) {
  const base = defaultRunConfig();
  const path = runConfigPath(projectRoot);
  if (!existsSync(path)) return base;
  let data;
  try {
    data = JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return base;
  }
  if (!data || typeof data !== "object" || data.generatedFrom !== GENERATED_FROM) return base;
  const merged = { ...base, ...data };
  merged.widths = normalizeWidths(merged.widths);
  if (merged.speed === "fast") merged.checkpoints = "auto";
  return merged;
}

/** Configured capture widths for a project (captureRoot's parent is the project). */
export function runWidths(projectRoot) {
  return loadRunConfig(projectRoot).widths;
}

export function isFastRun(projectRoot) {
  return loadRunConfig(projectRoot).speed === "fast";
}

export function widthsLabel(widths) {
  return widths.join(" / ");
}
