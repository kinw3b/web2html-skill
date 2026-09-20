// 1.2 compact chrome → FRAME Navigation (relative), then onto home-desktop
// only when that lander has no navbar. Never the live page/hero shell
// (#110 #168).
//
//   node park-12-chrome.mjs --project /path/to/project --file-id <id>
//
// Reads each viewport's 00-header.html + 00-nav.html, then writes three real
// captures to Navigation: 01 · nav-1600, 02 · nav-768, 03 · nav-390.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { importSibling } from "./skill-paths.mjs";
import { ensureNavigationBoard } from "./park-capture-boards.mjs";

export function chromeHtmlFromCapture(desktopDir) {
  return importSibling("url-to-paper", "scripts/chrome-bars.mjs").then(({
    combineChromeHtml, readChromeFragments,
  }) => {
    const { header, nav } = readChromeFragments(desktopDir);
    return combineChromeHtml(header, nav);
  });
}

export async function park12ChromeOnNavigation({
  call,
  fileId,
  projectRoot,
  captureDirs,
  replace = false,
  log = console.error,
} = {}) {
  if (!call || !fileId) return { written: false, reason: "need call and file" };
  const ready = await ensureNavigationBoard({ call, fileId, log });
  if (!ready.ready) return { written: false, reason: ready.reason };
  const { mcpPayload, writePaperSection } = await importSibling(
    "url-to-paper", "scripts/write-paper-section.mjs",
  );
  const info = mcpPayload(await call("get_basic_info", { fileId }));
  const board = (info.artboards || []).find((item) => item.name === "Navigation");
  if (!board?.id) return { written: 0, reason: "Navigation board missing" };
  const defaults = [
    { width: 1600, label: "01 · nav-1600" },
    { width: 768, label: "02 · nav-768" },
    { width: 390, label: "03 · nav-390" },
  ];
  const dirs = captureDirs || defaults.map(({ width }) => ({
    width, dir: path.join(projectRoot || ".", "capture", `home-${width === 1600 ? "desktop" : width}`),
  }));
  const existing = mcpPayload(await call("get_children", { nodeId: board.id, fileId }));
  const stale = (existing.children || existing.nodes || [])
    .filter((item) => /^0[123] · nav-(1600|768|390)$/i.test(item.name || ""));
  if (stale.length) await call("delete_nodes", { fileId, nodeIds: stale.map((item) => item.id) });
  let written = 0;
  for (const spec of defaults) {
    const capture = dirs.find((item) => Number(item.width) === spec.width);
    const html = capture && await chromeHtmlFromCapture(capture.dir);
    if (!html) continue;
    const wrote = await writePaperSection({
      call, targetId: board.id, name: spec.label, html, projectRoot, log,
    });
    if (wrote?.nodeId) written += 1;
  }
  const receiptDir = dirs.find((item) => Number(item.width) === 1600)?.dir;
  if (receiptDir && written) {
    const receipt = path.join(receiptDir, "12-chrome-navigation.json");
    fs.writeFileSync(receipt, `${JSON.stringify({
      generatedFrom: "hover-reel/park-12-chrome", writtenAt: new Date().toISOString(),
      fileId, board: "Navigation", takes: written,
    }, null, 2)}\n`);
  }
  return { written, replace };
}

export async function portChromeOntoDesktopIfMissing({
  call,
  fileId,
  desktopId,
  desktopDir,
  projectRoot,
  log = console.error,
} = {}) {
  if (!call || !fileId || !desktopId) {
    return { written: false, reason: "need call, file, and desktop" };
  }
  const captureDir = desktopDir || path.join(projectRoot || ".", "capture", "home-desktop");
  const html = await chromeHtmlFromCapture(captureDir);
  if (!html) return { written: false, reason: "no 00-header/00-nav" };
  const { desktopLanderHasNavbar } = await importSibling(
    "url-to-paper",
    "scripts/chrome-bars.mjs",
  );
  const { mcpPayload, prepareSectionHtml } = await importSibling(
    "url-to-paper",
    "scripts/write-paper-section.mjs",
  );
  const kids = mcpPayload(await call("get_children", { nodeId: desktopId, fileId }));
  const nodes = kids.children || kids.nodes || [];
  if (desktopLanderHasNavbar(nodes)) {
    log("desktop already has navbar — skip chrome port");
    return { written: false, skipped: true, reason: "desktop already has navbar" };
  }
  const prepared = await prepareSectionHtml(html, { projectRoot: projectRoot || path.dirname(path.dirname(captureDir)) });
  if (!prepared?.html) return { written: false, reason: "chrome html empty after prepare" };
  const res = mcpPayload(await call("write_html", {
    html: prepared.html,
    targetNodeId: desktopId,
    mode: "insert-children",
    fileId,
  }));
  const created = res.createdNodes?.[0]?.id || res.ids?.[0] || null;
  if (!created) return { written: false, reason: "write_html created no node" };
  try {
    await call("rename_nodes", { fileId, updates: [{ nodeId: created, name: "00 · chrome" }] });
  } catch { /* name is best-effort */ }
  try {
    await call("move_nodes", {
      fileId,
      nodeIds: [created],
      parentId: desktopId,
      index: 0,
    });
  } catch { /* leave where write_html appended */ }
  log("1.2 chrome → home-desktop (lander was missing navbar)");
  const receipt = path.join(captureDir, "12-chrome-desktop.json");
  fs.writeFileSync(receipt, `${JSON.stringify({
    generatedFrom: "hover-reel/park-12-chrome",
    writtenAt: new Date().toISOString(),
    fileId,
    board: "home-desktop",
    nodeId: created,
    bytes: prepared.html.length,
  }, null, 2)}\n`);
  return { written: true, nodeId: created, receipt };
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const argv = process.argv.slice(2);
  const arg = (name) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 ? argv[i + 1] : "";
  };
  const projectRoot = path.resolve(arg("project") || ".");
  const fileId = arg("file-id") || process.env.PAPER_FILE_ID;
  const replace = argv.includes("--replace");
  if (!fileId) {
    console.error("park-12-chrome: --file-id is required");
    process.exit(1);
  }
  const { call, setFileId } = await importSibling("url-to-paper", "scripts/mcp-client.mjs");
  setFileId(fileId);
  const result = await park12ChromeOnNavigation({
    call,
    fileId,
    projectRoot,
    captureDirs: [1600, 768, 390].map((width) => ({
      width,
      dir: path.join(projectRoot, "capture", `home-${width === 1600 ? "desktop" : width}`),
    })),
    replace,
    log: console.error,
  });
  console.log(JSON.stringify(result));
  if (!result.written) process.exit(result.skipped ? 0 : 2);
}
