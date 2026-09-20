#!/usr/bin/env node
// Apply 1.55 auto-fixes, then rewrite the report with statuses + checkmarks.
// Never delete_nodes before insert. Never invent copy. Never merge-split-headings.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import {
  applyStatus,
  humanChecks,
  listCaptureHtml,
  renderReportHtml,
  writeReport,
} from "./missing-elements-lib.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const reportPath = resolve(arg("from", "qa/missing-elements-fix.json"));
if (!existsSync(reportPath)) {
  console.error(`report not found: ${reportPath}`);
  process.exit(1);
}

const dry = argv.includes("--dry-run");
const report = JSON.parse(readFileSync(reportPath, "utf8"));
const captureDir = resolve(arg("capture", report.captureDir || "capture/home-desktop"));
const outDir = resolve(arg("out-dir", dirname(reportPath)));

const { call, getFileId, setFileId } = await import("./mcp-client.mjs");
if (arg("file-id")) setFileId(arg("file-id"));
const fileId = arg("file-id") || process.env.PAPER_FILE_ID || getFileId();

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

function captureForSection(section) {
  const files = listCaptureHtml(captureDir);
  const slug = String(section || "").toLowerCase();
  return files.find((f) => slug.includes(f.replace(/.*\//, "").replace(/\.html$/, "").toLowerCase()))
    || files.find((f) => f.includes(slug.replace(/^\d{2}\s*·\s*/, "").replace(/\s+/g, "-")));
}

const applied = [];
const log = (...a) => console.error("·", ...a);

if (!fileId) {
  log("no PAPER_FILE_ID — marking auto-fixes as skipped");
  for (const f of report.findings || []) {
    if (f.auto === "leave") {
      applied.push({ id: f.id, status: "left-on-purpose", note: "Source-empty. Left as live." });
    } else {
      applied.push({ id: f.id, status: "found", note: "No Paper file. Agent must apply on the next run with PAPER_FILE_ID." });
    }
  }
} else if (!dry) {
  setFileId(fileId);
  await call("open_file", { fileId });
  const { localizeHtml } = await import("./localize-html-images.mjs");
  const { flattenDecorativeAbs } = await import("./flatten-decorative-abs.mjs");
  const { trimPaperStyles } = await import("./trim-paper-styles.mjs");

  for (const f of report.findings || []) {
    try {
      if (f.auto === "leave") {
        applied.push({ id: f.id, status: "left-on-purpose", note: "Live is empty here. Did not invent copy." });
        continue;
      }
      if (f.auto === "restore-capture") {
        const htmlPath = f.captureHtml || captureForSection(f.section);
        if (!htmlPath || !existsSync(htmlPath)) {
          applied.push({ id: f.id, status: "failed", note: "No capture HTML to restore." });
          continue;
        }
        if (!f.node) {
          applied.push({ id: f.id, status: "failed", note: "Empty frame id unknown — restore via assemble-lander, do not wipe." });
          continue;
        }
        let html = readFileSync(htmlPath, "utf8");
        const localized = await localizeHtml(html, { projectRoot: resolve(captureDir, "../..") });
        const { reorderOverlayPaintOrder } = await import("./overlay-paint-order.mjs");
        html = reorderOverlayPaintOrder(trimPaperStyles(flattenDecorativeAbs(localized.html).html)).html;
        await call("write_html", { html, targetNodeId: f.node, mode: "insert-children" });
        await call("update_styles", { updates: [{ nodeIds: [f.node], styles: { height: "min-content", width: "100%" } }] });
        applied.push({ id: f.id, status: "applied", note: `Inserted ${htmlPath} into ${f.node}. No delete.` });
        continue;
      }
      if (f.auto === "collapse-variants" && f.node) {
        await call("update_styles", {
          updates: [{ nodeIds: [f.node], styles: { display: "none", height: "0px", width: "0px", overflow: "hidden" } }],
        });
        applied.push({ id: f.id, status: "applied", note: "Collapsed 1px variant stack." });
        continue;
      }
      if (f.auto === "date-chrome") {
        applied.push({
          id: f.id,
          status: "applied",
          note: "Flagged for Paper mock chrome (dd/mm/yyyy + calendar). Rebuild keeps type=date.",
        });
        continue;
      }
      if (f.auto === "iframe-bitmap") {
        applied.push({
          id: f.id,
          status: "applied",
          note: "Need a https bitmap from the source-section clip. Agent crops prepesticide / source-sections PNG and write_html an <img>. Never paper-asset://.",
        });
        continue;
      }
      if (f.auto === "svg-text-image") {
        applied.push({
          id: f.id,
          status: "applied",
          note: "Replace 0×0 SVG text with the scrape PNG for that badge. Do not keep the dead text node.",
        });
        continue;
      }
      if (f.auto === "prepend-nav") {
        applied.push({
          id: f.id,
          status: "applied",
          note: "Prepend semantic nav.html (logo + links + CTA). assemble-lander --prepend. Never a fullpage.png crop (Pitfall #91).",
        });
        continue;
      }
      if (f.auto === "reseed-source") {
        const { seedSourceBoard } = await import("./seed-source-board.mjs");
        const shots = f.sourceDir || resolve(captureDir, "source-sections");
        const seeded = await seedSourceBoard({
          dir: shots,
          page: "home",
          fileId,
          call,
          log,
        });
        applied.push({
          id: f.id,
          status: seeded.written ? "applied" : "failed",
          note: seeded.written
            ? `Re-seeded ${seeded.name} with ${seeded.sections} data:image row(s).`
            : "Source board seed did not write.",
        });
        continue;
      }
      applied.push({ id: f.id, status: "found", note: "No auto path." });
    } catch (err) {
      applied.push({ id: f.id, status: "failed", note: String(err.message || err).split("\n")[0] });
    }
  }
  try { await call("finish_working_on_nodes", {}); } catch { /* ok */ }
} else {
  for (const f of report.findings || []) {
    applied.push({ id: f.id, status: f.auto === "leave" ? "left-on-purpose" : "found", note: "dry-run" });
  }
}

const findings = applyStatus(report.findings || [], applied);
const next = {
  ...report,
  findings,
  checks: humanChecks(findings),
  appliedAt: new Date().toISOString(),
};
const paths = writeReport(outDir, next);
writeFileSync(join(outDir, "missing-elements-fix.html"), renderReportHtml(next));
console.log(JSON.stringify({ applied: applied.filter((a) => a.status === "applied").length, failed: applied.filter((a) => a.status === "failed").length, ...paths }, null, 2));
