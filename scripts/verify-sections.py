#!/usr/bin/env python3
"""HARD GATE — Paper named page bands must be real <section> tags.

Fails if a `data-paper-section` content band (hero, features, about,
testimonials, article, cta, …) is still a <div>. Header / nav / footer
are not content bands.

  python3 verify-sections.py rebuild/index.html
  python3 verify-sections.py --html rebuild/index.html
  python3 verify-sections.py rebuild/index.html --qa qa/section-pass-qa.json

Exit 0 ok · 1 usage · 2 failed checks
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from section_promote import section_gate_errors


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html_pos", type=Path, nargs="?", help="rebuild/index.html")
    ap.add_argument("--html", type=Path, help="rebuild/index.html")
    ap.add_argument("--qa", type=Path, help="Write section-pass-qa.json")
    args = ap.parse_args(argv)
    html_path = args.html or args.html_pos
    if html_path is None:
        fail("pass rebuild/index.html (positional or --html)")
        return 1
    if not html_path.is_file():
        fail(f"missing {html_path}")
        return 1
    html = html_path.read_text(encoding="utf-8")
    errors = section_gate_errors(html)
    leftover = []
    for msg in errors:
        # "data-paper-section=\"features\" is still a <div> — …"
        if 'data-paper-section="' in msg:
            leftover.append(msg.split('data-paper-section="', 1)[1].split('"', 1)[0])
        else:
            leftover.append(msg)
    qa = {
        "ok": not errors,
        "leftover_div_sections": leftover,
        "section_count": len(re.findall(r"<section\b", html, re.I)),
        "errors": errors,
    }
    dest = args.qa
    if dest is None:
        guess = html_path.parent.parent / "qa" / "section-pass-qa.json"
        if guess.parent.is_dir() or args.qa is not None:
            dest = guess
    if dest is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    if errors:
        for msg in errors:
            fail(f"{html_path} {msg}")
        print(f"{len(errors)} section check(s) failed.", file=sys.stderr)
        return 2
    print(f"OK Paper content bands are <section> on {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
