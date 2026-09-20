import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  assertDesignLibrarySources,
  COMMAND_HARD_CAP_MS,
  designLibraryStepCommands,
  foundationsLibraryReceiptOk,
  runDesignLibraryStep,
  stallReason,
} from "../scripts/run-design-library-step.mjs";

function projectRoot() {
  return mkdtempSync(join(tmpdir(), "design-library-step-"));
}

test("1.3 stall watch kills a silent command instead of retrying it", () => {
  assert.equal(stallReason({ startedAt: 0, lastByteAt: 5_000, now: 24_999 }), null);
  assert.match(stallReason({ startedAt: 0, lastByteAt: 5_000, now: 25_000 }), /silent 20000ms/);
  assert.match(stallReason({ startedAt: 0, lastByteAt: COMMAND_HARD_CAP_MS - 10_000, now: COMMAND_HARD_CAP_MS }), /hard cap/);
});

test("1.3 requires three landers and the Navigation take, not Capture Tool Done", () => {
  const inventory = assertDesignLibrarySources([
    { name: "home-desktop" }, { name: "home-768" }, { name: "home-390" },
    { name: "Buttons" }, { name: "Components" }, { name: "Navigation" },
  ]);
  assert.deepEqual(inventory.landers, ["home-desktop", "home-768", "home-390"]);
  assert.throws(
    () => assertDesignLibrarySources([{ name: "home-desktop" }, { name: "home-768" }, { name: "home-390" }]),
    /Navigation frame/,
  );
});

test("1.3 has one mine, one foundations render, and one token bind", () => {
  const commands = designLibraryStepCommands({ projectRoot: "/tmp/site", fileId: "paper-file", expectFile: "site" });
  assert.deepEqual(commands.map(([script]) => script), [
    "extract-library.mjs", "render-library.mjs", "apply-theme-tokens.mjs",
  ]);
  assert.equal(commands.flat().includes("validate-library-seed.mjs"), false);
  assert.equal(foundationsLibraryReceiptOk({
    status: "done", writer: "render-library.mjs", kind: "foundations",
    commands: commands.map(([script]) => script),
  }), true);
});

test("1.3 stops at the first failed command and writes no receipt", async () => {
  const root = projectRoot();
  const boards = ["home-desktop", "home-768", "home-390", "Navigation"].map((name) => ({ name }));
  const ran = [];
  await assert.rejects(() => runDesignLibraryStep({
    projectRoot: root, fileId: "paper-file", expectFile: "site",
    paperCall: async () => ({ content: [{ type: "text", text: JSON.stringify({ fileName: "site", artboards: boards }) }] }),
    runCommand: (script) => { ran.push(script); return { status: script === "render-library.mjs" ? 2 : 0 }; },
  }), /render-library\.mjs failed/);
  assert.deepEqual(ran, ["extract-library.mjs", "render-library.mjs"]);
  assert.equal(existsSync(join(root, "qa", "design-library-step.json")), false);
});

test("1.3 writes its receipt after one successful pass", async () => {
  const root = projectRoot();
  const sourceBoards = ["home-desktop", "home-768", "home-390", "Navigation"].map((name) => ({ name }));
  let reads = 0;
  const receipt = await runDesignLibraryStep({
    projectRoot: root, fileId: "paper-file", expectFile: "site",
    paperCall: async () => {
      reads += 1;
      const artboards = reads === 1 ? sourceBoards : [...sourceBoards, { name: "Design Library" }];
      return { content: [{ type: "text", text: JSON.stringify({ fileName: "site", artboards }) }] };
    },
    runCommand: () => ({ status: 0 }), now: () => "2026-08-29T00:00:00.000Z",
  });
  assert.equal(reads, 2);
  assert.deepEqual(receipt.commands, ["extract-library.mjs", "render-library.mjs", "apply-theme-tokens.mjs"]);
  assert.equal(receipt.seedPasses, undefined);
  assert.equal(existsSync(join(root, "qa", "design-library-step.json")), true);
});
