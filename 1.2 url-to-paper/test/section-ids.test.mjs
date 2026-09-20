import test from "node:test";
import assert from "node:assert/strict";
import { paperSectionName, SECTION_ID_LEGEND } from "../scripts/section-ids.mjs";

test("desktop names are id · slug (the comment)", () => {
  assert.equal(
    paperSectionName({ id: "09", slug: "they-use-subba-to-create" }, { desktop: true }),
    "09 · they-use-subba-to-create",
  );
});

test("tablet keeps the slug", () => {
  assert.equal(
    paperSectionName({ id: "09", name: "they-use-subba-to-create" }, { desktop: false }),
    "they-use-subba-to-create",
  );
});

test("legend board name is exact so retire can find it", () => {
  assert.equal(SECTION_ID_LEGEND, "Desktop section IDs");
});
