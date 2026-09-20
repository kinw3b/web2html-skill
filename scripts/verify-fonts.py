#!/usr/bin/env python3
"""Verify rebuild @font-face files exist, cover Latin, and stacks have fallbacks.

Framer lists Inter (and Google faces) as many subset files. The first
@font-face hash is often Cyrillic Extended (U+0460-052F). Pointing
fonts.css at that file makes English text silently fall back to system-ui
(Pitfall #59).

Usage:
  python3 verify-fonts.py --rebuild prior-run/rebuild \\
      --scrape prior-run/source-site/pages/..html

Exit 0 ok · 1 usage · 2 failed checks
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from emit_fonts import file_hash, font_face_errors

LATIN_MARK = "U+0000"
GENERIC_FALLBACKS = ("sans-serif", "serif", "monospace", "system-ui")
FACE_RE = re.compile(r"@font-face\s*\{([^}]+)\}", re.I)
FAMILY_RE = re.compile(r"font-family\s*:\s*([^;]+)", re.I)
WEIGHT_RE = re.compile(r"font-weight\s*:\s*([^;]+)", re.I)
STYLE_RE = re.compile(r"font-style\s*:\s*([^;]+)", re.I)
SRC_RE = re.compile(r"src\s*:\s*url\(\s*[\"']?([^\"')]+)", re.I)
RANGE_RE = re.compile(r"unicode-range\s*:\s*([^;]+)", re.I)
STACK_RE = re.compile(r"font-family\s*:\s*([^;{]+)", re.I)


def parse_faces(css: str) -> list[dict]:
    out: list[dict] = []
    for body in FACE_RE.findall(css):
        fam = FAMILY_RE.search(body)
        src = SRC_RE.search(body)
        if not (fam and src):
            continue
        weight = WEIGHT_RE.search(body)
        style = STYLE_RE.search(body)
        urange = RANGE_RE.search(body)
        out.append(
            {
                "family": fam.group(1).strip().strip("\"'"),
                "weight": (weight.group(1).strip() if weight else ""),
                "style": (style.group(1).strip() if style else "normal"),
                "src": src.group(1).strip(),
                "unicode_range": (urange.group(1).strip() if urange else ""),
            }
        )
    return out


def latin_files_from_scrape(html: str) -> dict[tuple[str, str, str], list[str]]:
    """family+weight+style → Latin basenames, preserving same-face alternatives."""
    found: dict[tuple[str, str, str], list[str]] = {}
    for face in parse_faces(html.replace("\n", "")):
        if LATIN_MARK not in face["unicode_range"]:
            continue
        key = (face["family"], face["weight"] or "400", face["style"])
        found.setdefault(key, []).append(Path(face["src"].split("?")[0]).name)
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", type=Path, required=True, help="rebuild/ directory")
    ap.add_argument(
        "--scrape",
        type=Path,
        help="Homepage scrape HTML with @font-face (optional but recommended)",
    )
    args = ap.parse_args(argv)

    rebuild: Path = args.rebuild
    fonts_css = rebuild / "css" / "fonts.css"
    fonts_dir = rebuild / "fonts"
    if not fonts_css.is_file():
        print(f"error: missing {fonts_css}", file=sys.stderr)
        return 1

    css = fonts_css.read_text(encoding="utf-8")
    faces = parse_faces(css)
    fails: list[str] = font_face_errors(rebuild.resolve().parent)
    warns: list[str] = []

    if not faces:
        fails.append("fonts.css has no @font-face rules")

    scrape_latin: dict[tuple[str, str, str], list[str]] = {}
    if args.scrape and args.scrape.is_file():
        scrape_latin = latin_files_from_scrape(
            args.scrape.read_text(encoding="utf-8", errors="replace")
        )

    for face in faces:
        src_name = Path(face["src"].split("?")[0]).name
        local = fonts_dir / src_name
        if not local.is_file():
            fails.append(
                f"{face['family']} {face['weight'] or '?'}: missing file "
                f"{local} — keep a system stack (system-ui, sans-serif) and "
                f"re-download the Latin woff2"
            )
            continue
        ur = face["unicode_range"]
        if ur and LATIN_MARK not in ur:
            fails.append(
                f"{face['family']} {face['weight'] or '?'}: unicode-range "
                f"is {ur!r} (no {LATIN_MARK}). First Framer hash is often "
                f"Cyrillic Extended — point src at the Latin subset."
            )
        key = (face["family"], face["weight"] or "400", face["style"])
        expected = scrape_latin.get(key)
        byte_match = bool(expected and args.scrape and any(
            p.is_file() and file_hash(p) == file_hash(local)
            for p in (args.scrape.parent / "assets" / name for name in expected)
        ))
        if expected and src_name not in expected and not byte_match and LATIN_MARK not in ur:
            fails.append(
                f"{face['family']} {face['weight']}: src {src_name} is not "
                f"the scrape Latin file {expected}"
            )
        elif expected and src_name not in expected and not byte_match:
            warns.append(
                f"{face['family']} {face['weight']}: src {src_name} "
                f"(scrape Latin was {expected})"
            )

    # Fallback stacks in utilities + components
    stack_files = [
        rebuild / "css" / "utilities.css",
        rebuild / "css" / "components.css",
        rebuild / "css" / "fonts.css",
        rebuild / "css" / "tokens.css",
        rebuild / "css" / "site.css",
    ]
    stack_ok = False
    for path in stack_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for decl in STACK_RE.findall(text):
            low = decl.lower()
            if any(g in low for g in GENERIC_FALLBACKS):
                stack_ok = True
                break
    if not stack_ok:
        fails.append(
            "no font-family stack includes system-ui / sans-serif — "
            "add fallbacks so missing woff2 still renders"
        )

    for w in warns:
        print(f"warning: {w}", file=sys.stderr)
    if fails:
        print("FONT CHECK FAIL:", file=sys.stderr)
        for f in fails:
            print(f"  - {f}", file=sys.stderr)
        return 2

    print(f"ok: {len(faces)} @font-face rule(s), source style/weight/bytes + Latin + fallback stack")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
