#!/usr/bin/env python3
"""Prepare and validate one read-only 768 + 390 reviewer wave for 2.2.d.

The controller still runs the responsive preflight, applies the sole CSS/HTML
batch, writes qa/responsive-22d.json, and invokes responsive_22d_gate.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import agent_loop


PHASE = "2.2.d"
REVIEWERS = ("tablet-768", "phone-390")


def _inputs(root: Path) -> list[str]:
    inputs = [
        "rebuild/index.html",
        "rebuild/css",
        "qa/responsive-pc-join.json",
        "capture/home-768",
        "capture/home-390",
    ]
    missing = [item for item in inputs if not (root / item).exists()]
    if missing:
        raise FileNotFoundError("2.2.d reviewer wave needs " + ", ".join(missing))
    return inputs


def prepare(root: Path, run_id: str) -> dict:
    root = root.resolve()
    snapshot = agent_loop.create_snapshot(root, PHASE, _inputs(root))
    agent_loop.write_snapshot(root, run_id, snapshot)
    for reviewer in REVIEWERS:
        agent_loop.claim_reviewer(root, reviewer, snapshot)
    return {"phase": PHASE, "reviewers": list(REVIEWERS), "snapshot": snapshot}


def ready_for_controller(root: Path, run_id: str, snapshot: dict) -> bool:
    root = root.resolve()
    for reviewer in REVIEWERS:
        report = agent_loop.findings_path(root, run_id, PHASE, reviewer)
        if not report.is_file() or agent_loop.reviewer_lease_path(root, reviewer) in agent_loop.active_reviewer_leases(root):
            return False
        try:
            finding = json.loads(report.read_text())
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        if agent_loop.validate_finding(root, snapshot, finding):
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_cmd = sub.add_parser("prepare")
    prepare_cmd.add_argument("root", type=Path)
    prepare_cmd.add_argument("--run-id", required=True)
    ready_cmd = sub.add_parser("ready")
    ready_cmd.add_argument("root", type=Path)
    ready_cmd.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            wave = prepare(args.root, args.run_id)
            print(json.dumps({"phase": wave["phase"], "reviewers": wave["reviewers"], "inputSha256": wave["snapshot"]["sha256"]}))
            return 0
        snapshot = json.loads(agent_loop.snapshot_path(args.root, args.run_id, PHASE).read_text())
        if ready_for_controller(args.root, args.run_id, snapshot):
            print("OK 2.2.d 768/390 reviewer wave is current; controller may apply one serial batch.")
            return 0
        print("FAIL: 2.2.d reviewers are missing, active, invalid, or stale.")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
