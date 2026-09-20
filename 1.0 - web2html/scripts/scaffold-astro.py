#!/usr/bin/env python3
"""5.1 — scaffold astro/ from the signed 3.4 homepage rebuild.

Copies tokens, site CSS, fonts, images, and client scripts from rebuild/.
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

from html_to_astro import rewrite_css_urls

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
  "dependencies": {
    "astro": "^5.13.0"
  }
}
"""

ASTRO_CONFIG = """import { defineConfig } from 'astro/config';

export default defineConfig({
  output: 'static',
  trailingSlash: 'always',
});
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
"""

BASE_LAYOUT = """---
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
    <link rel="stylesheet" href="/styles/tokens.css" />
    <link rel="stylesheet" href="/styles/fonts.css" />
    <link rel="stylesheet" href="/styles/site.css" />
    <link rel="stylesheet" href="/styles/hover.css" />
  </head>
  <body>
    <slot />
    <script src="/scripts/main.js"></script>
  </body>
</html>
"""


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


def scaffold(root: Path) -> dict:
    root = root.resolve()
    rebuild = root / "rebuild"
    if not rebuild.is_dir():
        raise FileNotFoundError("need rebuild/ from the 3.4 homepage run")
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
        for path in sorted(css_dir.glob("*.css")):
            if path.name in SKIP_CSS:
                continue
            dest = styles / path.name
            dest.write_text(rewrite_css_urls(path.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
            copied["styles"].append(path.name)
    js_dir = rebuild / "js"
    if js_dir.is_dir():
        for path in sorted(js_dir.glob("*.js")):
            if path.name in SKIP_JS:
                continue
            shutil.copy2(path, scripts / path.name)
            copied["scripts"].append(path.name)
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
    (astro / "src" / "layouts" / "BaseLayout.astro").write_text(BASE_LAYOUT, encoding="utf-8")
    if not (styles / "hover.css").is_file():
        (styles / "hover.css").write_text("/* hover — copied when rebuild/css/hover.css exists */\n", encoding="utf-8")
    if not (scripts / "main.js").is_file():
        (scripts / "main.js").write_text("/* client boot — copied when rebuild/js/main.js exists */\n", encoding="utf-8")

    receipt = {
        "generatedFrom": "web2html/phase-5-scaffold",
        "ok": bool(copied["styles"]),
        "astro": "astro",
        "copied": copied,
        "updated": _now_iso(),
        "errors": [] if copied["styles"] else ["missing rebuild/css tokens/site styles"],
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
    print(json.dumps({"ok": True, "astro": "astro/", "styles": receipt["copied"]["styles"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
