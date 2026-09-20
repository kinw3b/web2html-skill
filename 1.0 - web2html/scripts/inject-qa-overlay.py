#!/usr/bin/env python3
"""Copy Pesticide-style QA overlay into rebuild/ and inject <link>/<script>.

  python3 inject-qa-overlay.py .
  python3 inject-qa-overlay.py rebuild/index.html
  python3 inject-qa-overlay.py /path/to/project

Always ship the overlay on the ship page in `rebuild/`. Default is TAGS
(pesticide TAGS mode ON). The user toggles with the corner button or Alt+O.

Assets ALWAYS land in <project>/rebuild/css and <project>/rebuild/js.
Never write css/ or js/ next to the project, never next to cwd.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
CSS_NAME = "qa-overlay.css"
JS_NAME = "qa-overlay.js"
SKIP_HTML = {"polish-report.html", "index-raw.html", "index-semantic.html"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def resolve_rebuild(path: Path) -> Path | None:
    """Return the rebuild/ directory that owns this path, or None."""
    path = path.resolve()
    if path.is_file():
        if path.parent.name == "rebuild":
            return path.parent
        return None
    if not path.is_dir():
        return None
    if path.name == "rebuild" and (path / "index.html").is_file():
        return path
    nested = path / "rebuild"
    if (nested / "index.html").is_file():
        return nested
    return None


def copy_assets(rebuild: Path) -> None:
    css_dest = rebuild / "css" / CSS_NAME
    js_dest = rebuild / "js" / JS_NAME
    css_dest.parent.mkdir(parents=True, exist_ok=True)
    js_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATES / CSS_NAME, css_dest)
    shutil.copy2(TEMPLATES / JS_NAME, js_dest)


def inject(html: str, css_href: str, js_href: str) -> str:
    if "data-qa-outlines=" not in html:
        if "<html" in html:
            html = html.replace("<html", '<html data-qa-outlines="tags"', 1)
        else:
            html = '<html data-qa-outlines="tags">' + html
    if CSS_NAME not in html:
        tag = f'<link rel="stylesheet" href="{css_href}"/>'
        if "</head>" in html:
            html = html.replace("</head>", f"{tag}\n</head>", 1)
        else:
            html = tag + html
    if JS_NAME not in html:
        tag = f'<script src="{js_href}" defer></script>'
        if "</body>" in html:
            html = html.replace("</body>", f"{tag}\n</body>", 1)
        else:
            html += "\n" + tag
    return html


def html_pages(rebuild: Path, requested: list[Path]) -> list[Path]:
    files = [p.resolve() for p in requested if p.is_file()]
    if files:
        return [p for p in files if p.parent == rebuild and p.name not in SKIP_HTML]
    return sorted(
        p
        for p in rebuild.glob("*.html")
        if p.is_file() and p.name not in SKIP_HTML
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "target",
        type=Path,
        nargs="+",
        help="Project root, rebuild/, or rebuild/*.html",
    )
    ap.add_argument("--css-href", default="css/qa-overlay.css")
    ap.add_argument("--js-href", default="js/qa-overlay.js")
    ap.add_argument(
        "--assets-dir",
        type=Path,
        help="Ignored unless it resolves to the same rebuild/ directory.",
    )
    args = ap.parse_args(argv)

    rebuilds: dict[Path, list[Path]] = {}
    for raw in args.target:
        rebuild = resolve_rebuild(raw)
        if rebuild is None:
            fail(
                f"{raw} is not a project root or rebuild/*.html. "
                "QA overlay stays in rebuild/css and rebuild/js "
                "(Pitfall #197)."
            )
            return 2
        rebuilds.setdefault(rebuild, []).append(raw.resolve())

    if args.assets_dir is not None:
        forced = args.assets_dir.resolve()
        if forced.name != "rebuild" or forced not in rebuilds:
            fail(
                f"--assets-dir {args.assets_dir} is not rebuild/. "
                "Refusing to write overlay outside the ship folder (Pitfall #197)."
            )
            return 2

    for rebuild, requested in rebuilds.items():
        copy_assets(rebuild)
        pages = html_pages(rebuild, requested)
        if not pages:
            fail(f"no rebuild HTML to inject under {rebuild}")
            return 2
        for path in pages:
            text = path.read_text(encoding="utf-8")
            path.write_text(
                inject(text, args.css_href, args.js_href), encoding="utf-8"
            )
            print(f"injected overlay → {path}")
        print(f"overlay assets → {rebuild / 'css' / CSS_NAME}")
        print(f"overlay assets → {rebuild / 'js' / JS_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
