import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  INTERACTIVE_COMPONENTS,
  isLibraryMineArtboard,
  isTokenPassArtboard,
  selectTokenPassArtboards,
} from '../scripts/token-pass-targets.mjs';
import {
  tokenPassVisitsInteractiveComponents,
} from '../scripts/apply-theme-tokens.mjs';

const APPLY = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../scripts/apply-theme-tokens.mjs');

test('library mining includes only landers and Capture Tool frames', () => {
  const included = [
    'home-desktop',
    'homepage-desktop',
    'about-768',
    'contact-390',
    'Buttons',
    'Hover States',
    'Components',
    'Navigation',
    'Interactive components',
    'A/6 · home · states',
  ];
  const excluded = [
    'Design Library',
    'Screenshots',
    'Ruler · desktop',
    'qa-token-review',
    'Source · home',
    'LIBRARY — Components',
  ];

  for (const name of included) assert.equal(isLibraryMineArtboard(name), true, name);
  for (const name of excluded) assert.equal(isLibraryMineArtboard(name), false, name);
});

test('token-pass visits Interactive components the same as landers + A/6', () => {
  assert.equal(isTokenPassArtboard('Interactive components'), true);
  assert.equal(isTokenPassArtboard('Navigation'), true);
  assert.equal(isTokenPassArtboard('Components'), true);
  assert.equal(isTokenPassArtboard('Buttons'), true);
  assert.equal(isTokenPassArtboard('Hover States'), true);
  assert.equal(isTokenPassArtboard(INTERACTIVE_COMPONENTS), true);
  assert.equal(isTokenPassArtboard('home-desktop'), true);
  assert.equal(isTokenPassArtboard('homepage-desktop'), true);
  assert.equal(isTokenPassArtboard('about-768'), true);
  assert.equal(isTokenPassArtboard('contact-390'), true);
  assert.equal(isTokenPassArtboard('A/6 · home · states'), true);
  assert.equal(isTokenPassArtboard('Design Library'), true);
  assert.equal(isTokenPassArtboard('Ruler · desktop'), false);
  assert.equal(isTokenPassArtboard('Source · home'), false);

  const selected = selectTokenPassArtboards([
    { name: 'home-desktop' },
    { name: 'A/6 · home · states' },
    { name: INTERACTIVE_COMPONENTS },
    { name: 'Ruler · desktop' },
  ]);
  assert.deepEqual(selected.map((a) => a.name), [
    'home-desktop',
    'A/6 · home · states',
    INTERACTIVE_COMPONENTS,
  ]);
  assert.equal(tokenPassVisitsInteractiveComponents(selected), true);

  const only = selectTokenPassArtboards(
    [{ name: 'home-desktop' }, { name: INTERACTIVE_COMPONENTS }],
    { only: 'Interactive components' },
  );
  assert.deepEqual(only.map((a) => a.name), [INTERACTIVE_COMPONENTS]);
});

test('apply-theme-tokens --list-targets includes Interactive components', () => {
  const res = spawnSync(process.execPath, [APPLY, '--list-targets'], { encoding: 'utf8' });
  assert.equal(res.status, 0, res.stderr);
  const body = JSON.parse(res.stdout);
  assert.equal(body.visitsInteractiveComponents, true);
  assert.ok(body.artboards.includes('Interactive components'));
  assert.ok(body.artboards.includes('A/6 · home · states'));
});
