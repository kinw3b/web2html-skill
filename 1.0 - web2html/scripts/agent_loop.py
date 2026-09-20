#!/usr/bin/env python3
"""Controller/reviewer evidence protocol for safe Web2Html reviewer waves.

Reviewers receive an immutable snapshot and may write only structured findings
under qa/agent-findings/. The controller remains the sole owner of Paper,
rebuild/, canonical QA receipts, and pipeline progress.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


FINDINGS_GENERATED_FROM = "web2html/agent-findings/v1"
SNAPSHOT_GENERATED_FROM = "web2html/agent-snapshot/v1"
AGENT_FINDINGS = Path("qa/agent-findings")
AGENT_RUNS = Path("qa/agent-runs")
LEASES = AGENT_RUNS / "leases"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _atomic_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".agent-", delete=False) as tmp:
        json.dump(data, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        temporary = Path(tmp.name)
    os.replace(temporary, path)
    return path


def _relative_file(root: Path, value: str | Path) -> Path:
    root = root.resolve()
    path = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        return path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"snapshot input must stay inside the project: {value}") from exc


def _expand_files(root: Path, inputs: list[str | Path]) -> list[Path]:
    files: list[Path] = []
    for value in inputs:
        rel = _relative_file(root, value)
        path = root.resolve() / rel
        if not path.exists():
            raise FileNotFoundError(f"snapshot input is missing: {rel}")
        if path.is_dir():
            files.extend(item.relative_to(root.resolve()) for item in sorted(path.rglob("*")) if item.is_file())
        else:
            files.append(rel)
    return sorted(set(files), key=lambda item: item.as_posix())


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_digest(phase: str, files: list[dict]) -> str:
    payload = json.dumps({"phase": phase, "files": files}, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def create_snapshot(root: Path, phase: str, inputs: list[str | Path]) -> dict:
    """Create an immutable, content-addressed view of the specified project inputs."""
    root = root.resolve()
    if not phase.strip():
        raise ValueError("snapshot phase is required")
    files = [
        {"path": rel.as_posix(), "sha256": _file_digest(root / rel), "bytes": (root / rel).stat().st_size}
        for rel in _expand_files(root, inputs)
    ]
    return {
        "generatedFrom": SNAPSHOT_GENERATED_FROM,
        "phase": phase,
        "createdAt": now_iso(),
        "files": files,
        "sha256": _snapshot_digest(phase, files),
    }


def snapshot_path(root: Path, run_id: str, phase: str) -> Path:
    return root.resolve() / AGENT_RUNS / run_id / phase / "snapshot.json"


def write_snapshot(root: Path, run_id: str, snapshot: dict) -> Path:
    phase = str(snapshot.get("phase") or "").strip()
    if not run_id.strip() or not phase:
        raise ValueError("run id and snapshot phase are required")
    return _atomic_json(snapshot_path(root, run_id, phase), snapshot)


def _current_sha(root: Path, snapshot: dict) -> str:
    inputs = [str(item.get("path") or "") for item in snapshot.get("files") or []]
    current = create_snapshot(root, str(snapshot.get("phase") or ""), inputs)
    return str(current["sha256"])


def validate_finding(root: Path, snapshot: dict, finding: dict) -> list[str]:
    """Validate reviewer evidence and reject anything created from stale inputs."""
    errors: list[str] = []
    phase = str(snapshot.get("phase") or "").strip()
    if snapshot.get("generatedFrom") != SNAPSHOT_GENERATED_FROM:
        errors.append("snapshot generatedFrom is invalid")
    if not phase:
        errors.append("snapshot phase is missing")
    if finding.get("generatedFrom") != FINDINGS_GENERATED_FROM:
        errors.append("finding generatedFrom is invalid")
    if finding.get("phase") != phase:
        errors.append("finding phase does not match snapshot")
    agent = str(finding.get("agent") or "").strip()
    if not agent or "/" in agent or "\\" in agent:
        errors.append("finding agent name is invalid")
    if finding.get("inputSha256") != snapshot.get("sha256"):
        errors.append("finding input SHA does not match snapshot")
    findings = finding.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")
    else:
        for index, row in enumerate(findings):
            if not isinstance(row, dict):
                errors.append(f"finding {index} is not an object")
                continue
            for field in ("key", "severity", "source", "evidence", "suggestion"):
                if not str(row.get(field) or "").strip():
                    errors.append(f"finding {index} missing {field}")
    if not errors:
        try:
            if _current_sha(root, snapshot) != snapshot.get("sha256"):
                errors.append("finding is stale: controller inputs changed after the snapshot")
        except (FileNotFoundError, ValueError) as exc:
            errors.append(f"finding cannot be checked against the current inputs: {exc}")
    return errors


def findings_path(root: Path, run_id: str, phase: str, agent: str) -> Path:
    return root.resolve() / AGENT_FINDINGS / run_id / phase / f"{agent}.json"


def submit_finding(root: Path, run_id: str, snapshot: dict, finding: dict) -> Path:
    """Persist a valid reviewer report outside canonical QA artifacts."""
    errors = validate_finding(root, snapshot, finding)
    if errors:
        raise ValueError("; ".join(errors))
    phase = str(finding["phase"])
    agent = str(finding["agent"])
    return _atomic_json(findings_path(root, run_id, phase, agent), finding)


def reviewer_lease_path(root: Path, agent: str) -> Path:
    return root.resolve() / LEASES / f"{agent}.json"


def active_reviewer_leases(root: Path) -> list[Path]:
    leases = root.resolve() / LEASES
    if not leases.is_dir():
        return []
    active: list[Path] = []
    for path in sorted(leases.glob("*.json")):
        if path.name == "controller.json":
            continue
        try:
            row = json.loads(path.read_text())
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(row, dict) and row.get("role") == "reviewer" and row.get("status") == "active":
            active.append(path)
    return active


def claim_reviewer(root: Path, agent: str, snapshot: dict) -> Path:
    if not str(snapshot.get("sha256") or "").strip():
        raise ValueError("reviewer lease requires a snapshot SHA")
    path = reviewer_lease_path(root, agent)
    if path.is_file():
        try:
            old = json.loads(path.read_text())
        except (OSError, ValueError, json.JSONDecodeError):
            old = {}
        if old.get("status") == "active" and old.get("inputSha256") != snapshot["sha256"]:
            raise ValueError(f"reviewer {agent!r} already has an active lease")
    return _atomic_json(
        path,
        {
            "role": "reviewer",
            "agent": agent,
            "phase": snapshot.get("phase"),
            "inputSha256": snapshot["sha256"],
            "status": "active",
            "claimedAt": now_iso(),
        },
    )


def release_reviewer(root: Path, agent: str, input_sha256: str) -> Path:
    path = reviewer_lease_path(root, agent)
    if not path.is_file():
        raise ValueError(f"reviewer {agent!r} has no active lease")
    row = json.loads(path.read_text())
    if row.get("role") != "reviewer" or row.get("status") != "active" or row.get("inputSha256") != input_sha256:
        raise ValueError(f"reviewer {agent!r} lease does not match the snapshot")
    row["status"] = "released"
    row["releasedAt"] = now_iso()
    return _atomic_json(path, row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot_cmd = commands.add_parser("snapshot")
    snapshot_cmd.add_argument("root", type=Path)
    snapshot_cmd.add_argument("--run-id", required=True)
    snapshot_cmd.add_argument("--phase", required=True)
    snapshot_cmd.add_argument("--input", action="append", required=True)
    claim_cmd = commands.add_parser("claim-reviewer")
    claim_cmd.add_argument("root", type=Path)
    claim_cmd.add_argument("--agent", required=True)
    claim_cmd.add_argument("--snapshot", type=Path, required=True)
    release_cmd = commands.add_parser("release-reviewer")
    release_cmd.add_argument("root", type=Path)
    release_cmd.add_argument("--agent", required=True)
    release_cmd.add_argument("--input-sha", required=True)
    submit_cmd = commands.add_parser("submit")
    submit_cmd.add_argument("root", type=Path)
    submit_cmd.add_argument("--run-id", required=True)
    submit_cmd.add_argument("--snapshot", type=Path, required=True)
    submit_cmd.add_argument("--finding", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            snapshot = create_snapshot(args.root, args.phase, args.input)
            dest = write_snapshot(args.root, args.run_id, snapshot)
            print(dest)
        elif args.command == "claim-reviewer":
            snapshot = json.loads(args.snapshot.read_text())
            print(claim_reviewer(args.root, args.agent, snapshot))
        elif args.command == "release-reviewer":
            print(release_reviewer(args.root, args.agent, args.input_sha))
        else:
            snapshot = json.loads(args.snapshot.read_text())
            finding = json.loads(args.finding.read_text())
            print(submit_finding(args.root, args.run_id, snapshot, finding))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
