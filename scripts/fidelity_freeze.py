#!/usr/bin/env python3
"""2.4 → 3.x fidelity freeze (2.10.10).

2.3 signed layout / type / geometry against Paper. 2.4 is the human
acceptance of that ship. 3.x may add a11y, scrape-only SEO, contrast on
existing tokens, anti-slop, and hover.css. It must not:

  - mutate rebuild/index.html (write rebuild/index-polish.html instead)
  - change font-size or --text-* token uses
  - drop or rename Design Library class names
  - reorder or retitle homepage <section> ids

  python3 fidelity_freeze.py snapshot .
  python3 fidelity_freeze.py verify .

Writes qa/fidelity-freeze-24.json. Exit 0 ok · 1 usage · 2 failed checks.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from seed_index_polish import index_path, live_html, sha256_file

FREEZE_NAME = "fidelity-freeze-24.json"
IGNORE_CSS = {"hover.css", "qa-overlay.css", "faq.css", "nav-dropdown.css", "nav-drawer.css"}
FONT_SIZE = re.compile(r"font-size\s*:\s*([^;}\n]+)", re.I)
TEXT_VAR = re.compile(r"--text-[a-z0-9-]+", re.I)
CLASS_ATTR = re.compile(r'\bclass\s*=\s*"([^"]*)"', re.I)
SECTION_ID = re.compile(r"<section\b[^>]*\bid\s*=\s*\"([^\"]+)\"", re.I)
STYLE_ATTR = re.compile(r'\bstyle\s*=\s*"([^"]*)"', re.I)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def freeze_path(root: Path) -> Path:
    return root / "qa" / FREEZE_NAME


def _library_names(root: Path) -> list[str]:
    lib_path = root / "design-library" / "library.json"
    if not lib_path.is_file():
        return []
    try:
        library = json.loads(lib_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = library.get("components") or []
    if isinstance(raw, dict):
        comps = (raw.get("inPage") or []) + (raw.get("crossPage") or [])
    elif isinstance(raw, list):
        comps = raw
    else:
        comps = []
    names: list[str] = []
    for comp in comps:
        if not isinstance(comp, dict):
            continue
        name = comp.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


def _iter_css(root: Path) -> list[Path]:
    css_dir = root / "rebuild" / "css"
    if not css_dir.is_dir():
        return []
    out = []
    for path in sorted(css_dir.glob("*.css")):
        if path.name in IGNORE_CSS:
            continue
        out.append(path)
    return out


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def collect(root: Path, html_path: Path | None = None) -> dict:
    path = html_path if html_path is not None else index_path(root)
    html = _read(path)
    css_blobs = [_read(p) for p in _iter_css(root)]
    blob = html + "\n" + "\n".join(css_blobs)
    inline_styles = "\n".join(STYLE_ATTR.findall(html))
    font_sizes = sorted(
        value.strip().lower()
        for value in FONT_SIZE.findall(blob + "\n" + inline_styles)
        if value.strip()
    )
    text_tokens = sorted(set(TEXT_VAR.findall(blob)))
    class_hits: dict[str, int] = {}
    html_classes = CLASS_ATTR.findall(html)
    for name in _library_names(root):
        token = re.compile(rf"(?:^|\s){re.escape(name)}(?:\s|$)")
        class_hits[name] = sum(1 for cls in html_classes if token.search(cls))
    section_ids = SECTION_ID.findall(html)
    rel = None
    if path.is_file():
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.name
    return {
        "version": "2.10.10",
        "html": rel,
        "html_sha256": sha256_file(path) if path.is_file() else None,
        "library_classes": class_hits,
        "font_sizes": font_sizes,
        "text_tokens": text_tokens,
        "section_ids": section_ids,
    }


def snapshot(root: Path) -> Path:
    dest = freeze_path(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = collect(root)
    dest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return dest


def _load_freeze(root: Path) -> dict | None:
    path = freeze_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def verify(root: Path) -> list[str]:
    frozen = _load_freeze(root)
    if frozen is None:
        return [f"missing {freeze_path(root)} — snapshot at 2.4 before 3.x"]
    lock = index_path(root)
    want_hash = frozen.get("html_sha256")
    errors: list[str] = []
    if isinstance(want_hash, str) and want_hash:
        got_hash = sha256_file(lock) if lock.is_file() else None
        if got_hash != want_hash:
            errors.append(
                "rebuild/index.html changed after 2.4. 3.x writes "
                "rebuild/index-polish.html only (Pitfall #203)."
            )
    live = collect(root, live_html(root))

    frozen_classes = frozen.get("library_classes") or {}
    live_classes = live.get("library_classes") or {}
    if isinstance(frozen_classes, dict):
        for name, want in frozen_classes.items():
            try:
                need = int(want)
            except (TypeError, ValueError):
                continue
            got = int(live_classes.get(name) or 0)
            if got < need:
                errors.append(
                    f"library class {name!r} dropped {need} → {got}. "
                    "3.x must not replace Design Library class names (Pitfall #196)."
                )

    if Counter(frozen.get("font_sizes") or []) != Counter(live.get("font_sizes") or []):
        errors.append(
            "font-size declarations changed after 2.4. 3.x must not restyle type "
            "(Pitfall #196)."
        )
    if list(frozen.get("text_tokens") or []) != list(live.get("text_tokens") or []):
        errors.append(
            "--text-* token uses changed after 2.4. 3.x must not restyle type "
            "(Pitfall #196)."
        )
    if list(frozen.get("section_ids") or []) != list(live.get("section_ids") or []):
        errors.append(
            "homepage <section> ids changed after 2.4. 3.x must not reorder or "
            "retag signed bands (Pitfall #196)."
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("snapshot", "verify"))
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.action == "snapshot":
        if not index_path(root).is_file():
            fail(f"missing {index_path(root)}")
            return 2
        dest = snapshot(root)
        print(f"OK fidelity freeze snapshot → {dest}")
        return 0
    errors = verify(root)
    if errors:
        for err in errors:
            fail(err)
        print(f"{len(errors)} fidelity-freeze check(s) failed.", file=sys.stderr)
        return 2
    print(f"OK fidelity freeze vs {freeze_path(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
