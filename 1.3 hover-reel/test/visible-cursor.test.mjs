import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { CURSOR_TAG, HUD_TAG, bootVisibleCursor, formatHud } from '../scripts/visible-cursor.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function fakeDocument() {
  const nodes = new Map();
  const events = {};
  const makeEl = (tag) => {
    const kids = {
      'hold-fill': { style: { width: '' } },
      hold: { hidden: true, style: { display: '' } },
      mark: { hidden: true, textContent: '01', style: { display: '' } },
      arrow: { style: { display: '' } },
      label: { textContent: '', style: { display: '' } },
    };
    const el = {
      tagName: tag,
      id: '',
      style: { cssText: '', transform: '', display: '', visibility: '' },
      innerHTML: '',
      textContent: '',
      querySelector: (sel) => {
        const key = String(sel);
        if (key.includes('hold-fill')) return kids['hold-fill'];
        if (key.includes('hold')) return kids.hold;
        if (key.includes('mark')) return kids.mark;
        if (key.includes('arrow')) return kids.arrow;
        if (key.includes('label')) return kids.label;
        return { style: {} };
      },
      contains: () => false,
      setAttribute() {},
      remove() {},
    };
    return el;
  };
  const doc = {
    querySelector: (sel) => nodes.get(sel) || null,
    createElement: (tag) => makeEl(tag),
    documentElement: { appendChild(el) { if (el?.id) nodes.set('#' + el.id, el); if (el?.tagName) nodes.set(el.tagName, el); } },
    body: { appendChild() {} },
    addEventListener: (type, fn) => { events[type] = fn; },
    elementFromPoint: () => null,
    _nodes: nodes,
    _events: events,
  };
  return doc;
}

test('visible cursor host and HUD are skipped by the Paper serializer prefix', () => {
  assert.equal(CURSOR_TAG, 'x-paper-cursor');
  assert.equal(HUD_TAG, 'x-paper-cursor-hud');
  assert.ok(CURSOR_TAG.startsWith('x-paper-'));
  assert.ok(HUD_TAG.startsWith('x-paper-'));
});

test('formatHud prints pass · n/N · label', () => {
  assert.equal(formatHud({ phase: 'Navbar', current: 3, total: 18, label: 'Pricing' }), 'hover-reel · 3/18 · Navbar · Pricing');
  assert.equal(formatHud({ text: 'Hover Reel · running' }), 'Hover Reel · running');
});

test('bootVisibleCursor mounts HUD and move() updates transform without mousemove', () => {
  globalThis.document = fakeDocument();
  globalThis.window = { addEventListener() {} };
  globalThis.MutationObserver = class { observe() {} };

  const api = bootVisibleCursor();
  assert.equal(api.host.id, 'x-paper-cursor');
  assert.equal(api.hud.id, 'x-paper-cursor-hud');
  assert.ok(api.host.id.startsWith('x-paper-'));
  assert.ok(api.hud.id.startsWith('x-paper-'));
  assert.equal(typeof api.move, 'function');
  assert.equal(typeof api.showHud, 'function');
  assert.equal(typeof api.setHold, 'function');
  assert.equal(typeof api.setClickMark, 'function');
  api.setClickMark(1);
  assert.equal(api.host.querySelector('[data-hr=mark]').hidden, false);
  assert.equal(api.host.querySelector('[data-hr=mark]').textContent, '01');
  api.setClickMark(null);
  assert.equal(api.host.querySelector('[data-hr=mark]').hidden, true);
  api.setHold(0.75);
  assert.equal(api.host.querySelector('[data-hr=hold]').hidden, false);
  assert.equal(api.host.querySelector('[data-hr=hold-fill]').style.width, '75%');
  api.setHold(null);
  assert.equal(api.host.querySelector('[data-hr=hold]').hidden, true);

  api.showHud({ phase: 'buttons', current: 4, total: 12, label: 'Get Started' });
  assert.match(api.hud.textContent, /4\/12/);
  assert.match(api.hud.textContent, /Get Started/);

  api.move(240, 80);
  assert.match(api.host.style.transform, /translate\(240px, 80px\)/);
  assert.equal(api.pos.x, 240);
  assert.equal(api.pos.y, 80);
});
