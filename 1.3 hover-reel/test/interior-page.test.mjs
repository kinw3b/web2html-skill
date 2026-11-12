import assert from "node:assert/strict";
import test from "node:test";
import { collectInteriorPageToPaper } from "../scripts/run-paper-phase.mjs";

test("interior collect refuses homepage, missing slug and missing file id", async () => {
  await assert.rejects(
    () => collectInteriorPageToPaper({ url: "https://example.com/about" }),
    /fileId/,
  );
  // pageId is optional now (interior landers park on the home canvas); a
  // missing slug is what gets refused.
  await assert.rejects(
    () => collectInteriorPageToPaper({ url: "https://example.com/about", fileId: "f" }),
    /homepage slug/,
  );
  await assert.rejects(
    () => collectInteriorPageToPaper({
      url: "https://example.com/",
      fileId: "f",
      pageId: "p",
      pageSlug: "home",
    }),
    /homepage/,
  );
});
