import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
const script = join(here, "../scripts/seed-interior-page-tokens.mjs");

test("4.3 refuses an empty library", () => {
  const root = mkdtempSync(join(tmpdir(), "phase4-"));
  mkdirSync(join(root, "qa"), { recursive: true });
  mkdirSync(join(root, "design-library"), { recursive: true });
  writeFileSync(join(root, "qa", "phase-4-pages.json"), JSON.stringify({
    fileId: "file",
    pages: [{ slug: "about", pageId: "p", artboard: "about-desktop" }],
  }));
  writeFileSync(join(root, "design-library", "library.json"), JSON.stringify({ tokens: {} }));
  const result = spawnSync(process.execPath, [script, "--project", root], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(`${result.stderr}${result.stdout}`, /empty|refuse/i);
});
