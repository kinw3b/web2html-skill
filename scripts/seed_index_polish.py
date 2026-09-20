#!/usr/bin/env python3
"""Seed rebuild/index-polish.html from the 2.4 ship (2.14.0).

3.x writes the polish file. rebuild/index.html stays the 2.4 lock so 3.4
can compare both. Call when 3.1 (or any 3.x) goes active — not at 2.4 done.
An unpolished copy on disk after 2.4 reads as polish already finished.
Idempotent: never overwrites an existing polish file.

  python3 seed_index_polish.py .
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

INDEX_REL = Path("rebuild") / "index.html"
POLISH_REL = Path("rebuild") / "index-polish.html"


def index_path(root: Path) -> Path:
    return root / INDEX_REL


def polish_path(root: Path) -> Path:
    return root / POLISH_REL


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str | None:
    try:
        return sha256_text(path.read_text(encoding="utf-8"))
    except OSError:
        return None


def live_html(root: Path) -> Path:
    """QA target when present; otherwise the 2.4 lock."""
    polish = polish_path(root)
    if polish.is_file():
        return polish
    return index_path(root)


def seed(root: Path) -> Path | None:
    src = index_path(root)
    dest = polish_path(root)
    if dest.is_file():
        return dest
    if not src.is_file():
        return None
    dest.write_bytes(src.read_bytes())
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    dest = seed(root)
    if dest is None:
        print(f"FAIL: missing {index_path(root)} — seed when 3.1 starts (needs the 2.4 lock)", file=sys.stderr)
        return 2
    print(f"OK index-polish → {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
