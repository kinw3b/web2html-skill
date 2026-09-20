import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SOURCE = readFileSync(path.join(ROOT, 'capture-extension/content/component-names.js'), 'utf8');

class FakeElement {
  constructor(spec = {}) {
    this.tagName = String(spec.tag || 'div').toUpperCase();
    this.attrs = spec.attrs || {};
    this.className = spec.className || '';
    this.id = spec.id || '';
    this.ownText = spec.text || '';
    this.children = (spec.children || []).map((child) =>
      child instanceof FakeElement ? child : new FakeElement(child));
    this.rect = spec.rect || { width: 320, height: 200 };
    this.styles = spec.styles || {};
  }

  get textContent() {
    return [this.ownText, ...this.children.map((child) => child.textContent)]
      .filter(Boolean).join(' ');
  }

  get innerText() {
    return this.textContent;
  }

  descendants() {
    return this.children.flatMap((child) => [child, ...child.descendants()]);
  }

  getAttribute(name) {
    return Object.prototype.hasOwnProperty.call(this.attrs, name) ? this.attrs[name] : null;
  }

  hasAttribute(name) {
    return this.getAttribute(name) !== null;
  }

  getBoundingClientRect() {
    return this.rect;
  }

  matchesSelector(selector) {
    return String(selector).split(',').some((part) => {
      const token = part.trim().toLowerCase();
      if (!token) return false;
      return token === this.tagName.toLowerCase();
    });
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  querySelectorAll(selector) {
    if (String(selector).trim() === '*') return this.descendants();
    return this.descendants().filter((node) => node.matchesSelector(selector));
  }

  closest() {
    return null;
  }
}

function load() {
  const context = {
    Element: FakeElement,
    getComputedStyle: (node) => ({
      display: node.styles?.display || 'block',
      fontSize: node.styles?.fontSize || '16px',
    }),
  };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(SOURCE, context);
  return context.PaperCaptureNaming;
}

const { componentName } = load();
const el = (spec) => new FakeElement(spec);

test('a feature card is named by its archetype, not by its body copy', () => {
  const card = el({
    tag: 'div',
    children: [
      { tag: 'svg' },
      { tag: 'h3', text: 'Expenses Management' },
      { tag: 'p', text: 'Creating account to our website and now use it for your required time.' },
    ],
  });
  assert.equal(componentName(card, { kind: 'component' }), 'Feature Card · Expenses Management');
});

test('a big-number block reads as a stat card', () => {
  const stat = el({
    tag: 'div',
    children: [
      { tag: 'div', text: '2.5X', styles: { fontSize: '72px' } },
      { tag: 'p', text: 'Faster deals' },
    ],
  });
  assert.equal(componentName(stat, { kind: 'component' }), 'Stat Card · 2.5X Faster Deals');
});

test('a short review strip reads as a rating badge', () => {
  const badge = el({
    tag: 'div',
    className: 'trustpilot-widget',
    children: [{ tag: 'p', text: '4.9 out of 5 based on 227 reviews' }],
  });
  assert.equal(componentName(badge, { kind: 'component' }), 'Rating Badge · 4.9 Out 5');
});

test('an expandable question reads as an accordion item', () => {
  const faq = el({
    tag: 'div',
    attrs: { 'aria-expanded': 'false' },
    children: [
      { tag: 'h3', text: 'Do you provide any support for this kit?' },
      { tag: 'p', text: 'It is a long established fact that a reader is distracted by the readable content of a page when looking at its layout.' },
    ],
  });
  assert.equal(componentName(faq, { kind: 'component' }), 'Accordion Item · Do Provide Any');
});

test('hover takes are marked without leaking page text', () => {
  const button = el({ tag: 'button', text: 'Get started', className: 'btn' });
  assert.equal(componentName(button, { kind: 'component', mode: 'hover' }), 'Button (Hover) · Get Started');
});

test('navbar and dropdown kinds keep their contract names', () => {
  const bar = el({ tag: 'nav', text: 'Home Pricing Docs Contact' });
  assert.match(componentName(bar, { kind: 'navbar' }), /^Navbar/);
});

test('a non-element falls back to the capture kind', () => {
  assert.equal(componentName(null, { kind: 'component' }), 'component');
});
