import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { paperFileName, readRunPaperReceipt, runPaperFileId } from "../scripts/create-paper-file.mjs";

const now = new Date("2026-08-30T12:05:00");
assert.equal(
  paperFileName({ projectRoot: "/tmp/templates/kp-thrive", now }),
  "kp-thrive 2026-08-30 1205",
);
assert.equal(
  paperFileName({ url: "https://kp-thrive.framer.website/home-01", now }),
  "kp-thrive.framer.website 2026-08-30 1205",
);
const a = paperFileName({ projectRoot: "/tmp/kp-thrive", now: new Date("2026-08-30T12:05:00") });
const b = paperFileName({ projectRoot: "/tmp/kp-thrive", now: new Date("2026-08-30T12:06:00") });
assert.notEqual(a, b, "two runs must not share a Paper file name");

assert.equal(runPaperFileId(null), "");
assert.equal(runPaperFileId({ fileId: "abc", generatedFrom: "other" }), "");
assert.equal(
  runPaperFileId({ fileId: "abc", generatedFrom: "url-to-paper/create-paper-file" }),
  "abc",
);

const root = mkdtempSync(join(tmpdir(), "paper-receipt-"));
assert.equal(readRunPaperReceipt(root), null);
mkdirSync(join(root, "qa"));
writeFileSync(
  join(root, "qa", "paper-file.json"),
  JSON.stringify({ fileId: "FILE1", generatedFrom: "url-to-paper/create-paper-file", fileName: "demo" }),
);
assert.equal(readRunPaperReceipt(root).fileId, "FILE1");
console.log("ok");
