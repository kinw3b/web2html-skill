#!/usr/bin/env python3
"""HARD GATE — Design Library is the prebuilt Tailwind foundations sheet.

A blocked node 1.4 script is not a license to write_html / create_artboard
a custom colour/type catalog. The only legal writer is
run-design-library-step.mjs → render-library.mjs --kind foundations
(templates/library/foundations). Pitfall #158.

  python3 library_14_foundations_gate.py /path/to/project

Exit 0 ok · 2 missing official receipt / hand-built substitute
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RECEIPT = Path("qa/design-library-step.json")
SEED = Path("qa/library-seed-qa.json")
LIB = Path("design-library/library.json")


def receipt_ok(rec: dict) -> bool:
    cmds = rec.get("commands") or []
    return (
        rec.get("status") == "done"
        and rec.get("writer") == "render-library.mjs"
        and rec.get("kind") == "foundations"
        and "extract-library.mjs" in cmds
        and "render-library.mjs" in cmds
    )


def gate_errors(root: Path) -> list[str]:
    errors: list[str] = []
    lib = root / LIB
    if not lib.is_file():
        errors.append("missing design-library/library.json")
    receipt = root / RECEIPT
    if not receipt.is_file():
        errors.append(
            "missing qa/design-library-step.json — run "
            "run-design-library-step.mjs. Do not write_html a Design Library. Pitfall #158"
        )
        return errors
    try:
        rec = json.loads(receipt.read_text(encoding="utf-8"))
    except Exception:
        errors.append("qa/design-library-step.json is not JSON")
        return errors
    if not receipt_ok(rec):
        errors.append(
            "qa/design-library-step.json is not an official foundations write "
            "(need writer=render-library.mjs, kind=foundations, extract+render). "
            "If node/1.4 scripts cannot run, STOP. Do not invent a frame. Pitfall #158"
        )
    seed = root / SEED
    if not seed.is_file():
        errors.append("missing qa/library-seed-qa.json")
    else:
        try:
            if json.loads(seed.read_text(encoding="utf-8")).get("ok") is not True:
                errors.append("qa/library-seed-qa.json is not ok")
        except Exception:
            errors.append("qa/library-seed-qa.json is not JSON")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    errors = gate_errors(args.root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print("1.4 foundations gate ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
