#!/usr/bin/env node
// Web2HTML installer — `npx github:kinw3b/web2html-skill`
//
// What it does, in order:
//   1. Copies the skill package to ONE stable home (~/.web2html/skills) when it
//      is running out of the npx cache. npx's cache is disposable; the home is not.
//      Running from a git checkout links the checkout directly (developer mode).
//   2. Symlinks each skill, by its plain name, into every agent skills folder.
//      Existing symlinks are replaced and reported; real folders are never touched.
//   3. Installs the npm dependencies each skill needs (Playwright), so the first
//      /web2html run has no surprises.
//
// It does NOT install the Paper Capture Tool browser extension or its native
// bridge. That is a separate, optional download.
//
// Flags:  --dry-run        print the plan, change nothing
//         --home <dir>     install home (default ~/.web2html/skills)
//         --skip-deps      do not run npm install inside the skills
//         --skip-browser   do not download Playwright's Chromium
"use strict";

const { spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");

// ---------------------------------------------------------------- args ----
const argv = process.argv.slice(2);
const flag = (name) => argv.includes(name);
const opt = (name) => {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : null;
};
const DRY = flag("--dry-run");
const SKIP_DEPS = flag("--skip-deps");
const SKIP_BROWSER = flag("--skip-browser");
const HOME_DIR = os.homedir();
const expand = (p) => p.replace(/^~(?=$|\/)/, HOME_DIR);

// -------------------------------------------------------------- output ----
const tty = process.stdout.isTTY && !process.env.NO_COLOR;
const c = (code, s) => (tty ? `\x1b[${code}m${s}\x1b[0m` : s);
const dim = (s) => c("2", s);
const bold = (s) => c("1", s);
const green = (s) => c("32", s);
const yellow = (s) => c("33", s);
const red = (s) => c("31", s);
const cyan = (s) => c("36", s);
const short = (p) => (p.startsWith(HOME_DIR) ? "~" + p.slice(HOME_DIR.length) : p);
const log = (s = "") => console.log(s);
const step = (n, title) => log(`\n${bold(`${n}.`)} ${bold(title)}`);
const line = (mark, text) => log(`   ${mark} ${text}`);

const BANNER = [
  " __        __   _     ____  _   _ _____ __  __ _",
  " \\ \\      / /__| |__ |___ \\| | | |_   _|  \\/  | |",
  "  \\ \\ /\\ / / _ \\ '_ \\  __) | |_| | | | | |\\/| | |",
  "   \\ V  V /  __/ |_) |/ __/|  _  | | | | |  | | |___",
  "    \\_/\\_/ \\___|_.__/|_____|_| |_| |_| |_|  |_|_____|",
];

log();
for (const row of BANNER) log(cyan(row));
log();
log(`   ${bold("Web2HTML")} ${dim("— live URL to pixel-perfect static HTML, via Paper")}`);
log(`   ${dim("github.com/kinw3b/w2h-private")}`);
if (DRY) log(`\n   ${yellow("DRY RUN")} ${dim("— printing the plan, changing nothing")}`);

// ------------------------------------------------------------- source ----
const source = path.resolve(__dirname, "..");
const fromNpxCache = source.split(path.sep).includes("_npx");
const homeOpt = opt("--home");
const home = homeOpt ? path.resolve(expand(homeOpt)) : path.join(HOME_DIR, ".web2html", "skills");
// Developer mode: a checkout links itself so edits are live immediately.
const root = fromNpxCache || homeOpt ? home : source;

const SKIP_COPY = new Set(["node_modules", ".git", "dist", ".DS_Store"]);
function copyPackage(from, to) {
  if (DRY) return;
  fs.mkdirSync(path.dirname(to), { recursive: true });
  // Replace the previous copy so removed skills do not linger.
  fs.rmSync(to, { recursive: true, force: true });
  fs.cpSync(from, to, {
    recursive: true,
    filter: (src) => !SKIP_COPY.has(path.basename(src)),
  });
}

step(1, "Install home");
if (root === source) {
  line(green("•"), `running from a checkout — linking it directly (edits are live)`);
  line(" ", dim(short(root)));
} else {
  line(green("•"), `copying skills to ${bold(short(root))}`);
  line(" ", dim(`from ${short(source)}`));
  line(" ", dim("npx's cache can be pruned at any time; this folder is permanent"));
  copyPackage(source, root);
}

// -------------------------------------------------------------- skills ----
const stripPrefix = (base) => base.replace(/^[0-9]+(\.[0-9]+)*\s+(-\s+)?/, "");
const skillDirs = fs
  .readdirSync(source, { withFileTypes: true })
  .filter((d) => d.isDirectory() && d.name !== "archive")
  .filter((d) => fs.existsSync(path.join(source, d.name, "SKILL.md")))
  .map((d) => d.name)
  .sort();

const links = skillDirs.map((base) => ({ name: stripPrefix(base), base }));
// Compat aliases: /website-to-html was the old invoke name.
const aliasFor = (base, alias) =>
  skillDirs.includes(base) && links.push({ name: alias, base, alias: true });
aliasFor("1.0 - web2html", "website-to-html");

step(2, `Skills (${skillDirs.length})`);
log(
  "   " +
    dim(
      links
        .filter((l) => !l.alias)
        .map((l) => l.name)
        .join("  ")
    )
);

// --------------------------------------------------------------- dests ----
const dests = [
  ["Claude Code", path.join(HOME_DIR, ".claude", "skills")],
  ["Cursor", path.join(HOME_DIR, ".cursor", "skills")],
  ["Codex", path.join(HOME_DIR, ".codex", "skills")],
  ["Hermes", path.join(HOME_DIR, ".hermes", "skills")],
  ["Agents", path.join(HOME_DIR, ".agents", "skills")],
];

step(3, "Linking into agent skills folders");
const replaced = [];
const skipped = [];
for (const [label, dest] of dests) {
  if (!DRY) fs.mkdirSync(dest, { recursive: true });
  let linked = 0;
  let same = 0;
  for (const { name, base } of links) {
    const target = path.join(dest, name);
    const want = path.join(root, base);
    let existing = null;
    try {
      const st = fs.lstatSync(target);
      if (!st.isSymbolicLink()) {
        skipped.push(`${short(target)} is a real folder, left alone`);
        continue;
      }
      existing = fs.readlinkSync(target);
    } catch {
      /* nothing there */
    }
    if (existing === want) {
      same += 1;
      continue;
    }
    if (existing !== null) replaced.push({ target, from: existing, to: want });
    if (!DRY) {
      fs.rmSync(target, { force: true });
      fs.symlinkSync(want, target);
    }
    linked += 1;
  }
  const detail =
    same && !linked ? dim("already up to date") : `${linked} linked` + (same ? dim(`, ${same} unchanged`) : "");
  line(green("✓"), `${label.padEnd(12)} ${dim(short(dest))}  ${detail}`);
}

if (replaced.length) {
  const prev = [...new Set(replaced.map((r) => path.dirname(r.from)))];
  log();
  line(yellow("!"), `${replaced.length} existing link(s) were repointed to ${short(root)}`);
  for (const p of prev) line(" ", dim(`previously → ${short(p)}`));
}
for (const s of skipped) line(yellow("!"), `skipped: ${s}`);

// ---------------------------------------------------------------- deps ----
step(4, "Dependencies");
const run = (cmd, args, cwd) =>
  spawnSync(cmd, args, { cwd, stdio: ["ignore", "ignore", "pipe"], encoding: "utf8" });

let depsFailed = 0;
if (SKIP_DEPS) {
  line(dim("–"), dim("skipped (--skip-deps)"));
} else {
  const withPkg = skillDirs.filter((b) => fs.existsSync(path.join(root, b, "package.json")));
  for (const base of withPkg) {
    const dir = path.join(root, base);
    const name = stripPrefix(base);
    if (DRY) {
      line(dim("–"), `would run npm install in ${name}`);
      continue;
    }
    const r = run("npm", ["install", "--no-audit", "--no-fund", "--loglevel=error"], dir);
    if (r.status === 0) line(green("✓"), `${name.padEnd(14)} ${dim("npm install")}`);
    else {
      depsFailed += 1;
      line(red("✗"), `${name.padEnd(14)} npm install failed`);
      if (r.stderr) log(dim(r.stderr.trim().split("\n").slice(-3).map((l) => "     " + l).join("\n")));
    }
  }

  // Playwright's Chromium: the capture skills render pages headlessly with it.
  const pwCache =
    process.platform === "darwin"
      ? path.join(HOME_DIR, "Library", "Caches", "ms-playwright")
      : path.join(HOME_DIR, ".cache", "ms-playwright");
  const hasChromium = () => {
    try {
      return fs.readdirSync(pwCache).some((d) => /^chromium/.test(d));
    } catch {
      return false;
    }
  };
  const hoverReel = withPkg.find((b) => stripPrefix(b) === "hover-reel");
  if (SKIP_BROWSER) line(dim("–"), dim("Chromium download skipped (--skip-browser)"));
  else if (hasChromium()) line(green("✓"), `${"chromium".padEnd(14)} ${dim("already in " + short(pwCache))}`);
  else if (DRY) line(dim("–"), "would download Playwright Chromium (~150 MB)");
  else if (hoverReel) {
    process.stdout.write(`   ${dim("↓")} ${"chromium".padEnd(14)} ${dim("downloading (~150 MB, one time)…")}`);
    const r = run("npx", ["playwright", "install", "chromium"], path.join(root, hoverReel));
    process.stdout.write("\r\x1b[2K");
    if (r.status === 0) line(green("✓"), `${"chromium".padEnd(14)} ${dim("installed to " + short(pwCache))}`);
    else {
      depsFailed += 1;
      line(red("✗"), `${"chromium".padEnd(14)} download failed — run: npx playwright install chromium`);
    }
  }
}

// --------------------------------------------------------- npx cleanup ----
// The npx cache entry that ran this install is throwaway now that the skills
// live in the home. Remove it, and any older web2html-skill entries, so nothing
// half-installed lingers under ~/.npm/_npx. Node has the script in memory, so
// deleting its own folder is safe. Only built-in modules are required above.
let cleaned = [];
if (fromNpxCache) {
  const parts = source.split(path.sep);
  const npxDir = parts.slice(0, parts.indexOf("_npx") + 1).join(path.sep);
  let entries = [];
  try {
    entries = fs.readdirSync(npxDir).map((h) => path.join(npxDir, h));
  } catch {
    /* cache already gone */
  }
  const isOurs = (entry) =>
    fs.existsSync(path.join(entry, "node_modules", "web2html-skill", "scripts", "npx-install.js"));
  for (const entry of entries) {
    if (!isOurs(entry)) continue;
    if (!DRY) fs.rmSync(entry, { recursive: true, force: true });
    cleaned.push(entry);
  }
  step(5, "Cleanup");
  if (cleaned.length) {
    line(green("✓"), `removed ${cleaned.length} throwaway npx cache folder(s)`);
    for (const e of cleaned) line(" ", dim(short(e)));
  } else line(dim("–"), dim("no npx cache folders to remove"));
}

// ------------------------------------------------------------- summary ----
step(fromNpxCache ? 6 : 5, "Not installed (optional)");
line(dim("–"), "Paper Capture Tool browser extension + native bridge");
line(" ", dim("Only needed for the 1.4 hover-capture step. Download separately:"));
line(" ", dim("https://github.com/kinw3b/paper-bridge"));

log();
log(bold(depsFailed ? yellow("Done, with warnings.") : green("Done.")));
log(`   Skills live in   ${bold(short(root))}`);
log(`   Linked into      ${dests.map(([l]) => l).join(", ")}`);
log(`   Nothing else on your machine was changed.`);
log();
log(`   Skill docs refer to ${bold("$SKILLS")}. Set it once (any linked folder works):`);
log(`     ${cyan('export SKILLS="' + short(dests[0][1]) + '"')}`);
log();
log(`   Next: open a new agent chat and run ${bold("/web2html")}  ${dim("(Convert <URL> to HTML)")}`);
log();

process.exit(depsFailed ? 1 : 0);
