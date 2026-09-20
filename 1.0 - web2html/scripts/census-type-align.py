#!/usr/bin/env python3
"""2.2.b / 3.3 type-align census from geometry-lock or ship HTML.

Gold is lock alignment + Tailwind size tokens. The skill does not lock fonts.
Writes qa/type-align-census.json.

  python3 census-type-align.py rebuild/index.html
  python3 census-type-align.py --root . --lock qa/fixtures/geometry-lock-home.html
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from type_align import (
    census_type_align,
    default_project_root,
    find_lock_html,
    write_census,
)


def default_qa_path(root: Path) -> Path:
    return root / "qa" / "type-align-census.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html_pos", type=Path, nargs="?", help="rebuild/index.html")
    ap.add_argument("--html", type=Path, help="Ship HTML (rebuild/index.html)")
    ap.add_argument("--lock", type=Path, help="Geometry-lock HTML if present")
    ap.add_argument("--root", type=Path, help="Project root")
    ap.add_argument("--qa", type=Path, help="Write type-align-census.json here")
    args = ap.parse_args(argv)

    ship = args.html or args.html_pos
    root = args.root
    if root is None and ship is not None:
        root = default_project_root(ship)
    if root is None:
        root = Path.cwd()
    root = root.resolve()

    lock = args.lock
    if lock is None:
        lock = find_lock_html(root, ship.resolve() if ship else None)
    source_path = None
    source_kind = "ship"
    if lock is not None and lock.is_file():
        source_path = lock
        # Prefer lock when it is not the ship file itself.
        if ship is None or lock.resolve() != ship.resolve():
            source_kind = "lock"
        else:
            source_kind = "ship"
    elif ship is not None and ship.is_file():
        source_path = ship
        source_kind = "ship"
    if source_path is None or not source_path.is_file():
        print("FAIL: no geometry-lock or rebuild/index.html to census", file=sys.stderr)
        return 1

    html = source_path.read_text(encoding="utf-8")
    rows = census_type_align(html, source=source_kind)
    dest = args.qa or default_qa_path(root)
    write_census(
        dest,
        rows,
        meta={
            "html": str(source_path),
            "kind": source_kind,
        },
    )
    print(
        f"type-align-census: {len(rows)} row(s) from {source_kind} {source_path} → {dest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
