#!/usr/bin/env python3
"""HARD GATE — 3.3 / 2.2.e comprehensive semantics sweep.

Fails on missing landmarks, leftover Paper <div> bands, card clusters
without <article>, illegal heading rank, unlabeled name/email inputs,
and content images missing alt. Skip-link is NEVER required. Missing
Open Graph is NEVER a fail when scrape had none.

  python3 verify-semantics.py rebuild/index.html
  python3 verify-semantics.py --html rebuild/index.html --qa qa/semantics-pass-qa.json

Exit 0 ok · 1 usage · 2 failed checks
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from heading_promote import census_headings, write_qa as write_heading_qa
from semantics_pass import build_qa, default_qa_path, write_qa


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html_pos", type=Path, nargs="?", help="rebuild/index.html")
    ap.add_argument("--html", type=Path, help="rebuild/index.html")
    ap.add_argument("--qa", type=Path, help="Write semantics-pass-qa.json")
    args = ap.parse_args(argv)
    html_path = args.html or args.html_pos
    if html_path is None:
        fail("pass rebuild/index.html (positional or --html)")
        return 1
    if not html_path.is_file():
        fail(f"missing {html_path}")
        return 1
    html = html_path.read_text(encoding="utf-8")
    qa = build_qa(html)
    dest = args.qa or default_qa_path(html_path)
    if dest is None:
        guess = html_path.parent.parent / "qa" / "semantics-pass-qa.json"
        dest = guess
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_qa(dest, qa)
    write_heading_qa(dest.with_name("heading-pass-qa.json"), census_headings(html))
    errors = qa.get("errors") or []
    if errors:
        for msg in errors:
            fail(f"{html_path} {msg}")
        print(f"{len(errors)} semantics check(s) failed.", file=sys.stderr)
        return 2
    print(
        f"OK semantics on {html_path} "
        f"(header={qa['landmarks']['header']} main={qa['landmarks']['main']} "
        f"footer={qa['landmarks']['footer']} articles={qa['articles']} "
        f"h1={qa['h1']} skip_link_required=false)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
