#!/usr/bin/env python3
"""Seed rebuild/index.html from the 2.2 first pass (2.13.0).

2.2 authors rebuild/index-semantic.html. 2.3 copies that file to
rebuild/index.html and is the only writer of the lock. Idempotent: never
overwrites an existing index.html. Never mutates index-semantic.html.

  python3 seed_index.py .
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SEMANTIC_REL = Path("rebuild") / "index-semantic.html"
INDEX_REL = Path("rebuild") / "index.html"


def semantic_path(root: Path) -> Path:
    return root / SEMANTIC_REL


def index_path(root: Path) -> Path:
    return root / INDEX_REL


def seed(root: Path) -> Path | None:
    src = semantic_path(root)
    dest = index_path(root)
    if dest.is_file():
        return dest
    if not src.is_file():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    dest = seed(root)
    if dest is None:
        print(
            f"FAIL: missing {semantic_path(root)} — 2.2 authors the first pass, "
            "then seed index.html",
            file=sys.stderr,
        )
        return 2
    print(f"OK index → {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
