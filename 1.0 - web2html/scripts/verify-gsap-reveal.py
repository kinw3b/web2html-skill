#!/usr/bin/env python3
"""HARD GATE — Emil / 3.2 GSAP in-view contract (2.10.11). Mandatory.

  python3 verify-gsap-reveal.py .

FAIL (exit 2) unless rebuild/index-polish.html (or index.html if the
polish file is not seeded yet) has:
  - vendored js/vendor/gsap.min.js + ScrollTrigger.min.js
  - js/gsap-reveal.js
  - data-reveal count > 0
  - no class="reveal" (Pitfall #1)

Writes qa/gsap-reveal-qa.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CLASS_REVEAL = re.compile(r'class="[^"]*\breveal\b')
DATA_REVEAL = re.compile(r"\bdata-reveal\b")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    polish = root / "rebuild" / "index-polish.html"
    index = polish if polish.is_file() else root / "rebuild" / "index.html"
    ship_label = (
        "rebuild/index-polish.html"
        if polish.is_file()
        else "rebuild/index.html"
    )
    errors = 0
    data_reveal = 0
    class_reveal = 0
    vendor_gsap = (root / "rebuild" / "js" / "vendor" / "gsap.min.js").is_file()
    vendor_st = (root / "rebuild" / "js" / "vendor" / "ScrollTrigger.min.js").is_file()
    runtime = (root / "rebuild" / "js" / "gsap-reveal.js").is_file()
    html = ""

    if not index.is_file():
        fail(f"missing {index} — Emil 3.2 needs a ship page")
        errors += 1
    else:
        html = index.read_text(encoding="utf-8", errors="replace")
        data_reveal = len(DATA_REVEAL.findall(html))
        class_reveal = len(CLASS_REVEAL.findall(html))
        if "gsap.min.js" not in html:
            fail(f"{ship_label} does not reference gsap.min.js")
            errors += 1
        if "ScrollTrigger.min.js" not in html:
            fail(f"{ship_label} does not reference ScrollTrigger.min.js")
            errors += 1
        if "gsap-reveal.js" not in html:
            fail(f"{ship_label} does not reference gsap-reveal.js")
            errors += 1
        if "paper-asset://" in html:
            fail(f"{ship_label} uses paper-asset:// — GSAP must be file://")
            errors += 1
        if data_reveal < 1:
            fail("data-reveal count is 0 — run inject-gsap-reveal.py (Pitfall #1)")
            errors += 1
        if class_reveal:
            fail('class="reveal" is banned (Pitfall #1)')
            errors += 1

    if not vendor_gsap:
        fail("missing rebuild/js/vendor/gsap.min.js")
        errors += 1
    if not vendor_st:
        fail("missing rebuild/js/vendor/ScrollTrigger.min.js")
        errors += 1
    if not runtime:
        fail("missing rebuild/js/gsap-reveal.js")
        errors += 1
    else:
        runtime_js = (root / "rebuild" / "js" / "gsap-reveal.js").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'START = "top 75%"' not in runtime_js and "top 75%" not in runtime_js:
            fail(
                'gsap-reveal.js start must be "top 75%" '
                "(section past 25% of the viewport from the bottom)"
            )
            errors += 1
        if "top 85%" in runtime_js or "top 80%" in runtime_js:
            fail(
                "gsap-reveal.js still uses the retired top 85%/80% start — "
                "use top 75% (Pitfall #204)"
            )
            errors += 1
        if "membersOf" not in runtime_js or "pickParents" not in runtime_js:
            fail(
                "gsap-reveal.js must resolve parent groups via membersOf / "
                "pickParents (heads, grids, mixed inners — not heading leaves)"
            )
            errors += 1

    qa_dir = root / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "ok": errors == 0,
        "data_reveal": data_reveal,
        "class_reveal": class_reveal,
        "vendor": {
            "gsap.min.js": vendor_gsap,
            "ScrollTrigger.min.js": vendor_st,
        },
        "runtime": "js/gsap-reveal.js",
        "runtime_present": runtime,
        "notes": (
            "Mandatory 3.2. Pitfall #1: data-reveal kept; class=reveal banned; "
            "no CSS hide; above-fold measured at boot. "
            "start top 75% (25% from viewport bottom); parent-group stagger "
            "(head children, grid items, mixed inners). "
            "QA/?qa-outlines= and reduced-motion skip prep. Pitfall #204."
        ),
    }
    (qa_dir / "gsap-reveal-qa.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    if errors:
        print(f"{errors} gsap-reveal check(s) failed. Emil/3.2 not verified.", file=sys.stderr)
        return 2
    print(f"OK gsap-reveal: {data_reveal} data-reveal, vendor + runtime present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
