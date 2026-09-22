#!/usr/bin/env python3
"""Parallel waves for the read-heavy steps — one contract, three adapters.

A wave fans the parallel-safe unit of a step out to workers and keeps every
write serial with the controller. Workers are read-only reviewers in the
agent_loop.py lane: SHA snapshot, a reviewer lease per task, one finding
file per task under qa/agent-findings/. The controller applies patches and
records receipts. 2.3 VALIDATE LOOK MUST run this after --shoot-open
(Pitfall #221); section_22_gate.py fails without an applied 2.3 wave.json.

  2.3  one task per open band: Read the three side PNGs → verdict + patch proposal
       (controller --shoots first, applies + --records after)
  3.2  one task per companion skill: guidelines / animation / apple-design receipt
  5.2  one task per interior page: author <main> of astro/src/pages/{slug}.astro

Adapters (harness_probe.py picks; absence lowers the rung, never blocks):
  orca      supervised Orca workers, SAME agent as this orchestrator (Pitfall #220)
  subagent  the harness's own subagent tool; this script prints the specs
  serial    the controller does each task itself; same finding files

  python3 wave.py prepare <root> --phase 2.3 --run-id r1 [--max-workers 4]
  python3 wave.py start   <root> --phase 2.3 --run-id r1 [--adapter auto]
  python3 wave.py wait    <root> --phase 2.3 --run-id r1 [--timeout-ms 900000] [--ack <delivery>]
  python3 wave.py check   <root> --phase 2.3 --run-id r1 --agent band-hero      # a worker's self-check
  python3 wave.py ready   <root> --phase 2.3 --run-id r1
  python3 wave.py apply   <root> --phase 2.3 --run-id r1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import agent_loop

GENERATED_FROM = "web2html/wave/v1"
PHASES = ("2.3", "3.2", "5.2")
DEFAULT_WORKERS = {"2.3": 4, "3.2": 3, "5.2": 2}
COMPANIONS = (
    ("web-design-guidelines", "qa/web-design-guidelines.md"),
    ("find-animation-opportunities", "qa/find-animation-opportunities.md"),
    ("apple-design", "qa/apple-design.md"),
)
WAIT_TYPES = "worker_done,escalation,question"
CLI_TIMEOUT_S = 60

Runner = Callable[[list[str], int], tuple[int, str]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _run(argv: list[str], timeout_s: int = CLI_TIMEOUT_S) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout


def _json(text: str) -> dict:
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _dig(obj: object, *names: str) -> object:
    """First value under any of `names`, searching nested dicts/lists breadth-first."""
    queue: list[object] = [obj]
    while queue:
        cur = queue.pop(0)
        if isinstance(cur, dict):
            for name in names:
                if name in cur and cur[name] not in (None, ""):
                    return cur[name]
            queue.extend(cur.values())
        elif isinstance(cur, list):
            queue.extend(cur)
    return None


def _id_of(obj: object, kind: str) -> object:
    """`<kind>_id` / `<kind>Id` when flat, else `<kind>.id` when nested — receipt shapes vary by host."""
    flat = _dig(obj, f"{kind}_id", f"{kind}Id")
    if flat:
        return flat
    nested = _dig(obj, kind)
    if isinstance(nested, dict):
        return nested.get("id") or None
    return None


def _safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "task"


def skills_dir() -> str:
    return os.environ.get("SKILLS") or str(Path(__file__).resolve().parents[2])


def wave_dir(root: Path, run_id: str, phase: str) -> Path:
    return root.resolve() / agent_loop.AGENT_RUNS / run_id / phase


def wave_path(root: Path, run_id: str, phase: str) -> Path:
    return wave_dir(root, run_id, phase) / "wave.json"


def load_wave(root: Path, run_id: str, phase: str) -> dict:
    path = wave_path(root, run_id, phase)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FileNotFoundError(f"no wave at {path} — run `wave.py prepare` first") from exc
    return data


def save_wave(root: Path, wave: dict) -> Path:
    wave["updatedAt"] = _now_iso()
    return agent_loop._atomic_json(wave_path(root, wave["runId"], wave["phase"]), wave)


# ------------------------------------------------------------------ plan ----

def _existing(root: Path, *rels: str) -> list[str]:
    return [rel for rel in rels if (root / rel).exists()]


def inputs_for(root: Path, phase: str) -> list[str]:
    root = root.resolve()
    if phase == "2.3":
        inputs = _existing(
            root, "rebuild/index.html", "rebuild/css", "rebuild/index-raw.html", "qa/paper-measure/compare"
        )
        if "rebuild/index.html" not in inputs:
            raise FileNotFoundError("2.3 wave needs rebuild/index.html (seed_index.py) and shot side-by-sides")
        return inputs
    if phase == "3.2":
        inputs = _existing(root, "rebuild/index-polish.html", "rebuild/css", "rebuild/js")
        if "rebuild/index-polish.html" not in inputs:
            raise FileNotFoundError("3.2 wave needs rebuild/index-polish.html (mark 3.1 active seeds it)")
        return inputs
    if phase == "5.2":
        inputs = _existing(root, "qa/phase-4-pages.json", "astro/src/layouts", "astro/src/components")
        if "qa/phase-4-pages.json" not in inputs:
            raise FileNotFoundError("5.2 wave needs qa/phase-4-pages.json from 4.2")
        return inputs
    raise ValueError(f"unknown wave phase {phase!r}; use {PHASES}")


def _open_bands(root: Path) -> list[dict]:
    import paper_23_validate as validate  # heavy import, only for 2.3

    return [row for row in validate.status_rows(root) if row.get("state") not in {"match", "residual"}]


def _pages(root: Path) -> list[str]:
    data = json.loads((root / "qa" / "phase-4-pages.json").read_text(encoding="utf-8"))
    rows = data.get("pages") if isinstance(data, dict) else data
    slugs: list[str] = []
    for row in rows or []:
        slug = str((row or {}).get("slug") or "").strip() if isinstance(row, dict) else str(row).strip()
        if slug and slug not in {"home", "index"}:
            slugs.append(slug)
    return slugs


def plan_tasks(root: Path, phase: str) -> list[dict]:
    root = root.resolve()
    if phase == "2.3":
        return [
            {"id": f"band-{_safe(str(row['id']))}", "kind": "validate-band", "band": str(row["id"]),
             "rounds": int(row.get("rounds") or 0)}
            for row in _open_bands(root)
        ]
    if phase == "3.2":
        return [{"id": skill, "kind": "companion-receipt", "skill": skill, "receipt": receipt} for skill, receipt in COMPANIONS]
    if phase == "5.2":
        return [{"id": f"page-{_safe(slug)}", "kind": "astro-body", "slug": slug,
                 "writes": [f"astro/src/pages/{slug}.astro"]} for slug in _pages(root)]
    raise ValueError(f"unknown wave phase {phase!r}")


def _run_widths(root: Path) -> tuple[int, ...]:
    """Configured widths (qa/run-config.json); fast run = 1600 + 390."""
    try:
        import run_config

        return tuple(run_config.widths(root))
    except Exception:  # noqa: BLE001
        return (1600, 768, 390)


def _side_pngs(root: Path, band: str) -> list[str]:
    compare = root / "qa" / "paper-measure" / "compare"
    found: list[str] = []
    for width in _run_widths(root):
        hits = sorted(compare.glob(f"*-{band}-{width}-side.png")) if compare.is_dir() else []
        found.append(str(hits[0].relative_to(root)) if hits else f"qa/paper-measure/compare/NN-{band}-{width}-side.png")
    return found


def spec_text(root: Path, phase: str, task: dict, sha: str, run_id: str) -> str:
    """Self-contained Task spec: target, change, constraints, ownership, acceptance."""
    root = root.resolve()
    skills = skills_dir()
    finding = task["findings"]
    agent = task["id"]
    check = (
        f'python3 "{skills}/web2html/scripts/wave.py" check "{root}" --phase {phase} --run-id {run_id} --agent {agent}'
    )
    done = (
        f"DONE  Under Orca: send worker_done with --report-path {finding} and --outcome succeeded "
        f"(failed if the target could not be read). Elsewhere: stop after the finding is written."
    )
    if phase == "2.3":
        band = task["band"]
        sides = _side_pngs(root, band)
        return f"""web2html 2.3 VALIDATE — band #{band}  (wave {run_id}, snapshot {sha[:12]})
Project  {root}

TARGET  Read all three side-by-sides for THIS band only (1.2 clip left, rebuild right):
  {sides[0]}
  {sides[1]}
  {sides[2]}
  Cross-check against rebuild/index-raw.html (Paper dump of this band) and the
  1.2 clips capture/home-{{desktop,768,390}}/source-sections/NN-*.png.

CHANGE  Write ONE file and nothing else: {finding}
  {{"generatedFrom":"web2html/agent-findings/v1","phase":"2.3","agent":"{agent}",
   "inputSha256":"{sha}","band":"{band}",
   "verdict":{{"1600":"match|miss","768":"match|miss","390":"match|miss"}},
   "seen":"at least 12 words: what each width showed, concretely",
   "misses":[{{"width":768,"what":"cards stack 1-col, Paper paints 2-col","fix":"#{band} .grid: repeat(2, 1fr) at 768"}}],
   "patch":"the exact CSS/HTML change scoped to #{band}, or empty when every width matches",
   "findings":[{{"key":"768","severity":"medium","source":"{sides[1]}","evidence":"what you saw","suggestion":"the fix"}}]}}
  `findings` may be an empty list when all three widths match.

CONSTRAINTS  Read-only. Do not edit rebuild/, qa/paper-measure/*.validate.json, or any
  other file. No Paper MCP. No pixel-perfect refine loop. Compare against the 1.2
  clip + index-raw, never 1.1 screenshots. Do not invent a 1320/1024 breakpoint
  (Pitfall #195 #202 #216).

OWNERSHIP  You own only {finding}. The controller applies the patch and records the round.

ACCEPTANCE  {check}   → exit 0
{done}
"""
    if phase == "3.2":
        skill = task["skill"]
        report_md = task["report"]
        return f"""web2html 3.2 companion — {skill}  (wave {run_id}, snapshot {sha[:12]})
Project  {root}

TARGET  rebuild/index-polish.html (the 3.x polish copy — never the 2.4 lock rebuild/index.html).
  Load the `{skill}` skill and run its audit on that file, read-only.

CHANGE  Write TWO files and nothing else:
  {report_md}   the receipt the skill prescribes for qa/{skill}.md — `applied` / `skipped` / `n-a`
                rows; a fidelity lock (Pitfall #81 #152 #196 #203) makes a skipped row, never a missing row.
  {finding}     {{"generatedFrom":"web2html/agent-findings/v1","phase":"3.2","agent":"{agent}",
                 "inputSha256":"{sha}","report":"{report_md}",
                 "findings":[{{"key":"<row>","severity":"low","source":"rebuild/index-polish.html","evidence":"…","suggestion":"…"}}]}}

CONSTRAINTS  Read-only on the ship. Do not write qa/{skill}.md yourself — the controller promotes
  your report there after validation (Pitfall #215). Do not change layout, type size, library
  class names, section order, or the colour system; propose, never restyle.

OWNERSHIP  You own only the two files above.

ACCEPTANCE  {check}   → exit 0
{done}
"""
    slug = task["slug"]
    return f"""web2html 5.2 interior body — {slug}  (wave {run_id}, snapshot {sha[:12]})
Project  {root}

TARGET  Author astro/src/pages/{slug}.astro on the 5.1 shared chrome, from rebuild/{slug}-raw.html
  (serial get_jsx dump written by the controller) and the Paper page {slug}-desktop.

CHANGE  Write ONE page file: astro/src/pages/{slug}.astro — import BaseLayout, Header, Footer;
  render <Header /> and <Footer /> around exactly one <main>; author only that <main>.
  Then write {finding}:
  {{"generatedFrom":"web2html/agent-findings/v1","phase":"5.2","agent":"{agent}","inputSha256":"{sha}",
   "slug":"{slug}","files":["astro/src/pages/{slug}.astro"],"findings":[]}}

CONSTRAINTS  No inline <header>/<footer>, no get_jsx dump metadata, no source or external hrefs
  (they stay `#` until 5.5), no new tokens or component classes — request them in `findings`.
  Do not touch astro/src/layouts, astro/src/components, or any other page (references/phase-5-astro.md).

OWNERSHIP  You own astro/src/pages/{slug}.astro and {finding}. The controller owns chrome and CSS.

ACCEPTANCE  python3 "{skills}/web2html/scripts/record-phase-5-pages.py" "{root}" reports no error for {slug},
  and {check} → exit 0
{done}
"""


def prepare(root: Path, run_id: str, phase: str, max_workers: int | None = None) -> dict:
    root = root.resolve()
    if phase not in PHASES:
        raise ValueError(f"unknown wave phase {phase!r}; use {PHASES}")
    inputs = inputs_for(root, phase)
    tasks = plan_tasks(root, phase)
    snapshot = agent_loop.create_snapshot(root, phase, inputs)
    agent_loop.write_snapshot(root, run_id, snapshot)
    sha = str(snapshot["sha256"])
    for task in tasks:
        task["findings"] = agent_loop.findings_path(root, run_id, phase, task["id"]).relative_to(root).as_posix()
        if phase == "3.2":
            task["report"] = task["findings"][:-5] + ".md"
        task["status"] = "planned"
        agent_loop.claim_reviewer(root, task["id"], snapshot)
        task["spec"] = spec_text(root, phase, task, sha, run_id)
    wave = {
        "generatedFrom": GENERATED_FROM,
        "runId": run_id,
        "phase": phase,
        "project": str(root),
        "inputSha256": sha,
        "inputs": inputs,
        "maxWorkers": int(max_workers or DEFAULT_WORKERS[phase]),
        "adapter": None,
        "orca": {},
        "tasks": tasks,
        "createdAt": _now_iso(),
    }
    save_wave(root, wave)
    return wave


# ----------------------------------------------------------------- start ----

def _probe(root: Path) -> dict:
    import harness_probe

    report = harness_probe.load_report(root)
    if not report:
        report = harness_probe.probe(root=root)
        harness_probe.write_report(root, report)
    return report


def _resolve_adapter(requested: str, probe: dict) -> tuple[str, str]:
    available = str((probe.get("adapters") or {}).get("waves") or "serial")
    if requested in {"auto", available}:
        return available, "probe"
    order = ["orca", "subagent", "serial"]
    if requested in order and order.index(requested) > order.index(available):
        return requested, "operator chose a lower rung"
    return available, f"{requested} unavailable → {available}"


def start(root: Path, run_id: str, phase: str, adapter: str = "auto", run: Runner = _run, env: dict | None = None) -> dict:
    root = root.resolve()
    env = dict(os.environ if env is None else env)
    wave = load_wave(root, run_id, phase)
    probe = _probe(root)
    chosen, why = _resolve_adapter(adapter, probe)
    wave["adapter"] = chosen
    wave["adapterReason"] = why
    if chosen != "orca":
        for task in wave["tasks"]:
            if task.get("status") == "planned":
                task["status"] = "dispatch"
        save_wave(root, wave)
        return wave
    cli = str((probe.get("orca") or {}).get("cli") or "orca")
    agent = str(probe.get("agent") or "")
    worktree = str((probe.get("orca") or {}).get("worktree") or "")
    if not agent or not worktree:
        wave["adapter"] = "subagent" if probe.get("harness") == "claude-code" else "serial"
        wave["adapterReason"] = "orca agent or worktree unknown (Pitfall #220)"
        save_wave(root, wave)
        return wave
    orca = wave.setdefault("orca", {})
    orca.update({"cli": cli, "agent": agent, "worktree": worktree})
    if not orca.get("runId"):
        code, text = run([cli, "orchestration", "run-create", "--objective",
                          f"web2html {root.name} {phase} wave {run_id}", "--json"], CLI_TIMEOUT_S)
        run_row = _json(text)
        orca["runId"] = str(_id_of(run_row.get("result") or run_row, "run") or _dig(run_row.get("result") or run_row, "id") or "") if code == 0 else ""
        orca["runCreate"] = {"exit": code, "raw": run_row}
        if code != 0 or not orca["runId"]:
            wave["adapter"] = "subagent" if probe.get("harness") == "claude-code" else "serial"
            wave["adapterReason"] = f"run-create exit {code} → lower rung (never relaunch)"
            for task in wave["tasks"]:
                if task.get("status") == "planned":
                    task["status"] = "dispatch"
            save_wave(root, wave)
            return wave
    launched = sum(1 for t in wave["tasks"] if t.get("status") in {"running"})
    for task in wave["tasks"]:
        if task.get("status") != "planned" or launched >= int(wave.get("maxWorkers") or 1):
            continue
        argv = [cli, "orchestration", "worker-start", "--spec", task["spec"], "--worktree", f"id:{worktree}",
                "--agent", agent, "--task-title", f"web2html {phase} {task['id']}", "--json"]
        if env.get("WEB2HTML_WAVE_MODEL"):
            argv += ["--model", env["WEB2HTML_WAVE_MODEL"]]
        code, text = run(argv, CLI_TIMEOUT_S * 3)
        receipt = _json(text)
        task["orca"] = {
            "exit": code,
            "taskId": _id_of(receipt.get("result") or receipt, "task"),
            "dispatchId": _id_of(receipt.get("result") or receipt, "dispatch"),
            "handle": _dig(receipt.get("result") or receipt, "handle", "terminalHandle", "terminal_handle"),
            "failedStage": _dig(receipt, "failedStage", "failed_stage") if code != 0 else None,
        }
        if code == 0 and task["orca"]["dispatchId"]:
            task["status"] = "running"
            launched += 1
        else:
            # Orca rule: never relaunch a failed worker-start. Read failedStage, drop the rung.
            task["status"] = "dispatch"
            wave["adapterReason"] = f"worker-start exit {code} on {task['id']} → remaining tasks {wave['adapter']}→serial"
            for other in wave["tasks"]:
                if other.get("status") == "planned":
                    other["status"] = "dispatch"
            break
    save_wave(root, wave)
    return wave


# ------------------------------------------------------------------ wait ----

def _task_by_dispatch(wave: dict, dispatch_id: object) -> dict | None:
    for task in wave["tasks"]:
        if str((task.get("orca") or {}).get("dispatchId") or "") == str(dispatch_id or "") and dispatch_id:
            return task
    return None


def _payload(message: dict) -> dict:
    payload = message.get("payload")
    if isinstance(payload, str):
        payload = _json(payload)
    return payload if isinstance(payload, dict) else {}


def validate_task(root: Path, wave: dict, task: dict) -> list[str]:
    snapshot = json.loads(agent_loop.snapshot_path(root, wave["runId"], wave["phase"]).read_text(encoding="utf-8"))
    path = root / task["findings"]
    try:
        finding = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{task['id']}: finding unreadable ({exc})"]
    errors = agent_loop.validate_finding(root, snapshot, finding)
    if wave["phase"] == "2.3":
        verdict = finding.get("verdict") or {}
        keys = tuple(str(w) for w in _run_widths(root))
        if not all(str(verdict.get(k)) in {"match", "miss"} for k in keys):
            errors.append("verdict must name match|miss at " + ", ".join(keys))
        if len(str(finding.get("seen") or "").split()) < 12:
            errors.append("seen must be at least 12 words")
    if wave["phase"] == "3.2":
        report = root / str(finding.get("report") or task.get("report") or "")
        if not report.is_file() or not report.read_text(encoding="utf-8", errors="replace").strip():
            errors.append("report markdown is missing or empty")
    return [f"{task['id']}: {e}" for e in errors]


def settle(root: Path, wave: dict, task: dict, run: Runner = _run) -> None:
    """After an accepted worker_done: release the Orca terminal and the reviewer lease."""
    orca = task.get("orca") or {}
    if wave.get("adapter") == "orca" and orca.get("dispatchId"):
        cli = str((wave.get("orca") or {}).get("cli") or "orca")
        code, text = run([cli, "orchestration", "worker-release", "--dispatch", str(orca["dispatchId"]), "--json"], CLI_TIMEOUT_S)
        orca["release"] = {"exit": code, "raw": _json(text)}
    try:
        agent_loop.release_reviewer(root, task["id"], wave["inputSha256"])
    except ValueError:
        pass


def wait(root: Path, run_id: str, phase: str, timeout_ms: int = 900_000, ack: str | None = None,
         run: Runner = _run) -> tuple[dict, int]:
    root = root.resolve()
    wave = load_wave(root, run_id, phase)
    if wave.get("adapter") != "orca":
        return {"adapter": wave.get("adapter"), "note": "wait is for the orca adapter; use `ready`"}, 0
    cli = str(wave["orca"].get("cli") or "orca")
    argv = [cli, "orchestration", "check", "--wait", "--types", WAIT_TYPES, "--timeout-ms", str(timeout_ms), "--json"]
    if ack:
        argv[3:3] = ["--ack", ack]
    code, text = run(argv, max(CLI_TIMEOUT_S, timeout_ms // 1000 + 30))
    body = _json(text)
    result = body.get("result") if isinstance(body.get("result"), dict) else body
    messages = _dig(result, "messages") or []
    delivery = _dig(result, "delivery_id", "deliveryId")
    if isinstance(_dig(result, "delivery"), dict) and not delivery:
        delivery = (_dig(result, "delivery") or {}).get("id")
    summary = {"exit": code, "delivery": delivery, "settled": [], "invalid": [], "needsReply": [], "launched": [], "empty": False}
    if not isinstance(messages, list) or not messages:
        summary["empty"] = True
        save_wave(root, wave)
        return summary, 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        mtype = str(message.get("type") or "")
        payload = _payload(message)
        dispatch_id = payload.get("dispatch_id") or payload.get("dispatchId") or message.get("dispatch_id")
        task = _task_by_dispatch(wave, dispatch_id)
        if mtype == "worker_done" and task is not None:
            outcome = str(payload.get("outcome") or message.get("outcome") or "")
            errors = validate_task(root, wave, task) if outcome != "failed" else [f"{task['id']}: worker reported failed"]
            task["status"] = "done" if not errors else "invalid"
            task["errors"] = errors
            settle(root, wave, task, run)
            (summary["settled"] if not errors else summary["invalid"]).append(task["id"])
        elif mtype in {"question", "escalation"}:
            summary["needsReply"].append({"id": message.get("id"), "type": mtype, "task": (task or {}).get("id"),
                                          "subject": message.get("subject"), "body": message.get("body")})
    # fill the wave: launch the next planned task per settled worker
    if summary["settled"] or summary["invalid"]:
        before = {t["id"] for t in wave["tasks"] if t.get("status") == "running"}
        save_wave(root, wave)
        wave = start(root, run_id, phase, "orca", run)
        summary["launched"] = [t["id"] for t in wave["tasks"] if t.get("status") == "running" and t["id"] not in before]
    if not summary["needsReply"] and delivery:
        code, text = run([cli, "orchestration", "check", "--ack", str(delivery), "--json"], CLI_TIMEOUT_S)
        summary["acked"] = code == 0
    save_wave(root, wave)
    return summary, (4 if summary["needsReply"] else 0)


# ----------------------------------------------------------- ready/apply ----

def ready(root: Path, run_id: str, phase: str) -> tuple[bool, list[str]]:
    root = root.resolve()
    wave = load_wave(root, run_id, phase)
    problems: list[str] = []
    for task in wave["tasks"]:
        if not (root / task["findings"]).is_file():
            problems.append(f"{task['id']}: no finding yet")
            continue
        problems.extend(validate_task(root, wave, task))
    return (not problems), problems


def check_one(root: Path, run_id: str, phase: str, agent: str) -> list[str]:
    root = root.resolve()
    wave = load_wave(root, run_id, phase)
    for task in wave["tasks"]:
        if task["id"] == agent:
            return validate_task(root, wave, task)
    return [f"{agent}: not a task in this wave ({', '.join(t['id'] for t in wave['tasks'])})"]


def _record_command(root: Path, band: str, finding: dict) -> str:
    skills = skills_dir()
    verdict = finding.get("verdict") or {}
    parts = [
        f'python3 "{skills}/web2html/scripts/paper_23_validate.py" "{root}" --id {shlex.quote(band)} --record',
        f"--seen {shlex.quote(str(finding.get('seen') or ''))}",
        "--verdict " + ",".join(f"{k}={verdict.get(k)}" for k in (str(w) for w in _run_widths(root))),
    ]
    misses = finding.get("misses") or []
    for miss in misses:
        if isinstance(miss, dict):
            parts.append("--miss " + shlex.quote(f"{miss.get('width')}|{miss.get('what')}|{miss.get('fix')}"))
    if misses:
        parts.append("--patched")
    return " \\\n  ".join(parts)


def apply(root: Path, run_id: str, phase: str) -> dict:
    """Controller-side: promote what the wave produced, release leases, print next actions."""
    root = root.resolve()
    wave = load_wave(root, run_id, phase)
    ok, problems = ready(root, run_id, phase)
    if not ok:
        raise ValueError("wave not ready: " + "; ".join(problems))
    out: dict = {"phase": phase, "runId": run_id, "actions": [], "promoted": []}
    for task in wave["tasks"]:
        finding = json.loads((root / task["findings"]).read_text(encoding="utf-8"))
        if phase == "2.3":
            patch = str(finding.get("patch") or "").strip()
            out["actions"].append({
                "band": task["band"],
                "verdict": finding.get("verdict"),
                "patch": patch,
                "record": _record_command(root, task["band"], finding),
                "note": "apply `patch` to #%s first (rebuild/index.html or rebuild/css), then run `record`, then --shoot the next round if still open" % task["band"],
            })
        elif phase == "3.2":
            report = root / str(finding.get("report") or task["report"])
            dest = root / task["receipt"]
            dest.write_text(report.read_text(encoding="utf-8"), encoding="utf-8")
            out["promoted"].append(task["receipt"])
        else:
            out["actions"].append({"slug": task["slug"], "files": finding.get("files") or task.get("writes")})
        try:
            agent_loop.release_reviewer(root, task["id"], wave["inputSha256"])
        except ValueError:
            pass
        task["status"] = "applied"
    if phase == "5.2":
        out["actions"].append({"record": f'python3 "{skills_dir()}/web2html/scripts/record-phase-5-pages.py" "{root}"'})
    wave["appliedAt"] = _now_iso()
    save_wave(root, wave)
    agent_loop._atomic_json(wave_dir(root, run_id, phase) / "apply.json", out)
    return out


# ------------------------------------------------------------------ main ----

def _print_dispatch(wave: dict) -> None:
    adapter = wave.get("adapter")
    todo = [t for t in wave["tasks"] if t.get("status") == "dispatch"]
    if adapter == "subagent":
        print(f"wave {wave['phase']} {wave['runId']}: {len(todo)} task(s) → dispatch each spec below to a SUBAGENT of this harness "
              f"(same model family; read-only; one finding file each). Then `wave.py ready`.")
    elif adapter == "serial":
        print(f"wave {wave['phase']} {wave['runId']}: {len(todo)} task(s) → do each spec YOURSELF, in order, writing the same finding file. Then `wave.py ready`.")
    for task in todo:
        print("\n" + "-" * 72 + f"\n{task['id']}\n" + "-" * 72)
        print(task["spec"].rstrip())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("root", type=Path)
        p.add_argument("--phase", required=True, choices=PHASES)
        p.add_argument("--run-id", required=True)

    pr = sub.add_parser("prepare", help="plan tasks, snapshot inputs, claim a reviewer lease per task")
    common(pr)
    pr.add_argument("--max-workers", type=int, default=None)
    st = sub.add_parser("start", help="launch the wave on the chosen adapter")
    common(st)
    st.add_argument("--adapter", default="auto", choices=("auto", "orca", "subagent", "serial"))
    wt = sub.add_parser("wait", help="orca: one check --wait; validates worker_done, releases settled workers, acks when clean")
    common(wt)
    wt.add_argument("--timeout-ms", type=int, default=900_000)
    wt.add_argument("--ack", default=None)
    ck = sub.add_parser("check", help="validate one task's finding (a worker's self-check)")
    common(ck)
    ck.add_argument("--agent", required=True)
    rd = sub.add_parser("ready", help="exit 0 when every task has a valid finding")
    common(rd)
    apl = sub.add_parser("apply", help="controller: promote results, release leases, print record/patch actions")
    common(apl)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "prepare":
            wave = prepare(args.root, args.run_id, args.phase, args.max_workers)
            print(json.dumps({"phase": wave["phase"], "runId": wave["runId"], "inputSha256": wave["inputSha256"],
                              "tasks": [t["id"] for t in wave["tasks"]], "maxWorkers": wave["maxWorkers"]}))
            return 0
        if args.cmd == "start":
            wave = start(args.root, args.run_id, args.phase, args.adapter)
            running = [t["id"] for t in wave["tasks"] if t.get("status") == "running"]
            print(f"wave adapter {wave['adapter']} ({wave.get('adapterReason')})"
                  + (f" · running {running}" if running else ""))
            if any(t.get("status") == "dispatch" for t in wave["tasks"]):
                _print_dispatch(wave)
            return 0
        if args.cmd == "wait":
            summary, code = wait(args.root, args.run_id, args.phase, args.timeout_ms, args.ack)
            print(json.dumps(summary, indent=2))
            if code == 4:
                print("wave: a worker asked or escalated — answer with `orca orchestration reply --id <id> --body …`, "
                      f"then `wave.py wait … --ack {summary.get('delivery')}`", file=sys.stderr)
            return code
        if args.cmd == "check":
            errors = check_one(args.root, args.run_id, args.phase, args.agent)
            print("OK finding is current" if not errors else "FAIL: " + "; ".join(errors))
            return 0 if not errors else 2
        if args.cmd == "ready":
            ok, problems = ready(args.root, args.run_id, args.phase)
            print("OK wave is current; controller may apply." if ok else "FAIL:\n  " + "\n  ".join(problems))
            return 0 if ok else 2
        out = apply(args.root, args.run_id, args.phase)
        print(json.dumps(out, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
