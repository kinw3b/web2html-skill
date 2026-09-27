#!/usr/bin/env python3
"""3.4 human checkpoint — refresh the C/3.1–3.3 report and open Chrome.

  python3 open-human-review.py .

Regenerates qa/polish-report.html and rebuild/polish-report.html from
receipts, links the polish page, verifies the polish contract, then opens
Google Chrome on:

  rebuild/index.html              (2.4 lock)
  rebuild/index-polish.html?qa-review=final&qa-outlines=off
  rebuild/polish-report.html

Do not stop at 3.4 without this. Exit 2 if the polish file or report is
missing. verify-polish-passes.py and verify-semantics.py also exit 2 unless
--requested: the human asked this session to move on, those quality gates
warn, and the review still opens (Pitfall #235).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from seed_index_polish import index_path, polish_path

_SCRIPTS = Path(__file__).resolve().parent


def _hint(step: str, status: str = "active", root=None) -> None:
    try:
        import importlib.util
        p = Path(__file__).resolve().parent / "pipeline-progress.py"
        spec = importlib.util.spec_from_file_location("pipeline_progress", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if root is not None:
            mod.hint(step, status, root)
        else:
            mod.hint(step, status)
    except Exception:
        pass


REPORT_HREF = "polish-report.html"
LINK_TAG = f'<link rel="polish-report" href="{REPORT_HREF}"/>'


def ensure_index_link(html: str) -> str:
    if REPORT_HREF in html and "polish-report" in html:
        return html
    if "</head>" in html:
        return html.replace("</head>", f"  {LINK_TAG}\n</head>", 1)
    return LINK_TAG + "\n" + html


def file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def open_chrome(lock: Path, polish: Path, report: Path) -> int:
    """Open the three 3.4 documents: Orca browser tabs when reachable, else Chrome (one call, all URIs)."""
    uris = [
        file_uri(lock),
        file_uri(polish) + "?qa-review=final&qa-outlines=off",
        file_uri(report),
    ]
    import open_doc

    results = open_doc.open_docs(uris, ["open", "-a", "Google Chrome", *uris])
    if all(r.get("opened") for r in results):
        print(f"opened in {open_doc.describe(results[0])}")
        return 0
    print(f"FAIL: could not open the 3.4 review ({results[0].get('error')}).", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument(
        "--no-open",
        action="store_true",
        help="Refresh + verify only (CI). Still writes rebuild/polish-report.html.",
    )
    ap.add_argument(
        "--requested",
        action="store_true",
        help="Human asked this session to move on. Polish / semantics / fidelity / type warn and the review still opens (Pitfall #235).",
    )
    args = ap.parse_args(argv)
    _hint("3.4", "active", args.root)
    root = args.root.resolve()
    lock = index_path(root)
    polish = polish_path(root)
    if not lock.is_file():
        print(f"FAIL: missing {lock}", file=sys.stderr)
        return 2
    if not polish.is_file():
        print(
            f"FAIL: missing {polish}. 3.x copies the 2.4 index and writes QA "
            "there. index-polish.html is created when 3.1 starts. Do not polish "
            "index.html (Pitfall #203).",
            file=sys.stderr,
        )
        return 2

    # Hyphenated modules — load via subprocess so names stay stable.
    rc = subprocess.call(
        [sys.executable, str(_SCRIPTS / "render-polish-report.py"), str(root)]
    )
    if rc != 0:
        return rc

    html = ensure_index_link(polish.read_text(encoding="utf-8"))
    polish.write_text(html, encoding="utf-8")

    # Polish phase owns GSAP. Re-apply here so a 3.3 rewrite cannot force a
    # manual inject at this checkpoint (Pitfall #236). Never touches index.html.
    rc = subprocess.call(
        [sys.executable, str(_SCRIPTS / "inject-gsap-reveal.py"), str(polish)]
    )
    if rc != 0:
        print(
            "FAIL: could not inject GSAP on index-polish.html. "
            "Do not inject by hand. Pitfall #236.",
            file=sys.stderr,
        )
        return rc
    rc = subprocess.call(
        [sys.executable, str(_SCRIPTS / "verify-gsap-reveal.py"), str(root)]
    )
    if rc != 0 and not args.requested:
        print(
            "FAIL: GSAP in-view is not on the polish file. "
            "3.2 active injects it; this checkpoint only refreshes that inject. "
            "Pitfall #236.",
            file=sys.stderr,
        )
        return rc
    if rc != 0:
        print(
            "WARN: GSAP verify red — requested advance, not a stop. Pitfall #236.",
            file=sys.stderr,
        )
    else:
        print("GSAP in-view → index-polish.html  do not inject by hand")

    rc = subprocess.call(
        [sys.executable, str(_SCRIPTS / "verify-polish-passes.py"), str(root)]
    )
    if rc != 0 and not args.requested:
        return rc
    if rc != 0:
        print(
            "WARN: quality gate red (polish / semantics / fidelity / type) — "
            "requested advance, not a stop. Opening the review anyway. Pitfall #235.",
            file=sys.stderr,
        )

    rc = subprocess.call(
        [sys.executable, str(_SCRIPTS / "verify-semantics.py"), str(polish)]
    )
    if rc != 0 and not args.requested:
        print(
            "FAIL: semantics gate (3.4). Run semantics_pass.py (3.3) on "
            "rebuild/index-polish.html before this checkpoint. "
            "See references/semantics-pass.md.",
            file=sys.stderr,
        )
        return rc
    if rc != 0:
        print(
            "WARN: semantics gate red — requested advance, not a stop. Pitfall #235.",
            file=sys.stderr,
        )

    report = root / "rebuild" / "polish-report.html"
    if not args.no_open:
        rc = open_chrome(lock, polish, report)
        if rc != 0:
            return rc
        print(f"opened: {file_uri(lock)}  (2.4 lock)")
        print(f"opened: {file_uri(polish)}  (QA polish, outlines off — ?qa-outlines=tags turns them on)")
        print(f"opened: {file_uri(report)}")
    else:
        print(f"ready for 3.4: {lock} vs {polish}")
        print(f"ready for 3.4: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
