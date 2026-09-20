import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  TAILWIND_FONT_SIZES,
  TAILWIND_RADII,
  TAILWIND_SHADOWS,
  TAILWIND_SEMANTIC_COLORS,
  TAILWIND_SPACING,
  closestFontSize,
  closestRadius,
  closestSpacing,
  paperTokenName,
} from "../scripts/tailwind-defaults.mjs";
import {
  assignSemanticColorRoles,
  baseFamily,
  bindThemeToTokens,
  buildLibraryReport,
  closestColorToken,
  cssVar,
  exactTokenForPaintedProp,
  mergeColors,
  familyTokens,
  mineFromStyledNodes,
  paperCreateTokens,
  paperFontFamilyValue,
  paperThemeFonts,
  buildFontFamilyValue,
  bindInlinePaperFonts,
  bindPaperFontUpdates,
  findUnboundFonts,
  isUnboundFontFamily,
  parseFontFamilyInfo,
  applyPaperFontFamilies,
  proposeLibraryTokens,
  assertFoundationsContract,
  bindInlineThemeTokens,
  buildTokenPassQa,
  isSkippedTokenPassBoard,
  isTokenPassArtboard,
  requireApplyThemeTokensScript,
  resolveBoundFontFamily,
  resolveBoundTokenValue,
  themeTokenPass,
  tokenWritePlan,
  tokenPassQaFails,
  tokenRebindUpdates,
  lineHeightToPercent,
  letterSpacingToRem,
  formatRem,
  remTokenSlug,
  lineHeightTokens,
  letterSpacingTokens,
} from "../scripts/library-tokens.mjs";
import {
  seedTokens,
  foundationsSheetContext,
  renderFoundationsChunks,
  renderTemplate,
  NEUTRAL_THEME,
} from "../scripts/library-sheet.mjs";

test("font token mining ignores already-bound CSS variables", () => {
  assert.equal(baseFamily("var(--font-sans)"), "");
  assert.equal(baseFamily("DM Serif Text"), "DM Serif Text");
  assert.equal(resolveBoundFontFamily("var(--font-sans)", [
    { name: "--font-sans", value: "Inter" },
  ]), "Inter");
  assert.equal(resolveBoundTokenValue("var(--color-accent)", [
    { name: "--color-accent", value: "#C9F269" },
  ]), "#C9F269");
  assert.equal(resolveBoundTokenValue("var(--color-accent)", [
    { name: "--color-accent", value: "var(--color-accent-wash)" },
    { name: "--color-accent-wash", value: "#EF4B3C1A" },
  ]), "#EF4B3C1A");
  assert.deepEqual(familyTokens([
    { value: "Inter", count: 10 },
    { value: "system-ui", count: 20 },
  ]).map((token) => token.value), ["Inter"]);
});

test("token writes upsert by default and replace duplicate names when requested", () => {
  const desired = [{ type: "color", name: "--color-accent", value: "#C9F269" }];
  const existing = [
    { name: "--color-accent", value: "#E11D2E" },
    { name: "--color-accent", value: "#FFD4944D" },
  ];
  const upsert = tokenWritePlan(desired, existing);
  assert.equal(upsert.creates.length, 0);
  assert.deepEqual(upsert.updates, [{ name: "--color-accent", value: "#C9F269" }]);
  const replace = tokenWritePlan(desired, existing, { replace: true });
  assert.equal(replace.deletes.length, 2);
  assert.deepEqual(replace.creates, desired);
});
import { refusesPaperFile } from "../scripts/bind-paper-fonts.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const scripts = join(__dir, "..", "scripts");

test("render-library delegates missing foundations creation and refuses other missing targets", () => {
  const source = readFileSync(join(scripts, "render-library.mjs"), "utf8");
  assert.doesNotMatch(source, /ensureDesignLibrary/);
  assert.doesNotMatch(source, /call\("create_artboard"/);
  assert.match(source, /updateDesignLibrary/);
  assert.match(source, /Only step 1\.4 foundations may create Design Library/);
  assert.match(source, /requires an existing --target artboard/);

  const missingLibrary = spawnSync(process.execPath, [
    join(scripts, "render-library.mjs"),
    "--library", join(tmpdir(), "does-not-exist-library.json"),
    "--kind", "foundations",
  ], { encoding: "utf8" });
  assert.equal(missingLibrary.status, 1);
  assert.match(missingLibrary.stderr, /requires an existing --library JSON file/);

  const missingKitTarget = spawnSync(process.execPath, [
    join(scripts, "render-library.mjs"),
    "--kind", "kit-components",
  ], { encoding: "utf8" });
  assert.equal(missingKitTarget.status, 1);
  assert.match(missingKitTarget.stderr, /requires an existing --target artboard/);
  assert.doesNotMatch(missingKitTarget.stderr, /Cannot read properties of null/);
});

function oddPxNodes() {
  const style = {
    backgroundColor: "#0D2C35",
    color: "#F4EFE6",
    fontFamily: "Satoshi-Bold",
    fontWeight: "700",
    fontStyle: "italic",
    fontSize: "56px",
    borderRadius: "11px",
    gap: "7px",
    padding: "15px",
    boxShadow: "0 12px 40px rgba(0,0,0,0.35)",
  };
  return Array.from({ length: 3 }, (_, i) => ({
    artboard: "home-desktop",
    name: `odd-${i}`,
    style,
  }));
}

test("spacing / type-size / radius tokens stay Tailwind defaults even with odd px", () => {
  const mined = mineFromStyledNodes(oddPxNodes(), { minUses: 1 });
  const proposed = proposeLibraryTokens(mined);
  const sizes = proposed.filter((t) => t.type === "fontSize");
  const spacing = proposed.filter((t) => t.type === "spacing");
  const radii = proposed.filter((t) => t.type === "radius");
  const shadows = proposed.filter((t) => t.type === "shadow");

  assert.equal(sizes.filter((t) => t.source === "tailwind-default").length, TAILWIND_FONT_SIZES.length);
  assert.equal(spacing.length, TAILWIND_SPACING.length);
  assert.equal(radii.length, TAILWIND_RADII.length);
  assert.equal(shadows.length, TAILWIND_SHADOWS.length);

  assert.equal(sizes.find((t) => t.name === "--text-3xl")?.value, "30px");
  assert.equal(sizes.find((t) => t.name === "--text-7xl")?.value, "72px");
  assert.ok(!sizes.some((t) => t.name === "--text-display" || t.name === "--text-display-xl"));
  const extra56 = sizes.find((t) => t.name === "--text-56");
  assert.equal(extra56?.value, "56px");
  assert.equal(extra56?.source, "mined");
  assert.ok(!spacing.some((t) => t.value === "7px" || t.value === "15px"));
  assert.ok(!radii.some((t) => t.value === "11px"));
  assert.ok(!sizes.some((t) => t.source === "display"));
  for (const step of ["7xl", "8xl", "9xl", "10xl", "11xl", "12xl"]) {
    assert.equal(sizes.find((t) => t.step === step)?.sheetGroup, "display");
    assert.equal(sizes.find((t) => t.step === step)?.onSheet, true);
  }
  assert.equal(sizes.find((t) => t.name === "--text-10xl")?.value, "160px");
  assert.equal(sizes.find((t) => t.name === "--text-11xl")?.value, "192px");
  assert.equal(sizes.find((t) => t.name === "--text-12xl")?.value, "224px");
  assert.ok(spacing.every((t) => t.source === "tailwind-default"));
});

test("colors, families, weights, and styles are still mined", () => {
  const mined = mineFromStyledNodes(oddPxNodes(), { minUses: 1 });
  const proposed = proposeLibraryTokens(mined);
  assert.ok(proposed.some((t) => t.type === "color" && t.value === "#0D2C35"));
  assert.ok(proposed.some((t) => t.type === "color" && t.value === "#F4EFE6"));
  assert.ok(proposed.some((t) => t.type === "fontFamily" && t.name === "--font-sans"));
  assert.equal(proposed.find((t) => t.type === "fontFamily")?.family, "Satoshi");
  assert.ok(proposed.some((t) => t.type === "fontWeight" && t.name === "--font-weight-bold" && t.value === 700));
  assert.ok(proposed.some((t) => t.type === "fontStyle" && t.name === "--font-style-italic"));
});

test("semantic colour bars stay 15px while mined brand swatches stay 104px", () => {
  const { chunks } = renderFoundationsChunks({
    proposedTokens: [
      { type: "color", name: "--color-surface", value: "#FFFFFF", source: "mined", uses: 12 },
      { type: "color", name: "--color-danger", value: "#EF4444", source: "semantic-role" },
    ],
  });
  const html = chunks.find((chunk) => chunk.name === "colour")?.html || "";
  const semanticAt = html.indexOf(">SEMANTIC</div>");
  assert.ok(semanticAt > 0);
  assert.match(html.slice(0, semanticAt), /width:250px; height:104px/);
  assert.match(html.slice(semanticAt), /width:250px; height:15px/);
});

test("Paper token names replace dots; shadows and font styles stay off create_tokens", () => {
  const proposed = proposeLibraryTokens(mineFromStyledNodes(oddPxNodes(), { minUses: 1 }));
  const paper = paperCreateTokens(proposed);
  assert.ok(paper.some((t) => t.name === "--spacing-0-5" && t.value === "2px"));
  assert.ok(!paper.some((t) => t.name.includes(".")));
  assert.ok(!paper.some((t) => t.type === "shadow" || t.type === "fontStyle"));
  assert.equal(paperTokenName("--spacing", "0.5"), "--spacing-0-5");
  assert.equal(paperTokenName("--radius", "DEFAULT"), "--radius");
});

test("closest Tailwind class maps odd measured px onto the default scale", () => {
  assert.equal(closestFontSize(56).twClass, "text-6xl");
  assert.equal(closestFontSize(56).value, "60px");
  assert.equal(closestFontSize(72).name, "--text-7xl");
  assert.equal(closestFontSize(160).name, "--text-10xl");
  assert.equal(closestFontSize(192).name, "--text-11xl");
  assert.equal(closestFontSize(224).name, "--text-12xl");
  assert.equal(closestSpacing(17).name, "--spacing-4");
  assert.equal(closestSpacing(17).value, "16px");
  assert.equal(closestSpacing(15).name, "--spacing-4");
  assert.equal(closestRadius(11).twClass, "rounded-xl");
  assert.equal(closestRadius(11).value, "12px");
});

test("library.json report does not census raw gaps or invented type sizes", () => {
  const mined = mineFromStyledNodes(oddPxNodes(), { minUses: 1 });
  const report = buildLibraryReport({
    file: "fixture",
    artboards: ["home-desktop"],
    nodes: 3,
    styledNodes: 3,
    minUses: 1,
    mined,
  });
  assert.deepEqual(report.scalePolicy.mined, ["color", "fontFamily", "fontWeight", "fontStyle", "fontSize-extras", "lineHeight", "letterSpacing"]);
  assert.ok(!report.spacing.some((t) => t.uses || t.rawValues || t.drift));
  assert.ok(report.typography.sizes.some((t) => t.source === "tailwind-default"));
  assert.ok(report.proposedTokens.some((t) => t.type === "fontSize" && t.value === "56px" && t.source === "mined"));
  assert.equal(report.typography.extraSizes?.[0]?.name, "--text-56");
});

test("cssVar and rebind put Paper tokens back after write_html strips var()", () => {
  assert.equal(cssVar("--text-6xl"), "var(--text-6xl)");
  const tokens = proposeLibraryTokens(mineFromStyledNodes(oddPxNodes(), { minUses: 1 }));
  const theme = bindThemeToTokens({
    ink: "#0D2C35", accent: "#F4EFE6", surface: "#FFFFFF",
    surfaceAlt: "#F3F8F9", border: "#DDE4E5", muted: "#647275",
    body: "#395963", display: "Satoshi", sans: "Satoshi",
  }, tokens);
  assert.equal(theme.ink, "var(--color-ink)");
  assert.equal(theme.sans, "var(--font-sans)");
  const updates = tokenRebindUpdates([
    { id: "t6", name: "glyph", style: { fontSize: "60px", color: "#0D2C35" } },
    { id: "hero", name: "hero", style: { fontSize: "56px" } },
    { id: "bar", name: "bar", style: { width: "16px", height: "14px" } },
    { id: "rad", name: "card", style: { borderRadius: "8px" } },
  ], tokens);
  const byId = Object.fromEntries(updates.map((u) => [u.nodeIds[0], u.styles]));
  assert.equal(byId.t6.fontSize, "var(--text-6xl)");
  assert.equal(byId.hero.fontSize, "var(--text-56)");
  assert.equal(byId.t6.color, "var(--color-ink)");
  assert.equal(byId.bar.width, "var(--spacing-4)");
  assert.equal(byId.rad.borderRadius, "var(--radius-lg)");
});

test("1.4 token-pass binds only exact geometry-affecting token values", () => {
  const tokens = [
    { type: "fontSize", name: "--text-3xl", value: "30px" },
    { type: "fontSize", name: "--text-2xl", value: "24px" },
    { type: "fontWeight", name: "--font-weight-bold", value: 700 },
    { type: "color", name: "--color-ink", value: "#0D2C35" },
    { type: "color", name: "--color-surface", value: "#FFFFFF" },
    { type: "spacing", name: "--spacing-4", value: "16px" },
    { type: "spacing", name: "--spacing-32", value: "128px" },
    { type: "radius", name: "--radius-lg", value: "8px" },
  ];
  assert.equal(exactTokenForPaintedProp("fontSize", "30px", tokens)?.name, "--text-3xl");
  assert.equal(exactTokenForPaintedProp("fontSize", "31px", tokens), null);
  assert.equal(exactTokenForPaintedProp("gap", "15px", tokens), null);
  assert.equal(exactTokenForPaintedProp("borderRadius", "7px", tokens), null);
  assert.equal(exactTokenForPaintedProp("fontWeight", "700.5", tokens), null);
  assert.equal(exactTokenForPaintedProp("fontWeight", "700foo", tokens), null);
  const pass = themeTokenPass([
    {
      id: "h",
      name: "headline",
      style: {
        x: "12px",
        y: "20px",
        width: "240px",
        height: "80px",
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        fontSize: "31px",
        fontWeight: "700",
        color: "#0E2C35",
      },
    },
    { id: "swatch", name: "fill", style: { backgroundColor: "#0D2C35" } },
    { id: "keep", name: "already", style: { fontSize: "var(--text-2xl)", color: "var(--color-ink)" } },
    { id: "pic", name: "hero", component: "Image", style: { fontSize: "31px", width: "400px" } },
    { id: "deco", name: "ornament", component: "SVG", style: { position: "absolute", fontSize: "31px" } },
    { id: "bar", name: "space-bar", style: { width: "128px", height: "14px" } },
    { id: "card", name: "card", style: { borderRadius: "7px", gap: "15px", padding: "16px" } },
  ], tokens);
  const byId = Object.fromEntries(pass.changes.map((c) => [`${c.nodeId}:${c.property}`, c]));
  assert.equal(byId["h:fontSize"], undefined);
  assert.equal(byId["h:fontWeight"].to, "var(--font-weight-bold)");
  assert.equal(byId["h:color"], undefined);
  assert.equal(byId["swatch:backgroundColor"].to, "var(--color-ink)");
  assert.equal(byId["bar:width"], undefined);
  assert.ok(pass.leftovers.some((item) => item.nodeId === "bar" && item.prop === "width"));
  assert.equal(byId["card:borderRadius"], undefined);
  assert.equal(byId["card:gap"], undefined);
  assert.equal(byId["card:padding"].to, "var(--spacing-4)");
  assert.ok(!pass.changes.some((c) => c.nodeId === "keep"));
  assert.ok(!pass.changes.some((c) => [
    "textWrap", "width", "height", "x", "y", "display", "flex",
    "flexDirection", "flexGrow", "alignItems", "alignSelf",
  ].includes(c.property)));
  assert.ok(pass.leftovers.some((item) => item.nodeId === "h" && item.prop === "fontSize"));
  assert.ok(pass.leftovers.some((item) => item.nodeId === "card" && item.prop === "gap"));
  assert.ok(pass.leftovers.some((item) => item.nodeId === "card" && item.prop === "borderRadius"));
  assert.ok(pass.skipped.some((s) => s.nodeId === "pic" && s.reason === "skip-image"));
  assert.ok(pass.skipped.some((s) => s.nodeId === "deco" && s.reason === "skip-scribble"));
  assert.ok(isTokenPassArtboard("home-desktop"));
  assert.ok(isTokenPassArtboard("homepage-desktop"));
  assert.ok(isTokenPassArtboard("A/6 · home · states"));
  assert.ok(isTokenPassArtboard("Design Library"));
  assert.ok(isTokenPassArtboard("Interactive components"));
  assert.ok(!isTokenPassArtboard("Ruler · desktop"));
  assert.ok(isSkippedTokenPassBoard("Source · home"));
  assert.ok(isSkippedTokenPassBoard("Screenshots"));
  assert.ok(isSkippedTokenPassBoard("Screenshots · about"));
  assert.ok(!isTokenPassArtboard("Source · home"));
});

test("every run ships at least five Tailwind semantic colors", () => {
  const proposed = proposeLibraryTokens(mineFromStyledNodes(oddPxNodes(), { minUses: 1 }));
  for (const row of TAILWIND_SEMANTIC_COLORS) {
    const token = proposed.find((t) => t.name === row.name);
    assert.equal(token?.value, row.value);
    assert.equal(token?.source, "semantic-role");
    assert.equal(token?.floor, "tailwind-default");
  }
  assert.ok(TAILWIND_SEMANTIC_COLORS.length >= 5);
});

test("foundations contract fails closed without the Tailwind floor or 10xl–12xl", () => {
  assert.throws(
    () => assertFoundationsContract([{ type: "color", name: "--color-ink", value: "#000" }]),
    /1.4 foundations contract missing/,
  );
  assert.equal(assertFoundationsContract(proposeLibraryTokens(mineFromStyledNodes(oddPxNodes(), { minUses: 1 }))), true);
  assert.equal(assertFoundationsContract(seedTokens()), true);
});

test("leftover #E11D2E becomes --color-danger and binds; white stays surface", () => {
  const brandFills = ["#FFFFFF", "#0D2C35", "#B99E5A", "#F4EFE6", "#395963", "#DDE4E5", "#647275", "#1A3A42"];
  const brandTexts = ["#0D2C35", "#F4EFE6", "#395963", "#647275", "#B99E5A"];
  const nodes = [];
  let n = 0;
  for (const bg of brandFills) {
    for (let i = 0; i < 3; i++) {
      nodes.push({ style: { backgroundColor: bg, color: brandTexts[n++ % brandTexts.length] } });
    }
  }
  nodes.push({ style: { backgroundColor: "#E11D2E", color: "#E11D2E" } });
  nodes.push({ style: { backgroundColor: "#FBFBFB" } });
  const mined = mineFromStyledNodes(nodes, { minUses: 1 });
  const proposed = proposeLibraryTokens(mined);
  const danger = proposed.find((t) => t.name === "--color-danger");
  const surface = proposed.find((t) => t.name === "--color-surface");
  const surfaceAlt = proposed.find((t) => t.name === "--color-surface-alt");
  assert.equal(danger?.value.toUpperCase(), "#E11D2E");
  assert.equal(danger?.source, "semantic-role");
  assert.equal(surface?.value.toUpperCase(), "#FFFFFF");
  assert.ok(!proposed.some((t) => t.name === "--color-surface-alt" && t.value.toUpperCase() === "#FFFFFF"));
  assert.equal(surfaceAlt?.value.toUpperCase(), "#FBFBFB");
  const pass = themeTokenPass([
    { id: "err", name: "error", style: { color: "#E11D2E", backgroundColor: "#E11D2E" } },
    { id: "card", name: "card", style: { backgroundColor: "#FBFBFB" } },
  ], proposed);
  const byId = Object.fromEntries(pass.changes.map((c) => [`${c.nodeId}:${c.property}`, c]));
  assert.equal(byId["err:color"].to, "var(--color-danger)");
  assert.equal(byId["err:backgroundColor"].to, "var(--color-danger)");
  assert.equal(byId["card:backgroundColor"].to, "var(--color-surface-alt)");

  const dir = mkdtempSync(join(tmpdir(), "lib-semantic-"));
  const jsonPath = join(dir, "library.json");
  writeFileSync(jsonPath, JSON.stringify(buildLibraryReport({
    file: "fixture", artboards: ["home-desktop"], nodes: nodes.length,
    styledNodes: nodes.length, minUses: 3, mined,
  })), "utf8");
  try {
    execFileSync(process.execPath, [
      join(scripts, "render-library.mjs"),
      "--library", jsonPath, "--kind", "foundations", "--dry-run", "--out-dir", dir,
    ], { stdio: "pipe" });
    const color = readFileSync(join(dir, "colour.html"), "utf8");
    assert.match(color, /background:var\(--color-danger\)/);
    assert.match(color, /background:var\(--color-surface-alt\)/);
    assert.match(color, /MINED/);
    assert.match(color, /SEMANTIC/);
    assert.match(color, /width:250px/);
    assert.match(color, /background:var\(--color-warning\)/);
    assert.match(color, /background:var\(--color-success\)/);
    assert.match(color, /background:var\(--color-info\)/);
    assert.match(color, /background:var\(--color-muted\)/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("opaque accent and alpha wash stay distinct; CTAs bind to the solid token", () => {
  const nodes = [];
  for (let i = 0; i < 24; i++) {
    nodes.push({ style: { backgroundColor: "#EF4B3C1A", color: "#000000" } });
  }
  for (let i = 0; i < 18; i++) {
    nodes.push({ style: { backgroundColor: "#EF4B3C", color: "#FFFFFF" } });
  }
  for (let i = 0; i < 6; i++) {
    nodes.push({ style: { backgroundColor: "#F7F3ED", color: "#000000" } });
  }
  const mined = mineFromStyledNodes(nodes, { minUses: 1 });
  const merged = mergeColors(mined.colors);
  assert.equal(merged.length, 3);
  assert.ok(!merged.some((e) => e.merged?.some((v) => String(v).toUpperCase().includes("EF4B3C"))));
  const proposed = proposeLibraryTokens(mined);
  const accent = proposed.find((t) => t.name === "--color-accent");
  const soft = proposed.find((t) => t.name === "--color-accent-soft");
  assert.equal(String(accent?.value || "").toUpperCase(), "#EF4B3C");
  assert.equal(String(soft?.value || "").toUpperCase(), "#EF4B3C1A");
  assert.equal(
    closestColorToken([accent, soft], "#EF4B3C")?.name,
    "--color-accent",
  );
  assert.equal(
    closestColorToken([accent, soft], "#EF4B3C1A")?.name,
    "--color-accent-soft",
  );
  const pass = themeTokenPass([
    { id: "cta", name: "a · Book A Schedule", style: { backgroundColor: "#EF4B3C", color: "#FFFFFF" } },
    { id: "well", name: "card well", style: { backgroundColor: "#EF4B3C1A" } },
  ], proposed);
  const byId = Object.fromEntries(pass.changes.map((c) => [`${c.nodeId}:${c.property}`, c]));
  assert.equal(byId["cta:backgroundColor"].to, "var(--color-accent)");
  assert.equal(byId["well:backgroundColor"].to, "var(--color-accent-soft)");
});

test("leftover matching still skips a role when that hex is absent", () => {
  const proposed = proposeLibraryTokens(mineFromStyledNodes(oddPxNodes(), { minUses: 1 }));
  assert.equal(proposed.find((t) => t.name === "--color-danger")?.value, "#EF4444");
  const none = assignSemanticColorRoles(
    { colors: [{ value: "#FFFFFF", count: 3 }], textColors: [{ value: "#0D2C35", count: 3 }] },
    [
      { type: "color", name: "--color-surface", value: "#FFFFFF" },
      { type: "color", name: "--color-ink", value: "#0D2C35" },
    ],
    { floor: false },
  );
  assert.ok(!none.some((t) => t.name === "--color-danger"));
  assert.ok(!none.some((t) => t.name === "--color-surface-alt"));
});

test("ink-soft / overlay leftovers fill roles; Paper overlay drops alpha", () => {
  const brand = [
    { type: "color", name: "--color-surface", value: "#FFFFFF" },
    { type: "color", name: "--color-ink", value: "#0D2C35" },
  ];
  const leftover = {
    colors: [
      { value: "#1D2B19B3", count: 2 },
      { value: "#F2F2F2", count: 1 },
    ],
    textColors: [
      { value: "#333333", count: 1 },
      { value: "#111111", count: 1 },
      { value: "#666666", count: 1 },
      { value: "#999999", count: 1 },
    ],
  };
  const roles = assignSemanticColorRoles(leftover, brand);
  assert.equal(roles.find((t) => t.name === "--color-ink-soft")?.value, "#333333");
  assert.equal(roles.find((t) => t.name === "--color-ink-strong")?.value, "#111111");
  const overlay = roles.find((t) => t.name === "--color-overlay");
  assert.equal(overlay?.value, "#1D2B19B3");
  assert.equal(overlay?.paperValue, "#1D2B19");
  assert.equal(roles.find((t) => t.name === "--color-surface-muted")?.value, "#F2F2F2");
  assert.equal(roles.find((t) => t.name === "--color-text-subtle")?.value, "#999999");
  assert.equal(roles.find((t) => t.name === "--color-text-secondary")?.value, "#666666");
  const paper = paperCreateTokens(roles);
  assert.equal(paper.find((t) => t.name === "--color-overlay")?.value, "#1D2B19");
});

test("1.4 token-pass binds exact type sizes without changing text wrapping", () => {
  const tokens = proposeLibraryTokens(mineFromStyledNodes(oddPxNodes(), { minUses: 1 }));
  const pass = themeTokenPass([
    { id: "hero", name: "hero", component: "Text", style: { fontSize: "72px" } },
    { id: "xxl", name: "display", component: "Text", style: { fontSize: "160px" } },
    { id: "odd", name: "odd", component: "Text", style: { fontSize: "161px" } },
  ], tokens);
  const byId = Object.fromEntries(pass.changes.map((c) => [`${c.nodeId}:${c.property}`, c]));
  assert.equal(byId["hero:fontSize"].to, "var(--text-7xl)");
  assert.equal(byId["xxl:fontSize"].to, "var(--text-10xl)");
  assert.equal(byId["odd:fontSize"], undefined);
  assert.ok(pass.leftovers.some((item) => item.nodeId === "odd" && item.prop === "fontSize"));
  assert.ok(!pass.changes.some((change) => change.property === "textWrap"));
});

test("foundations sheet is a scale specimen, not a measurement report", () => {
  const mined = mineFromStyledNodes(oddPxNodes(), { minUses: 1 });
  const report = buildLibraryReport({
    file: "fixture",
    artboards: ["home-desktop"],
    nodes: 3,
    styledNodes: 3,
    minUses: 1,
    mined,
  });
  const dir = mkdtempSync(join(tmpdir(), "lib-sheet-"));
  const jsonPath = join(dir, "library.json");
  writeFileSync(jsonPath, JSON.stringify(report), "utf8");
  try {
    execFileSync(process.execPath, [
      join(scripts, "render-library.mjs"),
      "--library", jsonPath,
      "--kind", "foundations",
      "--dry-run",
      "--out-dir", dir,
    ], { stdio: "pipe" });
    const spacing = readFileSync(join(dir, "spacing.html"), "utf8");
    const elevation = readFileSync(join(dir, "elevation-radii.html"), "utf8");
    const type = readFileSync(join(dir, "typography.html"), "utf8");
    const color = readFileSync(join(dir, "colour.html"), "utf8");
    const header = readFileSync(join(dir, "header.html"), "utf8");
    const all = [header, color, type, spacing, elevation].join("\n");
    assert.match(all, /var\(--text-/);
    assert.match(all, /var\(--color-/);
    assert.match(all, /var\(--spacing-/);
    assert.match(all, /var\(--radius-/);
    assert.match(type, /font-size:var\(--text-6xl\)/);
    assert.match(type, /font-size:var\(--text-7xl\)/);
    assert.match(type, /font-size:var\(--text-8xl\)/);
    assert.match(type, /font-size:var\(--text-9xl\)/);
    assert.match(type, /font-size:var\(--text-10xl\)/);
    assert.match(type, /font-size:var\(--text-12xl\)/);
    assert.match(type, />Aa</);
    assert.doesNotMatch(type, /--text-display/);
    const scaleStart = type.indexOf("SCALE");
    const twelve = type.indexOf("--text-12xl", scaleStart);
    const xs = type.indexOf("--text-xs", scaleStart);
    assert.ok(twelve >= 0 && xs > twelve);
    assert.match(color, /width:250px/);
    assert.match(color, /background:var\(--color-danger\)/);
    assert.match(color, /background:var\(--color-warning\)/);
    assert.match(type, /DISPLAY/);
    assert.match(type, /text-wrap:pretty/);
    assert.doesNotMatch(type, /font-size:\s*60px/);
    assert.doesNotMatch(type, /font-size:\s*72px/);
    assert.match(type, /60px/);
    assert.match(type, /72px/);
    assert.match(spacing, /width:var\(--spacing-0-5\)/);
    assert.match(spacing, /width:var\(--spacing-32\)/);
    assert.doesNotMatch(spacing, /width:\s*128px/);
    assert.match(spacing, /128px/);
    assert.match(spacing, /2px/);
    assert.doesNotMatch(spacing, /uses|raw ·|snapped|Measured values are snapped/);
    assert.match(elevation, /border-radius:var\(--radius-lg\)/);
    assert.match(color, /background:var\(--color-/);
    assert.match(color, /MINED/);
    assert.match(color, /SEMANTIC/);
    assert.doesNotMatch(elevation, /Paper's create_tokens|N uses/);
    assert.match(header, /var\(--token\)/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

const CENSUS_TOKENS = [
  { type: "color", name: "--color-ink", value: "#0A073B" },
  { type: "fontSize", name: "--text-base", value: "16px" },
  { type: "spacing", name: "--spacing-4", value: "16px" },
  { type: "spacing", name: "--spacing-32", value: "128px" },
  { type: "radius", name: "--radius-lg", value: "8px" },
];

function censusFixture() {
  return [
    {
      id: "rebound-1",
      name: "headline",
      artboard: "home-desktop",
      style: { fontSize: "16px", color: "#0A073B" },
    },
    {
      id: "leftover-1",
      name: "wide-gap",
      artboard: "home-desktop",
      style: { gap: "200px" },
    },
    {
      id: "image-1",
      name: "hero",
      component: "Image",
      artboard: "home-desktop",
      style: { fontSize: "16px", width: "400px" },
    },
  ];
}

test("token-pass QA census: rebound + leftover>128 + image skip, every node listed", () => {
  const tree = censusFixture();
  const pass = themeTokenPass(tree, CENSUS_TOKENS);
  assert.ok(pass.changes.some((c) => c.nodeId === "rebound-1" && c.to === "var(--text-base)"));
  assert.ok(pass.changes.some((c) => c.nodeId === "rebound-1" && c.to === "var(--color-ink)"));
  assert.ok(pass.leftovers.some((L) => L.nodeId === "leftover-1" && L.why === "spacing-over-128-no-token"));
  assert.ok(!pass.changes.some((c) => c.nodeId === "leftover-1"));
  assert.ok(pass.skipped.some((s) => s.nodeId === "image-1" && s.reason === "skip-image"));

  const qa = buildTokenPassQa({ treeNodes: tree, pass, tokens: CENSUS_TOKENS, skippedBoards: ["Source · home"] });
  assert.equal(qa.nodes["rebound-1"], "rebound");
  assert.equal(qa.nodes["leftover-1"], "leftover");
  assert.equal(qa.nodes["image-1"], "skip-image");
  assert.equal(qa.coverage.treeNodes, 3);
  assert.equal(qa.coverage.accounted, 3);
  assert.deepEqual(qa.coverage.missing, []);
  assert.equal(qa.nodesTouchedCount, 3);
  assert.ok(qa.propsReboundCount >= 2);
  assert.ok(qa.leftovers.some((L) => L.nodeId === "leftover-1" && L.prop === "gap" && L.value === "200px"));
  assert.deepEqual(qa.skippedBoards, ["Source · home"]);
  assert.equal(qa.ok, true);
  assert.equal(tokenPassQaFails(qa), false);
});

test("token-pass QA fails when a tree node is omitted from the QA file", () => {
  const tree = censusFixture();
  const pass = themeTokenPass(tree, CENSUS_TOKENS);
  const qa = buildTokenPassQa({
    treeNodes: tree,
    pass,
    tokens: CENSUS_TOKENS,
    accounts: { "rebound-1": "rebound", "leftover-1": "leftover" },
  });
  assert.deepEqual(qa.coverage.missing, ["image-1"]);
  assert.equal(qa.ok, false);
  assert.equal(tokenPassQaFails(qa), true);
});

test("token-pass QA fails when a tokenable hex stays raw and unlisted", () => {
  const tree = [
    { id: "miss", name: "cta", artboard: "Interactive components", style: { color: "#0A073B" } },
  ];
  const pass = { changes: [], skipped: [], leftovers: [] };
  const qa = buildTokenPassQa({ treeNodes: tree, pass, tokens: CENSUS_TOKENS });
  assert.equal(qa.nodes.miss, "rebound");
  assert.ok(qa.defects.some((d) => d.nodeId === "miss" && d.why === "tokenable-raw-unlisted" && d.value === "#0A073B"));
  assert.equal(qa.ok, false);
  assert.equal(tokenPassQaFails(qa), true);
});

test("spacer width without an exact token is leftover, not resized", () => {
  const tree = [{
    id: "bar",
    name: "space-bar",
    artboard: "home-desktop",
    style: { width: "17px", height: "14px" },
  }];
  const pass = themeTokenPass(tree, CENSUS_TOKENS);
  assert.ok(!pass.changes.some((c) => c.nodeId === "bar"));
  assert.ok(pass.leftovers.some((L) => L.nodeId === "bar" && L.why === "spacer-width-no-exact-token"));
  const qa = buildTokenPassQa({ treeNodes: tree, pass, tokens: CENSUS_TOKENS });
  assert.equal(qa.nodes.bar, "leftover");
  assert.equal(qa.ok, true);
});

test("catch-at-write HTML binds type/color/space/radius and keeps fluid layout", () => {
  const html = '<div style="width: 100%; height: fit-content; align-items: flex-start; font-size: 16px; color: #0A073B; gap: 16px; border-radius: 8px; padding: 200px"></div>';
  const bound = bindInlineThemeTokens(html, CENSUS_TOKENS);
  assert.match(bound, /font-size: var\(--text-base\)/);
  assert.match(bound, /color: var\(--color-ink\)/);
  assert.match(bound, /gap: var\(--spacing-4\)/);
  assert.match(bound, /border-radius: var\(--radius-lg\)/);
  assert.match(bound, /width: 100%/);
  assert.match(bound, /height: fit-content/);
  assert.match(bound, /align-items: flex-start/);
  assert.match(bound, /padding: 200px/);
});

test("missing apply-theme-tokens.mjs fails — no silent subset update_styles", () => {
  assert.doesNotThrow(() => requireApplyThemeTokensScript(join(scripts, "apply-theme-tokens.mjs")));
  assert.throws(
    () => requireApplyThemeTokensScript(join(scripts, "does-not-exist-apply-theme-tokens.mjs")),
    /apply-theme-tokens\.mjs is missing/,
  );
});


test("Paper fontFamily payload is a catalog face; build keeps the CSS stack", () => {
  const stack = '"Inter", system-ui, sans-serif';
  const mined = mineFromStyledNodes(
    Array.from({ length: 3 }, () => ({ style: { fontFamily: stack, color: "#111111" } })),
    { minUses: 1 },
  );
  const proposed = proposeLibraryTokens(mined);
  const fam = proposed.find((t) => t.type === "fontFamily");
  assert.equal(fam.family, "Inter");
  assert.equal(fam.paperValue, "Inter");
  assert.equal(fam.value, stack);
  assert.equal(paperFontFamilyValue(fam), "Inter");
  assert.equal(buildFontFamilyValue(fam), stack);
  const paper = paperCreateTokens(proposed);
  assert.equal(paper.find((t) => t.type === "fontFamily")?.value, "Inter");
  assert.ok(!paper.some((t) => t.type === "fontFamily" && String(t.value).includes(",")));
});

test("unavailable Paper faces fall back or skip; build stack is unchanged", () => {
  const stack = '"General Sans", system-ui, sans-serif';
  const tokens = [{
    type: "fontFamily",
    name: "--font-sans",
    value: stack,
    family: "General Sans",
    paperValue: "General Sans",
  }];
  const catalog = parseFontFamilyInfo({
    fontsPerFamily: { Inter: [{ weight: 400 }] },
    errors: ['Font family "General Sans" is not available.'],
  });
  const shaped = applyPaperFontFamilies(tokens, catalog);
  assert.equal(shaped[0].paperValue, "Inter");
  assert.equal(shaped[0].paperFallback, "Inter");
  assert.equal(buildFontFamilyValue(shaped[0]), stack);
  assert.equal(paperCreateTokens(shaped)[0].value, "Inter");

  const none = applyPaperFontFamilies(tokens, parseFontFamilyInfo({
    fontsPerFamily: {},
    errors: ['Font family "General Sans" is not available.'],
  }), { fallbacks: [] });
  assert.equal(none[0].paperToken, false);
  assert.equal(none[0].paperSkip, "unavailable-face");
  assert.equal(paperCreateTokens(none).length, 0);
  assert.equal(buildFontFamilyValue(none[0]), stack);
});

test("MCP-down catalog still sends the bare family, not the stack", () => {
  const stack = '"Inter", system-ui, sans-serif';
  const tokens = [{
    type: "fontFamily",
    name: "--font-sans-inter",
    value: stack,
    family: "Inter",
  }];
  const shaped = applyPaperFontFamilies(tokens, null);
  assert.equal(paperCreateTokens(shaped)[0].value, "Inter");
  assert.equal(buildFontFamilyValue(shaped[0]), stack);
});

test("Design Library seed stores Inter for Paper and the stack for CSS", () => {
  const sans = seedTokens().find((t) => t.name === "--font-sans");
  assert.equal(sans.paperValue, "Inter");
  assert.equal(sans.family, "Inter");
  assert.equal(sans.value, "Inter, system-ui, sans-serif");
  assert.equal(paperCreateTokens([sans])[0].value, "Inter");
  assert.equal(buildFontFamilyValue(sans), "Inter, system-ui, sans-serif");
});


test("Paper theme.sans is Inter, not a CSS stack", () => {
  assert.equal(NEUTRAL_THEME.sans, "Inter");
  assert.equal(NEUTRAL_THEME.display, "Inter");
  assert.equal(NEUTRAL_THEME.mono, "SF Mono");
  assert.ok(!String(NEUTRAL_THEME.sans).includes(","));
  assert.ok(!String(NEUTRAL_THEME.mono).includes(","));

  const ctx = foundationsSheetContext({
    proposedTokens: [
      {
        type: "fontFamily",
        name: "--font-sans",
        value: "Inter, system-ui, sans-serif",
        paperValue: "Inter",
        family: "Inter",
      },
      {
        type: "fontFamily",
        name: "--font-serif",
        value: "Lora, Georgia, serif",
        paperValue: "Lora",
        family: "Lora",
      },
    ],
  }, { seed: false, useVar: true });
  assert.equal(ctx.theme.sans, "Inter");
  assert.equal(ctx.theme.display, "Lora");
  assert.ok(!String(ctx.theme.mono).includes(","));
  assert.ok(!String(ctx.theme.sans).includes("system-ui"));

  const paper = paperThemeFonts(ctx.tokens);
  assert.equal(paper.sans, "Inter");
  assert.equal(paper.display, "Lora");
});

test("family card Aa uses the catalog face, not var() or a stack", () => {
  const ctx = foundationsSheetContext({
    proposedTokens: [
      {
        type: "fontFamily",
        name: "--font-serif",
        value: "Lora, Georgia, serif",
        paperValue: "Lora",
        family: "Lora",
      },
    ],
  }, { seed: false, useVar: true });
  const lora = ctx.families.find((f) => f.name === "--font-serif");
  assert.equal(lora.paperValue, "Lora");
  const tpl = readFileSync(join(__dir, "..", "templates", "library", "foundations", "03-typography.html"), "utf8");
  const html = renderTemplate(tpl, ctx);
  assert.match(html, /font-family:Lora/);
  assert.match(html, /font-size:var\(--text-xl\); font-weight:600/);
  assert.match(html, />Lora</);
  assert.match(html, /font-size:var\(--text-sm\); font-weight:700;[^>]*>FAMILIES</);
  assert.match(html, /data-font-token="--font-serif"/);
  assert.doesNotMatch(html, /font-family:var\(--font-serif\)/);
  assert.doesNotMatch(html, /font-family:Lora, Georgia/);
});

test("unbound-font detector flags System Sans-Serif when font tokens exist", () => {
  assert.equal(isUnboundFontFamily("System Sans-Serif"), true);
  assert.equal(isUnboundFontFamily("system-ui"), true);
  assert.equal(isUnboundFontFamily("sans-serif"), true);
  assert.equal(isUnboundFontFamily("Inter, system-ui, sans-serif"), true);
  assert.equal(isUnboundFontFamily(""), true);
  assert.equal(isUnboundFontFamily("Inter"), false);
  assert.equal(isUnboundFontFamily("var(--font-serif)"), false);

  const tokens = [
    { type: "fontFamily", name: "--font-sans", value: "Inter, system-ui, sans-serif", paperValue: "Inter", family: "Inter" },
    { type: "fontFamily", name: "--font-serif", value: "Lora, Georgia, serif", paperValue: "Lora", family: "Lora" },
  ];
  const findings = findUnboundFonts([
    { id: "aa", name: "Aa", component: "Text", artboard: "Design Library", style: { fontFamily: "System Sans-Serif" } },
    { id: "ok", name: "body", component: "Text", style: { fontFamily: "Inter" } },
    { id: "img", name: "photo", component: "Image", style: { fontFamily: "System Sans-Serif" } },
  ], tokens);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].type, "unbound-font");
  assert.equal(findings[0].severity, "high");
  assert.equal(findings[0].node, "aa");

  const pass = bindPaperFontUpdates([
    { id: "aa", name: "heading", component: "Text", style: { fontFamily: "System Sans-Serif" } },
    { id: "stack", name: "caption", component: "Text", style: { fontFamily: "Inter, system-ui, sans-serif" } },
  ], tokens);
  const byId = Object.fromEntries(pass.changes.map((c) => [c.nodeId, c]));
  assert.equal(byId.aa.to, "var(--font-serif)");
  assert.equal(byId.stack.to, "var(--font-sans)");
});

test("write_html font stacks collapse to a catalog face; build stack is unchanged", () => {
  const tokens = [
    { type: "fontFamily", name: "--font-sans", value: "Inter, system-ui, sans-serif", paperValue: "Inter", family: "Inter" },
  ];
  const html = bindInlinePaperFonts(
    '<div style="font-family: Inter, system-ui, sans-serif; font-size: 16px">Hi</div>',
    tokens,
  );
  assert.match(html, /font-family: Inter/);
  assert.doesNotMatch(html, /system-ui/);
  assert.equal(buildFontFamilyValue(tokens[0]), "Inter, system-ui, sans-serif");
  assert.equal(paperCreateTokens(tokens)[0].value, "Inter");
});

test("bind-paper-fonts honors caller-supplied protected files", () => {
  const guard = { protectedIds: "protected-file-id", protectedNames: "gold,do-not-write" };
  assert.equal(refusesPaperFile({ ...guard, fileId: "protected-file-id" }), "protected id protected-file-id");
  assert.equal(refusesPaperFile({ ...guard, fileName: "Gold homepage" }), "protected name gold");
  assert.equal(refusesPaperFile({ ...guard, fileName: "Working homepage" }), null);
});

test("line-height converts to percent and letter-spacing converts to rem", () => {
  assert.equal(lineHeightToPercent("1.2"), "120%");
  assert.equal(lineHeightToPercent("24px", "16px"), "150%");
  assert.equal(lineHeightToPercent("120%"), "120%");
  assert.equal(lineHeightToPercent("1.15em"), "115%");
  assert.equal(lineHeightToPercent("normal"), null);
  assert.equal(letterSpacingToRem("normal"), "0rem");
  assert.equal(letterSpacingToRem("-0.8px"), "-0.05rem");
  assert.equal(letterSpacingToRem("0.02em", "40px"), "0.05rem");
  assert.equal(letterSpacingToRem("0.02rem"), "0.02rem");
  assert.equal(formatRem(0), "0rem");
  assert.equal(remTokenSlug(-0.02), "neg-0-02");
  assert.equal(lineHeightTokens([{ value: "120%", count: 4 }])[0].name, "--line-height-120");
  assert.equal(letterSpacingTokens([{ value: "-0.05rem", count: 2 }])[0].name, "--letter-spacing-neg-0-05");
});

test("desktop mines line-height and letter-spacing; 768 does not", () => {
  const nodes = [
    {
      artboard: "home-desktop",
      name: "hero",
      style: { fontSize: "40px", lineHeight: "48px", letterSpacing: "-0.8px" },
    },
    {
      artboard: "home-desktop",
      name: "body",
      style: { fontSize: "16px", lineHeight: "24px", letterSpacing: "normal" },
    },
    {
      artboard: "home-768",
      name: "hero-tab",
      style: { fontSize: "32px", lineHeight: "80px", letterSpacing: "4px" },
    },
  ];
  const mined = mineFromStyledNodes(nodes, { minUses: 1 });
  assert.deepEqual(mined.lineHeights.map((e) => e.value).sort(), ["120%", "150%"]);
  assert.deepEqual(mined.letterSpacings.map((e) => e.value).sort(), ["-0.05rem", "0rem"]);
  const proposed = proposeLibraryTokens(mined);
  const leading = proposed.filter((t) => t.type === "lineHeight");
  const tracking = proposed.filter((t) => t.type === "letterSpacing");
  assert.ok(leading.some((t) => t.name === "--line-height-120" && t.value === "120%"));
  assert.ok(leading.some((t) => t.name === "--line-height-150" && t.value === "150%"));
  assert.ok(tracking.some((t) => t.name === "--letter-spacing-neg-0-05" && t.value === "-0.05rem"));
  assert.ok(tracking.some((t) => t.name === "--letter-spacing-0" && t.value === "0rem"));
  const paper = paperCreateTokens(proposed);
  assert.ok(paper.some((t) => t.type === "lineHeight" && t.name === "--line-height-120" && t.value === "120%"));
  assert.ok(paper.some((t) => t.type === "letterSpacing" && t.name === "--letter-spacing-neg-0-05"));
  const { chunks } = renderFoundationsChunks({ proposedTokens: proposed });
  const type = chunks.find((chunk) => chunk.name === "typography")?.html || "";
  assert.match(type, /LINE HEIGHT/);
  assert.match(type, /LETTER SPACING/);
  assert.match(type, /--line-height-120/);
  assert.match(type, /--letter-spacing-neg-0-05/);
  assert.match(type, /line-height:var\(--line-height-120\)/);
  assert.match(type, /letter-spacing:var\(--letter-spacing-neg-0-05\)/);
});

test("token-pass binds exact desktop line-height and letter-spacing across frames", () => {
  const tokens = [
    { type: "fontSize", name: "--text-base", value: "16px" },
    { type: "fontSize", name: "--text-5xl", value: "48px" },
    { type: "lineHeight", name: "--line-height-170", value: "170%", source: "mined" },
    { type: "lineHeight", name: "--line-height-120", value: "120%", source: "mined" },
    { type: "letterSpacing", name: "--letter-spacing-neg-0-112", value: "-0.112rem", source: "mined" },
  ];
  assert.equal(exactTokenForPaintedProp("lineHeight", "27.2px", tokens, {
    style: { fontSize: "var(--text-base)" },
  })?.name, "--line-height-170");
  assert.equal(exactTokenForPaintedProp("lineHeight", "24px", tokens, {
    style: { fontSize: "16px" },
  }), null);
  assert.equal(exactTokenForPaintedProp("letterSpacing", "-1.8px", tokens, {
    style: { fontSize: "48px" },
  })?.name, "--letter-spacing-neg-0-112");

  const pass = themeTokenPass([
    {
      id: "body",
      name: "copy",
      artboard: "home-768",
      style: { fontSize: "var(--text-base)", lineHeight: "27.2px" },
    },
    {
      id: "hero",
      name: "title",
      artboard: "home-desktop",
      style: { fontSize: "var(--text-5xl)", lineHeight: "57.6px", letterSpacing: "-1.8px" },
    },
    {
      id: "keep",
      name: "already",
      style: { fontSize: "var(--text-base)", lineHeight: "var(--line-height-170)" },
    },
  ], tokens);
  const byId = Object.fromEntries(pass.changes.map((c) => [`${c.nodeId}:${c.property}`, c]));
  assert.equal(byId["body:lineHeight"].to, "var(--line-height-170)");
  assert.equal(byId["hero:lineHeight"].to, "var(--line-height-120)");
  assert.equal(byId["hero:letterSpacing"].to, "var(--letter-spacing-neg-0-112)");
  assert.ok(!pass.changes.some((c) => c.nodeId === "keep"));

  const rebound = tokenRebindUpdates([
    { id: "body", style: { fontSize: "16px", lineHeight: "27.2px" } },
  ], tokens);
  assert.equal(rebound[0].styles.lineHeight, "var(--line-height-170)");

  const html = bindInlineThemeTokens(
    '<p style="font-size: 16px; line-height: 27.2px; letter-spacing: -1.8px">Hi</p>',
    tokens,
  );
  assert.match(html, /line-height: var\(--line-height-170\)/);
});
