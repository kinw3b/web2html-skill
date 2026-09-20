import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { authorButtonHover } from "../scripts/author-button-hover.mjs";
import {
  controlMatchesSelector,
  cssHoverRecipes,
  extractControls,
  extractStyleBlocks,
  extractStylesheetHrefs,
  findControlForLabel,
  isBareTagHover,
  labelKey,
  loadSourceCss,
  parseHoverRules,
  paperStylesFromHover,
  suggestedLibraryClass,
} from "../scripts/source-button-hover.mjs";

const HTML = `
  <a class="framer-abc btn-primary" href="/go">Get Started Now</a>
  <a class="ghost" href="/hire">Hire An Expert</a>
  <button class="plain">Submit</button>
`;

const CSS = `
  a:hover { color: blue; }
  .btn-primary:hover {
    background-color: #111111;
    color: #ffffff;
    transition: 200ms ease;
  }
  .ghost:hover { color: #0a0; }
  @media (hover: hover) {
    .plain:hover { background: rgb(20, 20, 20); color: white; }
  }
`;

test("bare a:hover is not a CTA recipe", () => {
  assert.equal(isBareTagHover("a:hover"), true);
  assert.equal(isBareTagHover(".btn-primary:hover"), false);
  const rules = parseHoverRules("a:hover { color: blue; } .cta:hover { background: #000; }");
  assert.equal(rules.length, 1);
  assert.equal(rules[0].matchSelector, ".cta");
});

test("parses inline and media-query hover paint", () => {
  const rules = parseHoverRules(CSS);
  assert.ok(rules.some((row) => row.matchSelector === ".btn-primary"));
  assert.ok(rules.some((row) => row.matchSelector === ".plain"));
  assert.ok(!rules.some((row) => row.matchSelector === "a"));
});

test("matches pulled button labels to source controls and CSS", () => {
  const recipes = cssHoverRecipes({
    html: HTML,
    css: CSS,
    buttons: [
      { label: "Primary - Get Started Now", sectionId: "01" },
      { label: "Hire An Expert", sectionId: "02" },
      { label: "Missing CTA", sectionId: "03" },
    ],
  });
  assert.equal(recipes.applied.length, 1);
  assert.equal(recipes.applied[0].className, "btn-primary");
  assert.equal(recipes.applied[0].declarations["background-color"], "#111111");
  assert.equal(recipes.applied[0].paperStyles.backgroundColor, "#111111");
  assert.ok(recipes.skipped.some((row) => row.label === "Hire An Expert"));
  assert.ok(recipes.skipped.some((row) => row.reason === "no matching source control"));
});

test("ghost class with paint hover becomes btn-ghost", () => {
  const recipes = cssHoverRecipes({
    html: HTML,
    css: ".ghost:hover { background-color: #111; color: #fff; }",
    buttons: [{ label: "Hire An Expert", sectionId: "02" }],
  });
  assert.equal(recipes.applied.length, 1);
  assert.equal(recipes.applied[0].className, "btn-ghost");
});

test("label keys strip Primary - prefixes", () => {
  assert.equal(labelKey("Primary - Get Started Now"), "get started now");
  const controls = extractControls(HTML);
  assert.equal(findControlForLabel(controls, "Primary - Get Started Now")?.text, "Get Started Now");
});

test("simple class selectors match; descendant selectors do not", () => {
  const control = extractControls(HTML)[0];
  assert.equal(controlMatchesSelector(control, ".btn-primary"), true);
  assert.equal(controlMatchesSelector(control, "a.btn-primary"), true);
  assert.equal(controlMatchesSelector(control, "header .btn-primary"), false);
});

test("extracts style blocks and stylesheet hrefs", () => {
  const html = `<link rel="stylesheet" href="/app.css"><style>.x:hover{background:#000}</style>`;
  assert.equal(extractStyleBlocks(html)[0].includes(".x:hover"), true);
  assert.equal(extractStylesheetHrefs(html, "https://ex.com/")[0], "https://ex.com/app.css");
});

test("paper styles drop transition-only paint", () => {
  const styles = paperStylesFromHover({
    "background-color": "#000",
    transition: "200ms ease",
  });
  assert.equal(styles.backgroundColor, "#000");
  assert.equal(styles.transition, undefined);
});

test("suggested class prefers source btn-* names", () => {
  assert.equal(suggestedLibraryClass({ classes: ["btn-secondary"] }, {}), "btn-secondary");
});

test("loads linked CSS from source-site before fetching the live href", async () => {
  const root = mkdtempSync(join(tmpdir(), "local-hover-css-"));
  mkdirSync(join(root, "source-site", "css"), { recursive: true });
  writeFileSync(
    join(root, "source-site", "css", "app.css"),
    ".btn-primary:hover { background-color: #111; color: #fff; }\n",
    "utf8",
  );
  const html = `<link rel="stylesheet" href="/css/app.css"><a class="btn-primary" href="/go">Go</a>`;
  let fetched = 0;
  const css = await loadSourceCss(html, "https://example.com/", {
    root,
    fetchImpl: async () => {
      fetched += 1;
      return { ok: false, text: async () => "" };
    },
  });
  assert.equal(fetched, 0);
  assert.match(css, /background-color: #111/);
});

test("authorButtonHover writes qa/button-hover.json from source CSS", async () => {
  const root = mkdtempSync(join(tmpdir(), "button-hover-"));
  mkdirSync(join(root, "qa"));
  mkdirSync(join(root, "source-site"));
  writeFileSync(
    join(root, "source-site", "index.html"),
    `<html>${HTML}<style>${CSS}</style></html>\n`,
    "utf8",
  );
  writeFileSync(
    join(root, "source-site", "pages.json"),
    JSON.stringify([{ path: "/", url: "https://example.com/" }]),
    "utf8",
  );
  const pull = {
    ok: true,
    writer: "pull-desktop-specimens.mjs",
    scannedSections: ["01 · hero"],
    buttons: [{ label: "Primary - Get Started Now", sectionId: "01", sectionName: "hero" }],
    components: [],
  };
  writeFileSync(join(root, "qa", "buttons-components-pull.json"), JSON.stringify(pull), "utf8");
  const receipt = await authorButtonHover({
    projectRoot: root,
    pull,
    now: () => "2026-09-07T00:00:00.000Z",
    log: () => {},
  });
  assert.equal(receipt.ok, true);
  assert.equal(receipt.applied.length, 1);
  assert.equal(receipt.applied[0].className, "btn-primary");
  assert.equal(receipt.applied[0].parked, false);
  const disk = JSON.parse(readFileSync(join(root, "qa", "button-hover.json"), "utf8"));
  assert.equal(disk.writer, "author-button-hover.mjs");
});
