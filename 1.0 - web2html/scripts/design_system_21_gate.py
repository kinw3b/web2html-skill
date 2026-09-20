#!/usr/bin/env python3
"""HARD GATE — 2.1 emitted the Design System page from 1.3 library.json.

rebuild/design-system.html is the token contract, not the ship.
rebuild/index-semantic.html and rebuild/index.html are still forbidden here.

  python3 design_system_21_gate.py /path/to/project

Exit 0 ok · 2 missing page / tokens / invented names / missing receipt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from emit_fonts import font_face_errors

GENERATED_FROM = "web2html/design-system-21"
EMITTED_FROM = "url-to-paper/emit-design-system"
RECEIPT = Path("qa/design-system-21.json")
QA = Path("qa/design-system-21-qa.json")
PAGE = Path("rebuild/design-system.html")
TOKENS = Path("rebuild/css/tokens.css")
LIBRARY = Path("design-library/library.json")
TOKEN_DEF_RE = re.compile(r"(--(?:color|font)-[a-z0-9-]+)\s*:", re.I)
LINK_HREF_RE = re.compile(r"""<link[^>]+href\s*=\s*["']([^"']+)["']""", re.I)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _href_names(html: str) -> set[str]:
    names: set[str] = set()
    for href in LINK_HREF_RE.findall(html or ""):
        names.add(Path(href.split("?", 1)[0]).name)
    return names


def _library_color_font_names(root: Path) -> set[str]:
    names: set[str] = set()
    tokens = root / TOKENS
    if tokens.is_file():
        try:
            names.update(TOKEN_DEF_RE.findall(tokens.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            pass
    library = root / LIBRARY
    if library.is_file():
        try:
            payload = json.loads(library.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            payload = {}
        for token in payload.get("proposedTokens") or []:
            if isinstance(token, dict):
                name = str(token.get("name") or "")
                if name.startswith("--color-") or name.startswith("--font-"):
                    names.add(name)
    return {name.lower() for name in names}


def gate_errors(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    page = root / PAGE
    tokens = root / TOKENS
    library = root / LIBRARY
    receipt = root / RECEIPT
    if not library.is_file():
        return ["missing design-library/library.json — 1.3 must mine the Design Library first"]
    if not page.is_file():
        return [
            "missing rebuild/design-system.html — 2.1 emits the Design System "
            "from library.json (emit-design-system.mjs). Not the ship."
        ]
    if not tokens.is_file():
        errors.append("missing rebuild/css/tokens.css — 2.1 writes tokens from library.json")
    try:
        html = page.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"cannot read rebuild/design-system.html: {exc}"]
    if "tokens.css" not in _href_names(html):
        errors.append("design-system.html must link css/tokens.css")
    fonts = root / "rebuild" / "css" / "fonts.css"
    woff_dir = root / "rebuild" / "fonts"
    has_woff = woff_dir.is_dir() and any(woff_dir.glob("*.woff2"))
    if has_woff and not fonts.is_file():
        errors.append(
            "missing rebuild/css/fonts.css — 2.1 emit_fonts.py self-hosts woff2 (Pitfall #164)"
        )
    if fonts.is_file() and "fonts.css" not in _href_names(html):
        errors.append("design-system.html must link css/fonts.css so token families load")
    errors.extend(font_face_errors(root))
    if "var(--color-" not in html:
        errors.append(
            "design-system.html must paint with var(--color-*) from tokens.css "
            "(do not hardcode #1A1A1A chrome)"
        )
    if 'data-page="design-system"' not in html and "DESIGN SYSTEM" not in html.upper():
        errors.append("rebuild/design-system.html is not the foundations sheet")
    known = _library_color_font_names(root)
    if not known:
        errors.append("no --color/--font names in tokens.css / library.json")
    invented: set[str] = set(TOKEN_DEF_RE.findall(html))
    css_dir = root / "rebuild" / "css"
    if css_dir.is_dir():
        for path in css_dir.glob("*.css"):
            if path.name == "tokens.css":
                continue
            try:
                invented.update(TOKEN_DEF_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
    extra = {name.lower() for name in invented} - known
    if extra:
        sample = ", ".join(sorted(extra)[:6])
        errors.append(f"invented --color/--font names vs 1.3 library: {sample}")
    if not receipt.is_file():
        errors.append(f"missing {RECEIPT} — run emit-design-system.mjs")
    else:
        try:
            payload = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            payload = {}
        if payload.get("generatedFrom") != EMITTED_FROM or payload.get("ok") is not True:
            errors.append(
                f"{RECEIPT} must come from emit-design-system.mjs "
                "(do not freehand the Design System page)"
            )
    return errors


def ready(root: Path) -> bool:
    return not gate_errors(root)


def install_passing_artifacts(root: Path) -> None:
    root = root.resolve()
    (root / "rebuild" / "css").mkdir(parents=True, exist_ok=True)
    (root / "qa").mkdir(parents=True, exist_ok=True)
    (root / "design-library").mkdir(parents=True, exist_ok=True)
    (root / LIBRARY).write_text(
        json.dumps(
            {
                "file": "TEST",
                "proposedTokens": [
                    {"type": "color", "name": "--color-ink", "value": "#111111"},
                    {"type": "color", "name": "--color-surface", "value": "#FFFFFF"},
                    {"type": "fontFamily", "name": "--font-sans", "value": "Inter, sans-serif"},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / TOKENS).write_text(
        ":root {\n  --color-ink: #111111;\n  --color-surface: #FFFFFF;\n"
        "  --font-sans: Inter, sans-serif;\n}\n",
        encoding="utf-8",
    )
    (root / PAGE).write_text(
        "<!doctype html><html lang=\"en\"><head><title>Test · Design system</title>"
        "<link rel=\"stylesheet\" href=\"css/tokens.css\"></head>"
        "<body data-page=\"design-system\"><main class=\"ds-sheet\" "
        "style=\"color:var(--color-ink);background:var(--color-surface)\">"
        "<p>DESIGN SYSTEM · FOUNDATIONS</p></main></body></html>\n",
        encoding="utf-8",
    )
    (root / RECEIPT).write_text(
        json.dumps(
            {
                "generatedFrom": EMITTED_FROM,
                "ok": True,
                "kind": "foundations",
                "tokens": 3,
                "page": "rebuild/design-system.html",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_receipt(root: Path, errors: list[str]) -> Path:
    dest = root / QA
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "ok": not errors,
                "errors": errors,
                "updated": _now_iso(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    errors = gate_errors(root)
    write_receipt(root, errors)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print("design-system-21: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
