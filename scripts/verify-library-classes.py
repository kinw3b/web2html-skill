#!/usr/bin/env python3
"""HARD GATE (2.8.48) — ship page must wear design-library class names.

Verify only before the 3.4 human checkpoint. Do not rename classes after 2.4
(Pitfall #196). Missing names are a 2.2/2.3 miss.

  python3 verify-library-classes.py \
      --html rebuild/index.html \
      --library design-library/library.json \
      --map qa/library-class-map.json

Exit 0 ok · 1 usage · 2 failed checks
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_COUNT = {"navbar-dropdown-icon"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def class_count(html: str, cls: str) -> int:
    return len(re.findall(rf'class="[^"]*\b{re.escape(cls)}\b', html))


def label_has_class(
    html: str, label: str, cls: str, *, window: int = 900, style_includes: list[str] | None = None
) -> bool:
    needles = style_includes or []
    start = 0
    found = False
    while True:
        i = html.find(label, start)
        if i < 0:
            return found
        chunk = html[max(0, i - window) : i + len(label)]
        if needles and not all(n in chunk for n in needles):
            start = i + 1
            continue
        found = True
        if f'class="{cls}"' in chunk or f" {cls}\"" in chunk or f" {cls} " in chunk:
            if re.search(rf'class="[^"]*\b{re.escape(cls)}\b', chunk):
                return True
        start = i + 1
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", type=Path, required=True)
    ap.add_argument("--library", type=Path, required=True)
    ap.add_argument("--map", type=Path, required=True)
    args = ap.parse_args(argv)

    if not args.html.is_file() or not args.library.is_file() or not args.map.is_file():
        fail("missing html, library.json, or class map")
        return 2

    html = args.html.read_text(encoding="utf-8")
    library = json.loads(args.library.read_text(encoding="utf-8"))
    spec = json.loads(args.map.read_text(encoding="utf-8"))
    errors = 0

    raw_comps = library.get("components") or []
    if isinstance(raw_comps, dict):
        comps = (raw_comps.get("inPage", []) or []) + (raw_comps.get("crossPage", []) or [])
    elif isinstance(raw_comps, list):
        comps = raw_comps
    else:
        comps = []

    for comp in comps:
        if not isinstance(comp, dict):
            continue
        name = comp.get("name")
        if not name or name in SKIP_COUNT:
            continue
        want = 1
        got = class_count(html, name)
        if got < want:
            fail(
                f"library {name!r} needs ≥{want} class hits, found {got}. "
                "Missing library class after 2.4 freeze — escalate to 2.2/2.3. Pitfall #196."
            )
            errors += 1

    for rule in spec.get("require") or []:
        cls = rule["class"]
        if "label" in rule:
            ok = label_has_class(
                html,
                rule["label"],
                cls,
                window=int(rule.get("window") or 900),
                style_includes=list(rule.get("styleIncludes") or []),
            )
            if not ok:
                fail(
                    f"{rule['label']!r} is not a {cls} (self or painted ancestor). "
                    "Outlines will show a bare div. Pitfall #62."
                )
                errors += 1
        if "min" in rule and "label" not in rule:
            got = class_count(html, cls)
            if got < int(rule["min"]):
                fail(f"{cls!r} count {got} < {rule['min']}")
                errors += 1

    if errors:
        print(f"{errors} library-class check(s) failed.", file=sys.stderr)
        return 2
    print(f"OK library classes on {args.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
