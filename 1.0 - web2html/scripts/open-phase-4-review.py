#!/usr/bin/env python3
"""4.4 — write the Phase 4 Paper review note and stop for a human."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TEMPLATE = """# Phase 4 human review

Walk every extra Paper page captured at 4.2. Pin comments on anything wrong.
Do not author rebuild HTML for these pages.

Pages:

{pages}

After sign-off, choose: finish the run (`qa/phase-5-skipped.json`, then tidy)
or continue to optional Phase 5 (`qa/phase-5-opted.json`, no tidy).
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = ap.parse_args(argv)
    root = args.root.resolve()
    pages_path = root / "qa" / "phase-4-pages.json"
    pages = []
    if pages_path.is_file():
        try:
            payload = json.loads(pages_path.read_text(encoding="utf-8"))
            pages = payload.get("pages") or []
        except (OSError, json.JSONDecodeError):
            pages = []
    lines = "\n".join(f"- {row.get('paperName') or row.get('slug')} — {row.get('url')}" for row in pages) or "- (none)"
    dest = root / "qa" / "phase-4-review.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(TEMPLATE.format(pages=lines), encoding="utf-8")
    paper = root / "qa" / "paper-file.json"
    if paper.is_file() and sys.platform == "darwin":
        subprocess.run(["open", "-a", "Paper"], check=False)
    print(dest)
    print("Walk the extra Paper pages, pin comments, then choose Phase 5 skip or opt-in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
