#!/usr/bin/env python3
"""Record a C/3 polish sub-pass on rebuild/ (2.20.1).

  python3 record-polish-pass.py . --id 3.1 --skill impeccable --phase start
  python3 record-polish-pass.py . --id 3.1 --phase end \\
      --status applied_with_waivers \\
      --applied applied.json --skipped skipped.json

Start writes a file-hash snapshot. End diffs rebuild/ (html/css/js only),
writes qa/polish-passes/c3-{id}-{skill}.json. Receipts record applied
improvements. A pass with no file changes must list skipped findings and
why they were not applied. Empty applied + empty skipped
is a failed run pretending to have run.

C/3 ids are sub-pass ids, not board steps: C/3.1 impeccable and C/3.2
design-taste land during board 3.1; C/3.3 emil lands during board 3.2.
The 3.2 companions (web-design-guidelines, find-animation-opportunities,
apple-design) take no C/3 receipt. Each writes qa/<skill>.md with
applied / skipped / n-a rows. Pitfall #215.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PASSES = {
    "3.1": "impeccable",
    "3.2": "design-taste-frontend",
    "3.3": "emil-design-eng",
}
# 3.2 companions write a markdown receipt, not a C/3 JSON receipt.
COMPANIONS = {
    "web-design-guidelines": "qa/web-design-guidelines.md",
    "find-animation-opportunities": "qa/find-animation-opportunities.md",
    "apple-design": "qa/apple-design.md",
}
STATUSES = {
    "applied",
    "applied_with_waivers",
    "no_op_fidelity",
    "pending",
}
SKIP_DIR_NAMES = {"images", "fonts", "node_modules"}
TEXT_SUFFIX = {".html", ".css", ".js", ".md", ".svg"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iter_text_files(rebuild: Path) -> list[Path]:
    out = []
    for p in sorted(rebuild.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in p.parts):
            continue
        if p.suffix.lower() not in TEXT_SUFFIX:
            continue
        out.append(p)
    return out


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(rebuild: Path) -> dict[str, str]:
    rel = {}
    for p in iter_text_files(rebuild):
        rel[p.relative_to(rebuild).as_posix()] = sha256_file(p)
    return rel


def tree_digest(snap: dict[str, str]) -> str:
    h = hashlib.sha256()
    for k in sorted(snap):
        h.update(k.encode())
        h.update(snap[k].encode())
    return h.hexdigest()[:16]


def load_list(arg: str | None) -> list:
    if not arg:
        return []
    path = Path(arg)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = json.loads(arg)
    if not isinstance(data, list):
        raise SystemExit("applied/skipped must be a JSON array")
    return data


def receipt_path(root: Path, pass_id: str, skill: str) -> Path:
    slug = skill.replace("_", "-")
    return root / "qa" / "polish-passes" / f"c3-{pass_id}-{slug}.json"


def snap_path(root: Path, pass_id: str) -> Path:
    return root / "qa" / "polish-passes" / f".snap-{pass_id}.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--id", required=True, choices=sorted(PASSES))
    ap.add_argument("--skill", help="Defaults from --id")
    ap.add_argument("--phase", required=True, choices=["start", "end"])
    ap.add_argument("--status", choices=sorted(STATUSES))
    ap.add_argument("--applied", help="JSON array or path")
    ap.add_argument("--skipped", help="JSON array or path")
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    rebuild = root / "rebuild"
    if not rebuild.is_dir():
        print(f"FAIL: missing {rebuild}", file=sys.stderr)
        return 2

    skill = args.skill or PASSES[args.id]
    expected = PASSES[args.id]
    companion = COMPANIONS.get(skill.replace("_", "-"))
    if companion:
        print(
            f"FAIL: {skill} is a 3.2 companion and takes no C/3 receipt. "
            f"Write {companion} (applied / skipped / n-a rows); "
            "verify-polish-passes.py and mark --step 3.2 read that file. "
            "Pitfall #215.",
            file=sys.stderr,
        )
        return 2
    if skill != expected:
        print(f"FAIL: pass {args.id} must use skill {expected}, got {skill}", file=sys.stderr)
        return 2

    passes_dir = root / "qa" / "polish-passes"
    passes_dir.mkdir(parents=True, exist_ok=True)

    if args.phase == "start":
        snap = snapshot(rebuild)
        payload = {
            "pass": args.id,
            "skill": skill,
            "started_at": utc_now(),
            "rebuild_hash_before": tree_digest(snap),
            "files": snap,
        }
        snap_path(root, args.id).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        print(f"started {args.id} {skill} hash={payload['rebuild_hash_before']}")
        return 0

    start_file = snap_path(root, args.id)
    if not start_file.is_file():
        print(f"FAIL: run --phase start first ({start_file})", file=sys.stderr)
        return 2
    start = json.loads(start_file.read_text(encoding="utf-8"))
    after = snapshot(rebuild)
    before_files = start.get("files") or {}
    changed = []
    for rel, digest in after.items():
        prev = before_files.get(rel)
        if prev != digest:
            changed.append(
                {
                    "path": f"rebuild/{rel}",
                    "before_sha": (prev or "")[:16],
                    "after_sha": digest[:16],
                    "kind": "modified" if prev else "added",
                }
            )
    for rel in before_files:
        if rel not in after:
            changed.append(
                {
                    "path": f"rebuild/{rel}",
                    "before_sha": before_files[rel][:16],
                    "after_sha": "",
                    "kind": "deleted",
                }
            )

    applied = load_list(args.applied)
    skipped = load_list(args.skipped)
    status = args.status
    if not status:
        if changed and applied:
            status = "applied_with_waivers" if skipped else "applied"
        elif not changed:
            status = "no_op_fidelity"
        else:
            status = "applied"

    if not applied and not skipped:
        print(
            "FAIL: pass claimed to end with no applied rows and no skipped rows. "
            "Record what changed, or list why nothing was applied.",
            file=sys.stderr,
        )
        return 2
    if changed and not applied:
        print(
            "FAIL: rebuild/ files changed but --applied is empty. List each improvement.",
            file=sys.stderr,
        )
        return 2
    if not changed and status == "applied":
        print(
            "FAIL: status=applied but rebuild/ html/css/js did not change.",
            file=sys.stderr,
        )
        return 2

    receipt = {
        "pass": args.id,
        "skill": skill,
        "status": status,
        "started_at": start.get("started_at"),
        "ended_at": utc_now(),
        "rebuild_hash_before": start.get("rebuild_hash_before"),
        "rebuild_hash_after": tree_digest(after),
        "files_changed": changed,
        "applied": applied,
        "skipped": skipped,
        "notes": args.notes,
    }
    out = receipt_path(root, args.id, skill)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    start_file.unlink(missing_ok=True)
    print(f"wrote {out} status={status} files_changed={len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
