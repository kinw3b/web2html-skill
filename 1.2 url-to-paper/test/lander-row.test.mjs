import test from 'node:test';
import assert from 'node:assert/strict';
import {
  contentOrigin,
  DESIGN_LIBRARY_NAME,
  ignoresLanderRightEdge,
  INTERACTIVE_COMPONENTS,
  isReviewBoard,
  LANDER_NAMES,
  landerRightEdge,
  LIBRARY_WIDTH,
  PARK_BUFFER,
  RULER_WIDTH,
  ensureRulers,
  landerRowArtboards,
  libraryPark,
  planLanderRow,
  RULER_THICK,
} from '../scripts/rulers.mjs';
import {
  DESIGN_LIBRARY_REFERENCE_HTML,
  ensureDesignLibrary,
  foundationsSheetContext,
  renderFoundationsChunks,
  updateDesignLibrary,
} from '../scripts/library-sheet.mjs';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

test('content hangs below a single desktop ruler', () => {
  const origin = contentOrigin([
    { name: 'Ruler · desktop', worldX: 0, worldY: 0, width: 20000, height: 8 },
  ]);
  assert.equal(origin.left, 0);
  assert.equal(origin.top, RULER_THICK + PARK_BUFFER);
});

test('planLanderRow places desktop, tablet, mobile left to right on one Y', () => {
  const planned = planLanderRow([
    { id: 'r', name: 'Ruler · desktop', width: 20000, height: 8 },
    { id: 'd', name: 'home-desktop', width: 1600, height: 4000 },
    { id: 'm', name: 'home-390', width: 390, height: 5000 },
    { id: 't', name: 'home-768', width: 768, height: 4200 },
  ], { gap: 120, originX: 0, originY: 108 });

  assert.deepEqual(planned.map((p) => p.name), LANDER_NAMES);
  assert.equal(planned[0].x, 0);
  assert.equal(planned[1].x, 1600 + 120);
  assert.equal(planned[2].x, 1600 + 120 + 768 + 120);
  assert.ok(planned.every((p) => p.y === 108));
});

test('Interactive components is a review board and is ignored for lander rightEdge', () => {
  assert.equal(isReviewBoard(INTERACTIVE_COMPONENTS), true);
  assert.equal(ignoresLanderRightEdge(INTERACTIVE_COMPONENTS), true);
  assert.equal(ignoresLanderRightEdge('Design Library'), true);
  assert.equal(ignoresLanderRightEdge('A/6 · home · states'), true);
  assert.equal(ignoresLanderRightEdge('Source · home'), false);
  assert.equal(ignoresLanderRightEdge('home-desktop'), false);

  const edge = landerRightEdge([
    { name: 'Ruler · desktop', worldX: 0, width: 20000 },
    { name: 'Source · home', worldX: 0, width: 1700 },
    { name: 'home-desktop', worldX: 1860, width: 1600 },
    { name: INTERACTIVE_COMPONENTS, worldX: 5000, width: 1400 },
    { name: 'A/6 · home · states', worldX: 4000, width: 1240 },
    { name: 'Design Library', worldX: 3600, width: 1200 },
  ], 0);
  assert.equal(edge, 1860 + 1600);
});

test('Design Library sits first, never between desktop and tablet', () => {
  const boards = [
    { id: 'r', name: 'Ruler · desktop', width: 20000, height: 8, worldX: 0, worldY: 0 },
    { id: 'lib', name: DESIGN_LIBRARY_NAME, width: 1200, height: 4000, worldX: -1360, worldY: 108 },
    { id: 'd', name: 'home-desktop', width: 1600, height: 4000, worldX: 0, worldY: 108 },
    { id: 't', name: 'home-768', width: 768, height: 4200, worldX: 1720, worldY: 108 },
    { id: 'm', name: 'home-390', width: 390, height: 5000, worldX: 2608, worldY: 108 },
  ];
  const planned = planLanderRow(boards, { gap: 120, originX: 0, originY: 108 });
  assert.deepEqual(planned.map((p) => p.name), [DESIGN_LIBRARY_NAME, ...LANDER_NAMES]);
  assert.equal(planned[0].name, DESIGN_LIBRARY_NAME);
  assert.equal(planned[0].x, 0);
  assert.equal(planned[1].name, 'home-desktop');
  assert.equal(planned[1].x, 1200 + 120);
  const row = landerRowArtboards(boards);
  assert.ok(row.some((b) => b.name === DESIGN_LIBRARY_NAME));
});

test('libraryPark sits left of screenshots + landers', () => {
  const empty = libraryPark({ originX: 0, originY: 108 });
  assert.equal(empty.x, 0);
  assert.equal(empty.y, 108);
  const before = libraryPark({
    originX: 0,
    originY: 108,
    boards: [
      { name: 'Source · home', worldX: 0, width: 1700 },
      { name: 'home-desktop', worldX: 1860, width: 1600 },
      { name: 'home-768', worldX: 3580, width: 768 },
      { name: 'home-390', worldX: 4468, width: 390 },
    ],
  });
  assert.equal(before.x, 0 - LIBRARY_WIDTH - 160);
  const right = libraryPark({ originX: 0, originY: 108, side: 'right' });
  assert.ok(right.x >= RULER_WIDTH);
});

function mockPaper() {
  const calls = [];
  const nodes = new Map();
  let seq = 1;
  const call = async (name, args = {}) => {
    calls.push({ name, args });
    if (name === 'create_artboard') {
      const id = `node-${seq++}`;
      nodes.set(id, { id, name: args.name, styles: args.styles });
      return { content: [{ type: 'text', text: JSON.stringify({ id }) }] };
    }
    if (name === 'write_html') {
      const id = `node-${seq++}`;
      return { content: [{ type: 'text', text: JSON.stringify({ createdNodes: [{ id }] }) }] };
    }
    if (name === 'get_children') {
      return { content: [{ type: 'text', text: JSON.stringify({ children: [] }) }] };
    }
    return { content: [{ type: 'text', text: '{}' }] };
  };
  return { call, calls, nodes };
}

test('--init path creates only Ruler · desktop (unit, no live Paper)', async () => {
  const { call, calls, nodes } = mockPaper();
  const fileId = 'FILE-TEST';
  const rulers = await ensureRulers({
    call,
    fileId,
    boards: [],
    init: true,
  });
  const library = await ensureDesignLibrary({
    call,
    fileId,
    boards: [],
    init: true,
  });
  const names = [...nodes.values()].map((n) => n.name);
  assert.deepEqual(names, ['Ruler · desktop']);
  assert.equal(rulers[0].name, 'Ruler · desktop');
  assert.equal(library, null);
  assert.ok(calls.every((c) => c.args.fileId === fileId));
  assert.ok(!calls.some((c) => c.name === 'write_html'));
});

test('updateDesignLibrary is the sole missing-board creation path', async () => {
  const { call, calls, nodes } = mockPaper();
  const updated = await updateDesignLibrary({
    call,
    fileId: 'FILE-TEST',
    boards: [],
    lib: { proposedTokens: [] },
    pace: 0,
  });
  assert.equal(updated.name, DESIGN_LIBRARY_NAME);
  assert.equal([...nodes.values()].filter((n) => n.name === DESIGN_LIBRARY_NAME).length, 1);
  assert.equal(calls.filter((c) => c.name === 'create_artboard').length, 1);
  assert.ok(calls.some((c) => c.name === 'write_html'));
});

test('draw-rulers does not create or seed Design Library', () => {
  const source = readFileSync(
    fileURLToPath(new URL('../scripts/draw-rulers.mjs', import.meta.url)),
    'utf8',
  );
  assert.doesNotMatch(source, /ensureDesignLibrary/);
  assert.match(source, /ensureRulers/);
});

test('seed foundations HTML has five sections, DISPLAY, and MINED/SEMANTIC chrome', () => {
  const { ctx, chunks } = renderFoundationsChunks({}, { seed: true });
  assert.deepEqual(chunks.map((c) => c.name), [
    'header', 'colour', 'typography', 'spacing', 'elevation-radii',
  ]);
  const html = chunks.map((c) => c.html).join('\n');
  assert.match(html, /MINED/);
  assert.match(html, /SEMANTIC/);
  assert.match(html, /DISPLAY/);
  assert.match(html, /--text-7xl/);
  assert.match(html, /--text-9xl/);
  assert.match(html, /--text-12xl/);
  assert.match(html, />Aa</);
  assert.match(html, /width:250px/);
  assert.match(html, /--color-warning/);
  assert.doesNotMatch(html, /--text-display/);
  assert.match(html, /TAILWIND DEFAULT/);
  assert.doesNotMatch(html, /Outfit/);
  assert.doesNotMatch(html, /#6052FF/i);
  assert.equal(ctx.sizesScale[0]?.name, '--text-12xl');
  assert.equal(ctx.sizesScale.at(-1)?.name, '--text-xs');
  assert.ok(ctx.sizesDisplay.some((t) => t.name === '--text-7xl' && t.value === '72px'));
  assert.ok(ctx.sizesDisplay.some((t) => t.name === '--text-9xl' && t.value === '128px'));
  assert.ok(ctx.sizesDisplay.some((t) => t.name === '--text-12xl' && t.value === '224px'));
  assert.ok(!ctx.sizesDisplay.some((t) => t.name === '--text-display' || t.name === '--text-display-xl'));
  assert.ok(ctx.colorsSurfaceSemantic.filter((t) => [
    '--color-danger', '--color-warning', '--color-success', '--color-info', '--color-muted',
  ].includes(t.name)).length >= 5);
  const sheet = foundationsSheetContext({
    proposedTokens: [
      { type: 'color', name: '--color-accent', value: '#112233' },
      { type: 'fontFamily', name: '--font-sans', value: 'Satoshi', family: 'Satoshi' },
      { type: 'spacing', name: '--spacing-9', value: '99px' },
      { type: 'fontSize', name: '--text-6xl', value: '99px' },
      { type: 'fontSize', name: '--text-80', value: '80px', source: 'mined', step: '80', sheetGroup: 'display', onSheet: true },
    ],
  }, { seed: false });
  assert.ok(sheet.colorsSurfaceMined.some((t) => t.name === '--color-accent' && t.value === '#112233'));
  assert.ok(sheet.families.some((t) => t.label === 'Satoshi'));
  assert.ok(sheet.spacing.every((t) => t.source === 'tailwind-default'));
  assert.ok(!sheet.spacing.some((t) => t.value === '99px'));
  assert.ok(sheet.sizesScale.some((t) => t.name === '--text-6xl' && t.value === '60px'));
  const mined80 = sheet.sizesScale.find((t) => t.name === '--text-80');
  assert.equal(mined80?.value, '80px');
  assert.match(mined80?.minedBadge || '', /MINED/);
  assert.match(mined80?.minedBadge || '', /#E11D2E/i);
  const colourHtml = chunks.find((c) => c.name === 'colour')?.html || '';
  assert.match(colourHtml, /background:#E11D2E/);
});

test('Design Library drops first, then Screenshots, landers, Buttons, Components, Navigation', () => {
  assert.equal(isReviewBoard('Source · home'), true);
  assert.equal(isReviewBoard('Screenshots'), true);
  assert.equal(isReviewBoard('Buttons'), true);
  assert.equal(isReviewBoard('Hover States'), true);
  assert.equal(isReviewBoard('Components'), true);
  assert.equal(isReviewBoard('Navigation'), true);
  assert.equal(isReviewBoard('home-desktop'), false);
  assert.equal(LANDER_NAMES.includes('Source · home'), false);

  const planned = planLanderRow([
    { id: 'r', name: 'Ruler · desktop', width: 20000, height: 8 },
    { id: 'lib', name: DESIGN_LIBRARY_NAME, width: 1200, height: 4000 },
    { id: 'nav', name: 'Navigation', width: 1800, height: 400 },
    { id: 'comp', name: 'Components', width: 1600, height: 400 },
    { id: 'hov', name: 'Buttons', width: 1600, height: 800 },
    { id: 's', name: 'Screenshots', width: 1700, height: 4000 },
    { id: 'd', name: 'home-desktop', width: 1600, height: 4000 },
    { id: 't', name: 'home-768', width: 768, height: 4200 },
    { id: 'm', name: 'home-390', width: 390, height: 5000 },
  ], { gap: 120, originX: 0, originY: 108 });

  assert.deepEqual(planned.map((p) => p.name), [
    DESIGN_LIBRARY_NAME,
    'Screenshots',
    'home-desktop',
    'home-768',
    'home-390',
    'Buttons',
    'Components',
    'Navigation',
  ]);
  assert.equal(planned[0].x, 0);
  assert.equal(planned[1].x, 1200 + 120);
  assert.equal(planned[2].x, 1200 + 120 + 1700 + 120);
  assert.ok(planned.every((p) => p.y === 108));
});

test('step 1.4 keeps a local HTML reference for the Design Library shell', () => {
  const reference = readFileSync(DESIGN_LIBRARY_REFERENCE_HTML, 'utf8');
  assert.match(reference, /width: 1200px/);
  assert.match(reference, />Foundations</);
  assert.match(reference, />Colour</);
  assert.match(reference, />Typography</);
  assert.match(reference, />Spacing</);
  assert.match(reference, />Elevation & Radii</);
});
