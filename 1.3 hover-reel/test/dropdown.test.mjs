import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  DESKTOP_DROPDOWN_WIDTH,
  INTERACTIVE_COMPONENTS_BOARD,
  INTERACTIVE_COMPONENTS_WIDTH,
  a6StatesBoardName,
  dropdownCaptureWidth,
  emptyKindManifest,
  fluidFitStyles,
  hamburgerKindWidth,
  interactiveRowMeta,
  isDropdownKind,
  isFaqKind,
  isHamburgerKind,
  isInteractiveKind,
  isFluidPairKind,
  isGeometryLockedRoot,
  kindCaptureWidth,
  looksLikeHamburger,
  paperBoardName,
  paperBoardWidth,
  paperCellWidth,
  paperPairRowHtml,
  paperRootBox,
  paperSectionBadgeHtml,
  paperSectionName,
  paperSlotBox,
  paperStateCellShell,
  prepareFluidPairHtml,
  resolveCaptureKinds,
  resolveDropdownOutDir,
  shouldCaptureDropdown,
  stripChevronTransforms,
} from '../scripts/component-state-utils.mjs';
import { prepareStateHtml } from '../scripts/prepare-state-html.mjs';
import { writeDropdownPairFiles, writeDropdownPairs, writeFluidPairFiles } from '../scripts/write-dropdown-pair.mjs';
import { parseMenuCaptureArgs } from '../scripts/capture-menu-states.mjs';
import { parseHamburgerCaptureArgs } from '../scripts/capture-hamburger-states.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CAPTURE = path.join(ROOT, 'scripts', 'capture-component-states.mjs');
const MENU = path.join(ROOT, 'scripts', 'capture-menu-states.mjs');

test('dropdown kind is fluid 100% / flex-start / fit-content — never captured px', () => {
  const html = '<div style="width: 220px; height: 48px; display: flex; align-items: center; transform: rotate(180deg); translate: 4px 2px">Products</div>';
  const box = paperRootBox({ kind: 'dropdown', mode: 'dropdown', rect: [0, 0, 220, 48] });
  assert.deepEqual(box, {
    width: '100%',
    maxWidth: '100%',
    height: 'fit-content',
    alignItems: 'flex-start',
    alignSelf: 'flex-start',
  });
  assert.equal(paperSlotBox({ kind: 'dropdown' }).width, '100%');
  assert.equal(paperSlotBox({ kind: 'dropdown' }).maxWidth, '100%');
  assert.equal(paperSlotBox({ kind: 'dropdown' }).alignItems, 'flex-start');
  assert.equal(paperSlotBox({ kind: 'dropdown' }).height, 'fit-content');
  assert.equal(paperCellWidth({ kind: 'dropdown', fallback: 'fit-content' }), '100%');
  assert.equal(isFluidPairKind('dropdown', 'dropdown'), true);
  assert.equal(isDropdownKind('navbar-dropdown'), true);
  assert.deepEqual(fluidFitStyles().alignItems, 'flex-start');

  const prepared = prepareStateHtml(html, {
    kind: 'dropdown',
    mode: 'dropdown',
    rect: [12, 40, 220, 48],
  });
  assert.match(prepared.html, /width: 100%/);
  assert.match(prepared.html, /max-width: 100%/);
  assert.match(prepared.html, /height: fit-content/);
  assert.match(prepared.html, /align-items: flex-start/);
  assert.doesNotMatch(prepared.html, /width: 220px/);
  assert.doesNotMatch(prepared.html, /height: 48px/);
  assert.doesNotMatch(prepared.html, /translate/);
  assert.doesNotMatch(prepared.html, /rotate/);
  assert.ok(isGeometryLockedRoot(prepared.html, { kind: 'dropdown', mode: 'dropdown' }));

  const shell = paperStateCellShell({
    name: 'navbar-dropdown',
    kind: 'dropdown',
    mode: 'dropdown',
    width: '100%',
  });
  assert.match(shell, /width: 100%/);
  assert.match(shell, /max-width: 100%/);
  assert.match(shell, /align-items: flex-start/);
  assert.match(shell, /height: fit-content/);
  assert.match(shell, /layer-name="Slot"[^>]*align-items: flex-start/);
  assert.doesNotMatch(shell, /layer-name="Slot"[^>]*align-items: center/);

  const stripped = stripChevronTransforms(
    '<div style="width: 12px; height: 12px; transform: rotate(180deg); translate: 3px 1px; rotate: 180deg"></div>',
  );
  assert.doesNotMatch(stripped, /transform/);
  assert.doesNotMatch(stripped, /translate/);
  assert.doesNotMatch(stripped, /rotate/);
  assert.match(prepareFluidPairHtml(html, { kind: 'dropdown' }), /align-items: flex-start/);
});

test('dropdown writes Navigation — objects on Components, hover on Buttons', () => {
  assert.equal(paperBoardName({ kind: 'dropdown', pageSlug: 'home' }), INTERACTIVE_COMPONENTS_BOARD);
  assert.equal(paperBoardName({ kind: 'navbar-dropdown', mode: 'dropdown' }), 'Navigation');
  assert.equal(paperSectionName({ kind: 'dropdown' }), 'Dropdown');
  assert.doesNotMatch(paperBoardName({ kind: 'dropdown' }), /A\/6/);

  assert.equal(paperBoardName({ kind: 'faq', mode: 'accordion', pageSlug: 'home' }), 'Components');
  assert.equal(paperBoardName({ kind: 'faq', pageSlug: 'home' }), 'Components');
  assert.equal(paperSectionName({ kind: 'faq', mode: 'accordion' }), 'Accordion');
  assert.equal(isFaqKind('faq', 'accordion'), true);
  assert.equal(isFluidPairKind('faq', 'accordion'), false);

  assert.equal(paperBoardName({ kind: 'nav', pageSlug: 'home' }), 'Buttons');
  assert.equal(paperBoardName({ kind: 'buttons', pageSlug: 'contact' }), 'Buttons');

  const row = paperPairRowHtml({ sid: '01', title: 'Products', token: 'navbar-dropdown' });
  assert.match(row, /#E11D2E/);
  assert.match(row, /width: 36px; height: 36px/);
  assert.match(row, /align-items: flex-start/);
  assert.match(row, /width: 100%/);
  assert.match(paperSectionBadgeHtml('01'), /01/);
});

test('no dropdown emit when --allow-dropdown is off', () => {
  assert.equal(shouldCaptureDropdown({ allowDropdown: false, kind: 'dropdown' }), false);
  assert.equal(shouldCaptureDropdown({ allowDropdown: true, kind: 'dropdown' }), true);
  assert.deepEqual(
    resolveCaptureKinds({ kinds: ['nav', 'buttons', 'forms', 'footer'], allowHamburger: false }),
    ['nav', 'buttons', 'forms', 'footer'],
  );
  assert.deepEqual(
    resolveCaptureKinds({ kinds: ['nav', 'buttons', 'forms', 'footer'] }),
    ['nav', 'buttons', 'forms', 'footer', 'nav-mobile-768', 'nav-mobile-390'],
  );
  assert.deepEqual(
    resolveCaptureKinds({ kinds: ['nav', 'buttons', 'forms', 'footer'], allowDropdown: true }),
    ['nav', 'buttons', 'forms', 'footer', 'dropdown', 'nav-mobile-768', 'nav-mobile-390'],
  );
  assert.deepEqual(
    resolveCaptureKinds({ kinds: ['nav', 'buttons', 'forms', 'footer', 'faq'], allowFaq: true, allowHamburger: false }),
    ['nav', 'buttons', 'forms', 'footer', 'faq'],
  );

  const empty = emptyKindManifest({
    kind: 'dropdown',
    reason: 'dropdown capture is off — do not hunt; pass --allow-dropdown when a hover-to-open panel exists',
  });
  assert.equal(empty.status, 'empty');
  assert.equal(empty.kind, 'dropdown');
  assert.equal(empty.states.length, 0);

  const out = mkdtempSync(path.join(tmpdir(), 'hr-dropdown-'));
  const res = spawnSync(process.execPath, [
    CAPTURE,
    '--url', 'https://example.test/',
    '--kind', 'dropdown',
    '--page', 'home',
    '--out', out,
  ], { encoding: 'utf8' });
  assert.equal(res.status, 0, res.stderr || res.stdout);
  const manifestPath = path.join(out, 'home', 'dropdown', 'manifest.json');
  assert.equal(existsSync(manifestPath), true);
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  assert.equal(manifest.status, 'empty');
  assert.equal(manifest.kind, 'dropdown');
  assert.equal(manifest.paperBoard, INTERACTIVE_COMPONENTS_BOARD);
  assert.equal(manifest.states.length, 0);
  assert.match(manifest.reason, /allow-dropdown/);
  assert.equal(existsSync(path.join(out, 'home', 'dropdown', '00-closed.html')), false);
  assert.equal(existsSync(path.join(out, 'home', 'dropdown', '00-open.html')), false);
});

test('dropdown captures at 1600, not the A/6 1440 default', () => {
  assert.equal(DESKTOP_DROPDOWN_WIDTH, 1600);
  assert.equal(dropdownCaptureWidth(), 1600);
  assert.equal(dropdownCaptureWidth(undefined), 1600);
  assert.equal(dropdownCaptureWidth(1440), 1600);
  assert.equal(dropdownCaptureWidth('1440'), 1600);
  assert.equal(dropdownCaptureWidth(1920), 1920);
  assert.equal(dropdownCaptureWidth(390), 390);
  assert.equal(kindCaptureWidth('dropdown', 1440), 1600);
  assert.equal(kindCaptureWidth('dropdown'), 1600);
  assert.equal(kindCaptureWidth('nav', 1440), 1440);
  assert.equal(kindCaptureWidth('faq', 1440), 1440);
  assert.equal(paperBoardWidth({ kind: 'dropdown' }), `${INTERACTIVE_COMPONENTS_WIDTH}px`);
  assert.equal(paperBoardWidth({ kind: 'faq', mode: 'accordion' }), null);
});

test('capture-menu-states defaults to 1600 and writes HTML, not JSON-only', () => {
  const src = readFileSync(MENU, 'utf8');
  assert.doesNotMatch(src, /viewport:\s*\{\s*width:\s*1440/);
  assert.doesNotMatch(src, /viewportWidth:\s*1440/);
  assert.match(src, /DESKTOP_DROPDOWN_WIDTH|1600/);
  assert.match(src, /writeDropdownPairFiles/);

  const defaults = parseMenuCaptureArgs(['node', MENU]);
  assert.equal(defaults.width, 1600);
  assert.equal(defaults.paperBoard, INTERACTIVE_COMPONENTS_BOARD);
  assert.match(defaults.dir, /home\/dropdown$/);
  assert.equal(defaults.json, null);

  const jsonOut = parseMenuCaptureArgs(['node', MENU, '--out', '/tmp/taro-menu.json', '--width', '1440']);
  assert.equal(jsonOut.width, 1600);
  assert.equal(jsonOut.json, '/tmp/taro-menu.json');
  assert.equal(jsonOut.dir, '/tmp/taro-menu');

  const explicit = parseMenuCaptureArgs(['node', MENU, '--width', '1920', '--page', 'home', '--out', '/tmp/components']);
  assert.equal(explicit.width, 1920);
  assert.equal(explicit.dir, '/tmp/components/home/dropdown');

  const nested = resolveDropdownOutDir('/tmp/site/home/dropdown', 'home');
  assert.equal(nested.dir, '/tmp/site/home/dropdown');

  const out = mkdtempSync(path.join(tmpdir(), 'hr-menu-html-'));
  const pair = {
    triggerLabel: 'All Pages',
    triggerBox: [80, 20, 93, 27],
    navBox: [40, 20, 720, 360],
    rootSel: '[data-hr-nav]',
    hoverConfirmed: true,
    items: [{ label: 'Explore Demos' }, { label: 'About' }],
    closed: { html: '<div style="width: 93px; height: 27px">All Pages</div>' },
    open: { html: '<div style="width: 720px; height: 360px">All Pages Explore Demos About</div>' },
  };
  const manifest = writeDropdownPairFiles({
    dir: out,
    pair,
    url: 'https://example.test/',
    page: 'home',
    pageSlug: 'home',
    viewportWidth: 1600,
    viewportHeight: 1100,
  });
  assert.equal(manifest.paperBoard, INTERACTIVE_COMPONENTS_BOARD);
  assert.doesNotMatch(manifest.paperBoard, /A\/6/);
  assert.equal(manifest.viewport.width, 1600);
  assert.equal(manifest.kind, 'dropdown');
  assert.equal(existsSync(path.join(out, '00-closed.html')), true);
  assert.equal(existsSync(path.join(out, '00-open.html')), true);
  assert.equal(existsSync(path.join(out, 'manifest.json')), true);
  const closed = readFileSync(path.join(out, '00-closed.html'), 'utf8');
  assert.match(closed, /width: 100%/);
  assert.match(closed, /height: fit-content/);
  assert.match(closed, /align-items: flex-start/);

  const missing = spawnSync(process.execPath, [MENU], { encoding: 'utf8' });
  assert.equal(missing.status, 1);
  assert.match(missing.stderr, /need --url/);
});

test('writeDropdownPairs stores multiple human picks on Interactive components', () => {
  const out = mkdtempSync(path.join(tmpdir(), 'hr-dd-multi-'));
  const manifest = writeDropdownPairs({
    dir: out,
    page: 'home',
    pageSlug: 'home',
    pairs: [
      {
        triggerLabel: 'All Pages',
        triggerBox: [80, 20, 93, 27],
        navBox: [40, 20, 720, 360],
        rootSel: '[data-hr-nav]',
        hoverConfirmed: true,
        closed: { html: '<div>All Pages</div>' },
        open: { html: '<div>All Pages Homepage</div>' },
      },
      {
        triggerLabel: 'Shop By Category',
        triggerBox: [10, 20, 120, 27],
        navBox: [10, 20, 400, 280],
        rootSel: '[data-hr-nav]',
        hoverConfirmed: true,
        closed: { html: '<div>Shop</div>' },
        open: { html: '<div>Shop Hats</div>' },
      },
    ],
  });
  assert.equal(manifest.paperBoard, INTERACTIVE_COMPONENTS_BOARD);
  assert.equal(manifest.states.length, 2);
  assert.equal(manifest.states[0].component, '01 · all-pages');
  assert.equal(existsSync(path.join(out, '00-all-pages-closed.html')), true);
  assert.equal(existsSync(path.join(out, '01-shop-by-category-open.html')), true);
});

test('navbar-dropdown alias is dropdown; hamburgers stay 4.1-M', () => {
  const alias = mkdtempSync(path.join(tmpdir(), 'hr-dd-alias-'));
  const res = spawnSync(process.execPath, [
    CAPTURE,
    '--url', 'https://example.test/',
    '--kind', 'navbar-dropdown',
    '--page', 'home',
    '--out', alias,
  ], { encoding: 'utf8' });
  assert.equal(res.status, 0, res.stderr || res.stdout);
  const manifest = JSON.parse(readFileSync(path.join(alias, 'home', 'dropdown', 'manifest.json'), 'utf8'));
  assert.equal(manifest.kind, 'dropdown');
  assert.equal(manifest.status, 'empty');

  assert.equal(looksLikeHamburger({
    width: 42, height: 42, label: 'Menu', aria: 'Open menu', viewportWidth: 390,
  }), true);
  assert.equal(looksLikeHamburger({
    width: 93, height: 27, label: 'Products', viewportWidth: 1440,
  }), false);
});

test('burger rows emit onto Interactive components — not A/6', () => {
  assert.equal(isHamburgerKind('nav-mobile-768'), true);
  assert.equal(isHamburgerKind('nav-mobile-390'), true);
  assert.equal(isInteractiveKind('hamburger', 'hamburger'), true);
  assert.equal(paperBoardName({ kind: 'nav-mobile-768' }), INTERACTIVE_COMPONENTS_BOARD);
  assert.equal(paperBoardName({ kind: 'nav-mobile-390', mode: 'hamburger' }), 'Navigation');
  assert.doesNotMatch(paperBoardName({ kind: 'nav-mobile-390' }), /A\/6/);
  assert.equal(paperBoardName({ kind: 'faq', pageSlug: 'home' }), 'Components');

  assert.deepEqual(interactiveRowMeta({ kind: 'dropdown' }), {
    sid: '01', token: 'navbar-dropdown', section: 'Dropdown',
  });
  assert.deepEqual(interactiveRowMeta({ kind: 'nav-mobile-768', viewportWidth: 768 }), {
    sid: '02', token: 'nav-mobile-768', section: 'Nav mobile',
  });
  assert.deepEqual(interactiveRowMeta({ kind: 'nav-mobile-390', viewportWidth: 390 }), {
    sid: '03', token: 'nav-mobile-390', section: 'Nav mobile',
  });
  assert.equal(hamburgerKindWidth('nav-mobile-768'), 768);
  assert.equal(hamburgerKindWidth('nav-mobile-390'), 390);
  assert.equal(kindCaptureWidth('nav-mobile-768', 1440), 768);

  const parsed = parseHamburgerCaptureArgs(['node', 'x', '--width', '768', '--page', 'home', '--out', '/tmp/components']);
  assert.equal(parsed.paperBoard, INTERACTIVE_COMPONENTS_BOARD);
  assert.equal(parsed.width, 768);
  assert.equal(parsed.row.sid, '02');
  assert.equal(parsed.row.token, 'nav-mobile-768');
  assert.match(parsed.dir, /nav-mobile-768$/);

  const out = mkdtempSync(path.join(tmpdir(), 'hr-burger-'));
  const manifest = writeFluidPairFiles({
    dir: out,
    kind: 'nav-mobile-390',
    mode: 'hamburger',
    viewportWidth: 390,
    viewportHeight: 844,
    pair: {
      triggerLabel: 'Menu',
      triggerBox: [340, 16, 42, 42],
      navBox: [0, 0, 390, 400],
      rootSel: '[data-hr-panel]',
      hoverConfirmed: true,
      opened: true,
      items: [{ t: 'About' }],
      closed: { html: '<div style="width: 42px; height: 42px">Menu</div>' },
      open: { html: '<div style="width: 390px; height: 400px">About Contact</div>' },
    },
  });
  assert.equal(manifest.paperBoard, INTERACTIVE_COMPONENTS_BOARD);
  assert.doesNotMatch(manifest.paperBoard, /A\/6/);
  assert.equal(manifest.states[0].component, '03 · nav-mobile-390');
  assert.equal(manifest.states[0].token, 'nav-mobile-390');
  const html = readFileSync(path.join(out, '00-closed.html'), 'utf8');
  assert.match(html, /width: fit-content|width: 42px/);
  assert.match(html, /max-width: 390px/);
  assert.match(html, /align-items: flex-start/);
  assert.match(html, /height: fit-content/);
  assert.doesNotMatch(html, /width: 100%/);

  const emptyBurger = emptyKindManifest({
    kind: 'nav-mobile-768',
    reason: 'no hamburger at this width — do not invent',
  });
  assert.equal(emptyBurger.paperBoard, INTERACTIVE_COMPONENTS_BOARD);
  assert.doesNotMatch(emptyBurger.paperBoard, /A\/6/);
});

test("Navigation dropdown groups park top-to-bottom", async () => {
  const { sortBoardGroups } = await import("../scripts/park-capture-boards.mjs");
  const rows = sortBoardGroups([
    { name: "Dropdown 02", y: 800 },
    { name: "Dropdown 01", y: 200 },
  ]);
  assert.equal(rows[0].name, "Dropdown 01");
  assert.equal(rows[1].name, "Dropdown 02");
});

test("Navigation treats placeholder as the first specimen", async () => {
  const { isNavigationSpecimen, navigationSpecimens } = await import("../scripts/park-capture-boards.mjs");
  assert.equal(isNavigationSpecimen("placeholder"), true);
  const rows = navigationSpecimens([
    { name: "header", y: 0, component: "Frame" },
    { name: "placeholder", y: 80, component: "Frame" },
  ]);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].name, "placeholder");
});

test("paper-first seeds Buttons, Components, and Navigation before the picker", async () => {
  const boards = await import("../scripts/park-capture-boards.mjs");
  assert.equal(typeof boards.ensureCaptureReviewBoards, "function");
  const phase = readFileSync(path.join(ROOT, "scripts", "run-paper-phase.mjs"), "utf8");
  assert.match(phase, /ensureCaptureReviewBoards/);
  assert.match(phase, /wantShots: true/);
  assert.match(phase, /shotsOnly = false/);
  assert.match(phase, /1\.2 needs source-sections at 1600 \/ 768 \/ 390/);
});

test("Navigation seed creates an empty titled frame before capture", async () => {
  const { ensureNavigationBoard } = await import("../scripts/park-capture-boards.mjs");
  const artboards = [
    { id: "ruler", name: "Ruler · desktop", worldX: 0, worldY: 0, width: 20000, height: 50 },
    { id: "home", name: "home-desktop", worldX: 0, worldY: 160, width: 1600, height: 900 },
  ];
  const children = new Map();
  const calls = [];
  const reply = (payload) => ({
    content: [{ type: "text", text: JSON.stringify(payload) }],
  });
  const call = async (method, args = {}) => {
    calls.push({ method, args });
    if (method === "get_basic_info") return reply({ artboards });
    if (method === "create_artboard") {
      const board = { id: "navigation", name: args.name, ...args.styles };
      artboards.push(board);
      return reply(board);
    }
    if (method === "get_children") return reply({ children: children.get(args.nodeId) || [] });
    if (method === "write_html") {
      children.set(args.targetNodeId, [{ id: "title", name: "Title", component: "Text" }]);
      return reply({ createdNodes: children.get(args.targetNodeId) });
    }
    return reply({});
  };

  const result = await ensureNavigationBoard({ call, fileId: "paper" });

  assert.equal(result.ready, true);
  assert.ok(calls.find((item) => item.method === "create_artboard" && item.args.name === "Navigation"));
  const write = calls.find((item) => item.method === "write_html");
  assert.equal(write.args.targetNodeId, "navigation");
  assert.match(write.args.html, /layer-name="Title"/);
  assert.match(write.args.html, />\s*Navigation\s*</);
  assert.doesNotMatch(write.args.html, /layer-name="placeholder"/);
  assert.doesNotMatch(write.args.html, /Navbar \/ dropdown/);
  const create = calls.find((item) => item.method === "create_artboard");
  assert.equal(create.args.styles.width, "fit-content");
  assert.equal(create.args.styles.height, "fit-content");
  assert.equal(create.args.styles.padding, "48px");
  assert.equal(create.args.styles.gap, "40px");
});

test("Navigation retry does not duplicate an existing title", async () => {
  const { ensureNavigationBoard } = await import("../scripts/park-capture-boards.mjs");
  const artboards = [{ id: "navigation", name: "Navigation", worldX: 0, worldY: 108, width: 1800, height: 128 }];
  const children = new Map([["navigation", [{ id: "title", name: "Title", component: "Text" }]]]);
  const calls = [];
  const reply = (payload) => ({ content: [{ type: "text", text: JSON.stringify(payload) }] });
  const call = async (method, args = {}) => {
    calls.push({ method, args });
    if (method === "get_basic_info") return reply({ artboards });
    if (method === "get_children") return reply({ children: children.get(args.nodeId) || [] });
    if (method === "write_html") {
      children.set(args.targetNodeId, [
        ...children.get(args.targetNodeId),
        { id: "placeholder", name: "placeholder", component: "Frame" },
      ]);
      return reply({ createdNodes: [{ id: "placeholder" }] });
    }
    return reply({});
  };

  const result = await ensureNavigationBoard({ call, fileId: "paper" });

  assert.equal(result.ready, true);
  assert.equal(calls.filter((item) => item.method === "write_html").length, 0);
});

test("Navbar specimen removes the dropdown-only open state", () => {
  const park = readFileSync(path.join(ROOT, "scripts", "park-capture-boards.mjs"), "utf8");
  const navbar = park.slice(park.indexOf("export async function parkNavbarOnNavigation"), park.indexOf("export async function parkDropdownsOnNavigation"));
  assert.match(navbar, /removeNavbarOpenState/);
});

test("HUD widths follow Navbar overlays on each lander frame", async () => {
  const { landerNavbarWidths, paperNavbarsReady } = await import("../scripts/park-capture-boards.mjs");
  const artboards = [
    { id: "d", name: "home-desktop" },
    { id: "t", name: "home-768" },
    { id: "m", name: "home-390" },
    { id: "n", name: "Navigation" },
  ];
  const kids = {
    d: [{ name: "Navbar" }],
    t: [{ name: "hero-section" }],
    m: [{ name: "Navbar" }],
    n: [{ name: "Navbar" }],
  };
  const reply = (payload) => ({
    content: [{ type: "text", text: JSON.stringify(payload) }],
  });
  const call = async (method, args = {}) => {
    if (method === "get_basic_info") return reply({ artboards });
    if (method === "get_children") return reply({ children: kids[args.nodeId] || [] });
    return reply({});
  };
  const widths = await landerNavbarWidths({ call, fileId: "paper", pageSlug: "home" });
  assert.deepEqual(widths, { 1600: "done", 768: "queue", 390: "done" });
  assert.equal(await paperNavbarsReady({ call, fileId: "paper", pageSlug: "home" }), false);
  kids.t = [{ name: "Navbar" }];
  assert.equal(await paperNavbarsReady({ call, fileId: "paper", pageSlug: "home" }), true);
});

test("1.2 seed creates empty Buttons, Components, and Navigation frames", async () => {
  const {
    ensureCaptureReviewBoards,
    REVIEW_BOARD_WIDTH,
    NAVIGATION_BOARD_WIDTH,
    REVIEW_BOARD_PARK_WIDTH,
    NAVIGATION_BOARD_PARK_WIDTH,
  } = await import("../scripts/park-capture-boards.mjs");
  const artboards = [
    { id: "ruler", name: "Ruler · desktop", worldX: 0, worldY: 0, width: 20000, height: 50 },
    { id: "home", name: "home-desktop", worldX: 0, worldY: 160, width: 1600, height: 900 },
  ];
  const children = new Map();
  const writes = [];
  const creates = [];
  const reply = (payload) => ({
    content: [{ type: "text", text: JSON.stringify(payload) }],
  });
  const call = async (method, args = {}) => {
    if (method === "get_basic_info") return reply({ artboards });
    if (method === "create_artboard") {
      creates.push(args);
      const board = { id: args.name.toLowerCase().replace(/\s+/g, "-"), name: args.name };
      artboards.push(board);
      return reply(board);
    }
    if (method === "get_children") return reply({ children: children.get(args.nodeId) || [] });
    if (method === "write_html") {
      writes.push(args.html);
      children.set(args.targetNodeId, [{ id: `${args.targetNodeId}-title`, name: "Title", component: "Text" }]);
      return reply({ createdNodes: children.get(args.targetNodeId) });
    }
    return reply({});
  };

  const result = await ensureCaptureReviewBoards({ call, fileId: "paper" });
  assert.equal(result.ready, true);
  assert.deepEqual(result.boards, ["Buttons", "Components", "Navigation"]);
  assert.ok(artboards.find((b) => b.name === "Buttons"));
  assert.ok(artboards.find((b) => b.name === "Components"));
  assert.ok(artboards.find((b) => b.name === "Navigation"));
  assert.equal(REVIEW_BOARD_WIDTH, "fit-content");
  assert.equal(NAVIGATION_BOARD_WIDTH, "fit-content");
  assert.equal(REVIEW_BOARD_PARK_WIDTH, 1400);
  assert.equal(NAVIGATION_BOARD_PARK_WIDTH, 1800);
  assert.equal(creates.length, 3);
  for (const created of creates) {
    assert.equal(created.styles.width, "fit-content");
    assert.equal(created.styles.height, "fit-content");
  }
  assert.deepEqual(children.get("buttons").map((c) => c.name), ["Title"]);
  assert.deepEqual(children.get("components").map((c) => c.name), ["Title"]);
  assert.deepEqual(children.get("navigation").map((c) => c.name), ["Title"]);
  for (const html of writes) {
    assert.doesNotMatch(html, /layer-name="Component 01"/);
    assert.doesNotMatch(html, /layer-name="Object 01"/);
    assert.doesNotMatch(html, /layer-name="placeholder"/);
    assert.doesNotMatch(html, />Button hover</);
  }
});

test("1.2 seed deletes leftover empty Button hover / component cards", async () => {
  const { ensureHoverStatesBoard } = await import("../scripts/park-capture-boards.mjs");
  const artboards = [{ id: "hover-states", name: "Hover States" }];
  const children = new Map([["hover-states", [
    { id: "title", name: "Title", component: "Text" },
    { id: "c01", name: "Component 01", component: "Frame" },
  ]]]);
  children.set("c01", [{ id: "states", name: "states", component: "Frame" }]);
  children.set("states", [{ id: "first", name: "first", component: "Frame" }]);
  children.set("first", [{ id: "slot", name: "slot", component: "Frame" }]);
  children.set("slot", []);
  const deleted = [];
  const reply = (payload) => ({ content: [{ type: "text", text: JSON.stringify(payload) }] });
  const call = async (method, args = {}) => {
    if (method === "get_basic_info") return reply({ artboards });
    if (method === "get_children") return reply({ children: children.get(args.nodeId) || [] });
    if (method === "delete_nodes") {
      deleted.push(...args.nodeIds);
      children.set("hover-states", children.get("hover-states").filter((n) => !args.nodeIds.includes(n.id)));
    }
    return reply({});
  };

  const result = await ensureHoverStatesBoard({ call, fileId: "paper" });
  assert.equal(result.ready, true);
  assert.deepEqual(deleted, ["c01"]);
  assert.deepEqual(children.get("hover-states").map((n) => n.name), ["Title"]);
});

test("seed HTML is title-only; park rows stay as writable templates", async () => {
  const {
    hoverStatesPlaceholderHtml,
    componentsPlaceholderHtml,
    navigationPlaceholderHtml,
    reviewRowHtml,
    navigationRowHtml,
  } = await import("../scripts/park-capture-boards.mjs");
  const hover = hoverStatesPlaceholderHtml();
  const components = componentsPlaceholderHtml();
  const navigation = navigationPlaceholderHtml();
  assert.match(hover, /layer-name="Title"[^>]*>\s*Buttons\s*</);
  assert.doesNotMatch(hover, /layer-name="Component 01"/);
  assert.match(components, /layer-name="Title"[^>]*>\s*Components\s*</);
  assert.doesNotMatch(components, /layer-name="Object 01"/);
  assert.match(navigation, /layer-name="Title"[^>]*>\s*Navigation\s*</);
  assert.doesNotMatch(navigation, /layer-name="placeholder"/);
  const row = reviewRowHtml({ name: "Component 01", label: "Button hover", pair: true });
  assert.match(row, /layer-name="Component 01"/);
  assert.match(row, />Button hover</);
  assert.match(row, /layer-name="section-number"/);
  assert.match(row, />01</);
  const sourced = reviewRowHtml({
    name: "Object 01",
    label: "Content Widget",
    pair: false,
    sid: "02",
  });
  assert.match(sourced, />02</);
  assert.match(sourced, />Content Widget</);
  assert.match(navigationRowHtml(), /layer-name="placeholder"/);
  assert.match(navigationRowHtml(), />\s*Navbar \/ dropdown\s*</);
});

test("first hover park writes a Component row onto an empty board", async () => {
  const { parkOneHoverOnBoard } = await import("../scripts/park-capture-boards.mjs");
  const artboards = [{ id: "hover-states", name: "Buttons" }];
  const children = new Map([["hover-states", [{ id: "title", name: "Title", component: "Text" }]]]);
  const calls = [];
  const reply = (payload) => ({ content: [{ type: "text", text: JSON.stringify(payload) }] });
  const call = async (method, args = {}) => {
    calls.push({ method, args });
    if (method === "get_basic_info") return reply({ artboards });
    if (method === "get_children") return reply({ children: children.get(args.nodeId) || [] });
    if (method === "write_html") {
      if (args.targetNodeId === "hover-states") {
        children.set("hover-states", [
          { id: "title", name: "Title", component: "Text" },
          { id: "c01", name: "Component 01", component: "Frame" },
        ]);
        children.set("c01", [
          { id: "c-title", name: "title", component: "Frame" },
          { id: "states", name: "states", component: "Frame" },
        ]);
        children.set("states", [
          { id: "first", name: "first", component: "Frame" },
          { id: "second", name: "second", component: "Frame" },
        ]);
        children.set("first", [{ id: "slot-a", name: "slot", component: "Frame" }]);
        children.set("second", [{ id: "slot-b", name: "slot", component: "Frame" }]);
        children.set("slot-a", []);
        children.set("slot-b", []);
      } else {
        children.set(args.targetNodeId, [{ id: `${args.targetNodeId}-take`, name: "take", component: "Frame" }]);
      }
      return reply({ createdNodes: [{ id: "wrote" }] });
    }
    return reply({});
  };

  const result = await parkOneHoverOnBoard({
    call,
    fileId: "paper",
    sid: "01",
    label: "Primary",
    defaultHtml: "<button>Go</button>",
    hoverHtml: "<button>Go hover</button>",
  });
  assert.equal(result.written, true);
  const seed = calls.find((item) => item.method === "write_html" && item.args.targetNodeId === "hover-states");
  assert.match(seed.args.html, /layer-name="Component 01"/);
  assert.match(seed.args.html, />Primary</);
});

test("duplicate_nodes replies expose the new node id", async () => {
  const { parseDupId } = await import("../scripts/park-capture-boards.mjs");
  assert.equal(parseDupId({ newNodeIds: ["5HR-0"] }).id, "5HR-0");
  assert.equal(parseDupId({ sourceId: "2OF-0", descendantIdMap: { "2OF-0": "5HR-0" } }).id, "5HR-0");
  assert.equal(parseDupId({ createdNodes: [{ id: "AB-0" }] }).id, "AB-0");
});

test("extra dropdowns append after parked Navbar / Dropdown 01", async () => {
  const { nextDropdownIndex, isParkedNavigationName } = await import("../scripts/park-capture-boards.mjs");
  assert.equal(isParkedNavigationName("Navbar"), true);
  assert.equal(isParkedNavigationName("Dropdown 01"), true);
  assert.equal(nextDropdownIndex([
    { name: "Navbar", y: 0 },
    { name: "Dropdown 01", y: 200 },
  ]), 2);
});

test("Buttons stacks Component rows", async () => {
  const { hoverSpecimens, isHoverSpecimen } = await import("../scripts/park-capture-boards.mjs");
  assert.equal(isHoverSpecimen("Component 01"), true);
  assert.equal(isHoverSpecimen("header"), false);
  assert.deepEqual(hoverSpecimens([
    { name: "header", y: 64 },
    { name: "Component 02", y: 800 },
    { name: "Component 01", y: 260 },
  ]).map((n) => n.name), ["Component 01", "Component 02"]);
});

test("Components appends after existing single and multi-state rows", async () => {
  const { nextComponentIndex } = await import("../scripts/park-capture-boards.mjs");
  const rows = [
    { name: "header" },
    { name: "Component 01" },
    { name: "Component 03" },
    { name: "Object 01" },
    { name: "Object 02" },
  ];
  assert.equal(nextComponentIndex(rows, "Component"), 4);
  assert.equal(nextComponentIndex(rows, "Object"), 3);
});
