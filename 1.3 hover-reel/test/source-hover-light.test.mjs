import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { authorHoverLight, shipButtons, WRITER } from "../scripts/source-hover-light.mjs";

const SOURCE = `<!DOCTYPE html><html><head><style>
  .btn-primary:hover { background: #111; color: #fff; }
</style></head><body>
  <a class="framer-x btn-primary" href="/go">Get Started</a>
  <a class="ghost" href="/hire">Hire An Expert</a>
</body></html>`;

const SHIP = `<!DOCTYPE html><html><body>
  <header><a class="btn btn-primary" href="#">Get Started</a></header>
  <main><a class="btn-ghost" href="#">Hire An Expert</a>
  <a class="nav-link" href="#">About us and everything we have ever done since the dawn of time</a>
  <button class="cta">Get Started</button></main>
</body></html>`;

function project() {
  const root = mkdtempSync(join(tmpdir(), "w2h-hover-light-"));
  mkdirSync(join(root, "source-site"), { recursive: true });
  mkdirSync(join(root, "rebuild"), { recursive: true });
  writeFileSync(join(root, "source-site", "index.html"), SOURCE);
  writeFileSync(join(root, "source-site", "pages.json"), JSON.stringify([{ url: "https://example.com/" }]));
  writeFileSync(join(root, "rebuild", "index.html"), SHIP);
  return root;
}

test("shipButtons picks button-ish controls once, drops long labels", () => {
  const rows = shipButtons(SHIP);
  assert.deepEqual(rows.map((r) => r.label), ["Get Started", "Hire An Expert"]);
});

test("light pass writes a 1.3-shaped receipt from source CSS without Paper", async () => {
  const root = project();
  const receipt = await authorHoverLight({
    projectRoot: root,
    log: () => {},
    fetchImpl: async () => { throw new Error("no network in tests"); },
    now: () => "2026-01-01T00:00:00.000Z",
  });
  assert.equal(receipt.writer, WRITER);
  assert.equal(receipt.lightPass, "source-hover-light.mjs");
  assert.equal(receipt.ok, true);
  assert.equal(receipt.shipButtonCount, 2);
  assert.equal(receipt.applied.length, 1);
  assert.equal(receipt.applied[0].label, "Get Started");
  assert.equal(receipt.applied[0].parked, false);
  assert.ok(receipt.skipped.some((row) => row.label === "Hire An Expert"), "no invented hover for the ghost link");
  const onDisk = JSON.parse(readFileSync(join(root, "qa", "button-hover.json"), "utf8"));
  assert.equal(onDisk.completedAt, "2026-01-01T00:00:00.000Z");
  assert.equal(onDisk.ship, "rebuild/index.html");
});

test("light pass prefers index-polish.html when present", async () => {
  const root = project();
  writeFileSync(join(root, "rebuild", "index-polish.html"), SHIP);
  const receipt = await authorHoverLight({
    projectRoot: root,
    log: () => {},
    fetchImpl: async () => { throw new Error("no network"); },
  });
  assert.equal(receipt.ship, "rebuild/index-polish.html");
});
