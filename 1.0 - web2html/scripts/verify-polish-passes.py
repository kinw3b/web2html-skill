#!/usr/bin/env python3
"""HARD GATE — C/3 polish receipts + 3.2 companions (2.20.1) + 2.4 fidelity freeze.

  python3 verify-polish-passes.py .

FAIL (exit 2) unless:
  1. qa/polish-passes/c3-3.1-impeccable.json
     qa/polish-passes/c3-3.2-design-taste-frontend.json
     qa/polish-passes/c3-3.3-emil-design-eng.json exist.
     C/3 ids are sub-pass ids, not board steps: impeccable + taste land
     during board 3.1, emil during board 3.2.
  2. Each has ended_at, status not pending
  3. Each has applied rows and/or skipped rows
  4. File changes require applied rows
  5. qa/polish-report.html exists and mentions 3.1, 3.2, 3.3, impeccable,
     emil, and the three 3.2 companion skills
  6. rebuild/index-polish.html exists, links polish-report.html, and
     verify-semantics.py passes on that file (3.3). Pitfall #93 #203.
  7. When qa/fidelity-freeze-24.json exists, fidelity_freeze.py verify
     passes (index.html hash still matches 2.4; polish did not restyle
     type, library classes, or section ids). Pitfall #196 #203.
  8. GSAP in-view is mandatory. verify-gsap-reveal.py must pass on
     rebuild/index-polish.html. Do not skip from a 1.4 archive
     (Pitfall #204).
  9. 3.2 button hover CSS from 1.3 (`apply-hover-css.py`).
     qa/button-hover-css.json `"ok": true`. If 1.3 applied source CSS
     hover, rebuild/css/hover.css must be linked from index-polish.html
     (Pitfall #207).
 10. 3.2 burger open drawer (`author-nav-drawer.py`).
     qa/nav-drawer.json `"ok": true`. If index-polish paints a hamburger,
     the polish file must have a stacked `#nav-panel` and a binder.
     Do not skip because Capture Tool did not run (Pitfall #208).
 11. 3.2 FAQ accordion (`author-faq.py`).
     qa/faq.json `"ok": true`. If FAQ rows are painted, wire toggle and
     fill empty answers from source-site. Do not skip empty Paper bodies
     (Pitfall #209).
 12. 3.2 nav dropdown (`author-nav-dropdown.py`).
     qa/nav-dropdown.json `"ok": true`. Wire painted or scrape-matched
     dropdowns. Do not skip for Capture Tool / --allow-dropdown
     (Pitfall #210).
 13. 3.2 companion receipts exist and are not empty:
     qa/web-design-guidelines.md, qa/find-animation-opportunities.md,
     qa/apple-design.md. A companion that ran without a receipt, or a
     blocked finding dropped instead of written as a skipped / n-a row,
     fails here (Pitfall #215).

Do not mark C/3 polish complete if this script fails.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REQUIRED = [
    ("3.1", "impeccable", "c3-3.1-impeccable.json"),
    ("3.2", "design-taste-frontend", "c3-3.2-design-taste-frontend.json"),
    ("3.3", "emil-design-eng", "c3-3.3-emil-design-eng.json"),
]
# 3.2 companions: markdown receipts, one per skill (Pitfall #215).
COMPANIONS = [
    ("web-design-guidelines", "qa/web-design-guidelines.md"),
    ("find-animation-opportunities", "qa/find-animation-opportunities.md"),
    ("apple-design", "qa/apple-design.md"),
]
REPORT_TOKENS = (
    "3.1",
    "3.2",
    "3.3",
    "impeccable",
    "emil",
    "web-design-guidelines",
    "find-animation-opportunities",
    "apple-design",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    folder = root / "qa" / "polish-passes"
    errors = 0

    if not folder.is_dir():
        fail(f"missing {folder} — run record-polish-pass.py for 3.1, 3.2, 3.3")
        return 2

    for pass_id, skill, name in REQUIRED:
        path = folder / name
        if not path.is_file():
            fail(f"missing receipt {path}")
            errors += 1
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"{path} is not JSON: {exc}")
            errors += 1
            continue
        if data.get("pass") != pass_id:
            fail(f"{path} pass id {data.get('pass')!r} != {pass_id}")
            errors += 1
        if data.get("skill") != skill:
            fail(f"{path} skill {data.get('skill')!r} != {skill}")
            errors += 1
        if not data.get("ended_at"):
            fail(f"{path} missing ended_at")
            errors += 1
        if data.get("status") in (None, "pending"):
            fail(f"{path} status is pending — pass was not finished")
            errors += 1
        applied = data.get("applied") or []
        skipped = data.get("skipped") or []
        changed = data.get("files_changed") or []
        if not applied and not skipped:
            fail(f"{path} has no applied and no skipped rows")
            errors += 1
        if changed and not applied:
            fail(f"{path} changed rebuild/ files but applied is empty")
            errors += 1

    for skill, rel in COMPANIONS:
        path = root / rel
        text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
        if not text.strip():
            fail(
                f"missing 3.2 companion receipt {rel} — {skill} did not run, "
                "or ran without a receipt. Write applied / skipped / n-a rows; "
                "a blocked finding is a skipped row, not a missing row. Pitfall #215."
            )
            errors += 1

    report = root / "qa" / "polish-report.html"
    if not report.is_file():
        fail("missing qa/polish-report.html — run render-polish-report.py")
        errors += 1
    else:
        html = report.read_text(encoding="utf-8", errors="replace")
        for token in REPORT_TOKENS:
            if token not in html:
                fail(f"qa/polish-report.html does not mention {token}")
                errors += 1

    ship_report = root / "rebuild" / "polish-report.html"
    if not ship_report.is_file():
        fail(
            "missing rebuild/polish-report.html — 3.4 Chrome review needs "
            "the report next to index-polish.html. Run render-polish-report.py "
            "or open-human-review.py. Pitfall #63."
        )
        errors += 1
    else:
        ship_html = ship_report.read_text(encoding="utf-8", errors="replace")
        for token in REPORT_TOKENS:
            if token not in ship_html:
                fail(f"rebuild/polish-report.html does not mention {token}")
                errors += 1

    polish = root / "rebuild" / "index-polish.html"
    if not polish.is_file():
        fail(
            "missing rebuild/index-polish.html — 3.x copies the 2.4 "
            "index.html and writes QA there. Run seed_index_polish.py. "
            "Pitfall #203."
        )
        errors += 1
    elif "polish-report.html" not in polish.read_text(
        encoding="utf-8", errors="replace"
    ):
        fail(
            "rebuild/index-polish.html does not link polish-report.html. "
            "Run open-human-review.py so 3.4 Chrome has the Polish control. "
            "Pitfall #63."
        )
        errors += 1

    if polish.is_file():
        verify = Path(__file__).resolve().parent / "verify-gsap-reveal.py"
        rc = subprocess.call([sys.executable, str(verify), str(root)])
        if rc != 0:
            fail(
                "GSAP in-view is mandatory at 3.2. Run "
                "inject-gsap-reveal.py rebuild/index-polish.html then "
                "verify-gsap-reveal.py . Do not skip because 1.4 did not "
                "record motion (Pitfall #204). See references/gsap-inview.md."
            )
            errors += 1
        hover = root / "qa" / "button-hover-css.json"
        hover_ok = False
        if hover.is_file():
            try:
                hover_ok = json.loads(hover.read_text(encoding="utf-8")).get("ok") is True
            except (OSError, json.JSONDecodeError, TypeError):
                hover_ok = False
        if not hover_ok:
            fail(
                "3.2 button hover CSS is missing. Run "
                "apply-hover-css.py . after 1.3 qa/button-hover.json. "
                "Do not skip because Capture Tool did not run (Pitfall #207)."
            )
            errors += 1
        else:
            polish_html = polish.read_text(encoding="utf-8", errors="replace")
            source = root / "qa" / "button-hover.json"
            applied = []
            if source.is_file():
                try:
                    applied = json.loads(source.read_text(encoding="utf-8")).get("applied") or []
                except (OSError, json.JSONDecodeError):
                    applied = []
            if applied and "css/hover.css" not in polish_html:
                fail(
                    "1.3 authored button hover but index-polish.html does not "
                    "link css/hover.css. Run apply-hover-css.py . Pitfall #207."
                )
                errors += 1
        drawer = root / "qa" / "nav-drawer.json"
        drawer_ok = False
        drawer_payload = {}
        if drawer.is_file():
            try:
                drawer_payload = json.loads(drawer.read_text(encoding="utf-8"))
                drawer_ok = (
                    drawer_payload.get("ok") is True
                    and drawer_payload.get("writer") == "author-nav-drawer.py"
                )
            except (OSError, json.JSONDecodeError, TypeError):
                drawer_ok = False
        banned = False
        for row in drawer_payload.get("skipped") or []:
            reason = str(row.get("reason") or "")
            finding = str(row.get("finding") or "")
            if "burger" in finding.casefold() and re.search(
                r"capture tool open-nav|inventing a sheet|new chrome", reason, re.I
            ):
                banned = True
        emil = folder / "c3-3.3-emil-design-eng.json"
        if emil.is_file():
            try:
                emil_data = json.loads(emil.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                emil_data = {}
            for row in emil_data.get("skipped") or []:
                reason = str(row.get("reason") or "")
                finding = str(row.get("finding") or "")
                if "burger" in finding.casefold() and re.search(
                    r"capture tool open-nav|inventing a sheet|new chrome",
                    reason,
                    re.I,
                ):
                    banned = True
        guidelines = root / "qa" / "web-design-guidelines.md"
        if guidelines.is_file():
            text = guidelines.read_text(encoding="utf-8", errors="replace")
            if re.search(
                r"burger[\s\S]{0,160}(capture tool open-nav|inventing a sheet|new chrome)",
                text,
                re.I,
            ):
                banned = True
        if banned or not drawer_ok:
            fail(
                "3.2 burger drawer is missing or was skipped for Capture Tool. "
                "Run author-nav-drawer.py . A painted hamburger must open the "
                "same desktop links stacked. Pitfall #208."
            )
            errors += 1
        elif polish.is_file() and drawer_payload.get("painted") is True:
            polish_html = polish.read_text(encoding="utf-8", errors="replace")
            if "nav-panel" not in polish_html or (
                "js/nav-drawer.js" not in polish_html
                and "nav-open" not in polish_html
                and "is-nav-open" not in polish_html
            ):
                fail(
                    "qa/nav-drawer.json says a hamburger was painted but "
                    "index-polish.html has no open drawer. Run "
                    "author-nav-drawer.py . Pitfall #208."
                )
                errors += 1
        faq = root / "qa" / "faq.json"
        faq_ok = False
        faq_payload = {}
        if faq.is_file():
            try:
                faq_payload = json.loads(faq.read_text(encoding="utf-8"))
                faq_ok = (
                    faq_payload.get("ok") is True
                    and faq_payload.get("writer") == "author-faq.py"
                )
            except (OSError, json.JSONDecodeError, TypeError):
                faq_ok = False
        faq_banned = False
        painted_faq = faq_payload.get("painted") is True
        for row in faq_payload.get("skipped") or []:
            reason = str(row.get("reason") or "")
            finding = str(row.get("finding") or "")
            if painted_faq and "faq" in finding.casefold() and re.search(
                r"empty bodies|do not invent copy|capture tool|detect-only|no faq capture",
                reason,
                re.I,
            ):
                faq_banned = True
        if faq_banned or not faq_ok:
            fail(
                "3.2 FAQ accordion is missing or was skipped because answers "
                "were empty in Paper. Run author-faq.py . Fill from "
                "source-site; still wire painted rows. Pitfall #209."
            )
            errors += 1
        elif polish.is_file() and painted_faq:
            polish_html = polish.read_text(encoding="utf-8", errors="replace")
            if "toggle-faq" not in polish_html or "js/faq.js" not in polish_html:
                fail(
                    "qa/faq.json says FAQ rows were painted but "
                    "index-polish.html has no accordion. Run author-faq.py . "
                    "Pitfall #209."
                )
                errors += 1
        dropdown = root / "qa" / "nav-dropdown.json"
        dropdown_ok = False
        dropdown_payload = {}
        if dropdown.is_file():
            try:
                dropdown_payload = json.loads(dropdown.read_text(encoding="utf-8"))
                dropdown_ok = (
                    dropdown_payload.get("ok") is True
                    and dropdown_payload.get("writer") == "author-nav-dropdown.py"
                )
            except (OSError, json.JSONDecodeError, TypeError):
                dropdown_ok = False
        dropdown_banned = False
        for row in dropdown_payload.get("skipped") or []:
            reason = str(row.get("reason") or "")
            finding = str(row.get("finding") or "")
            if "dropdown" in finding.casefold() and re.search(
                r"capture tool|allow-dropdown|do not hunt|no dropdown capture",
                reason,
                re.I,
            ):
                dropdown_banned = True
        if dropdown_banned or not dropdown_ok:
            fail(
                "3.2 nav dropdown is missing or was skipped for Capture Tool. "
                "Run author-nav-dropdown.py . Wire painted or scrape-matched "
                "menus. Pitfall #210."
            )
            errors += 1
        elif polish.is_file() and dropdown_payload.get("painted") is True:
            polish_html = polish.read_text(encoding="utf-8", errors="replace")
            if (
                "data-nav-dropdown-trigger" not in polish_html
                or "js/nav-dropdown.js" not in polish_html
            ):
                fail(
                    "qa/nav-dropdown.json says a dropdown was painted but "
                    "index-polish.html has no panel. Run "
                    "author-nav-dropdown.py . Pitfall #210."
                )
                errors += 1
        sem = Path(__file__).resolve().parent / "verify-semantics.py"
        rc = subprocess.call([sys.executable, str(sem), str(polish)])
        if rc != 0:
            fail(
                "semantics contract failed — run semantics_pass.py (3.3) "
                "on rebuild/index-polish.html before 3.4. "
                "See references/semantics-pass.md. Pitfall #93."
            )
            errors += 1
        freeze = root / "qa" / "fidelity-freeze-24.json"
        if freeze.is_file():
            freeze_py = Path(__file__).resolve().parent / "fidelity_freeze.py"
            rc = subprocess.call(
                [sys.executable, str(freeze_py), "verify", str(root)]
            )
            if rc != 0:
                fail(
                    "3.x broke the 2.4 fidelity freeze (mutated index.html, "
                    "font-size, library classes, or section ids). "
                    "Revert those edits. Pitfall #196 #203."
                )
                errors += 1

    if errors:
        print(f"{errors} check(s) failed. C/3.1–3.3 not verified.", file=sys.stderr)
        return 2
    print(
        "OK polish-pass contract: C/3.1 impeccable + C/3.2 taste (board 3.1), "
        "C/3.3 emil + guidelines + find-animation + apple-design (board 3.2), "
        "semantics (board 3.3)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
