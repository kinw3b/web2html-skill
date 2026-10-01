#!/usr/bin/env python3
"""5.1 — scaffold astro/ from the signed 3.4 homepage rebuild.

Copies tokens, CSS, fonts, images, and client scripts from rebuild/ (js/
RECURSIVELY, so vendor/ rides along), then derives BaseLayout's stylesheet +
script wiring from the SHIP's own head (rebuild/index.html) instead of a
fixed manifest. Each inline <style> becomes its own sheet (site.css, then
site-2.css, …) linked at that block's position so a <link> between two
style blocks keeps cascade order. Inline <script> bodies are written to
public/scripts/ship-inline-N.js — never pasted into the .astro template,
where `{` is an Astro expression and breaks the build. Head scripts stay
in <head>. The receipt FAILS when BaseLayout references an asset that does
not exist under public/ (Pitfall #240).

Writes the Astro project files (BaseLayout carries title / description /
lang / canonical / og:image so 5.5 SEO is props, not markup). Does not
start a server. Next: extract-astro-components.py, convert-astro-home.py.

  python3 scaffold-astro.py /path/to/project
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from html_to_astro import rewrite_css_urls, ship_wiring

SKIP_CSS = frozenset({"qa-overlay.css"})
SKIP_JS = frozenset({"qa-overlay.js"})

PACKAGE_JSON = """{
  "name": "web2html-astro",
  "type": "module",
  "private": true,
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview"
  },
  "engines": {
    "node": ">=22.12.0"
  },
  "dependencies": {
    "astro": "^7.3.5"
  }
}
"""

# No `trailingSlash`: Astro's default ('ignore') matches /about and /about/
# alike, so hosts and a future CMS are never forced into one URL shape.
# build.format stays the default 'directory' (about/index.html), which
# astro_build.relativize_dist depends on for file:// previews.
ASTRO_CONFIG = """import { defineConfig } from 'astro/config';

export default defineConfig({
  output: 'static',
});
"""

# Live content collections (src/live.config.ts) — the seam for a future CMS.
# Static builds never call getLiveCollection(), so this costs nothing until a
# page opts in with `export const prerender = false` + an adapter. Written
# only when missing so a wired CMS loader survives a re-scaffold.
LIVE_CONFIG = """// Live content collections: fetched at request time, no rebuild per edit.
// Query from an on-demand page (`export const prerender = false`, adapter
// installed) with getLiveCollection('pages') / getLiveEntry('pages', id).
// Static pages keep their markup; nothing here runs during `astro build`.
import { defineLiveCollection } from 'astro:content';
import { cmsLoader } from './loaders/cms';

const pages = defineLiveCollection({
  loader: cmsLoader({ endpoint: import.meta.env.CMS_API_URL, resource: 'pages' }),
});

export const collections = { pages };
"""

CMS_LOADER = """import type { LiveLoader } from 'astro/loaders';

// Generic REST live loader. Swap for the CMS's own loader package when one
// is chosen; the collection API (getLiveCollection / getLiveEntry) stays.
export interface CmsEntry {
  id: string;
  [key: string]: unknown;
}

type EntryFilter = { id: string };
type CollectionFilter = Record<string, string>;

export function cmsLoader(opts: { endpoint?: string; resource: string }): LiveLoader<CmsEntry, EntryFilter, CollectionFilter> {
  const base = opts.endpoint?.replace(/\\/+$/, '');
  const missing = () => new Error(`CMS_API_URL is not set; live collection "${opts.resource}" has no source`);
  const url = (path: string, params?: CollectionFilter) => {
    const u = new URL(`${base}/${opts.resource}${path}`);
    for (const [key, value] of Object.entries(params ?? {})) u.searchParams.set(key, value);
    return u;
  };
  return {
    name: `cms-${opts.resource}`,
    loadCollection: async ({ filter }) => {
      if (!base) return { error: missing() };
      try {
        const res = await fetch(url('', filter));
        if (!res.ok) return { error: new Error(`${res.status} ${res.statusText}`) };
        const rows = (await res.json()) as CmsEntry[];
        return { entries: rows.map((data) => ({ id: String(data.id), data })) };
      } catch (cause) {
        return { error: new Error(`Failed to load ${opts.resource}`, { cause }) };
      }
    },
    loadEntry: async ({ filter }) => {
      if (!base) return { error: missing() };
      try {
        const res = await fetch(url(`/${encodeURIComponent(filter.id)}`));
        if (res.status === 404) return undefined;
        if (!res.ok) return { error: new Error(`${res.status} ${res.statusText}`) };
        const data = (await res.json()) as CmsEntry;
        return { id: String(data.id), data };
      } catch (cause) {
        return { error: new Error(`Failed to load ${opts.resource}/${filter.id}`, { cause }) };
      }
    },
  };
}
"""

ENV_EXAMPLE = """# Live content collections (src/live.config.ts). Leave empty for a static build.
CMS_API_URL=
"""

TSCONFIG = """{
  "extends": "astro/tsconfigs/strict",
  "include": [".astro/types.d.ts", "**/*"],
  "exclude": ["dist"]
}
"""

GITIGNORE = """node_modules/
dist/
.astro/
.env
"""

# Wiring is DERIVED from the ship head (ship_wiring) — never a fixed list.
# A hardcoded /styles/site.css once 404'd on every route and shipped the
# whole site unstyled (Pitfall #240).
BASE_LAYOUT_TOP = """---
interface Props {
  title: string;
  description?: string;
  lang?: string;
  canonical?: string;
  ogImage?: string;
}
const { title, description = '', lang = 'en', canonical = '', ogImage = '' } = Astro.props;
---
<!doctype html>
<html lang={lang}>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    {description && <meta name="description" content={description} />}
    {canonical && <link rel="canonical" href={canonical} />}
    <meta property="og:title" content={title} />
    {description && <meta property="og:description" content={description} />}
    {ogImage && <meta property="og:image" content={ogImage} />}
    <meta name="twitter:card" content={ogImage ? 'summary_large_image' : 'summary'} />
"""

BASE_LAYOUT_MID = """  </head>
  <body>
    <slot />
"""

BASE_LAYOUT_END = """  </body>
</html>
"""


def base_layout(style_tags: list[str], head_scripts: list[str], body_scripts: list[str]) -> str:
    styles = "".join(f"    {tag}\n" for tag in style_tags)
    head = "".join(f"    {tag}\n" for tag in head_scripts)
    body = "".join(f"    {tag}\n" for tag in body_scripts)
    return BASE_LAYOUT_TOP + styles + head + BASE_LAYOUT_MID + body + BASE_LAYOUT_END


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _copy_dir(src: Path, dest: Path) -> int:
    if not src.is_dir():
        return 0
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in src.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
    return count


def _unused_name(taken: set[str], preferred: str) -> str:
    if preferred not in taken:
        return preferred
    stem, ext = preferred.rsplit(".", 1)
    n = 2
    while f"{stem}-{n}.{ext}" in taken:
        n += 1
    return f"{stem}-{n}.{ext}"


def scaffold(root: Path) -> dict:
    root = root.resolve()
    import run_config

    adopted = run_config.adopt_mode(root)
    rebuild = root / ("source-html" if adopted else "rebuild")
    if not rebuild.is_dir():
        raise FileNotFoundError(
            "need source-html/ — the provided folder is the ship"
            if adopted
            else "need rebuild/ from the 3.4 homepage run"
        )
    ship = rebuild / "index.html"
    if not ship.is_file():
        raise FileNotFoundError(
            f"need {ship.relative_to(root).as_posix()} — BaseLayout wiring is derived from the signed ship"
        )
    astro = root / "astro"
    public = astro / "public"
    styles = public / "styles"
    scripts = public / "scripts"
    images = public / "images"
    fonts = public / "fonts"
    for path in (styles, scripts, images, fonts, astro / "src" / "layouts", astro / "src" / "components", astro / "src" / "pages"):
        path.mkdir(parents=True, exist_ok=True)

    copied = {"styles": [], "scripts": [], "images": 0, "fonts": 0}
    css_dir = rebuild / "css"
    if css_dir.is_dir():
        for path in sorted(css_dir.rglob("*.css")):
            if path.name in SKIP_CSS:
                continue
            rel = path.relative_to(css_dir).as_posix()
            dest = styles / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rewrite_css_urls(path.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
            copied["styles"].append(rel)
    js_dir = rebuild / "js"
    if js_dir.is_dir():
        # rglob, not glob: rebuild/js/vendor/ (GSAP + ScrollTrigger) must ride along
        for path in sorted(js_dir.rglob("*.js")):
            if path.name in SKIP_JS:
                continue
            rel = path.relative_to(js_dir).as_posix()
            dest = scripts / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            copied["scripts"].append(rel)
    copied["images"] += _copy_dir(rebuild / "images", images)
    copied["images"] += _copy_dir(rebuild / "img", images)
    copied["fonts"] += _copy_dir(rebuild / "fonts", fonts)

    for name, body in (
        ("package.json", PACKAGE_JSON),
        ("astro.config.mjs", ASTRO_CONFIG),
        ("tsconfig.json", TSCONFIG),
        (".gitignore", GITIGNORE),
    ):
        (astro / name).write_text(body, encoding="utf-8")
    live_files: list[str] = []
    for rel, body in (
        ("src/live.config.ts", LIVE_CONFIG),
        ("src/loaders/cms.ts", CMS_LOADER),
        (".env.example", ENV_EXAMPLE),
    ):
        target = astro / rel
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        live_files.append(rel)
    if not adopted and not (styles / "hover.css").is_file():
        (styles / "hover.css").write_text("/* hover — copied when rebuild/css/hover.css exists */\n", encoding="utf-8")
    if not adopted and not (scripts / "main.js").is_file():
        (scripts / "main.js").write_text("/* client boot — copied when rebuild/js/main.js exists */\n", encoding="utf-8")

    # --- derive BaseLayout wiring from the signed ship (Pitfall #240) ---
    wiring = ship_wiring(ship.read_text(encoding="utf-8", errors="replace"))

    style_tags: list[str] = []
    linked_styles: set[str] = set()
    inline_sheets: list[str] = []
    taken_styles = set(copied["styles"])
    site_existed = "site.css" in taken_styles
    style_i = 0
    for row in wiring["styles"]:
        if row["kind"] == "style":
            style_i += 1
            if style_i == 1 and not site_existed:
                preferred = "site.css"
            elif style_i == 1:
                preferred = "site-inline.css"
            elif not site_existed:
                preferred = f"site-{style_i}.css"
            else:
                preferred = f"site-inline-{style_i}.css"
            name = _unused_name(taken_styles, preferred)
            (styles / name).write_text(rewrite_css_urls(row["css"]).rstrip() + "\n", encoding="utf-8")
            copied["styles"].append(name)
            taken_styles.add(name)
            inline_sheets.append(name)
            href = f"/styles/{name}"
            style_tags.append(f'<link rel="stylesheet" href="{href}"{row.get("extra") or ""} />')
            linked_styles.add(href)
            continue
        href = row["href"]
        style_tags.append(f'<link rel="stylesheet" href="{href}"{row.get("extra") or ""} />')
        if not row["external"]:
            linked_styles.add(href)

    head_scripts: list[str] = []
    body_scripts: list[str] = []
    linked_scripts: set[str] = set()
    taken_scripts = set(copied["scripts"])
    inline_js = 0

    def _emit_script(row: dict) -> None:
        nonlocal inline_js
        bucket = head_scripts if row.get("where") == "head" else body_scripts
        flags = "".join(f" {flag}" for flag in row.get("flags") or [])
        if row["kind"] == "src":
            bucket.append(f'<script is:inline{flags} src="{row["src"]}"></script>')
            if not row["external"]:
                linked_scripts.add(row["src"])
            return
        inline_js += 1
        name = _unused_name(taken_scripts, f"ship-inline-{inline_js}.js")
        (scripts / name).write_text(row["js"].rstrip() + "\n", encoding="utf-8")
        copied["scripts"].append(name)
        taken_scripts.add(name)
        href = f"/scripts/{name}"
        bucket.append(f'<script is:inline{flags} src="{href}"></script>')
        linked_scripts.add(href)

    for row in wiring["scripts"]:
        _emit_script(row)

    # Author runs: link copied sheets/scripts the ship head forgot (Fault A
    # safety net). Adopt runs: the export's unreferenced files are recorded,
    # never force-linked. Forgotten scripts land at end of body.
    appended = {"styles": [], "scripts": []}
    unreferenced = {"styles": [], "scripts": []}
    for rel in copied["styles"]:
        href = f"/styles/{rel}"
        if href in linked_styles:
            continue
        if adopted:
            unreferenced["styles"].append(rel)
        else:
            style_tags.append(f'<link rel="stylesheet" href="{href}" />')
            linked_styles.add(href)
            appended["styles"].append(rel)
    for rel in copied["scripts"]:
        href = f"/scripts/{rel}"
        if href in linked_scripts:
            continue
        if adopted:
            unreferenced["scripts"].append(rel)
        else:
            body_scripts.append(f'<script is:inline src="{href}"></script>')
            linked_scripts.add(href)
            appended["scripts"].append(rel)

    (astro / "src" / "layouts" / "BaseLayout.astro").write_text(
        base_layout(style_tags, head_scripts, body_scripts), encoding="utf-8"
    )

    # --- gate: every local asset BaseLayout references must exist on disk ---
    errors: list[str] = []
    public_dirs = {"/styles/": styles, "/scripts/": scripts, "/images/": images, "/fonts/": fonts}
    for href in sorted(linked_styles | linked_scripts):
        target = None
        for prefix, folder in public_dirs.items():
            if href.startswith(prefix):
                target = folder / href[len(prefix):]
                break
        if target is None:
            errors.append(
                f"BaseLayout references {href} — not a /styles /scripts /images /fonts path and not external; "
                "move the ship asset into a pipeline folder or make the reference external"
            )
        elif not target.is_file():
            errors.append(
                f"BaseLayout references {href} but {target.relative_to(root).as_posix()} does not exist — "
                "the ship links an asset the source folder never shipped"
            )

    has_css = bool(copied["styles"])
    if not has_css and not adopted:
        errors.append("missing rebuild/css tokens/site styles")
    receipt = {
        "generatedFrom": "web2html/phase-5-scaffold",
        "ok": (has_css or adopted) and not errors,
        "astro": "astro",
        "copied": copied,
        "liveCollections": live_files,
        "wiring": {
            "stylesheets": [row["href"] for row in wiring["styles"] if row["kind"] == "link"],
            "scripts": [row["src"] for row in wiring["scripts"] if row["kind"] == "src"],
            "inlineCss": inline_sheets[0] if inline_sheets else None,
            "inlineSheets": inline_sheets,
            "inlineScripts": sum(1 for row in wiring["scripts"] if row["kind"] == "inline"),
            "appendedBeyondShip": appended,
            "unreferenced": unreferenced,
        },
        "ship": "source-html" if adopted else "rebuild",
        "updated": _now_iso(),
        "errors": errors,
    }
    dest = root / "qa" / "phase-5-scaffold.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    try:
        receipt = scaffold(args.root.resolve())
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if not receipt["ok"]:
        for err in receipt["errors"]:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    wiring = receipt["wiring"]
    print(json.dumps({
        "ok": True,
        "astro": "astro/",
        "styles": receipt["copied"]["styles"],
        "scripts": receipt["copied"]["scripts"],
        "inlineCss": wiring["inlineCss"],
        "wiredStylesheets": len(wiring["stylesheets"]) + len(wiring["inlineSheets"]) + len(wiring["appendedBeyondShip"]["styles"]),
        "wiredScripts": len(wiring["scripts"]) + wiring["inlineScripts"] + len(wiring["appendedBeyondShip"]["scripts"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
