import assert from "node:assert/strict";
import test from "node:test";
import { collectInteriorPageToPaper } from "../scripts/run-paper-phase.mjs";

test("interior collect refuses homepage and missing ids", async () => {
  await assert.rejects(
    () => collectInteriorPageToPaper({ url: "https://example.com/about" }),
    /fileId/,
  );
  await assert.rejects(
    () => collectInteriorPageToPaper({ url: "https://example.com/about", fileId: "f" }),
    /pageId/,
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
