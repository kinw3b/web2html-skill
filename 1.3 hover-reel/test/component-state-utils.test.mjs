import test from 'node:test';
import assert from 'node:assert/strict';
import * as componentStateUtils from '../scripts/component-state-utils.mjs';
import {
  a6BoardWidthPx,
  applyAncestorFill,
  assignDesignSystemTokens,
  centerDesktopFlex,
  designSystemEyebrow,
  designSystemToken,
  faqFitStyles,
  fluidInteractiveFitStyles,
  htmlChanged,
  isFaqKind,
  isFluidInteractiveKind,
  isHugParentKind,
  isGeometryLockedRoot,
  paperCellWidth,
  paperRootBox,
  paperSlotBox,
  patternKey,
  prepareFaqStateHtml,
  normalizePaperRoot,
  sectionLabelForRect,
  shouldWidenBoardForKind,
  stripAccordionIconTransforms,
  styleDelta,
  uniquePageEntries,
  objectTypeLabel,
  pickStatesForSection,
  hasVisibleHoverDelta,
  isHumanClickPair,
  isSourceCta,
  asNamedButtonHtml,
  sourceHoverItemHtml,
  unwrapSerializerHtml,
  sourceHoverStackInnerHtml,
  sourceHoverStackHtml,
  leftoverSourceSectionBadgeIds,
  SOURCE_HEADING_FILL,
  SOURCE_HOVER_PAD,
  SOURCE_HOVER_WIDTH,
  paperBoardName,
  parksOnSource,
  parksOnInteractive,
} from '../scripts/component-state-utils.mjs';
import { prepareStateHtml } from '../scripts/prepare-state-html.mjs';

test('row flex children use Fill on the main axis', () => {
  assert.equal(typeof componentStateUtils.fillStylesForFlexChild, 'function');
  assert.deepEqual(componentStateUtils.fillStylesForFlexChild(
    { display: 'flex', flexDirection: 'row' },
    {},
  ), { flexGrow: '1' });
});

test('column flex children use Fill on the cross axis', () => {
  assert.deepEqual(componentStateUtils.fillStylesForFlexChild(
    { display: 'flex', flexDirection: 'column' },
    {},
  ), { alignSelf: 'stretch' });
});

test('computed flexGrow zero does not suppress row Fill', () => {
  assert.deepEqual(componentStateUtils.fillStylesForFlexChild(
    { display: 'flex', flexDirection: 'row' },
    { width: '1280px', flexGrow: 0, flexShrink: 1 },
  ), { flexGrow: '1' });
  assert.deepEqual(componentStateUtils.fillStylesForFlexChild(
    { display: 'flex', flexDirection: 'row' },
    { width: '1280px', 'flex-grow': '0' },
  ), { flexGrow: '1' });
});

test('Fill policy preserves hugged and already-filled children', () => {
  const row = { display: 'flex', flexDirection: 'row' };
  const column = { display: 'flex', flexDirection: 'column' };
  assert.deepEqual(componentStateUtils.fillStylesForFlexChild(
    row,
    { width: 'fit-content', flexGrow: '0' },
  ), {});
  assert.deepEqual(componentStateUtils.fillStylesForFlexChild(
    row,
    { flexGrow: '1' },
  ), {});
  assert.deepEqual(componentStateUtils.fillStylesForFlexChild(
    column,
    { alignSelf: 'stretch' },
  ), {});
});

test('normalizes a transparent serialized root for an isolated Paper cell', () => {
  const html = '<a style="display: block; width: min-content; height: min-content; background-color: rgb(0, 0, 0); color: rgb(0, 0, 238)" data-hr-item="0"><span style="color: rgb(255, 255, 255)">Donate</span></a>';
  const normalized = normalizePaperRoot(html, {
    rect: [0, 100, 599, 67],
    backgroundColor: 'rgba(0, 0, 0, 0)',
  });
  assert.match(normalized, /width: 599px/);
  assert.match(normalized, /height: 67px/);
  assert.match(normalized, /background-color: rgb\(0, 0, 0\)/);
  assert.doesNotMatch(normalized, /data-hr-item/);
});

test('keeps a real component background while locking its geometry', () => {
  const normalized = normalizePaperRoot(
    '<button style="background-color: rgb(20, 30, 40); width: 100px; height: 40px">Give</button>',
    { rect: [0, 0, 120, 48], backgroundColor: 'rgb(20, 30, 40)' },
  );
  assert.match(normalized, /background-color: rgb\(20, 30, 40\)/);
  assert.match(normalized, /width: 120px/);
  assert.match(normalized, /height: 48px/);
});

test('paints a transparent light-text root with the ancestor fill', () => {
  const html = '<a style="width: 160px; height: 48px; color: rgb(255, 255, 255)">Start free trial</a>';
  const filled = applyAncestorFill(html, 'rgb(18, 22, 22)');
  assert.match(filled, /background-color: rgb\(18, 22, 22\)/);
  const normalized = normalizePaperRoot(html, {
    rect: [0, 0, 160, 48],
    backgroundColor: 'rgba(0, 0, 0, 0)',
    ancestorBackground: 'rgb(18, 22, 22)',
  });
  assert.match(normalized, /background-color: rgb\(18, 22, 22\)/);
});

test('prefers the measured source fill over a serializer ancestor fallback', () => {
  const html = '<a style="background-color: rgb(255, 255, 255); color: rgb(255, 255, 255)">Trial</a>';
  const normalized = normalizePaperRoot(html, {
    rect: [0, 0, 218, 51],
    backgroundColor: 'rgb(8, 14, 19)',
    ancestorBackground: 'rgb(255, 255, 255)',
  });
  assert.match(normalized, /background-color: rgb\(8, 14, 19\)/);
});

test('does not invent a fill for transparent dark-text roots', () => {
  const html = '<a style="color: rgb(17, 17, 17)">Donate</a>';
  assert.equal(applyAncestorFill(html, 'rgb(0, 0, 0)'), html);
});

test('adds a geometry style when a serializer root has no style attribute', () => {
  const normalized = normalizePaperRoot('<div data-hr-root>Give</div>', { rect: [0, 0, 90, 32] });
  assert.match(normalized, /style="width: 90px; height: 32px"/);
});

test('records child hover style deltas, not only root changes', () => {
  const before = '<a style="color: white"><span style="opacity: 1">Give</span></a>';
  const after = '<a style="color: white"><span style="opacity: .8">Give</span></a>';
  assert.equal(htmlChanged(before, after), true);
  assert.deepEqual(styleDelta(before, after), [{ node: 1, prop: 'opacity', from: '1', to: '.8' }]);
});

test('deduplicates page URLs and maps route sections', () => {
  const pages = uniquePageEntries([
    { path: '/', url: 'https://example.test/' },
    { path: '/duplicate', url: 'https://example.test/' },
    { path: '/about', url: 'https://example.test/about' },
  ]);
  assert.equal(pages.length, 2);
  assert.equal(sectionLabelForRect([0, 550, 100, 80], [
    { name: 'Hero', top: 0, height: 500 },
    { name: 'CTA', top: 500, height: 200 },
  ]), 'CTA');
  assert.equal(sectionLabelForRect([0, 100, 100, 40], [
    { id: '02', name: 'discover-nurture-grow', top: 89, height: 832 },
  ]), '02');
});

test('prepareStateHtml flattens hover stroke overlays and stacked labels', () => {
  const html = `<a style="position: relative; width: 222px; height: 54px; background-image: linear-gradient(rgb(7, 8, 15) 0%, rgb(76, 80, 100) 100%)" data-hr-item="0"><div style="display: flex; flex-direction: column; height: 30px"><div><p>Try 14 Days Free Trial</p></div><div><p>Try 14 Days Free Trial</p></div></div><div style="position: absolute; top: 0px; right: 0px; bottom: 0px; left: 0px; width: 221.766px; height: 54px; pointer-events: none; border-top-width: 1.5px; border-right-width: 1.5px; border-bottom-width: 1.5px; border-left-width: 1.5px; border-style: solid; border-color: rgb(9, 12, 28); border-radius: 28px"></div></a>`;
  const out = prepareStateHtml(html, { rect: [0, 0, 222, 54], backgroundColor: 'rgb(7, 8, 15)' });
  assert.equal(out.removed.length, 1);
  assert.equal(out.collapsed.length, 1);
  assert.match(out.html, /border: 1\.5px solid #090C1C/);
  assert.doesNotMatch(out.html, /position: absolute/);
  assert.equal((out.html.match(/Try 14 Days Free Trial/g) || []).length, 1);
  assert.doesNotMatch(out.html, /data-hr-item/);
});

test('prepareStateHtml strips absolute button fills to CSS background', () => {
  const html = `<a style="position: relative; width: 220px; height: 54px"><div style="position: absolute; inset: 0; background-color: #C4A574"></div><p>Book A Room</p></a>`;
  const out = prepareStateHtml(html, { kind: 'buttons', rect: [0, 0, 220, 54] });
  assert.match(out.html, /background-color: #C4A574/);
  assert.doesNotMatch(out.html, /position:\s*absolute/);
  assert.match(out.html, /Book A Room/);
});

test('A/6 eyebrows use design-system tokens, not marketing copy', () => {
  assert.equal(designSystemToken({ component: 'Product' }, { kind: 'nav' }), 'navbar-link');
  assert.equal(designSystemToken({ component: 'About Us' }, { kind: 'footer' }), 'footer-link');
  assert.equal(designSystemToken({ sourceBackground: 'rgb(8, 14, 19)', rect: [0, 0, 222, 54] }, { kind: 'buttons' }), 'btn-primary');
  assert.equal(designSystemToken({ sourceBackground: 'rgb(255, 255, 255)', rect: [0, 0, 201, 54] }, { kind: 'buttons' }), 'btn-secondary');
  assert.equal(designSystemToken({ sourceBackground: 'rgb(236, 208, 70)', rect: [0, 0, 200, 54] }, { kind: 'buttons' }), 'btn-accent');
  assert.equal(designSystemEyebrow('btn-primary', 'default'), 'btn-primary');
  assert.equal(designSystemEyebrow('btn-primary', 'hover'), 'btn-primary:hover');
  assert.equal(designSystemEyebrow('pill', 'hover'), 'pill:hover');
});

test('new visual patterns get unique names; repeats share one', () => {
  const gradientCta = {
    rect: [501, 545, 222, 54],
    sourceBackground: 'rgba(0, 0, 0, 0)',
    changed: true,
    styleDelta: [{ prop: 'background-image', from: 'linear-gradient(rgb(76, 80, 100) 0%, rgb(7, 8, 14) 100%)', to: 'linear-gradient(rgb(7, 8, 15) 0%, rgb(76, 80, 100) 100%)' }],
  };
  const wideSameCta = { ...gradientCta, rect: [132, 7848, 344, 54] };
  const datePill = {
    rect: [132, 9752, 117, 36],
    sourceBackground: 'rgba(0, 0, 0, 0)',
    changed: false,
    styleDelta: [],
  };
  const footerText = {
    rect: [1056, 11462, 134, 20],
    sourceBackground: 'rgba(0, 0, 0, 0)',
    changed: true,
    styleDelta: [{ prop: 'color', from: 'rgb(72, 77, 103)', to: 'rgb(117, 139, 253)' }],
  };
  const navLink = {
    rect: [646, 43, 102, 27],
    sourceBackground: 'rgba(0, 0, 0, 0)',
    changed: true,
    styleDelta: [{ prop: 'color', from: 'rgb(9, 12, 28)', to: 'rgb(117, 139, 253)' }],
  };
  const navDropdown = {
    rect: [520, 43, 93, 27],
    sourceBackground: 'rgba(0, 0, 0, 0)',
    changed: true,
    styleDelta: [
      { prop: 'color', from: 'rgb(9, 12, 28)', to: 'rgb(117, 139, 253)' },
      { prop: 'transform', from: null, to: 'rotate(180deg)' },
    ],
  };

  assert.notEqual(patternKey(gradientCta, { kind: 'buttons' }), patternKey(datePill, { kind: 'buttons' }));
  assert.equal(patternKey(gradientCta, { kind: 'buttons' }), patternKey(wideSameCta, { kind: 'buttons' }));
  assert.equal(designSystemToken(datePill, { kind: 'buttons' }), 'pill');
  assert.equal(designSystemToken(footerText, { kind: 'buttons' }), 'text-link');
  assert.equal(designSystemToken(navDropdown, { kind: 'nav' }), 'navbar-dropdown');

  const names = assignDesignSystemTokens(
    [gradientCta, datePill, wideSameCta, footerText],
    { kind: 'buttons' },
  );
  assert.deepEqual(names, ['btn-primary', 'pill', 'btn-primary', 'text-link']);

  const navNames = assignDesignSystemTokens([navLink, navDropdown, navLink], { kind: 'nav' });
  assert.deepEqual(navNames, ['navbar-link', 'navbar-dropdown', 'navbar-link']);
});

test('compact pills match desktop Autoflex center, not Framer flex-start', () => {
  const pill = '<div style="align-items: flex-start; background-image: linear-gradient(rgb(238, 243, 251), rgb(255, 235, 242)); border-radius: 24px; display: flex; height: 36px; justify-content: flex-start; padding: 6px 16px; width: 117px">20 Jan, 2024</div>';
  const centered = centerDesktopFlex(pill);
  assert.match(centered, /align-items: center/);
  assert.match(centered, /justify-content: center/);
  assert.doesNotMatch(centered, /flex-start/);

  const normalized = normalizePaperRoot(pill, { rect: [0, 0, 117, 36] });
  assert.match(normalized, /align-items: center/);
  assert.match(normalized, /justify-content: center/);

  const slide = '<a style="align-items: center; border-radius: 28px; display: flex; height: 54px; justify-content: flex-end; padding: 12px 32px; width: 222px">Trial</a>';
  assert.match(centerDesktopFlex(slide), /justify-content: flex-end/);

  const link = '<a style="align-items: flex-start; color: rgb(72, 77, 103); display: flex; height: 20px; justify-content: flex-start">Terms</a>';
  assert.match(centerDesktopFlex(link), /justify-content: flex-start/);
});

test('FAQ / accordion roots are fluid in the A/6 parent — never captured px width', () => {
  const html = '<div style="width: 99px; height: 48px; color: rgb(17, 17, 17)">How does the free trial work?</div>';
  const box = paperRootBox({ kind: 'faq', mode: 'accordion', rect: [0, 0, 99, 48] });
  assert.deepEqual(box, {
    width: '100%',
    maxWidth: '100%',
    height: 'fit-content',
    alignItems: 'flex-start',
    alignSelf: 'flex-start',
  });
  assert.equal(paperSlotBox({ kind: 'faq' }).width, '100%');
  assert.equal(paperSlotBox({ kind: 'faq' }).maxWidth, '100%');
  assert.equal(paperCellWidth({ kind: 'faq', fallback: 'fit-content' }), '100%');
  assert.equal(isFaqKind('faq', 'accordion'), true);
  assert.equal(shouldWidenBoardForKind('faq', 'accordion'), false);

  const normalized = normalizePaperRoot(html, {
    kind: 'faq',
    mode: 'accordion',
    rect: [0, 0, 99, 48],
  });
  assert.match(normalized, /width: 100%/);
  assert.match(normalized, /max-width: 100%/);
  assert.match(normalized, /height: fit-content/);
  assert.doesNotMatch(normalized, /width: 99px/);

  const prepared = prepareStateHtml(html, { kind: 'faq', rect: [12, 80, 99, 48] });
  assert.match(prepared.html, /width: 100%/);
  assert.match(prepared.html, /max-width: 100%/);
  assert.doesNotMatch(prepared.html, /width: 99px/);

  const buttons = normalizePaperRoot(html, { kind: 'buttons', rect: [0, 0, 99, 48] });
  assert.match(buttons, /width: 99px/);
  assert.match(buttons, /height: 48px/);
  assert.equal(paperCellWidth({ kind: 'buttons', fallback: 'fit-content' }), 'fit-content');
  assert.equal(paperSlotBox({ kind: 'nav' }).width, 'fit-content');
  assert.equal(shouldWidenBoardForKind('buttons', 'elements'), true);

  const board = a6BoardWidthPx({
    kind: 'faq',
    mode: 'accordion',
    states: [{ rect: [40, 200, 99, 48] }],
  });
  assert.equal(board, 1240);
  assert.doesNotMatch(String(board), /99/);
  assert.ok(isGeometryLockedRoot(prepared.html, { kind: 'faq' }));
});

test('FAQ accordion emit is top-aligned, fit-content, and strips icon transforms', () => {
  const collapsed = '<div style="display: flex; align-items: center; width: 99px; height: 190px"><p>How does the free trial work?</p><div style="width: 35px; height: 35px; transform: rotate(45deg); translate: 12px 5px"></div></div>';
  const open = '<div style="display: flex; align-items: center; width: 600px; height: 190px"><div style="display: flex; flex-direction: column; align-items: center"><p>How does the free trial work?</p><p>You get 14 days.</p></div><div style="width: 35px; height: 35px; transform: rotate(90deg); translate: 8px 4px"></div></div>';

  const slot = paperSlotBox({ kind: 'faq', mode: 'accordion' });
  assert.equal(slot.alignItems, 'flex-start');
  assert.equal(slot.alignSelf, 'flex-start');
  assert.equal(slot.height, 'fit-content');
  assert.equal(slot.width, '100%');
  assert.equal(slot.maxWidth, '100%');
  assert.deepEqual(faqFitStyles(), {
    width: '100%',
    maxWidth: '100%',
    height: 'fit-content',
    overflow: 'visible',
    alignItems: 'flex-start',
    alignSelf: 'flex-start',
    justifyContent: 'flex-start',
  });

  for (const html of [collapsed, open]) {
    const out = prepareStateHtml(html, {
      kind: 'faq',
      mode: 'accordion',
      rect: [0, 0, 99, 190],
    });
    assert.match(out.html, /align-items: flex-start/);
    assert.match(out.html, /height: fit-content/);
    assert.match(out.html, /width: 100%/);
    assert.match(out.html, /max-width: 100%/);
    assert.doesNotMatch(out.html, /height: 190px/);
    assert.doesNotMatch(out.html, /translate/);
    assert.doesNotMatch(out.html, /rotate/);
    assert.doesNotMatch(out.html, /align-items: center/);
  }

  const stripped = stripAccordionIconTransforms(
    '<div style="width: 35px; height: 35px; transform: rotate(45deg); translate: 12px 5px; rotate: 45deg"></div>',
  );
  assert.doesNotMatch(stripped, /transform/);
  assert.doesNotMatch(stripped, /translate/);
  assert.doesNotMatch(stripped, /rotate/);

  const aligned = prepareFaqStateHtml(collapsed);
  assert.match(aligned, /align-items: flex-start/);
  assert.doesNotMatch(aligned, /height: 190px/);
});

test('dropdown hugs parent; 390 nav stays narrow then token-pass at write', async () => {
  const { bindInlineThemeTokens } = await import('../../1.2 url-to-paper/scripts/library-tokens.mjs');
  const drop = paperRootBox({ kind: 'dropdown', rect: [0, 0, 390, 84] });
  assert.equal(drop.width, '100%');
  assert.equal(isHugParentKind('dropdown'), true);
  assert.equal(isHugParentKind('nav-mobile-390'), false);
  assert.equal(isHugParentKind('forms'), false);
  const burger = paperRootBox({ kind: 'nav-mobile-390', rect: [0, 0, 362, 232] });
  assert.equal(burger.width, '362px');
  assert.equal(burger.maxWidth, '390px');
  assert.equal(burger.height, 'fit-content');
  const tablet = paperRootBox({ kind: 'nav-mobile-768', rect: [0, 0, 720, 80] });
  assert.equal(tablet.maxWidth, '768px');
  assert.equal(paperSlotBox({ kind: 'forms' }).width, 'fit-content');
  const html = '<div style="position: absolute; top: 86px; width: 100%; height: fit-content; font-size: 16px; color: #0A073B; gap: 16px">Home</div>';
  const normalized = prepareStateHtml(html, { kind: 'nav-mobile-390', mode: 'hamburger', rect: [14, 86, 362, 232] }).html;
  assert.match(normalized, /position: relative/);
  assert.doesNotMatch(normalized, /position: absolute/);
  assert.doesNotMatch(normalized, /top: 86px/);
  assert.match(normalized, /width: 362px/);
  const bound = bindInlineThemeTokens(normalized, [
    { type: 'fontSize', name: '--text-base', value: '16px' },
    { type: 'color', name: '--color-ink', value: '#0A073B' },
    { type: 'spacing', name: '--spacing-4', value: '16px' },
  ]);
  assert.match(bound, /font-size: var\(--text-base\)/);
  assert.match(bound, /color: var\(--color-ink\)/);
  assert.equal(isFluidInteractiveKind('buttons'), false);
});

test('objectTypeLabel is type-only and footer links are Text link', () => {
  assert.equal(objectTypeLabel({ token: 'btn-primary' }, 'buttons'), 'Button');
  assert.equal(objectTypeLabel({ token: 'text-link' }, 'buttons'), 'Text link');
  assert.equal(objectTypeLabel({ token: 'footer-link' }, 'footer'), 'Text link');
  assert.equal(objectTypeLabel({ token: 'navbar-link' }, 'nav'), 'Text link');
  assert.equal(objectTypeLabel({ token: 'pill' }, 'buttons'), 'Pill');
  assert.equal(objectTypeLabel({ token: 'object', type: 'Object' }, 'buttons'), 'Object');
  assert.equal(objectTypeLabel({ captureMethod: 'hover-leave', token: 'btn-primary' }, 'buttons'), 'buttons');
  assert.equal(objectTypeLabel({ captureMethod: 'press-solo', token: 'btn-primary' }, 'buttons'), 'component');
  assert.equal(objectTypeLabel({ captureMethod: 'click-solo', token: 'btn-primary' }, 'buttons'), 'component');
  assert.equal(objectTypeLabel({ captureMethod: 'click-pair', type: 'Object' }, 'buttons'), 'objects');
  assert.equal(objectTypeLabel({ type: 'component' }, 'buttons'), 'component');
  assert.equal(isHumanClickPair({ captureMethod: 'click-pair' }), true);
  assert.equal(hasVisibleHoverDelta({
    captureMethod: 'click-pair',
    type: 'objects',
    hoverFile: '12-img-2-hover.html',
    includeHover: true,
    styleDelta: [],
  }), true);
  const clickPair = pickStatesForSection([{
    sectionId: '07',
    component: '07 · img 2',
    captureMethod: 'click-pair',
    type: 'objects',
    hoverFile: '12-img-2-hover.html',
    includeHover: true,
    token: 'btn-ghost',
    changed: false,
  }], 'buttons');
  assert.equal(clickPair[0].states[0].includeHover, true);
  const groups = pickStatesForSection([
    { sectionId: '09', token: 'footer-link', component: '09 · About', sourceBackground: 'rgba(0,0,0,0)', hoverBackground: 'rgb(23, 26, 31)', changed: true },
    { sectionId: '09', token: 'footer-link', component: '09 · Appointment', sourceBackground: 'rgba(0,0,0,0)', hoverBackground: 'rgb(23, 26, 31)', changed: true },
  ], 'footer');
  assert.equal(groups[0].sid, '09');
  assert.deepEqual(groups[0].types, ['Text link']);
  assert.equal(groups[0].states.length, 2);
});


test('parks dropdowns on Navigation, objects on Components, hover on Buttons, never A/6', () => {
  assert.equal(paperBoardName({ kind: 'nav', pageSlug: 'home' }), 'Buttons');
  assert.equal(paperBoardName({ kind: 'forms', pageSlug: 'home' }), 'Components');
  assert.equal(paperBoardName({ kind: 'faq', pageSlug: 'home' }), 'Components');
  assert.equal(paperBoardName({ kind: 'dropdown', pageSlug: 'home' }), 'Navigation');
  assert.equal(paperBoardName({ kind: 'buttons', pageSlug: 'home' }), 'Buttons');
  assert.equal(paperBoardName({ kind: 'footer', pageSlug: 'home' }), 'Buttons');
  assert.equal(paperBoardName({ kind: 'objects', captureMethod: 'click-pair' }), 'Components');
  assert.equal(paperBoardName({ kind: 'buttons', captureMethod: 'click-solo', type: 'component' }), 'Components');
  assert.equal(paperBoardName({ kind: 'buttons', captureMethod: 'press-solo', type: 'component' }), 'Components');
  assert.equal(paperBoardName({ kind: 'buttons', captureMethod: 'hover-leave' }), 'Buttons');
  assert.equal(parksOnSource('buttons'), true);
  assert.equal(parksOnInteractive('dropdown'), true);
  assert.doesNotMatch(paperBoardName({ kind: 'dropdown' }), /A\/6/);
});

test('pickStatesForSection keeps one of the same button label', () => {
  const groups = pickStatesForSection([
    { sectionId: '01', label: 'Request A Free Demo', token: 'btn-a', component: '01 · Request A Free Demo', sourceBackground: 'rgb(40,208,138)', hoverBackground: 'rgb(20,160,100)', changed: true },
    { sectionId: '01', label: 'Request A Free Demo', token: 'btn-b', component: '01 · Request A Free Demo 2', sourceBackground: 'rgb(40,208,138)', hoverBackground: 'rgb(20,160,100)', changed: true },
    { sectionId: '01', label: 'Hire An Expert', token: 'btn-c', component: '01 · Hire An Expert', sourceBackground: 'rgba(0,0,0,0)', hoverBackground: 'rgb(23, 26, 31)', changed: true },
  ], 'buttons');
  assert.equal(groups[0].states.length, 2);
});

test('open hamburger panel is in-flow so Interactive components can hug it', () => {
  const html = '<div style="position: absolute; top: 86px; left: 0px; width: 100%; height: fit-content">Home</div>';
  const out = prepareStateHtml(html, { kind: 'nav-mobile-390', mode: 'hamburger' }).html;
  assert.match(out, /position: relative/);
  assert.doesNotMatch(out, /position: absolute/);
  assert.doesNotMatch(out, /top: 86px/);
});

test('identical default/hover pairs omit Hover; CTAs still park Default', () => {
  assert.equal(hasVisibleHoverDelta({
    changed: false, hoverConfirmed: false,
    sourceBackground: 'rgba(0, 0, 0, 0)', hoverBackground: 'rgba(0, 0, 0, 0)',
  }), false);
  assert.equal(hasVisibleHoverDelta({
    changed: true, hoverConfirmed: true,
    sourceBackground: 'rgba(0, 0, 0, 0)', hoverBackground: 'rgba(0, 0, 0, 0)',
    styleDelta: [{ prop: 'color', from: 'rgb(0,0,0)', to: 'rgb(40,208,138)' }],
  }), false);
  assert.equal(hasVisibleHoverDelta({
    kind: 'footer', token: 'text-link',
    sourceBackground: 'rgba(0, 0, 0, 0)', hoverBackground: 'rgba(0, 0, 0, 0)',
    styleDelta: [{ prop: 'color', from: 'rgb(120,120,120)', to: 'rgb(75,0,130)' }],
  }), true);
  assert.equal(hasVisibleHoverDelta({
    changed: true,
    sourceBackground: 'rgba(0, 0, 0, 0)', hoverBackground: 'rgb(23, 26, 31)',
  }), true);
  assert.equal(isSourceCta({ token: 'btn-primary', patternKey: 'buttons|cta|dark|none' }, 'buttons'), true);
  assert.equal(isSourceCta({ token: 'btn-ghost', patternKey: 'buttons|block|transparent|none' }, 'buttons'), true);
  const groups = pickStatesForSection([
    { sectionId: '07', label: '5 reasons', token: 'btn-ghost', patternKey: 'buttons|block|transparent|none', changed: false, sourceBackground: 'rgba(0,0,0,0)', hoverBackground: 'rgba(0,0,0,0)' },
    { sectionId: '01', label: 'Request A Free Demo', token: 'btn-primary', patternKey: 'buttons|cta|dark|none', changed: false, sourceBackground: 'rgb(40,208,138)', hoverBackground: 'rgb(40,208,138)' },
    { sectionId: '01', label: 'Hire An Expert', token: 'btn-ghost', patternKey: 'buttons|cta|transparent|fill', changed: true, sourceBackground: 'rgba(0,0,0,0)', hoverBackground: 'rgb(23, 26, 31)' },
  ], 'buttons');
  const seven = groups.find((g) => g.sid === '07');
  const one = groups.find((g) => g.sid === '01');
  assert.equal(seven?.states.length || 0, 1);
  assert.equal(seven.states[0].includeHover, false);
  assert.equal(one.states.length, 2);
  assert.equal(one.states[0].includeHover, true);
  assert.equal(one.states[1].includeHover, false);
  assert.match(one.states[0].label, /Hire An Expert/);
});

test('Source hover stack is one section-number plus a list of objects', () => {
  const html = sourceHoverStackInnerHtml([
    { sid: '01', type: 'Button', defaultHtml: '<div>A</div>', hoverHtml: '<div>B</div>', includeHover: true },
    { sid: '01', type: 'Button', defaultHtml: '<div>C</div>', hoverHtml: '', includeHover: false },
  ]);
  assert.match(html, /layer-name="section-number"/);
  assert.match(html, /layer-name="list"/);
  assert.equal((html.match(/layer-name="object"/g) || []).length, 2);
  assert.equal((html.match(/layer-name="hover"/g) || []).length, 1);
  assert.equal((html.match(/layer-name="default"/g) || []).length, 2);
  assert.equal((html.match(/layer-name="button"/g) || []).length, 3);
  assert.equal((html.match(/layer-name="section-number"/g) || []).length, 1);
  assert.doesNotMatch(html, /layer-name="Hover item"/);
  const objects = sourceHoverItemHtml({
    type: 'objects',
    captureMethod: 'click-pair',
    defaultHtml: '<div>Open</div>',
    hoverHtml: '<div>Closed</div>',
    includeHover: true,
  });
  assert.match(objects, /flex-direction: column/);
  assert.match(objects, /layer-name="01"/);
  assert.match(objects, /layer-name="02"/);
  assert.doesNotMatch(objects, />Default</);
  assert.doesNotMatch(objects, />Hover</);
  assert.doesNotMatch(objects, /layer-name="label"/);
  assert.doesNotMatch(html, /position:\s*absolute/);
  assert.doesNotMatch(html, /padding: 24px/);
  assert.doesNotMatch(html, /padding-top: 14px/);
  assert.match(html, /flex-direction: column/);
  assert.equal((html.match(/<div /g) || []).length, (html.match(/layer-name="/g) || []).length);
});

test('asNamedButtonHtml stamps the painted CTA — never wraps another Frame', () => {
  const named = asNamedButtonHtml('<div style="background-color: #C4A574; padding-inline: 28px">Book A Room</div>');
  assert.match(named, /<div [^>]*layer-name="button"/);
  assert.equal((named.match(/<div /g) || []).length, 1);
  assert.doesNotMatch(named, /padding: 24px/);
});

test('unwrapSerializerHtml reads fe() {status,html} — never String(object)', () => {
  assert.equal(unwrapSerializerHtml({ status: 'success', html: '<a href="#">Go</a>' }), '<a href="#">Go</a>');
  assert.equal(unwrapSerializerHtml('[object Object]'), '');
  assert.equal(unwrapSerializerHtml({ status: 'error', error: 'nope' }), '');
  assert.equal(unwrapSerializerHtml({ status: 'aborted' }), '');
  assert.equal(asNamedButtonHtml('[object Object]'), '');
  assert.match(asNamedButtonHtml({ status: 'success', html: '<button>X</button>' }), /layer-name="button"/);
});

test('Source hover column is a fixed 780px Hover States so rows below do not shift', () => {
  assert.equal(SOURCE_HOVER_WIDTH, 780);
  assert.equal(SOURCE_HOVER_PAD, 24);
  assert.equal(SOURCE_HEADING_FILL, '#E8E8E8');
  const html = sourceHoverStackHtml([
    { sid: '01', type: 'Button', defaultHtml: '<div>A</div>', hoverHtml: '', includeHover: false },
  ]);
  assert.match(html, /layer-name="Hover States"/);
  assert.match(html, /width: 780px/);
  assert.match(html, /min-width: 780px/);
  assert.match(html, /max-width: 780px/);
  assert.match(html, /padding: 24px/);
  assert.match(html, /background-color: #E8E8E8/);
  assert.doesNotMatch(html, /padding: 16px/);
  assert.match(html, /flex-shrink: 0/);
});

test('Source hover column repeats no section number — one section-number, then objects', () => {
  const html = sourceHoverStackInnerHtml([
    { sid: '04', type: 'Pill', defaultHtml: '<div>A</div>', hoverHtml: '', includeHover: false },
    { sid: '04', type: 'Pill', defaultHtml: '<div>B</div>', hoverHtml: '', includeHover: false },
  ]);
  assert.equal((html.match(/layer-name="object"/g) || []).length, 2);
  assert.equal((html.match(/#E11D2E/g) || []).length, 1);
  assert.equal((html.match(/>04</g) || []).length, 1);
  assert.equal((html.match(/layer-name="section-number"/g) || []).length, 1);
});

test('leftoverSourceSectionBadgeIds is the parent sibling, not the shot', () => {
  const ids = leftoverSourceSectionBadgeIds([
    { id: 'G7-0', name: 'Frame', component: 'Frame', childCount: 1 },
    { id: 'GB-0', name: 'Hover States', component: 'Frame', childCount: 11 },
    { id: 'GA-0', name: 'Divider', component: 'Frame', childCount: 0 },
    { id: 'G9-0', name: 'Interior design website', component: 'Rectangle', childCount: 0 },
  ], { keepIds: ['GB-0'] });
  assert.deepEqual(ids, ['G7-0']);
});
