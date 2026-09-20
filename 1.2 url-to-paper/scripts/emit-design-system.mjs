#!/usr/bin/env node
// 2.1 Design System — write rebuild/css/tokens.css + rebuild/design-system.html
// from the signed 1.3 library.json. Script, not the model. Not the ship.
//
//   node emit-design-system.mjs --project /path/to/kp-thrive
//
// Mirror of the Paper Design Library foundations sheet. 2.2 authors
// rebuild/index.html from Paper using these tokens.

import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { renderFoundationsChunks } from "./library-sheet.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

export function tokensCss(proposed = []) {
  const lines = [];
  for (const t of proposed) {
    if (!t || !t.name || t.value == null || t.value === "") continue;
    const value = typeof t.value === "number" ? String(t.value) : String(t.value);
    lines.push(`  ${t.name}: ${value};`);
  }
  return `:root {\n${lines.join("\n")}\n}\n`;
}

export function wrapDesignSystemPage({ site, chunks, fonts = false }) {
  const title = `${site || "Design system"} · Design system`;
  const body = (chunks || []).map((c) => c.html).join("\n");
  const fontsLink = fonts
    ? `  <link rel="stylesheet" href="css/fonts.css" />\n`
    : "";
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(title)}</title>
  <link rel="stylesheet" href="css/tokens.css" />
${fontsLink}  <style>
    html, body { margin: 0; background: var(--color-surface, #fff); color: var(--color-ink, #111); }
    body { font-synthesis: none; -webkit-font-smoothing: antialiased; }
    .ds-sheet {
      box-sizing: border-box;
      width: 1200px;
      max-width: 100%;
      padding: var(--spacing-16, 64px);
      display: flex;
      flex-direction: column;
      gap: var(--spacing-16, 64px);
    }
  </style>
</head>
<body data-page="design-system">
  <main class="ds-sheet">
${body}
  </main>
</body>
</html>
`;
}

function runEmitFonts(root) {
  const candidates = [
    join(__dir, "..", "..", "1.0 - web2html", "scripts", "emit_fonts.py"),
    join(__dir, "..", "..", "web2html", "scripts", "emit_fonts.py"),
  ];
  const script = candidates.find((p) => existsSync(p));
  if (!script) return;
  const result = spawnSync("python3", [script, root], { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error((result.stderr || result.stdout || "emit_fonts.py failed").trim());
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function emitDesignSystem(projectRoot) {
  const root = resolve(projectRoot);
  const libraryPath = join(root, "design-library", "library.json");
  if (!existsSync(libraryPath)) {
    throw new Error(`missing ${libraryPath} — 1.3 Design Library must exist before 2.1`);
  }
  const lib = JSON.parse(readFileSync(libraryPath, "utf8"));
  const proposed = Array.isArray(lib.proposedTokens) ? lib.proposedTokens : [];
  if (!proposed.length) {
    throw new Error("library.json has no proposedTokens");
  }
  const { chunks } = renderFoundationsChunks(lib);
  if (!chunks.length) {
    throw new Error("foundations templates produced no chunks");
  }
  const css = tokensCss(proposed);
  mkdirSync(join(root, "rebuild", "css"), { recursive: true });
  writeFileSync(join(root, "rebuild", "css", "tokens.css"), css, "utf8");
  runEmitFonts(root);
  const fontsPath = join(root, "rebuild", "css", "fonts.css");
  const html = wrapDesignSystemPage({
    site: lib.file || "site",
    chunks,
    fonts: existsSync(fontsPath),
  });
  const cssDir = join(root, "rebuild", "css");
  const qaDir = join(root, "qa");
  mkdirSync(cssDir, { recursive: true });
  mkdirSync(qaDir, { recursive: true });
  const pagePath = join(root, "rebuild", "design-system.html");
  writeFileSync(pagePath, html, "utf8");
  const receipt = {
    generatedFrom: "url-to-paper/emit-design-system",
    ok: true,
    kind: "foundations",
    tokens: proposed.length,
    chunks: chunks.map((c) => c.name),
    page: "rebuild/design-system.html",
    tokensCss: "rebuild/css/tokens.css",
    fontsCss: existsSync(fontsPath) ? "rebuild/css/fonts.css" : null,
    library: "design-library/library.json",
  };
  writeFileSync(join(qaDir, "design-system-21.json"), JSON.stringify(receipt, null, 2) + "\n", "utf8");
  return receipt;
}

const isMain = resolve(process.argv[1] || "") === resolve(fileURLToPath(import.meta.url));
if (isMain) {
  const project = arg("project", process.cwd());
  try {
    const receipt = emitDesignSystem(project);
    console.log(JSON.stringify(receipt, null, 2));
  } catch (err) {
    console.error(`FAIL: ${err.message}`);
    process.exit(1);
  }
}
