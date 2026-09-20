#!/usr/bin/env node
// 1.3 — after pull-desktop-specimens, author FRAME Buttons hover cells from
// source CSS :hover (not Capture Tool). Writes qa/button-hover.json.

import { mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { importSibling } from "./skill-paths.mjs";
import { parkCssHoverOnRow } from "./park-capture-boards.mjs";
import {
  WRITER,
  buttonHoverReceiptOk,
  cssHoverRecipes,
  loadSourceCss,
} from "./source-button-hover.mjs";

export { buttonHoverReceiptOk, WRITER };

function requiredArg(argv, name) {
  const i = argv.indexOf(`--${name}`);
  const value = i >= 0 ? argv[i + 1] : "";
  if (!value || value.startsWith("--")) {
    throw new Error(`author-button-hover.mjs requires --${name}`);
  }
  return value;
}

function readJson(path, fallback = null) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function pageUrlOf(root) {
  const pages = readJson(join(root, "source-site", "pages.json"), []);
  if (Array.isArray(pages) && pages[0]?.url) return pages[0].url;
  const paper = readJson(join(root, "qa", "paper-file.json"), {});
  return paper.url || paper.sourceUrl || "";
}

export async function authorButtonHover({
  call, fileId, projectRoot, pull,
  now = () => new Date().toISOString(),
  log = console.error,
  fetchImpl = globalThis.fetch,
} = {}) {
  const root = resolve(projectRoot);
  const receiptPull = pull || readJson(join(root, "qa", "buttons-components-pull.json"), {});
  const buttons = Array.isArray(receiptPull.buttons) ? receiptPull.buttons : [];
  const htmlPath = join(root, "source-site", "index.html");
  let html = "";
  try {
    html = readFileSync(htmlPath, "utf8");
  } catch {
    html = "";
  }
  const pageUrl = pageUrlOf(root);
  const css = html
    ? await loadSourceCss(html, pageUrl, { fetchImpl, log, root })
    : "";
  const recipes = cssHoverRecipes({ html, css, buttons });
  const applied = [];
  for (const row of recipes.applied) {
    let parked = false;
    let hoverNodeId = "";
    if (call && fileId && row.rowNodeId && row.parkedNodeId && Object.keys(row.paperStyles || {}).length) {
      try {
        const wrote = await parkCssHoverOnRow({
          call, fileId,
          groupId: row.rowNodeId,
          parkedNodeId: row.parkedNodeId,
          styles: row.paperStyles,
          label: row.label,
          log,
        });
        parked = Boolean(wrote.written);
        hoverNodeId = wrote.hoverNodeId || "";
      } catch (error) {
        log(`hover park skipped ${row.label}: ${error.message || error}`);
      }
    }
    applied.push({ ...row, parked, hoverNodeId });
  }

  const receipt = {
    ok: true,
    writer: WRITER,
    completedAt: now(),
    fileId: fileId || receiptPull.fileId || "",
    source: html ? "source-site/index.html" : "missing",
    pageUrl,
    controlCount: recipes.controlCount,
    ruleCount: recipes.ruleCount,
    applied,
    skipped: recipes.skipped,
  };
  const dest = join(root, "qa", "button-hover.json");
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, `${JSON.stringify(receipt, null, 2)}\n`, "utf8");
  log(`1.3 button hover ${applied.length} applied · ${recipes.skipped.length} skipped`);
  return receipt;
}

const invoked = process.argv[1]
  && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(resolve(process.argv[1]));

if (invoked) {
  try {
    const argv = process.argv.slice(2);
    const projectRoot = requiredArg(argv, "project");
    const fileId = argv.includes("--file-id") ? requiredArg(argv, "file-id") : "";
    let call;
    if (fileId) {
      const mcp = await importSibling("url-to-paper", "scripts/mcp-client.mjs");
      mcp.setFileId(fileId);
      call = mcp.call;
    }
    const receipt = await authorButtonHover({ call, fileId, projectRoot });
    console.log(JSON.stringify(receipt, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
