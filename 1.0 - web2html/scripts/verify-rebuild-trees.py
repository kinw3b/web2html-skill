#!/usr/bin/env python3
"""HARD GATE — one ship folder (2.9.0).

  python3 verify-rebuild-trees.py .
  python3 verify-rebuild-trees.py . --prefix rebuild

FAIL (exit 2) unless <prefix>/index.html is the only rebuild tree and has
the QA overlay. Extra rebuild-semantic / rebuild-hover trees fail.
A get_jsx dump is not the ship.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from rebuild_write_gate import RAW_PAPER_EXPORT_RE

def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, help="Project root")
    ap.add_argument(
        "--prefix",
        default="rebuild",
        help="Ship folder name (default: rebuild)",
    )
    args = ap.parse_args(argv)
    root = args.root.resolve()
    prefix = args.prefix
    ship = root / prefix
    errors = 0

    forbidden = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        name = p.name
        if name == prefix:
            continue
        if name in {"rebuild-semantic", "rebuild-hover"}:
            forbidden.append(name)
        elif name.endswith("-semantic") or name.endswith("-hover"):
            if name.startswith("rebuild"):
                forbidden.append(name)
    if forbidden:
        fail(
            "extra rebuild trees on disk: "
            + ", ".join(sorted(forbidden))
            + " — keep one authored page in "
            + f"{prefix}/ and delete the sibling folders"
        )
        errors += 1

    html_path = ship / "index.html"
    if not html_path.is_file():
        fail(f"missing ship {html_path}")
        errors += 1
        print(f"{errors} check(s) failed.", file=sys.stderr)
        return 2

    html = html_path.read_text(encoding="utf-8", errors="replace")
    if RAW_PAPER_EXPORT_RE.search(html):
        fail(
            f"{html_path} still has get_jsx dump metadata — "
            "2.1 authors the page, it does not ship a dump"
        )
        errors += 1
    css = ship / "css" / "qa-overlay.css"
    js = ship / "js" / "qa-overlay.js"
    if not css.is_file() or css.stat().st_size < 200:
        fail(f"{css} missing — run inject-qa-overlay.py (tags in HTML are not enough)")
        errors += 1
    if not js.is_file() or js.stat().st_size < 200:
        fail(f"{js} missing — run inject-qa-overlay.py")
        errors += 1
    leaked = []
    for folder in (root / "css", root / "js", root.parent / "css", root.parent / "js"):
        for name in ("qa-overlay.css", "qa-overlay.js"):
            hit = folder / name
            if hit.is_file():
                leaked.append(hit)
    if leaked:
        fail(
            "QA overlay leaked outside rebuild/: "
            + ", ".join(str(p) for p in leaked)
            + " — keep css/js inside rebuild/ only (Pitfall #197)"
        )
        errors += 1
    if "qa-overlay.css" not in html:
        fail(f"{html_path} does not link qa-overlay.css")
        errors += 1
    if "qa-overlay.js" not in html:
        fail(f"{html_path} does not load qa-overlay.js")
        errors += 1
    if re.search(r"""id\s*=\s*["']skip(?:-to)?(?:-content)?["']""", html, re.I):
        fail("invented skip-link — Paper did not paint that chrome")
        errors += 1
    if 'id="header-2"' in html or 'data-paper-section="header-2"' in html:
        fail("nested chrome still in ship HTML (header-2). Re-export after Pitfall #51.")
        errors += 1

    if errors:
        print(
            f"{errors} check(s) failed. One ship folder: {prefix}/index.html.",
            file=sys.stderr,
        )
        return 2
    print(f"OK single-folder contract: {ship}/index.html (authored + Outlines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
