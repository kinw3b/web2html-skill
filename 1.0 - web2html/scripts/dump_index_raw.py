#!/usr/bin/env python3
"""2.2 — write rebuild/index-raw.html as file:// HTML, not JSON.

Paper get_jsx returns JSON. This script converts it, expands self-closing
non-void tags, and links 2.1 tokens.css (and fonts.css when present).

  python3 dump_index_raw.py /path/to/project
  python3 dump_index_raw.py /path/to/project --from qa/index-raw.jsx.json

If --from is omitted, uses rebuild/index-raw.html (when it is still JSON)
or qa/index-raw.jsx.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsx_to_static_html import conversion_errors, to_static_html
from emit_fonts import emit_fonts

GENERATED_FROM = "web2html/dump-index-raw"
RECEIPT = Path("qa/index-raw-22.json")
DEST = Path("rebuild/index-raw.html")
TOKENS = Path("rebuild/css/tokens.css")
FONTS = Path("rebuild/css/fonts.css")
CANDIDATES = (
    Path("rebuild/index-raw.html"),
    Path("qa/index-raw.jsx.json"),
    Path("qa/get_jsx.json"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resolve_source(root: Path, source: Path | None) -> Path:
    if source is not None:
        path = source if source.is_absolute() else root / source
        if not path.is_file():
            raise FileNotFoundError(f"missing get_jsx dump: {path}")
        return path
    for rel in CANDIDATES:
        path = root / rel
        if path.is_file():
            return path
    raise FileNotFoundError(
        "no get_jsx dump — save Paper get_jsx JSON then rerun "
        "dump_index_raw.py --from qa/index-raw.jsx.json"
    )


def dump_index_raw(root: Path, source: Path | None = None) -> dict:
    root = root.resolve()
    dest = root / DEST
    src = resolve_source(root, source)
    tokens = root / TOKENS
    if not tokens.is_file():
        raise FileNotFoundError(
            "missing rebuild/css/tokens.css — emit the 2.1 Design System first"
        )
    emit_fonts(root)
    fonts_href = "css/fonts.css" if (root / FONTS).is_file() else None
    html = to_static_html(
        src.read_text(encoding="utf-8"),
        wrap=True,
        tokens_href="css/tokens.css",
        fonts_href=fonts_href,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    leftover = conversion_errors(html)
    if leftover:
        raise ValueError("; ".join(leftover))
    receipt = {
        "generatedFrom": GENERATED_FROM,
        "ok": True,
        "source": src.relative_to(root).as_posix() if src.is_relative_to(root) else str(src),
        "page": DEST.as_posix(),
        "tokensCss": TOKENS.as_posix(),
        "fontsCss": FONTS.as_posix() if fonts_href else None,
        "bytes": dest.stat().st_size,
        "updated": _now_iso(),
    }
    rec_path = root / RECEIPT
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    rec_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--from", dest="source", type=Path)
    args = ap.parse_args(argv)
    try:
        receipt = dump_index_raw(args.root.resolve(), args.source)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
