import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { listOpenPaperComments, openCommentExitCode } from "../scripts/list-paper-comments.mjs";

test("2.1 comment gate exits 2 while threads remain", () => {
  assert.equal(openCommentExitCode(0), 0);
  assert.equal(openCommentExitCode(2), 2);
});

test("2.1 comment gate writes every open thread before build", async () => {
  const root = mkdtempSync(join(tmpdir(), "paper-comments-"));
  const out = join(root, "qa", "paper-comments.json");
  const calls = [];
  const paperCall = async (name, args) => {
    calls.push([name, args]);
    if (name === "list_comment_threads") {
      return { content: [{ type: "text", text: JSON.stringify({
        commentThreads: [{ commentThreadId: "c-nav", firstMessagePreview: { text: "Fix the navbar" } }],
      }) }] };
    }
    if (name === "get_comment_thread") {
      return { content: [{ type: "text", text: JSON.stringify({
        commentThreadId: args.commentThreadId,
        status: "open",
        firstMessagePreview: { text: "Fix the navbar" },
      }) }] };
    }
    return { content: [{ type: "text", text: "{}" }] };
  };

  const report = await listOpenPaperComments({ fileId: "paper-file", out, paperCall });
  assert.equal(report.openCount, 1);
  assert.equal(openCommentExitCode(report.openCount), 2);
  assert.equal(JSON.parse(readFileSync(out, "utf8")).openCount, 1);
  assert.deepEqual(calls.map(([name]) => name), [
    "open_file",
    "list_comment_threads",
    "get_comment_thread",
  ]);
});
