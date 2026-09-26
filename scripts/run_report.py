#!/usr/bin/env python3
"""Run report — one portable Markdown file per run: <project>/run-report.md.

A self-improving log of the run for the human to drop into any database or
template pipeline afterwards. It records, with no tool names and no gates:

  - every session with its agent + model
  - per-step and per-phase durations (the sum-of-steps clock from the board)
  - each human checkpoint: status, duration, who ran it, auto-accepted or not
  - the Paper review comments captured around the 1.4 sign-off and whether
    each one was still open the last time the canvas was checked
  - free-form notes / additional requests logged at any step

The report regenerates automatically when a human checkpoint is marked done;
it is never a gate and a failed regeneration never fails the mark.

  python3 run_report.py build <project>                       # (re)write run-report.md
  python3 run_report.py note  <project> --step 2.4 --text "Hero CTA should be pill" [--author human]

Notes live in qa/run-report-notes.json (chronological). The report itself
survives the end-of-run tidy at the project root next to the finished board.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

REPORT_NAME = "run-report.md"
NOTES_RELPATH = Path("qa") / "run-report-notes.json"
COMMENTS_RELPATH = Path("qa") / "paper-comments.json"


def _pp():
    """Load pipeline-progress.py (dashed filename) and reuse its board helpers."""
    spec = importlib.util.spec_from_file_location("pipeline_progress", _SCRIPTS / "pipeline-progress.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def report_path(root: Path) -> Path:
    return root.resolve() / REPORT_NAME


def notes_path(root: Path) -> Path:
    return root.resolve() / NOTES_RELPATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_notes(root: Path) -> list[dict]:
    path = notes_path(root)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []


def add_note(root: Path, step: str, text: str, author: str = "agent") -> dict:
    entry = {"ts": _now_iso(), "step": step, "author": author or "agent", "text": text.strip()}
    notes = load_notes(root)
    notes.append(entry)
    path = notes_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")
    return entry


def _thread_id(thread: dict) -> str:
    return str(thread.get("commentThreadId") or thread.get("id") or "")


def _thread_text(thread: dict) -> str:
    preview = thread.get("firstMessagePreview")
    if isinstance(preview, dict) and str(preview.get("text") or "").strip():
        return str(preview["text"]).strip()
    messages = thread.get("messages") or thread.get("replies")
    if isinstance(messages, list):
        for message in messages:
            if isinstance(message, dict):
                text = str(message.get("text") or message.get("content") or "").strip()
                if text:
                    return text
    for key in ("text", "preview", "body"):
        if str(thread.get(key) or "").strip():
            return str(thread[key]).strip()
    return "(no text captured)"


def collect_paper_comments(root: Path) -> list[dict]:
    """Threads captured around the 1.4 sign-off, newest snapshot status per thread.

    Reads the append-only qa/paper-comments-log.jsonl — every open-thread
    snapshot the build phase took while remediating the canvas. Merged by
    thread id: the text from the first sighting, the status from the last. A
    thread missing from the newest snapshot was resolved. Falls back to the
    latest qa/paper-comments.json when no log exists.
    """
    root = root.resolve()
    log_path = root / "qa" / "paper-comments-log.jsonl"
    snapshots: list[dict] = []
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                snap = json.loads(line)
            except ValueError:
                continue
            if isinstance(snap, dict) and isinstance(snap.get("threads"), list):
                snapshots.append(snap)
    if not snapshots:
        path = root / COMMENTS_RELPATH
        if not path.is_file():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        threads = data.get("threads") if isinstance(data, dict) else None
        if not isinstance(threads, list):
            return []
        snapshots = [{"generatedAt": data.get("generatedAt"), "threads": threads}]

    merged: dict[str, dict] = {}
    order: list[str] = []
    for index, snap in enumerate(snapshots):
        seen_now: set[str] = set()
        for thread in snap["threads"]:
            if not isinstance(thread, dict):
                continue
            tid = _thread_id(thread) or f"anon-{index}-{len(seen_now)}"
            seen_now.add(tid)
            if tid not in merged:
                merged[tid] = {
                    "id": tid,
                    "text": _thread_text(thread),
                    "status": str(thread.get("status") or "open"),
                    "capturedAt": str(snap.get("generatedAt") or ""),
                }
                order.append(tid)
            else:
                merged[tid]["status"] = str(thread.get("status") or merged[tid]["status"])
        if index > 0:
            # Open earlier, absent from a later snapshot → resolved on the canvas.
            for tid in order:
                if tid not in seen_now and merged[tid]["status"] == "open":
                    merged[tid]["status"] = "resolved"
    return [merged[tid] for tid in order]


def _checkpoint_rows(pp, data: dict, root: Path) -> list[dict]:
    steps = data.get("steps") or {}
    rows = []
    for sid in sorted(pp.HUMAN_CHECKPOINTS, key=lambda s: [int(p) for p in s.split(".")]):
        if sid not in pp.counted_step_ids(root, data):
            continue
        row = steps.get(sid) or {}
        rows.append(
            {
                "step": sid,
                "title": pp.TITLES.get(sid, ""),
                "status": row.get("status", "pending"),
                "durationSeconds": row.get("durationSeconds"),
                "agent": row.get("agent"),
                "model": row.get("model"),
                "reason": str(row.get("reason") or ""),
            }
        )
    return rows


def build(root: Path) -> Path:
    """(Re)write <project>/run-report.md from the board + checkpoint artifacts."""
    pp = _pp()
    import run_config

    root = root.resolve()
    if not pp.progress_path(root).is_file():
        raise FileNotFoundError("no run here (missing qa/pipeline-progress.json)")
    data = pp.load_progress(root)
    timing = pp.refresh_timing(data)
    config = run_config.load(root)
    paper = pp.read_paper_file(root)
    url = pp.paper_source_url(paper)
    rows = pp.timing_rows(data, root)
    notes = load_notes(root)
    comments = collect_paper_comments(root)
    checkpoints = _checkpoint_rows(pp, data, root)
    sessions = [s for s in (data.get("sessions") or []) if isinstance(s, dict)]

    done = sum(1 for r in rows if r["status"] in {"done", "skipped"})
    total = len(rows)
    current = data.get("current") or timing.get("activeStep")
    progress = f"{done}/{total} steps" + (f" · current {current}" if current else " · complete")

    src = config.get("source") or {}
    source_line = url or (str(src.get("path") or "") if src.get("kind") not in (None, "none") else "")

    md: list[str] = []
    md.append(f"# Run report — {data.get('project') or root.name}")
    md.append("")
    md.append(f"- Source: {source_line or '—'}")
    md.append(
        f"- Mode: {config.get('speed', 'full')} run · checkpoints: {config.get('checkpoints', 'human')}"
    )
    md.append(f"- Run started: {pp.fmt_clock(data.get('started'))}")
    md.append(f"- Report generated: {pp.fmt_clock(_now_iso())}")
    md.append(f"- Progress: {progress}")
    md.append(
        f"- Run total: {pp.fmt_duration(timing['totalSeconds'])}"
        + (
            f" (agent {pp.fmt_duration(timing['agentSeconds'])} · human checkpoints {pp.fmt_duration(timing['humanSeconds'])})"
            if timing["humanSeconds"]
            else ""
        )
    )
    md.append("")

    if sessions:
        md.append("## Sessions")
        md.append("")
        md.append("| Session | Kind | At step | Agent | Model | Started |")
        md.append("|---|---|---|---|---|---|")
        for i, entry in enumerate(sessions, 1):
            md.append(
                f"| {i} | {entry.get('kind', '?')} | {entry.get('at') or '—'} "
                f"| {entry.get('agent') or '—'} | {entry.get('model') or '—'} "
                f"| {pp.fmt_clock(entry.get('startedAt'))} |"
            )
        md.append("")

    md.append("## Phases")
    md.append("")
    md.append("| Phase | Took | Agent · Model |")
    md.append("|---|---|---|")
    for phase in sorted(timing["phases"]):
        took = pp.fmt_duration(timing["phases"][phase])
        named = [
            entry
            for entry in (timing["phaseAgents"].get(phase) or [])
            if entry.get("agent") or entry.get("model")
        ]
        if not named:
            who = "—"
        elif len(named) == 1:
            who = pp.agent_label(named[0].get("agent"), named[0].get("model"))
        else:
            who = " + ".join(
                f"{pp.agent_label(entry.get('agent'), entry.get('model')) or 'unknown'} "
                f"({pp.fmt_duration(entry['seconds'])})"
                for entry in named
            )
        md.append(f"| {phase} | {took} | {who} |")
    md.append("")

    md.append("## Steps")
    md.append("")
    md.append("| Step | Title | Status | Started | Finished | Took | Agent | Model |")
    md.append("|---|---|---|---|---|---|---|---|")
    for row in rows:
        took = pp.fmt_duration(row["durationSeconds"]) if row["durationSeconds"] is not None else "—"
        if row["durationSeconds"] is None and row["status"] == "active" and row["started"]:
            started_dt = pp.parse_iso(row["started"])
            if started_dt:
                took = f"{pp.fmt_duration((datetime.now(timezone.utc) - started_dt).total_seconds())}…"
        title = row["title"] + (" †" if row["human"] else "")
        md.append(
            f"| {row['step']} | {title} | {row['status']} | {pp.fmt_clock(row['started'])} "
            f"| {pp.fmt_clock(row['ended'])} | {took} | {row.get('agent') or '—'} | {row.get('model') or '—'} |"
        )
    md.append("")
    md.append("† human checkpoint.")
    md.append("")

    md.append("## Human checkpoints")
    md.append("")
    for cp in checkpoints:
        took = pp.fmt_duration(cp["durationSeconds"]) if cp["durationSeconds"] is not None else "—"
        who = pp.agent_label(cp["agent"], cp["model"]) or "—"
        auto = " · auto-accepted" if "auto" in cp["reason"].lower() else ""
        md.append(f"### {cp['step']} — {cp['title']}")
        md.append("")
        md.append(f"Status: {cp['status']} · took {took} · {who}{auto}")
        if cp["step"] == "1.4":
            md.append("")
            if comments:
                md.append(f"Paper review comments captured: {len(comments)}")
                md.append("")
                for thread in comments:
                    md.append(f"- [{thread['status']}] “{thread['text']}”")
            else:
                md.append("Paper review comments captured: none on record.")
        step_notes = [n for n in notes if str(n.get("step")) == cp["step"]]
        if step_notes:
            md.append("")
            md.append("Notes:")
            md.append("")
            for note in step_notes:
                md.append(f"- {pp.fmt_clock(note.get('ts'))} · {note.get('author', 'agent')}: {note.get('text', '')}")
        md.append("")

    md.append("## Notes & additional requests")
    md.append("")
    if notes:
        for note in notes:
            md.append(
                f"- {pp.fmt_clock(note.get('ts'))} · step {note.get('step') or '—'} · "
                f"{note.get('author', 'agent')}: {note.get('text', '')}"
            )
    else:
        md.append("_No notes recorded._")
    md.append("")

    dest = report_path(root)
    dest.write_text("\n".join(md), encoding="utf-8")
    return dest


def cmd_build(root: Path) -> int:
    try:
        dest = build(root)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"run report → {dest}")
    return 0


def cmd_note(root: Path, step: str, text: str, author: str) -> int:
    if not text.strip():
        print("FAIL: --text is required and cannot be empty.", file=sys.stderr)
        return 2
    entry = add_note(root, step, text, author)
    print(f"note recorded · step {entry['step']} · {entry['author']}")
    try:
        dest = build(root)
        print(f"run report → {dest}")
    except FileNotFoundError:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="(Re)write run-report.md from the board + checkpoint records")
    b.add_argument("root")
    n = sub.add_parser("note", help="Log a note / additional request against a step, then rebuild the report")
    n.add_argument("root")
    n.add_argument("--step", required=True, help="Step id the note belongs to, e.g. 2.4")
    n.add_argument("--text", required=True, help="The note")
    n.add_argument("--author", default="agent", help="human (default: agent)")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if args.cmd == "build":
        return cmd_build(root)
    return cmd_note(root, args.step, args.text, args.author)


if __name__ == "__main__":
    raise SystemExit(main())
