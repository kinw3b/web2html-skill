import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { assertSafeTool, dumpInteriorPages, FORBIDDEN_TOOLS } from "../scripts/dump-interior-raw.mjs";

test("5.1 dump refuses create_file and list_files", () => {
  assert.deepEqual(FORBIDDEN_TOOLS, ["create_file", "list_files"]);
  assert.throws(() => assertSafeTool("create_file"), /create_file/);
  assert.throws(() => assertSafeTool("list_files"), /list_files/);
});

test("5.1 dump is serial and --file-id scoped", async () => {
  const root = mkdtempSync(join(tmpdir(), "phase5-dump-"));
  mkdirSync(join(root, "rebuild"), { recursive: true });
  mkdirSync(join(root, "qa"), { recursive: true });
  const order = [];
  const call = async (name, params) => {
    assertSafeTool(name);
    order.push({ name, fileId: params.fileId, pageId: params.pageId });
    if (name === "get_jsx") {
      return { content: [{ type: "text", text: JSON.stringify({ jsx: "<div>About</div>" }) }] };
    }
    return {};
  };
  const pages = await dumpInteriorPages({
    project: root,
    fileId: "FILE",
    pages: [
      { slug: "about", pageId: "p1", artboardId: "a1" },
      { slug: "work", pageId: "p2", artboardId: "a2" },
    ],
    call,
  });
  assert.equal(pages.length, 2);
  assert.deepEqual(order.map((row) => row.name), ["open_file", "get_jsx", "open_file", "get_jsx"]);
  assert.ok(order.every((row) => row.fileId === "FILE"));
  assert.match(readFileSync(join(root, "rebuild", "about-raw.html"), "utf8"), /About|div/);
});
