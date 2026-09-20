import test from "node:test";
import assert from "node:assert/strict";
import { buildLayerIds, persistCensusRow } from "../scripts/layer-ids.mjs";

test("buildLayerIds keeps serializer census fields", () => {
  const payload = buildLayerIds(
    [
      {
        section: { id: "01", slug: "hero" },
        ids: [
          {
            pcId: "pc-01-0.0",
            path: "0.0",
            tag: "h1",
            class: "framer-text framer-styles-preset-abc extra",
            classes: ["framer-text", "framer-styles-preset-abc"],
            role: "heading",
            "data-framer-name": "Headline",
            text: "Headline",
          },
        ],
      },
    ],
    { url: "https://example.com", width: 1440 },
  );
  const row = payload.ids["pc-01-0.0"];
  assert.equal(row.tag, "h1");
  assert.equal(row.class, "framer-text framer-styles-preset-abc extra");
  assert.deepEqual(row.classes, ["framer-text", "framer-styles-preset-abc"]);
  assert.equal(row.role, "heading");
  assert.equal(row["data-framer-name"], "Headline");
  assert.equal(row.text, "Headline");
  assert.match(row.section, /hero/);
});

test("persistCensusRow does not invent a thin {pcId,file,section} row", () => {
  const row = persistCensusRow(
    { pcId: "pc-01-0", path: "0", tag: "section", class: "hero", classes: [], file: "01-hero.html" },
    "01 · hero",
  );
  assert.equal(row.tag, "section");
  assert.equal(row.class, "hero");
  assert.equal(row.file, "01-hero.html");
  assert.equal(row.section, "01 · hero");
});
