import assert from "node:assert/strict";
import test from "node:test";
import { assertNoPaperWrite, FORBIDDEN_PAPER_TOOLS, WIDTHS } from "../scripts/capture-interior-breakpoints.mjs";

test("5.4 live capture refuses Paper writes and stays off desktop", () => {
  assert.deepEqual(WIDTHS, [768, 390]);
  assert.ok(FORBIDDEN_PAPER_TOOLS.includes("create_file"));
  assert.ok(FORBIDDEN_PAPER_TOOLS.includes("create_page"));
  assert.ok(FORBIDDEN_PAPER_TOOLS.includes("write_html"));
  assert.throws(() => assertNoPaperWrite("create_file"), /create_file/);
  assert.throws(() => assertNoPaperWrite("write_html"), /write_html/);
});
