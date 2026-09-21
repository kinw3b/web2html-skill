#!/usr/bin/env python3
"""Open the authored ship page in Chrome with QA TAGS outlines.

  python3 open-build-review.py /path/to/project --stage 2.4
  python3 open-build-review.py /path/to/templates/prior-run

2.4 is the human checkpoint after the 2.3 section-vs-Paper loop. Inject the
QA overlay first. Pesticide TAGS mode is ON by default. A successful Chrome
launch writes qa/build-checkpoint-opened.json. Human approval lands in
qa/build-checkpoint.md before 3.0.

Opens file://…/rebuild/index.html?qa-outlines=tags (query, not hash — Chrome
drops file:// fragments). Alt+O cycles off / on / tags / mono.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def ship_review_uri(index: Path) -> str:
    return index.resolve().as_uri() + "?qa-outlines=tags"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, help="Project root that contains the ship HTML")
    ap.add_argument(
        "--index",
        default="rebuild/index.html",
        help="Ship page relative to root (default: rebuild/index.html)",
    )
    ap.add_argument(
        "--stage",
        choices=("2.4",),
        default="2.4",
        help="2.4 TAGS checkpoint (default)",
    )
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    index = (root / args.index).resolve()
    if not index.is_file():
        print(f"FAIL: missing {index}", file=sys.stderr)
        return 2
    overlay = index.parent / "js" / "qa-overlay.js"
    if not overlay.is_file():
        inject = Path(__file__).resolve().parent / "inject-qa-overlay.py"
        rc = subprocess.call([sys.executable, str(inject), str(index)])
        if rc != 0 or not overlay.is_file():
            print(
                f"FAIL: overlay missing ({overlay}). "
                "inject-qa-overlay.py writes rebuild/css + rebuild/js only "
                "(Pitfall #197).",
                file=sys.stderr,
            )
            return 2
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from section_22_gate import gate_errors as section_errors

    loop_errors = section_errors(root)
    if loop_errors:
        for msg in loop_errors:
            print(f"FAIL: {msg}", file=sys.stderr)
        print(
            "FAIL: 2.4 blocked — 2.3 is still red. Sign each section against "
            "Paper 1600 / 768 / 390.",
            file=sys.stderr,
        )
        return 2
    uri = ship_review_uri(index)
    print(f"2.4 TAGS checkpoint → {uri}")
    print("Pesticide TAGS mode is ON. Record approval in qa/build-checkpoint.md.")
    print("YOU ARE HERE  2.4 · polish has not started.")
    print("NEXT          Continue → Session 3 polish at 3.1")
    print("NOT YET       index-polish.html is created when 3.1 starts.")
    if not args.no_open:
        import open_doc

        result = open_doc.open_doc(uri, ["open", "-a", "Google Chrome", uri])
        if not result.get("opened"):
            print(f"FAIL: could not open the 2.4 review ({result.get('error')}). Open {uri} yourself.", file=sys.stderr)
            return 1
        print(f"opened in {open_doc.describe(result)}")
    receipt = root / "qa" / "build-checkpoint-opened.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        json.dumps(
            {
                "generatedFrom": "web2html/open-build-review",
                "stage": "2.4",
                "uri": uri,
                "openedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
