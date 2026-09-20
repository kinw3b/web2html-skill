import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  HUD_ID,
  HUD_STYLE_ID,
  HUD_TAG,
  collectInventory,
  documentFromHtml,
  inspectRecord,
  isSerializerSkip,
  paperComponentType,
  paintRole,
  slugify,
  tailwindFromBox,
} from "../scripts/pre-pesticide-core.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const fixture = readFileSync(join(__dir, "fixtures/pre-pesticide.html"), "utf8");
const hudSrc = readFileSync(join(__dir, "../scripts/pre-pesticide.js"), "utf8");
const serializerSrc = readFileSync(join(__dir, "../scripts/serializer.js"), "utf8");

test("HUD root starts with x-paper-", () => {
  assert.equal(HUD_TAG.startsWith("x-paper-"), true);
  assert.equal(HUD_ID.startsWith("x-paper-"), true);
  assert.equal(HUD_STYLE_ID.startsWith("x-paper-"), true);
  assert.match(hudSrc, /createElement\(\s*HUD_TAG|createElement\(\s*"x-paper-prepesticide"/);
  assert.match(hudSrc, /id = HUD_ID|id = "x-paper-prepesticide"/);
  assert.match(hudSrc, /x-paper-prepesticide/);
  assert.match(hudSrc, /inventory\s*\(/);
  assert.match(hudSrc, /preventDefault/);
  assert.match(hudSrc, /via:\s*"background"/);
});

test("serializer skip still holds for the HUD tag and id", () => {
  assert.equal(isSerializerSkip(HUD_TAG, ""), true);
  assert.equal(isSerializerSkip("div", HUD_ID), true);
  assert.equal(isSerializerSkip("style", HUD_STYLE_ID), true);
  assert.equal(isSerializerSkip("section", "content-01"), false);
  assert.equal(isSerializerSkip("img", "hero"), false);

  // The lifted serializer still skips x-paper-* by tag or id. Snapshot 0.3.8–0.3.12
  // reads the id through elementId(e); older ports read e.id. Accept either.
  assert.match(
    serializerSrc,
    /L\.startsWith\("x-paper-"\) \|\| (?:e\.id|elementId\(e\))\.startsWith\("x-paper-"\)/,
  );
  assert.equal(
    HUD_TAG.startsWith("x-paper-") || HUD_ID.startsWith("x-paper-"),
    true,
  );
});

test("inventory counts imgs and sections on the orchard fixture", () => {
  const doc = documentFromHtml(fixture);
  const inv = collectInventory(doc);

  assert.equal(inv.images.length, 3, `images: ${JSON.stringify(inv.images)}`);
  assert.equal(inv.images.filter((i) => i.via === "img").length, 2);
  assert.equal(inv.images.filter((i) => i.via === "background").length, 1);
  assert.ok(inv.images.some((i) => i.src.includes("grove.jpg") && i.via === "background"));
  assert.ok(inv.sections.length >= 3, `sections: ${inv.sections.map((s) => s.slug).join(",")}`);

  const slugs = inv.sections.map((s) => s.slug);
  assert.ok(slugs.includes("hero") || slugs.includes("content-01"), slugs.join(","));
  assert.ok(slugs.some((s) => s.includes("contact") || s.includes("nav") || s.includes("footer")), slugs.join(","));

  const hero = inv.sections.find((s) => s.slug === "hero" || s.slug === "content-01" || s.framerName === "Hero");
  assert.ok(hero, `missing hero in ${slugs.join(",")}`);
  assert.equal(hero.childCounts.img, 2);
  assert.equal(hero.childCounts.button, 1);
  assert.equal(hero.childCounts.h, 1);

  const grove = inv.images.find((i) => i.src.includes("hero.jpg"));
  assert.ok(grove);
  assert.equal(grove.alt, "Grove at dusk");
  assert.equal(grove.w, 1200);
  assert.equal(grove.h, 640);
  assert.ok(grove.section === "hero" || grove.section === "content-01");

  assert.equal(inv.forms.length, 1);
  assert.equal(inv.forms[0].method, "post");
  assert.ok(inv.landmarks.some((l) => l.tag === "header"));
  assert.ok(inv.landmarks.some((l) => l.tag === "form"));

  // HUD node is in the fixture but must not become a section or image.
  assert.equal(inv.sections.every((s) => !s.tag.startsWith("x-paper-")), true);
  assert.equal(inv.images.every((i) => !String(i.src).includes("x-paper")), true);
});

test("inspect record names Paper type and Tailwind v3", () => {
  const doc = documentFromHtml(fixture);
  const img = doc.querySelector("img");
  const rec = inspectRecord(img, [], { twPrefix: "tw-" });
  assert.equal(rec.paperType, "Image");
  assert.equal(rec.paintRole, "content");
  assert.match(rec.tailwind, /tw-w-\[1200px\]/);
  assert.match(rec.paperRow, /type=Image/);
  assert.match(rec.paperRow, /role=content/);

  const leaf = doc.querySelectorAll("img")[1];
  assert.equal(paintRole(leaf), "decorative");
  assert.equal(paperComponentType(doc.querySelector("h1")), "Text");
  assert.equal(paperComponentType(doc.querySelector("section")), "Frame");
});

test("slugify matches detect-sections style", () => {
  assert.equal(slugify("Yearning orchard", "section"), "yearning-orchard");
  assert.equal(slugify("Nav Bar", "nav"), "nav-bar");
});

test("bookmarklet is a javascript: URL that mounts the x-paper- HUD", () => {
  const cli = join(__dir, "../scripts/pre-pesticide.mjs");
  const r = spawnSync(process.execPath, [cli, "--bookmarklet"], { encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /^javascript:/);
  const decoded = decodeURIComponent(r.stdout.trim().slice("javascript:".length));
  assert.match(decoded, /x-paper-prepesticide/);
  assert.match(decoded, /__xPaperPrePesticide/);
  assert.match(decoded, /__xPaperDetectSections/);
});

test("tailwindFromBox records box metrics, not flex-wrap (Pitfall #75)", () => {
  const el = {
    tagName: "DIV",
    getAttribute: () => null,
    _bbox: { x: 0, y: 0, w: 72, h: 72 },
    _computed: {
      display: "flex",
      flexWrap: "wrap",
      gap: "24px",
      justifyContent: "center",
    },
    textContent: "",
  };
  const tw = tailwindFromBox(el, { prefix: "" });
  assert.match(tw, /w-\[72px\]/);
  assert.match(tw, /h-\[72px\]/);
  assert.match(tw, /gap-\[24px\]/);
  assert.doesNotMatch(tw, /flex-wrap/);
  assert.doesNotMatch(tw, /46%/);
});

test("tailwind prefix is optional", () => {
  const el = {
    tagName: "DIV",
    getAttribute: () => null,
    _bbox: { x: 0, y: 0, w: 160, h: 48 },
    _computed: { display: "flex", justifyContent: "center", backgroundColor: "rgb(8, 14, 19)" },
    textContent: "",
  };
  const plain = tailwindFromBox(el, { prefix: "" });
  const pref = tailwindFromBox(el, { prefix: "tw-" });
  assert.match(plain, /w-\[160px\]/);
  assert.doesNotMatch(plain, /tw-/);
  assert.match(pref, /tw-w-\[160px\]/);
  assert.match(pref, /tw-flex/);
  assert.match(pref, /tw-bg-\[#080e13\]/);
});
