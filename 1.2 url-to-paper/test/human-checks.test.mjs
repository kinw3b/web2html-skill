import test from "node:test";
import assert from "node:assert/strict";
import { humanChecks } from "../scripts/missing-elements-lib.mjs";

test("1.5 checklist always asks the human to pin Paper comments", () => {
  const checks = humanChecks([]);
  const ids = checks.map((c) => c.id);
  assert.ok(ids.includes("walk-1600"));
  assert.ok(ids.includes("paper-comments"));
  const row = checks.find((c) => c.id === "paper-comments");
  assert.match(row.label, /Paper comment/i);
  assert.match(row.label, /next agent/i);
});
