// Locate a sibling skill package without hardcoding an install path, so this
// package runs the same wherever it is checked out or installed.
//
// Order: the directory this package sits in -> $SKILLS -> ~/.claude/skills.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const PKG_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function roots() {
  return [
    path.resolve(PKG_ROOT, '..'),
    process.env.SKILLS,
    path.join(os.homedir(), '.claude', 'skills'),
  ].filter(Boolean);
}

function pkgDir(root, name) {
  const exact = path.join(root, name);
  if (fs.existsSync(exact)) return exact;
  try {
    for (const entry of fs.readdirSync(root)) {
      if (entry === name || entry.endsWith(` ${name}`) || entry.endsWith(`- ${name}`)) {
        const found = path.join(root, entry);
        if (fs.statSync(found).isDirectory()) return found;
      }
    }
  } catch {
    /* missing root */
  }
  return null;
}

export function siblingSkill(name, rel = '') {
  for (const root of roots()) {
    const pkg = pkgDir(root, name);
    if (!pkg) continue;
    const p = rel ? path.join(pkg, rel) : pkg;
    if (fs.existsSync(p)) return p;
  }
  throw new Error(
    `skill "${name}${rel ? '/' + rel : ''}" not found next to ${PKG_ROOT}. ` +
      'Install it alongside this package or set $SKILLS to your skills directory.',
  );
}

export const importSibling = (name, rel) =>
  import(pathToFileURL(siblingSkill(name, rel)).href);
