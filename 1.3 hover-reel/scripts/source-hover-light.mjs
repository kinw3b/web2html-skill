#!/usr/bin/env node
// 3.2 fast-run light pass — source CSS :hover → qa/button-hover.json, WITHOUT 1.3.
//
// A fast run skips 1.3 (no Design Library, no FRAME Buttons pull), so there is no
// qa/buttons-components-pull.json to feed author-button-hover.mjs. This script
// takes the CTA list from the authored page instead (rebuild/index-polish.html,
// falling back to rebuild/index.html), matches each control by label onto the
// source markup, and mines the same source CSS :hover paint with the same
// parser 1.3 uses (source-button-hover.mjs). The receipt has the exact shape
// apply-hover-css.py already reads. Nothing is written to Paper.
//
//   node source-hover-light.mjs --project /path/to/project
//
// Never invents a hover: a control with no source :hover paint is skipped with
// a reason, exactly like 1.3 (Pitfall #33).

import { mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  cssHoverRecipes,
  extractControls,
  loadSourceCss,
} from "./source-button-hover.mjs";

// Same writer string as 1.3 so apply-hover-css.py + verify-polish-passes.py accept it.
export const WRITER = "author-button-hover.mjs";
export const LIGHT_WRITER = "source-hover-light.mjs";

function readJson(path, fallback = null) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function readText(path) {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return "";
  }
}

function pageUrlOf(root) {
  const pages = readJson(join(root, "source-site", "pages.json"), []);
  if (Array.isArray(pages) && pages[0]?.url) return pages[0].url;
  const paper = readJson(join(root, "qa", "paper-file.json"), {});
  return paper.url || paper.sourceUrl || "";
}

const CTA_CLASS_RE = /\b(btn|button|cta|pill)\b|^btn-/i;

/** CTAs on the authored page: <a>/<button> with a button-ish class or a short label. */
export function shipButtons(html = "") {
  const out = [];
  const seen = new Set();
  for (const control of extractControls(html)) {
    const text = String(control.text || "").trim();
    if (!text || text.length > 48) continue;
    const looksButton = control.tag === "button" || control.classes.some((cls) => CTA_CLASS_RE.test(cls));
    if (!looksButton) continue;
    const key = text.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      label: text,
      sectionId: "",
      sectionName: "",
      shipClasses: control.classes,
    });
  }
  return out;
}

export async function authorHoverLight({
  projectRoot,
  now = () => new Date().toISOString(),
  log = console.error,
  fetchImpl = globalThis.fetch,
} = {}) {
  const root = resolve(projectRoot);
  const shipPath = ["index-polish.html", "index.html"]
    .map((name) => join(root, "rebuild", name))
    .find((path) => readText(path));
  const shipHtml = shipPath ? readText(shipPath) : "";
  const buttons = shipButtons(shipHtml);
  const sourceHtml = readText(join(root, "source-site", "index.html"));
  const pageUrl = pageUrlOf(root);
  const css = sourceHtml ? await loadSourceCss(sourceHtml, pageUrl, { fetchImpl, log, root }) : "";
  const recipes = cssHoverRecipes({ html: sourceHtml, css, buttons });
  const receipt = {
    ok: true,
    writer: WRITER,
    lightPass: LIGHT_WRITER,
    completedAt: now(),
    fileId: "",
    source: sourceHtml ? "source-site/index.html" : "missing",
    ship: shipPath ? shipPath.slice(root.length + 1) : "missing",
    pageUrl,
    controlCount: recipes.controlCount,
    ruleCount: recipes.ruleCount,
    shipButtonCount: buttons.length,
    applied: recipes.applied.map((row) => ({ ...row, parked: false, hoverNodeId: "" })),
    skipped: recipes.skipped,
  };
  const dest = join(root, "qa", "button-hover.json");
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, `${JSON.stringify(receipt, null, 2)}\n`, "utf8");
  log(`3.2 light hover ${receipt.applied.length} applied · ${receipt.skipped.length} skipped (no 1.3)`);
  return receipt;
}

const invoked = process.argv[1]
  && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(resolve(process.argv[1]));

if (invoked) {
  try {
    const argv = process.argv.slice(2);
    const i = argv.indexOf("--project");
    const projectRoot = i >= 0 ? argv[i + 1] : "";
    if (!projectRoot || projectRoot.startsWith("--")) throw new Error("source-hover-light.mjs requires --project");
    const receipt = await authorHoverLight({ projectRoot });
    console.log(JSON.stringify(receipt, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
