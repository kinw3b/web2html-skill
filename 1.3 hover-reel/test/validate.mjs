// Manifest / file sanity checks for the Capture Tool extension (step 1.3).
// Files are enumerated at RUN time so this stays valid as sibling components land.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EXT_DIR = path.resolve(ROOT, 'capture-extension');
const MANIFEST_PATH = path.join(EXT_DIR, 'manifest.json');

function readManifest() {
  return JSON.parse(readFileSync(MANIFEST_PATH, 'utf8'));
}

function walkSourceFiles(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkSourceFiles(full));
    else if (entry.isFile() && /\.m?js$/.test(entry.name)) out.push(full);
  }
  return out;
}

test('manifest.json parses and has the expected identity', () => {
  const manifest = readManifest();
  assert.equal(manifest.manifest_version, 3);
  assert.equal(manifest.name, 'Paper Capture Tool');
  assert.ok(manifest.background?.service_worker, 'background.service_worker set');
  assert.ok(manifest.side_panel?.default_path, 'side_panel.default_path set');
  assert.ok(
    (manifest.permissions || []).includes('nativeMessaging'),
    'nativeMessaging permission declared for the Paper bridge',
  );
});

test('every manifest-referenced file exists', () => {
  const manifest = readManifest();
  const referenced = [
    manifest.background.service_worker,
    manifest.side_panel.default_path,
    ...(manifest.content_scripts || []).flatMap((entry) => [
      ...(entry.js || []),
      ...(entry.css || []),
    ]),
    // injected via chrome.scripting at capture time, so not listed in the manifest:
    'content/targeting.js',
    'content/nav-breakpoints.js',
    'content/capture.js',
    'content/capture.css',
    // installed as the native messaging host:
    'bridge/host.mjs',
    'bridge/semantics.mjs',
  ];
  const missing = referenced.filter((rel) => !existsSync(path.join(EXT_DIR, rel)));
  assert.deepEqual(missing, [], `missing extension files: ${missing.join(', ')}`);
});

test('every .js/.mjs file under capture-extension/ passes `node --check`', () => {
  const files = walkSourceFiles(EXT_DIR);
  assert.ok(files.length > 0, 'found extension sources to check');
  const failures = [];
  for (const file of files) {
    const res = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
    if (res.status !== 0) {
      failures.push(`${path.relative(ROOT, file)}:\n${(res.stderr || '').trim()}`);
    }
  }
  assert.deepEqual(failures, [], `syntax errors:\n${failures.join('\n\n')}`);
});

test('HC_* message literals in the side panel also appear in the service worker (drift guard)', () => {
  const workerPath = path.join(EXT_DIR, 'service-worker.js');
  const senderPaths = [
    path.join(EXT_DIR, 'sidepanel', 'panel.js'),
    ...walkSourceFiles(path.join(EXT_DIR, 'content')),
  ].filter((file) => existsSync(file));

  const names = new Set();
  const re = /["'](HC_[A-Z_]+)["']/g;
  for (const file of senderPaths) {
    for (const match of readFileSync(file, 'utf8').matchAll(re)) names.add(match[1]);
  }
  assert.ok(names.size > 0, 'found HC_* message literals to guard');

  const worker = readFileSync(workerPath, 'utf8');
  const panel = readFileSync(path.join(EXT_DIR, 'sidepanel', 'panel.js'), 'utf8');
  const drifted = [...names].filter((name) => !worker.includes(name) && !panel.includes(name));
  assert.deepEqual(drifted, [], `HC_* literals defined nowhere they are handled: ${drifted.join(', ')}`);
});
