#!/usr/bin/env python3
"""Live Web2Html pipeline board.

Every run writes a condensed live board into the *template project* folder
(e.g. Documents/templates/prior-run/pipeline.html). Never overwrite the spec
at the repository's pipeline.html.

  python3 pipeline-progress.py start  /path/to/project            # NEW run only
  python3 pipeline-progress.py resume /path/to/project --at 2.1 --owner session-2
  python3 pipeline-progress.py resume /path/to/project --owner session-2   # --at detected from the board
  python3 pipeline-progress.py mark   /path/to/project --step 1.2 --status active
  python3 pipeline-progress.py mark   /path/to/project --step 1.2 --status done
  python3 pipeline-progress.py timing /path/to/project [--json]        # per-step durations + run total
  python3 pipeline-progress.py mark   /path/to/project --step 1.4 --status active   # opens Paper + browser on the stamped source URL
  python3 pipeline-progress.py open-capture   /path/to/project   # re-open that Capture Tool tab
  python3 pipeline-progress.py capture-doctor /path/to/project   # bridge check; FAIL = side panel OFFLINE
  python3 pipeline-progress.py handoff /path/to/project          # copy-ready next-session prompt
  python3 pipeline-progress.py sync   /path/to/project
  python3 pipeline-progress.py finish /path/to/project

AGENT + MODEL. Each session records who ran it, so the board can attribute every
step. `--agent` defaults to the harness probe (opencode / claude-code / codex …);
`--model` (or WEB2HTML_MODEL) is explicit because a model id is not detectable.
Pass them on `resume`, e.g. `resume . --owner session-2 --model claude-fable-5.1`.
`mark --status active` stamps the step with the recording agent so a phase that
mixed agents still shows duration + agent + model. The board HUD names the
current session; each phase card carries its own `duration · agent · model` line.

THREE SESSIONS, TWO HANDOFFS. A run spans three sessions so the model can change
at each phase: 1 capture (1.1–1.4) → 2 build (2.1–2.4) → 3 QA (3.1–3.4).
Optional Phase 4 (4.1–4.4) imports remaining source pages into Paper after 3.4.
Optional Phase 5 (5.1–5.6) binds the site into astro/ after 4.4: scaffold the
Astro app + pull Header / Footer / components ONCE from the 3.4 polish, then
author each Paper page as a .astro body on that chrome, QA, wire routes + SEO,
build, review. 5.6 done tidies (keeps rebuild/ + astro/ + pipeline.html).
`mark --step 1.4 --status done` and `mark --step 2.4 --status done` release the
controller lease and print a copy-ready prompt for the next session
(qa/handoff-2.0.md / qa/handoff-3.0.md). 4.4 opted in emits qa/handoff-5.0.md.

HARD RULE: `start` is for a NEW run and force-resets the board. A second or third
session must use `resume` — it never resets, never quarantines, and never
reopens the live board. Only `start` opens pipeline.html (once, at the
beginning of the run). Assume that tab is still open. Every step script must
hint/mark; a frozen board is Pitfall #96.
Never skip a step (Pitfall #98). `skip` and `mark --status skipped` fail.
`mark` cannot jump to 2.1+ while 1.1–1.4 are open (Pitfall #148).
1.3 is the Design Library (mined off the 1.2 Paper frames) plus pulling
unique buttons/components from desktop and authoring button hover from
source CSS. 1.4 is the human checkpoint: `mark 1.4 active` opens Paper AND
the browser on the stamped source URL so the Capture Tool side panel connects
(leftover live hover; `open-capture` re-opens, `capture-doctor` checks the
bridge). Not a done-gate. 1.4 is not done until
qa/paper-human-review.md is written.
2.0 children are 2.1 / 2.2 / 2.3 / 2.4. Retired 2.2.a–e aliases are not live steps.
Leftover rebuild/*.html is quarantined by start. mark --status active when you enter a step,
mark --status done when you leave.
TodoWrite / banners must use these same IDs, in this order.
The live copy auto-refreshes every 15s so the bar moves as the JSON/HTML is
stamped. Once qa/paper-file.json exists, the Capture Tool URL is stamped
under the progress bar so a pull can start anytime.

TIMING. `mark active` stamps `started`, `mark done` stamps `ended`; each closed
step carries `durationSeconds` and the board shows when it finished and how
long it took. The run total is the SUM of step durations — never wall clock —
so pauses between sessions / terminals do not count. `start` and `resume`
append to `sessions[]`; `resume` without `--at` detects the step from the
board. A step marked done without a prior `mark active` gets `started`
inferred (previous step's end / this session's claim) and is flagged
`startedInferred`. `timing` prints the table.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from rebuild_write_gate import (
    ALLOW_DESIGN_SYSTEM,
    ALLOW_INDEX,
    ALLOW_PAGES,
    ALLOW_POLISH,
    gate_errors as rebuild_write_errors,
    quarantine_unauthorized_ship,
)
import run_config
from seed_index import seed as seed_index_html
from promote_ship import promote as promote_ship, ship_ready
from seed_index_polish import polish_path, seed as seed_index_polish

_APPLY_HOVER = importlib.util.spec_from_file_location(
    "apply_hover_css", _SCRIPTS / "apply-hover-css.py"
)
_apply_hover_css = importlib.util.module_from_spec(_APPLY_HOVER)
assert _APPLY_HOVER.loader
_APPLY_HOVER.loader.exec_module(_apply_hover_css)

_AUTHOR_DRAWER = importlib.util.spec_from_file_location(
    "author_nav_drawer", _SCRIPTS / "author-nav-drawer.py"
)
_author_nav_drawer = importlib.util.module_from_spec(_AUTHOR_DRAWER)
assert _AUTHOR_DRAWER.loader
_AUTHOR_DRAWER.loader.exec_module(_author_nav_drawer)

_AUTHOR_FAQ = importlib.util.spec_from_file_location(
    "author_faq", _SCRIPTS / "author-faq.py"
)
_author_faq = importlib.util.module_from_spec(_AUTHOR_FAQ)
assert _AUTHOR_FAQ.loader
_AUTHOR_FAQ.loader.exec_module(_author_faq)

_AUTHOR_DROPDOWN = importlib.util.spec_from_file_location(
    "author_nav_dropdown", _SCRIPTS / "author-nav-dropdown.py"
)
_author_nav_dropdown = importlib.util.module_from_spec(_AUTHOR_DROPDOWN)
assert _AUTHOR_DROPDOWN.loader
_AUTHOR_DROPDOWN.loader.exec_module(_author_nav_dropdown)

STEPS = [
    ("1.1", "Contract, files, fonts"),
    ("1.2", "Breakpoints + Navigation"),
    ("1.3", "Design Library + Tokens"),
    ("1.4", "Human checkpoint"),
    ("2.1", "Design System"),
    ("2.2", "Author the homepage"),
    ("2.3", "Validate vs Paper"),
    ("2.4", "Sign-off → 3.0 polish"),
    ("3.1", "QA pass 1"),
    ("3.2", "QA pass 2"),
    ("3.3", "Semantics + SEO sweep"),
    ("3.4", "Human checkpoint"),
    ("4.1", "Sitemap"),
    ("4.2", "Capture pages"),
    ("4.3", "Seed tokens"),
    ("4.4", "Human review"),
    ("5.1", "Scaffold Astro"),
    ("5.2", "Author pages"),
    ("5.3", "Desktop QA"),
    ("5.4", "Responsive"),
    ("5.5", "Wire routes + SEO"),
    ("5.6", "Human checkpoint"),
]
STEP_IDS = [s[0] for s in STEPS]
PHASE4_STEPS = [s[0] for s in STEPS if s[0].startswith("4.")]
PHASE5_STEPS = [s[0] for s in STEPS if s[0].startswith("5.")]
REQUIRED_STEPS = [s[0] for s in STEPS if not s[0].startswith(("4.", "5."))]
OPTIONAL_STEPS = PHASE4_STEPS + PHASE5_STEPS
TITLES = dict(STEPS)
RETIRED_22 = ("2.2.a", "2.2.b", "2.2.c", "2.2.d", "2.2.e")
SPINE_GROUPS = {
    "url": ("1.1",),
    "evidence": ("1.1", "1.2", "1.3"),
    "paper": ("1.2", "1.3", "1.4"),
    "static": ("2.1", "2.2", "2.3", "2.4"),
    "qa": ("3.1", "3.2", "3.3", "3.4"),
}
STATUSES = {"pending", "active", "done", "skipped"}
REFRESH = '<meta http-equiv="refresh" content="15" />'
REFRESH_RE = re.compile(r"\s*<meta http-equiv=[\"']refresh[\"'][^>]*>\s*", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ----------------------------------------------------------------- timing ----
# Each step row carries `started` (first `mark active`) and `ended` (last
# `mark done`). The run total is the SUM of step durations — never wall clock
# between sessions, so a run that pauses overnight between 1.4 and 2.1 does not
# count the pause. A step closed without ever going active gets `started`
# inferred from the tightest lower bound (previous step's end, this session's
# claim, run start) and is flagged `startedInferred` so the receipt is honest.


def parse_iso(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc).astimezone()
    return parsed


def fmt_duration(seconds: int | float | None) -> str:
    """42s · 4m 12s · 1h 12m. None → '—'."""
    if seconds is None:
        return "—"
    total = max(0, int(round(seconds)))
    if total < 60:
        return f"{total}s"
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {secs:02d}s"


def fmt_clock(value, *, with_date: bool = True) -> str:
    """Local clock of an ISO stamp, in the offset it was recorded with."""
    parsed = parse_iso(value)
    if parsed is None:
        return "—"
    return parsed.strftime("%d %b %H:%M" if with_date else "%H:%M:%S")


def step_duration_seconds(row: dict) -> int | None:
    started = parse_iso(row.get("started"))
    ended = parse_iso(row.get("ended"))
    if started is None or ended is None:
        return None
    return max(0, int((ended - started).total_seconds()))


def step_phase(sid: str) -> str:
    return sid.split(".", 1)[0]


def refresh_timing(data: dict) -> dict:
    """Recompute derived durations. Idempotent; called on every save and stamp.

    steps[*].durationSeconds — present when both stamps exist.
    timing.totalSeconds      — sum over done/skipped steps with a duration.
    timing.humanSeconds      — the part of that spent inside HUMAN_CHECKPOINTS.
    timing.phases            — per-phase sums ("1".."5").
    timing.untimedSteps      — closed rows with no measurable duration.
    """
    steps = data.get("steps") or {}
    total = human = timed = untimed = 0
    phases: dict[str, int] = {}
    last_sid = last_iso = None
    last_dt: datetime | None = None
    for sid in STEP_IDS:
        row = steps.get(sid)
        if not isinstance(row, dict):
            continue
        dur = step_duration_seconds(row)
        if dur is None:
            row.pop("durationSeconds", None)
        else:
            row["durationSeconds"] = dur
        if row.get("status") not in {"done", "skipped"}:
            continue
        if dur is None:
            untimed += 1
        else:
            timed += 1
            total += dur
            phases[step_phase(sid)] = phases.get(step_phase(sid), 0) + dur
            if sid in HUMAN_CHECKPOINTS:
                human += dur
        ended_dt = parse_iso(row.get("ended"))
        if ended_dt is not None and (last_dt is None or ended_dt >= last_dt):
            last_dt, last_sid, last_iso = ended_dt, sid, row.get("ended")
    active = next((sid for sid in STEP_IDS if (steps.get(sid) or {}).get("status") == "active"), None)
    data["timing"] = {
        "totalSeconds": total,
        "agentSeconds": total - human,
        "humanSeconds": human,
        "timedSteps": timed,
        "untimedSteps": untimed,
        "phases": phases,
        "phaseAgents": collect_phase_agents(steps),
        "lastEndedStep": last_sid,
        "lastEnded": last_iso,
        "activeStep": active,
        "activeSince": (steps.get(active) or {}).get("started") if active else None,
    }
    return data["timing"]


def collect_phase_agents(steps: dict) -> dict[str, list[dict]]:
    """Per phase, the timed steps grouped by the agent/model that ran them.

    A phase is usually one agent, but the run spans sessions so any phase can
    mix. Groups are ordered by the time they account for.
    """
    out: dict[str, list[dict]] = {}
    for sid in STEP_IDS:
        row = steps.get(sid)
        if not isinstance(row, dict) or row.get("status") not in {"done", "skipped"}:
            continue
        dur = row.get("durationSeconds")
        if dur is None:
            continue
        agent, model = row.get("agent") or None, row.get("model") or None
        bucket = out.setdefault(step_phase(sid), [])
        for entry in bucket:
            if entry["agent"] == agent and entry["model"] == model:
                entry["seconds"] += dur
                entry["steps"].append(sid)
                break
        else:
            bucket.append({"agent": agent, "model": model, "seconds": dur, "steps": [sid]})
    for bucket in out.values():
        bucket.sort(key=lambda entry: entry["seconds"], reverse=True)
    return out


def agent_label(agent: str | None, model: str | None) -> str:
    return " · ".join(part for part in (agent, model) if part)


def phase_agent_copy(entries: list[dict] | None, seconds: int | None) -> str:
    """`1h 51m · opencode · deepseek-v4.1-flash`, or one clause per agent if mixed."""
    duration = fmt_duration(seconds) if seconds else ""
    named = [entry for entry in (entries or []) if entry.get("agent") or entry.get("model")]
    if not named:
        return duration
    if len(named) == 1:
        return " · ".join(part for part in (duration, agent_label(named[0].get("agent"), named[0].get("model"))) if part)
    clauses = " + ".join(
        f"{agent_label(entry.get('agent'), entry.get('model')) or 'unknown'} ({fmt_duration(entry['seconds'])})"
        for entry in named
    )
    return " · ".join(part for part in (duration, clauses) if part)


def infer_started(data: dict, step: str) -> str | None:
    """Best lower bound for when work on `step` began, when it never went active.

    Only one step is active at a time, so the latest `ended` of any other
    closed step, the controller claim of this session, the last session log
    entry, and the run start are all lower bounds — take the tightest one.
    """
    candidates: list[tuple[datetime, str]] = []

    def add(value) -> None:
        parsed = parse_iso(value)
        if parsed is not None:
            candidates.append((parsed, value))

    add(data.get("started"))
    add((data.get("controller") or {}).get("claimedAt"))
    for entry in data.get("sessions") or []:
        if isinstance(entry, dict):
            add(entry.get("startedAt"))
    for sid, row in (data.get("steps") or {}).items():
        if sid != step and isinstance(row, dict) and row.get("status") in {"done", "skipped"}:
            add(row.get("ended"))
    now = datetime.now(timezone.utc)
    candidates = [(dt, raw) for dt, raw in candidates if dt <= now]
    if not candidates:
        return None
    return max(candidates, key=lambda pair: pair[0])[1]


def close_step_timing(data: dict, step: str, *, infer: bool = True) -> None:
    """Stamp `ended` now; backfill a missing `started` when asked."""
    row = data["steps"][step]
    row["ended"] = now_iso()
    if infer and not row.get("started"):
        guess = infer_started(data, step)
        if guess:
            row["started"] = guess
            row["startedInferred"] = True


def resolve_agent_model(
    root: Path | None,
    agent: str | None = None,
    model: str | None = None,
) -> tuple[str | None, str | None]:
    """Who is doing the work: explicit flag → env → harness probe → unknown.

    The harness is detectable (opencode / claude-code / codex …) so the agent is
    filled in for free. The model is not, so a session records it explicitly
    (`--model`, or WEB2HTML_MODEL) — it may differ from phase to phase.
    """
    who = (agent or "").strip() or os.environ.get("WEB2HTML_AGENT", "").strip() or None
    if who is None and root is not None and not os.environ.get("WEB2HTML_NO_PROBE"):
        report = _probe_report(root) or {}
        who = str(report.get("agent") or report.get("harness") or "").strip() or None
    what = (model or "").strip() or os.environ.get("WEB2HTML_MODEL", "").strip() or None
    return who, what


def log_session(
    data: dict,
    *,
    kind: str,
    owner: str | None,
    at: str | None,
    agent: str | None = None,
    model: str | None = None,
) -> dict:
    """Append one line to the run's session log (start / resume / relay)."""
    entry = {"kind": kind, "owner": owner, "at": at, "startedAt": now_iso()}
    if agent:
        entry["agent"] = agent
    if model:
        entry["model"] = model
    sessions = data.setdefault("sessions", [])
    if not isinstance(sessions, list):
        sessions = data["sessions"] = []
    sessions.append(entry)
    return entry


def current_session(data: dict) -> dict:
    """The newest session entry — the one holding the controller lease."""
    for entry in reversed(data.get("sessions") or []):
        if isinstance(entry, dict):
            return entry
    return {}


def stamp_step_who(row: dict, agent: str | None, model: str | None, *, overwrite: bool) -> None:
    """Attribute a step to an agent/model. `overwrite` is for a fresh `active`."""
    if agent and (overwrite or not row.get("agent")):
        row["agent"] = agent
    if model and (overwrite or not row.get("model")):
        row["model"] = model


def detect_resume_step(data: dict, root: Path | None = None) -> str | None:
    """Where the run sits: the active step, else the first pending step."""
    _, _, current = counts(data, root)
    if current:
        return current
    return next_pending_step(data, root)


def timing_summary_line(data: dict) -> str:
    timing = refresh_timing(data)
    total = fmt_duration(timing["totalSeconds"])
    parts = [f"run total {total}"]
    if timing["humanSeconds"]:
        parts.append(f"agent {fmt_duration(timing['agentSeconds'])} · human {fmt_duration(timing['humanSeconds'])}")
    parts.append(f"{timing['timedSteps']} step{'s' if timing['timedSteps'] != 1 else ''} timed")
    if timing["untimedSteps"]:
        parts.append(f"{timing['untimedSteps']} untimed")
    if timing["lastEndedStep"]:
        parts.append(f"last finished {timing['lastEndedStep']} at {fmt_clock(timing['lastEnded'])}")
    return "   ".join(parts)


def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def skill_pkg() -> Path:
    return Path(__file__).resolve().parents[1]


def spec_pipeline() -> Path:
    return skill_root() / "pipeline.html"


def live_template() -> Path:
    return skill_pkg() / "templates" / "pipeline-live.html"


NEXT_NAME = "NEXT.html"
LIVE_NAME = "pipeline.html"
NOISE_DIRS = (
    "qa",
    "capture",
    "source-site",
    "analysis",
    "cms",
    "design-library",
    "first-pass",
)
NOISE_REBUILD_FILES = ("polish-report.html", NEXT_NAME)
# Verification shots and scratch trees that must never ship inside rebuild/.
NOISE_REBUILD_GLOBS = (
    "qa",
    "verification",
    "diff-heatmap.png",
    "ref_*.png",
    "build_*.png",
    "side_by_side_*.png",
    "*-build.png",
    "*.spec.png",
    "*.spec.json",
    "section-[0-9][0-9].png",
)
KEEP_ROOT = frozenset({"rebuild", "astro", LIVE_NAME, "run-report.md"})
TIDY_SUMMARY = "tidy → lean folder (rebuild/ + astro/ + pipeline.html)"
AGENT_RUNS = Path("qa/agent-runs")
LEASES = AGENT_RUNS / "leases"


class ProgressConflict(RuntimeError):
    """Raised when a controller tries to write an out-of-date progress revision."""


def qa_dir(root: Path) -> Path:
    return root.resolve() / "qa"


def live_html(root: Path) -> Path:
    return root.resolve() / LIVE_NAME


def is_spec_repo(root: Path) -> bool:
    r = root.resolve()
    return r == skill_root() or (r / "1.0 - web2html").is_dir()


def progress_path(root: Path) -> Path:
    return qa_dir(root) / "pipeline-progress.json"


def phase4_opted(root: Path) -> bool:
    return (root.resolve() / PHASE4_OPTED).is_file()


def phase4_skipped(root: Path) -> bool:
    return (root.resolve() / PHASE4_SKIPPED).is_file()


def phase4_receipt(root: Path) -> bool:
    return phase4_opted(root) or phase4_skipped(root)


def write_phase4_required(root: Path) -> Path:
    """Folder / Webflow runs do not ask. Phase 4 is the rest of the run."""
    dest = root.resolve() / PHASE4_OPTED
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.is_file():
        dest.write_text(
            json.dumps(
                {
                    "generatedFrom": "web2html/phase-4-required",
                    "reason": "Webflow / HTML folder — Phase 4 runs through 4.4",
                    "recordedAt": now_iso(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return dest


def phase5_opted(root: Path) -> bool:
    return (root.resolve() / PHASE5_OPTED).is_file()


def phase5_skipped(root: Path) -> bool:
    return (root.resolve() / PHASE5_SKIPPED).is_file()


def phase5_receipt(root: Path) -> bool:
    return phase5_opted(root) or phase5_skipped(root)


def _optional_phase_active(data: dict | None, ids: list[str]) -> bool:
    if not data:
        return False
    return any(
        (data.get("steps") or {}).get(sid, {}).get("status") in {"active", "done", "skipped"}
        for sid in ids
    )


def counted_step_ids(root: Path | None = None, data: dict | None = None) -> list[str]:
    ids = list(REQUIRED_STEPS)
    include4 = (root is not None and phase4_opted(root)) or _optional_phase_active(data, PHASE4_STEPS)
    include5 = (root is not None and phase5_opted(root)) or _optional_phase_active(data, PHASE5_STEPS)
    if include4:
        ids.extend(PHASE4_STEPS)
    if include5:
        ids.extend(PHASE5_STEPS)
    return ids


def controller_lease_path(root: Path) -> Path:
    return root.resolve() / LEASES / "controller.json"


def active_reviewer_leases(root: Path) -> list[Path]:
    """Return only active read-only reviewer leases; the controller may finish a run."""
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


def _revision(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _progress_conflict(expected: int, actual: int) -> str:
    return f"FAIL: stale progress revision {expected}; current revision is {actual}. Reload before writing."


HUMAN_CHECKPOINTS = frozenset({"1.4", "2.4", "3.4", "4.4", "5.6"})
# Three sessions, two handoffs. 1.4 hands off to the build tier, 2.4 to the QA
# tier. Each emits a copy-ready prompt that names the recommended tier; the
# tier is advice, never a gate — any model may run any session.
# Phase 4 is optional session 4 after a 3.4 opt-in. Phase 5 (Astro-first
# site) is optional session 5 after a 4.4 opt-in (recommended strong tier).
SESSION_OF = {
    "1.1": 1, "1.2": 1, "1.3": 1, "1.4": 1,
    "2.1": 2, "2.2": 2, "2.3": 2, "2.4": 2,
    "3.1": 3, "3.2": 3, "3.3": 3, "3.4": 3,
    "4.1": 4, "4.2": 4, "4.3": 4, "4.4": 4,
    "5.1": 5, "5.2": 5, "5.3": 5, "5.4": 5, "5.5": 5, "5.6": 5,
}
HANDOFF_AT = {"1.4": 2, "2.4": 3, "4.4": 5}
HANDOFF_FILE = {2: "qa/handoff-2.0.md", 3: "qa/handoff-3.0.md", 5: "qa/handoff-5.0.md"}
# First pending step after a session yield. HUD / Here-Next use these so 2.4
# done never reads as "Ready" or as polish already running.
SESSION_YIELD = {
    "2.1": "Session 2 build — not started",
    "3.1": "Session 3 polish — not started",
    "4.1": "optional Phase 4 — not started",
    "5.1": "optional Phase 5 (Astro site) — not started",
}
# 1.1 inventory and 1.2 capture may overlap. Everything after that is serial.
OVERLAP_ACTIVE = frozenset({("1.2", "1.1")})
ARTIFACT_DONE_REQUIRED = frozenset({
    "1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3",
    "4.1", "4.2", "4.3", "5.1", "5.2", "5.3", "5.4", "5.5",
})
BUILD_STEPS = frozenset(sid for sid in STEP_IDS if sid.startswith(("2.", "3.", "5.")))
PHASE4_OPTED = "qa/phase-4-opted.json"
PHASE4_SKIPPED = "qa/phase-4-skipped.json"
PHASE5_OPTED = "qa/phase-5-opted.json"
PHASE5_SKIPPED = "qa/phase-5-skipped.json"
TOKEN_DEF_RE = re.compile(r"(--(?:color|font)-[a-z0-9-]+)\s*:", re.I)
LINK_HREF_RE = re.compile(r"""<link[^>]+href\s*=\s*["']([^"']+)["']""", re.I)


def _href_names(html: str) -> set[str]:
    names: set[str] = set()
    for href in LINK_HREF_RE.findall(html):
        names.add(Path(href.split("?", 1)[0]).name)
    return names


def _library_color_font_names(root: Path) -> set[str]:
    names: set[str] = set()
    tokens = root / "rebuild" / "css" / "tokens.css"
    if tokens.is_file():
        try:
            names.update(TOKEN_DEF_RE.findall(tokens.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            pass
    library = root / "design-library" / "library.json"
    if library.is_file():
        try:
            payload = json.loads(library.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            payload = {}
        tokens_obj = payload.get("tokens") if isinstance(payload, dict) else None
        if isinstance(tokens_obj, dict):
            for key in tokens_obj.get("color") or {}:
                slug = str(key).replace("_", "-")
                names.add(f"--color-{slug}")
            for bucket in ("font", "type"):
                for key in tokens_obj.get(bucket) or {}:
                    slug = str(key).replace("_", "-")
                    names.add(f"--font-{slug}")
    return {name.lower() for name in names}


def authored_page_ready(root: Path) -> bool:
    """2.2 Author: first-pass page exists and is not a get_jsx soup dump."""
    from rebuild_write_gate import RAW_PAPER_EXPORT_RE, ship_markup_errors

    ship = root / "rebuild" / "index-semantic.html"
    if not ship.is_file():
        return False
    try:
        html = ship.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if RAW_PAPER_EXPORT_RE.search(html):
        return False
    if run_config.raw_dump_enabled(root) and not (root / "rebuild" / "index-raw.html").is_file():
        return False
    return not ship_markup_errors(html)


def design_system_page_ready(root: Path) -> bool:
    """2.1: emit-design-system wrote the token contract page."""
    from design_system_21_gate import ready as ds_ready

    return ds_ready(root)


def design_system_bound(root: Path) -> bool:
    """2.2: first pass links 1.3-signed tokens.css; no invented --color/--font names.

    Fast run: there is no 1.3 library and no 2.1 token sheet, so there is
    nothing to bind against. The markup gates (authored_page_ready) still apply.
    """
    if not run_config.design_system_enabled(root):
        return True
    ship = root / "rebuild" / "index-semantic.html"
    tokens = root / "rebuild" / "css" / "tokens.css"
    if not ship.is_file() or not tokens.is_file():
        return False
    try:
        html = ship.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    hrefs = _href_names(html)
    if "tokens.css" not in hrefs:
        return False
    utilities = root / "rebuild" / "css" / "token-utilities.css"
    if utilities.is_file() and "token-utilities.css" not in hrefs:
        return False
    known = _library_color_font_names(root)
    if not known:
        return False
    invented: set[str] = set(TOKEN_DEF_RE.findall(html))
    css_dir = root / "rebuild" / "css"
    if css_dir.is_dir():
        for path in css_dir.glob("*.css"):
            if path.name == "tokens.css":
                continue
            try:
                invented.update(TOKEN_DEF_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
    extra = {name.lower() for name in invented} - known
    return not extra


def find_live_root(start: Path | None = None) -> Path | None:
    """Walk cwd (or start) for qa/pipeline-progress.json. Never the spec repo."""
    try:
        cur = (start or Path.cwd()).resolve()
    except OSError:
        return None
    if cur.is_file():
        cur = cur.parent
    seen: set[Path] = set()
    while cur not in seen:
        seen.add(cur)
        if (cur / "qa" / "pipeline-progress.json").is_file() and not is_spec_repo(cur):
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None


def hint(step: str, status: str = "active", root: Path | None = None) -> None:
    """Best-effort stamp. Never raise. No-op if no live board / spec repo / unknown step."""
    try:
        if step not in TITLES or status not in STATUSES:
            return
        live: Path | None = None
        if root is not None:
            try:
                r = Path(root).resolve()
            except OSError:
                r = None
            if r is not None:
                if r.is_file():
                    r = r.parent
                if progress_path(r).is_file() and not is_spec_repo(r):
                    live = r
                else:
                    live = find_live_root(r)
        else:
            live = find_live_root()
        if live is None:
            return
        cmd_mark(live, step, status, None)
    except Exception:
        return


def hint_step(step: str, status: str = "active", root: Path | None = None) -> None:
    """Importable alias for hint(). Callers may sys.path-insert this folder."""
    hint(step, status, root)


def _any_exists(root: Path, *relpaths: str) -> bool:
    return any((root / rel).exists() for rel in relpaths)


def _any_glob(root: Path, *patterns: str) -> bool:
    return any(next(root.glob(pat), None) is not None for pat in patterns)


def layer_ids_census_done(root: Path) -> bool:
    """Optional invisible 1.2 QA. Not required to mark 1.2 done."""
    for path in (
        root / "capture" / "home-desktop" / "layer-ids-census.json",
        root / "qa" / "layer-ids-census.json",
    ):
        if not path.is_file():
            continue
        try:
            report = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if report.get("ok") is True:
            return True
    return False


def geometry_postflight_done(root: Path) -> bool:
    evidence = root / "qa" / "stretch-root-evidence.md"
    if not evidence.is_file():
        return False
    try:
        return "Result: PASS" in evidence.read_text()
    except OSError:
        return False


def has_source_section_shots(folder: Path) -> bool:
    """True when capture/.../source-sections holds at least one NN-*.png clip."""
    if not folder.is_dir():
        return False
    return any(
        path.is_file()
        and path.suffix.lower() == ".png"
        and re.match(r"^\d{2}-.+\.png$", path.name, re.I)
        for path in folder.iterdir()
    )


def source_section_shots_done(root: Path, page_slug: str = "home") -> bool:
    """1.2 stores per-section clips at the configured widths. Screenshots board stays 1600."""
    capture = root / "capture"
    for width in run_config.widths(root):
        folder = f"{page_slug}-desktop" if width >= 1400 else f"{page_slug}-{width}"
        if not has_source_section_shots(capture / folder / "source-sections"):
            return False
    return True


def breakpoint_shot_qa_done(root: Path) -> bool:
    """Captured home-768 / home-390 (only the configured ones) passed one screenshot pass."""
    path = root / "qa" / "breakpoint-shot-qa.json"
    if not path.is_file():
        return False
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    need = len([w for w in run_config.widths(root) if w < 1400])
    return (
        report.get("ok") is True
        and not report.get("missingFrames")
        and len(report.get("frames") or []) >= need
    )


def pending_predecessors(data: dict, step: str, *, for_active: bool) -> list[str]:
    """Steps that must already be done before this mark is legal."""
    try:
        idx = STEP_IDS.index(step)
    except ValueError:
        return []
    pending: list[str] = []
    for sid in STEP_IDS[:idx]:
        if sid.startswith("4.") and not step.startswith(("4.", "5.")):
            continue
        if sid.startswith("5.") and not step.startswith("5."):
            continue
        if for_active and (step, sid) in OVERLAP_ACTIVE:
            continue
        row = data.get("steps", {}).get(sid) or {}
        status = row.get("status")
        if step.startswith("4.") and sid.startswith("4.") and status in {"done", "skipped"}:
            continue
        if step.startswith("5.") and sid.startswith("5.") and status in {"done", "skipped"}:
            continue
        if status != "done":
            pending.append(sid)
    return pending


def buttons_components_pull_done(root: Path) -> bool:
    """1.3 filled FRAME Buttons + Components from token-seeded home-desktop."""
    path = root / "qa" / "buttons-components-pull.json"
    if not path.is_file():
        return False
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    scanned = rec.get("scannedSections") or []
    geometry = rec.get("geometry") or {}
    return (
        rec.get("ok") is True
        and rec.get("writer") == "pull-desktop-specimens.mjs"
        and geometry.get("ok") is True
        and isinstance(scanned, list)
        and len(scanned) >= 1
        and isinstance(rec.get("buttons"), list)
        and isinstance(rec.get("components"), list)
    )


def button_hover_done(root: Path) -> bool:
    """1.3 authored FRAME Buttons hover from source CSS (may apply zero)."""
    path = root / "qa" / "button-hover.json"
    if not path.is_file():
        return False
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        rec.get("ok") is True
        and rec.get("writer") == "author-button-hover.mjs"
        and isinstance(rec.get("applied"), list)
        and isinstance(rec.get("skipped"), list)
    )


def button_hover_css_done(root: Path) -> bool:
    """3.2 linked 1.3 button hover CSS onto index-polish.html."""
    path = root / "qa" / "button-hover-css.json"
    if not path.is_file():
        return False
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        rec.get("ok") is True
        and rec.get("writer") == "apply-hover-css.py"
        and isinstance(rec.get("applied"), list)
        and isinstance(rec.get("skipped"), list)
    )


def nav_drawer_done(root: Path) -> bool:
    """3.2 authored the painted burger drawer (Capture Tool not required)."""
    path = root / "qa" / "nav-drawer.json"
    if not path.is_file():
        return False
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if (
        rec.get("ok") is not True
        or rec.get("writer") != "author-nav-drawer.py"
        or not isinstance(rec.get("applied"), list)
        or not isinstance(rec.get("skipped"), list)
    ):
        return False
    for row in rec.get("skipped") or []:
        reason = str(row.get("reason") or "")
        finding = str(row.get("finding") or "")
        if "burger" in finding.casefold() and re.search(
            r"capture tool open-nav|inventing a sheet|new chrome", reason, re.I
        ):
            return False
    return True


def faq_done(root: Path) -> bool:
    """3.2 authored FAQ accordion when rows are painted (Capture Tool not required)."""
    path = root / "qa" / "faq.json"
    if not path.is_file():
        return False
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if (
        rec.get("ok") is not True
        or rec.get("writer") != "author-faq.py"
        or not isinstance(rec.get("applied"), list)
        or not isinstance(rec.get("skipped"), list)
    ):
        return False
    painted = rec.get("painted") is True
    for row in rec.get("skipped") or []:
        reason = str(row.get("reason") or "")
        finding = str(row.get("finding") or "")
        if (
            painted
            and "faq" in finding.casefold()
            and re.search(
                r"empty bodies|do not invent copy|capture tool|detect-only|no faq capture",
                reason,
                re.I,
            )
        ):
            return False
    return True


COMPANION_RECEIPTS = (
    "qa/web-design-guidelines.md",
    "qa/find-animation-opportunities.md",
    "qa/apple-design.md",
)


def companion_receipts_done(root: Path) -> bool:
    """3.2 companions each left a non-empty markdown receipt (Pitfall #215)."""
    for rel in COMPANION_RECEIPTS:
        path = root / rel
        try:
            if not path.read_text(encoding="utf-8", errors="replace").strip():
                return False
        except OSError:
            return False
    return True


def nav_dropdown_done(root: Path) -> bool:
    """3.2 authored nav dropdowns from polish + scrape (Capture Tool not required)."""
    path = root / "qa" / "nav-dropdown.json"
    if not path.is_file():
        return False
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if (
        rec.get("ok") is not True
        or rec.get("writer") != "author-nav-dropdown.py"
        or not isinstance(rec.get("applied"), list)
        or not isinstance(rec.get("skipped"), list)
    ):
        return False
    for row in rec.get("skipped") or []:
        reason = str(row.get("reason") or "")
        finding = str(row.get("finding") or "")
        if "dropdown" in finding.casefold() and re.search(
            r"capture tool|allow-dropdown|do not hunt|no dropdown capture",
            reason,
            re.I,
        ):
            return False
    return True


def artifact_done(root: Path, step: str) -> bool:
    """Conservative: file exists ⇒ that step can be marked done. Missing optional artifacts ⇒ False."""
    if step == "1.1":
        return (root / "source-site").exists() or _any_exists(
            root,
            "qa/fidelity-contract.md",
            "scrape-contract.md",
            "source-site/scraped-tokens.md",
        )
    if step == "1.2":
        return (
            (root / "capture" / "home-desktop").is_dir()
            and geometry_postflight_done(root)
            and source_section_shots_done(root)
            and breakpoint_shot_qa_done(root)
        )
    if step == "1.4":
        # 1.4 is the human Paper checkpoint. Buttons + Components are filled
        # in 1.3 from desktop. Capture Tool is opt-in leftover hover, not a
        # done-gate.
        return _any_exists(root, "qa/paper-human-review.md")
    if step == "1.3":
        if not run_config.design_library_enabled(root):
            # Fast run: 1.3 is skipped by contract; the intake wrote the receipt.
            return (root / run_config.DESIGN_LIBRARY_SKIPPED).is_file()
        has_lib = _any_exists(
            root,
            "library.json",
            "design-library/library.json",
            "design-library/exports-inline/library/design-library.json",
        )
        if not has_lib:
            return False
        seed = root / "qa" / "library-seed-qa.json"
        step_receipt = root / "qa" / "design-library-step.json"
        if not seed.is_file() or not step_receipt.is_file():
            return False
        try:
            seed_ok = json.loads(seed.read_text(encoding="utf-8")).get("ok") is True
            rec = json.loads(step_receipt.read_text(encoding="utf-8"))
            cmds = rec.get("commands") or []
            return (
                seed_ok
                and rec.get("status") == "done"
                and rec.get("writer") == "render-library.mjs"
                and rec.get("kind") == "foundations"
                and "extract-library.mjs" in cmds
                and "render-library.mjs" in cmds
                and buttons_components_pull_done(root)
                and button_hover_done(root)
            )
        except Exception:
            return False
    if step == "2.1":
        if run_config.adopt_mode(root):
            import source_fidelity

            return source_fidelity.phase_2_off(root)
        if not run_config.design_system_enabled(root):
            # Fast still self-hosts fonts.
            return (root / run_config.DESIGN_SYSTEM_SKIPPED).is_file() and (
                root / "rebuild" / "css" / "fonts.css"
            ).is_file()
        return design_system_page_ready(root)
    if step == "2.2":
        if run_config.adopt_mode(root):
            import source_fidelity

            return source_fidelity.phase_2_off(root)
        return authored_page_ready(root) and design_system_bound(root)
    if step == "2.3":
        if run_config.adopt_mode(root):
            import source_fidelity

            return source_fidelity.phase_2_off(root)
        from section_22_gate import ready as section_22_ready

        return section_22_ready(root)
    if step == "2.4":
        if run_config.adopt_mode(root):
            import source_fidelity

            return source_fidelity.phase_2_off(root)
        if run_config.auto_accepts(root, "2.4"):
            return _any_exists(root, "qa/build-checkpoint.md")
        opened = root / "qa" / "build-checkpoint-opened.json"
        try:
            opened_payload = json.loads(opened.read_text(encoding="utf-8"))
            opened_ok = (
                opened_payload.get("generatedFrom") == "web2html/open-build-review"
                and opened_payload.get("stage") == "2.4"
            )
        except (OSError, ValueError, json.JSONDecodeError):
            opened_ok = False
        overlay = root / "rebuild" / "js" / "qa-overlay.js"
        try:
            overlay_text = overlay.read_text(encoding="utf-8")
            overlay_tags = '|| "tags"' in overlay_text or "|| 'tags'" in overlay_text
        except OSError:
            overlay_tags = False
        return (
            opened_ok
            and overlay_tags
            and _any_exists(root, "qa/build-checkpoint.md")
        )
    if step == "3.1":
        if run_config.adopt_mode(root):
            import source_fidelity

            return source_fidelity.load_snapshot(root) is not None and not source_fidelity.verify(root)
        return (
            _any_exists(root, "qa/polish-passes/c3-3.1-impeccable.json")
            and _any_exists(root, "qa/polish-passes/c3-3.2-design-taste-frontend.json")
        )
    if step == "3.2":
        if run_config.adopt_mode(root):
            import source_fidelity

            return source_fidelity.load_snapshot(root) is not None and not source_fidelity.verify(root)
        gsap = root / "qa" / "gsap-reveal-qa.json"
        gsap_ok = False
        if gsap.is_file():
            try:
                gsap_ok = json.loads(gsap.read_text(encoding="utf-8")).get("ok") is True
            except (OSError, json.JSONDecodeError, TypeError):
                gsap_ok = False
        return (
            _any_exists(root, "qa/polish-passes/c3-3.3-emil-design-eng.json")
            and gsap_ok
            and button_hover_css_done(root)
            and nav_drawer_done(root)
            and faq_done(root)
            and nav_dropdown_done(root)
            and companion_receipts_done(root)
        )
    if step == "3.3":
        if run_config.adopt_mode(root):
            import source_fidelity

            return source_fidelity.load_snapshot(root) is not None and not source_fidelity.verify(root)
        return _any_exists(root, "qa/semantics-pass-qa.json")
    if step == "4.1":
        if run_config.adopt_mode(root):
            return _any_exists(root, "qa/phase-4-sitemap.json") and _any_exists(root, "qa/source-gaps.json")
        return _any_exists(root, "qa/phase-4-sitemap.json")
    if step == "4.2":
        return _any_exists(root, "qa/phase-4-pages.json")
    if step == "4.3":
        seed = root / "qa" / "phase-4-token-seed.json"
        if run_config.adopt_mode(root):
            import source_fidelity

            return source_fidelity.gap_author_ready(root)
        if not seed.is_file():
            return False
        return True
    if step == "4.4":
        return _any_exists(root, "qa/phase-4-review.md")
    if step == "5.1":
        return (
            _any_exists(root, "qa/phase-5-scaffold.json")
            and _any_exists(root, "qa/phase-5-components.json")
            and _any_exists(root, "qa/phase-5-home.json")
        )
    if step == "5.2":
        return _any_exists(root, "qa/phase-5-pages.json")
    if step == "5.3":
        return _any_exists(root, "qa/phase-5-clip-compare.json")
    if step == "5.4":
        return _any_exists(root, "qa/phase-5-responsive.json")
    if step == "5.5":
        return _any_exists(root, "qa/phase-5-links.json")
    if step == "5.6":
        return _any_exists(root, "qa/phase-5-review.md")
    return False


def cmd_restamp(root: Path) -> int:
    """Rewrite pipeline.html from current progress. Does not change step status.

    1.2 calls this the moment qa/paper-file.json exists so the open board
    picks up the Capture Tool URL on its next 15s refresh.
    """
    if is_spec_repo(root):
        print("FAIL: do not stamp the web2html spec repo. Pass the template project folder.", file=sys.stderr)
        return 2
    if not progress_path(root).is_file():
        print("restamp: no-op (no live board)")
        return 0
    dest = write_live(root, load_progress(root))
    print(dest.resolve().as_uri())
    url = capture_tool_board_url(root)
    print(url or "capture: waiting for Paper (qa/paper-file.json)")
    return 0


def cmd_sync(root: Path) -> int:
    """Mark artifact-backed steps done, then the next unfinished step active.

    Never auto-completes human checkpoints. No-op if nothing matches.
    """
    if is_spec_repo(root):
        print("FAIL: do not stamp the web2html spec repo. Pass the template project folder.", file=sys.stderr)
        return 2
    if active_reviewer_leases(root):
        print("FAIL: sync refused while reviewer leases are active.", file=sys.stderr)
        return 2
    if not progress_path(root).is_file():
        print("sync: no-op (no live board)")
        return 0
    data = load_progress(root)
    marked: list[tuple[str, str]] = []
    any_match = False
    for sid in STEP_IDS:
        if sid in HUMAN_CHECKPOINTS:
            continue
        if sid.startswith("4.") and not phase4_opted(root):
            continue
        if sid.startswith("5.") and not phase5_opted(root):
            continue
        if pending_predecessors(data, sid, for_active=False):
            continue
        if not artifact_done(root, sid):
            continue
        any_match = True
        row = data["steps"][sid]
        if row.get("status") in {"done", "skipped"}:
            continue
        row["status"] = "done"
        if not row.get("ended"):
            close_step_timing(data, sid)
        if data.get("current") == sid:
            data["current"] = None
        marked.append((sid, "done"))
    if not any_match:
        print("sync: no-op (no matching artifacts)")
        return 0
    next_sid = next(
        (sid for sid in STEP_IDS if data["steps"][sid]["status"] not in {"done", "skipped"}),
        None,
    )
    if next_sid:
        for sid, row in data["steps"].items():
            if row.get("status") == "active" and sid != next_sid:
                if sid in HUMAN_CHECKPOINTS:
                    continue
                row["status"] = "done"
                if not row.get("ended"):
                    close_step_timing(data, sid)
                marked.append((sid, "done"))
        row = data["steps"][next_sid]
        if row.get("status") != "active":
            row["status"] = "active"
            row["started"] = row.get("started") or now_iso()
            marked.append((next_sid, "active"))
        data["current"] = next_sid
    try:
        save_progress(root, data)
    except ProgressConflict as exc:
        print(str(exc), file=sys.stderr)
        return 2
    dest = write_live(root, data)
    write_capture_tool_session(root)
    if not marked:
        print("sync: already in sync")
    else:
        for sid, status in marked:
            print(f"sync: {sid} → {status}")
    done, total, current = counts(data)
    extra = f"   current {current}" if current else ""
    print(f"{done}/{total}{extra}")
    print(dest.resolve().as_uri())
    return 0


def empty_progress(project: str) -> dict:
    return {
        "project": project,
        "started": now_iso(),
        "updated": now_iso(),
        "revision": 0,
        "current": None,
        "steps": {sid: {"title": TITLES[sid], "status": "pending"} for sid in STEP_IDS},
    }


def load_progress(root: Path) -> dict:
    p = progress_path(root)
    if not p.is_file():
        return empty_progress(root.name)
    data = json.loads(p.read_text())
    data["revision"] = _revision(data.get("revision"))
    steps = data.setdefault("steps", {})
    if "1.6" in steps:
        old = dict(steps)
        extension_rows = [old.get(sid, {"status": "pending"}) for sid in ("1.3", "1.4")]
        extension_statuses = [row.get("status", "pending") for row in extension_rows]
        merged_extension = dict(extension_rows[0])
        merged_extension["title"] = TITLES["1.3"]
        old_current = data.get("current")
        merged_extension["status"] = (
            "active" if old_current in {"1.3", "1.4"} or "active" in extension_statuses
            else "done" if all(status in {"done", "skipped"} for status in extension_statuses)
            else "active" if any(status in {"done", "skipped"} for status in extension_statuses)
            else "pending"
        )
        steps = {
            "1.1": old.get("1.1", {"title": TITLES["1.1"], "status": "pending"}),
            "1.2": old.get("1.2", {"title": TITLES["1.2"], "status": "pending"}),
            "1.3": merged_extension,
            "1.4": old.get("1.5", {"title": TITLES["1.4"], "status": "pending"}),
            "1.5": old.get("1.6", {"title": "Human Review + Paper sign-off", "status": "pending"}),
            **{sid: row for sid, row in old.items() if sid.startswith("2.")},
        }
        current_map = {"1.4": "1.3", "1.5": "1.4", "1.6": "1.5"}
        data["current"] = current_map.get(data.get("current"), data.get("current"))
        data["steps"] = steps
    if "1.5" in steps:
        # Older boards still split the human checkpoint into 1.4 (Capture Tool)
        # and 1.5 (Paper sign-off). Fold both into the single 1.4 checkpoint.
        old = dict(steps)
        old_current = data.get("current")
        rows = [old.get(sid, {"status": "pending"}) for sid in ("1.4", "1.5")]
        statuses = [row.get("status", "pending") for row in rows]
        merged_checkpoint = dict(rows[0])
        merged_checkpoint["title"] = TITLES["1.4"]
        merged_checkpoint["status"] = (
            "active" if old_current in {"1.4", "1.5"} or "active" in statuses
            else "done" if all(status in {"done", "skipped"} for status in statuses)
            else "active" if any(status in {"done", "skipped"} for status in statuses)
            else "pending"
        )
        started = next((row.get("started") for row in rows if row.get("started")), None)
        ended = next((row.get("ended") for row in reversed(rows) if row.get("ended")), None)
        if started:
            merged_checkpoint["started"] = started
        if ended and merged_checkpoint["status"] == "done":
            merged_checkpoint["ended"] = ended
        steps = {sid: row for sid, row in old.items() if sid != "1.5"}
        steps["1.4"] = merged_checkpoint
        data["current"] = "1.4" if old_current in {"1.4", "1.5"} else old_current
        data["steps"] = steps
    if any(sid.startswith("2.3.") for sid in steps) or (
        "2.4" in steps and "3.4" not in steps
    ):
        old = dict(steps)
        old_current = data.get("current")

        def merged_qa(new_id: str, old_ids: tuple[str, ...]) -> dict:
            rows = [old.get(sid, {"status": "pending"}) for sid in old_ids]
            statuses = [row.get("status", "pending") for row in rows]
            if old_current in old_ids or "active" in statuses:
                status = "active"
            elif all(status in {"done", "skipped"} for status in statuses):
                status = "done"
            elif any(status in {"done", "skipped"} for status in statuses):
                status = "active"
            else:
                status = "pending"
            row = {"title": TITLES[new_id], "status": status}
            started = next((item.get("started") for item in rows if item.get("started")), None)
            ended = next((item.get("ended") for item in reversed(rows) if item.get("ended")), None)
            if started:
                row["started"] = started
            if ended and status == "done":
                row["ended"] = ended
            return row

        migrated = {
            sid: row
            for sid, row in old.items()
            if not sid.startswith("2.3.") and sid != "2.4"
        }
        migrated.update({
            "3.1": merged_qa("3.1", ("2.3.a", "2.3.b")),
            "3.2": merged_qa("3.2", ("2.3.c", "2.3.d")),
            "3.3": merged_qa("3.3", ("2.3.e",)),
            "3.4": merged_qa("3.4", ("2.4",)),
        })
        current_map = {
            "2.3.a": "3.1",
            "2.3.b": "3.1",
            "2.3.c": "3.2",
            "2.3.d": "3.2",
            "2.3.e": "3.3",
            "2.4": "3.4",
        }
        data["current"] = current_map.get(old_current, old_current)
        data["steps"] = steps = migrated
    if any(sid in steps for sid in RETIRED_22):
        old = dict(steps)
        old_current = data.get("current")

        def merged_build(new_id: str, old_ids: tuple[str, ...]) -> dict:
            rows = [old.get(sid, {"status": "pending"}) for sid in old_ids]
            statuses = [row.get("status", "pending") for row in rows]
            if old_current in old_ids or "active" in statuses:
                status = "active"
            elif all(status in {"done", "skipped"} for status in statuses):
                status = "done"
            elif any(status in {"done", "skipped"} for status in statuses):
                status = "active"
            else:
                status = "pending"
            row = {"title": TITLES[new_id], "status": status}
            started = next((item.get("started") for item in rows if item.get("started")), None)
            ended = next((item.get("ended") for item in reversed(rows) if item.get("ended")), None)
            if started:
                row["started"] = started
            if ended and status == "done":
                row["ended"] = ended
            return row

        migrated = {sid: row for sid, row in old.items() if sid not in RETIRED_22}
        author = dict(old.get("2.1") or {"status": "pending"})
        author_status = author.get("status", "pending")
        dump_rows = [old.get(sid, {"status": "pending"}) for sid in ("2.2.a", "2.2.b")]
        dump_statuses = [row.get("status", "pending") for row in dump_rows]
        if author_status == "pending" and any(status in {"done", "active", "skipped"} for status in dump_statuses):
            migrated["2.1"] = merged_build("2.1", ("2.1", "2.2.a", "2.2.b"))
        else:
            author["title"] = TITLES["2.1"]
            migrated["2.1"] = author
        migrated["2.3"] = merged_build("2.3", ("2.2.c", "2.2.d"))
        migrated["2.4"] = merged_build("2.4", ("2.2.e",))
        current_map = {
            "2.2.a": "2.1",
            "2.2.b": "2.1",
            "2.2.c": "2.3",
            "2.2.d": "2.3",
            "2.2.e": "2.4",
        }
        data["current"] = current_map.get(old_current, old_current)
        data["steps"] = steps = migrated
    if "2.1.ds" in steps:
        old = dict(steps)
        old_current = data.get("current")
        migrated = {sid: row for sid, row in old.items() if sid != "2.1.ds"}
        ds = dict(old.get("2.1.ds") or {"status": "pending"})
        validate = dict(old.get("2.2") or {"status": "pending"})
        human = dict(old.get("2.3") or {"status": "pending"})
        ds["title"] = TITLES["2.2"]
        validate["title"] = TITLES["2.3"]
        human["title"] = TITLES["2.4"]
        migrated["2.2"] = ds
        migrated["2.3"] = validate
        migrated["2.4"] = human
        current_map = {"2.1.ds": "2.2", "2.2": "2.3", "2.3": "2.4"}
        data["current"] = current_map.get(old_current, old_current)
        data["steps"] = steps = migrated
    for sid, title in STEPS:
        row = steps.setdefault(sid, {"title": title, "status": "pending"})
        row["title"] = title
    steps.pop("1.55", None)
    for sid in RETIRED_22:
        steps.pop(sid, None)
    if data.get("current") in {"1.55", *RETIRED_22}:
        data["current"] = None if data.get("current") == "1.55" else data.get("current")
    return data


def save_progress(
    root: Path,
    data: dict,
    expected_revision: int | None = None,
    *,
    force: bool = False,
) -> int:
    """Atomically save a new controller revision.

    Callers normally pass a freshly loaded document, so its embedded revision
    becomes the compare-and-swap value. `force` is reserved for `start`, which
    deliberately begins a completely new run.
    """
    path = progress_path(root)
    actual = 0
    if path.is_file():
        try:
            actual = _revision(json.loads(path.read_text()).get("revision"))
        except (OSError, ValueError, json.JSONDecodeError, AttributeError):
            actual = 0
    expected = _revision(data.get("revision")) if expected_revision is None else expected_revision
    if not force and expected != actual:
        raise ProgressConflict(_progress_conflict(expected, actual))
    refresh_timing(data)
    data["updated"] = now_iso()
    data["revision"] = actual + 1
    qa_dir(root).mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=".pipeline-progress-", delete=False
    ) as tmp:
        tmp.write(json.dumps(data, indent=2) + "\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)
    return data["revision"]


def claim_controller(root: Path, owner: str, expected_revision: int) -> int:
    """Claim the sole mutation lease for a run using a progress CAS revision."""
    owner = owner.strip()
    if not owner:
        print("FAIL: controller owner is required.", file=sys.stderr)
        return 2
    data = load_progress(root)
    actual = _revision(data.get("revision"))
    if expected_revision != actual:
        print(_progress_conflict(expected_revision, actual), file=sys.stderr)
        return 2
    controller = data.get("controller")
    if isinstance(controller, dict) and controller.get("owner") not in {None, "", owner}:
        print(f"FAIL: controller lease belongs to {controller.get('owner')!r}.", file=sys.stderr)
        return 2
    data["controller"] = {"owner": owner, "status": "active", "claimedAt": now_iso()}
    try:
        revision = save_progress(root, data, expected_revision)
    except ProgressConflict as exc:
        print(str(exc), file=sys.stderr)
        return 2
    lease = controller_lease_path(root)
    lease.parent.mkdir(parents=True, exist_ok=True)
    lease.write_text(
        json.dumps({"role": "controller", "owner": owner, "status": "active", "revision": revision}, indent=2)
        + "\n"
    )
    print(f"controller claimed → {owner} @ revision {revision}")
    return 0


def release_controller(root: Path, owner: str, expected_revision: int) -> int:
    """Release the controller lease after all reviewer waves have settled."""
    data = load_progress(root)
    actual = _revision(data.get("revision"))
    if expected_revision != actual:
        print(_progress_conflict(expected_revision, actual), file=sys.stderr)
        return 2
    controller = data.get("controller")
    if not isinstance(controller, dict) or controller.get("owner") != owner:
        print("FAIL: only the active controller may release this lease.", file=sys.stderr)
        return 2
    if active_reviewer_leases(root):
        print("FAIL: cannot release the controller while reviewer leases are active.", file=sys.stderr)
        return 2
    data.pop("controller", None)
    try:
        save_progress(root, data, expected_revision)
    except ProgressConflict as exc:
        print(str(exc), file=sys.stderr)
        return 2
    controller_lease_path(root).unlink(missing_ok=True)
    print(f"controller released → {owner}")
    return 0


def counts(data: dict, root: Path | None = None) -> tuple[int, int, str | None]:
    ids = counted_step_ids(root, data)
    done = sum(1 for sid in ids if data["steps"][sid]["status"] in {"done", "skipped"})
    current = next((sid for sid in STEP_IDS if data["steps"][sid]["status"] == "active"), None)
    return done, len(ids), current


def next_pending_step(data: dict, root: Path | None = None) -> str | None:
    walk = counted_step_ids(root, data)
    return next(
        (sid for sid in walk if data["steps"][sid]["status"] == "pending"),
        None,
    )


def last_signed_step(data: dict, root: Path | None = None) -> str | None:
    walk = counted_step_ids(root, data)
    signed = [sid for sid in walk if data["steps"][sid]["status"] in {"done", "skipped"}]
    return signed[-1] if signed else None


def hud_label(data: dict, root: Path | None = None) -> str:
    """Active step, else the next pending step, else Done. Never a vague Ready."""
    _, _, current = counts(data, root)
    if current:
        return f"▶ {current}  {TITLES[current]}"
    if run_is_complete(data, root):
        return "Done"
    nxt = next_pending_step(data, root)
    if nxt:
        return f"NEXT  {nxt}  {TITLES[nxt]}"
    return "Ready"


def here_next_copy(data: dict, root: Path | None = None) -> tuple[str, str]:
    """Board Here / Next lines. After 2.4 done this is signed 2.4 → 3.1 polish."""
    _, _, current = counts(data, root)
    complete = run_is_complete(data, root)
    nxt = next_pending_step(data, root)
    signed = last_signed_step(data, root)

    def titled(sid: str) -> str:
        return f"{sid}  {TITLES[sid]}"

    def next_line(sid: str) -> str:
        extra = SESSION_YIELD.get(sid, "not started")
        return f"{titled(sid)}  ·  {extra}"

    if current:
        here = f"{titled(current)}  ·  in progress"
        if nxt:
            return here, next_line(nxt)
        return here, "sign off this step"
    if complete:
        here = f"{titled(signed)}  ·  signed" if signed else "Run complete"
        return here, "Run complete"
    here = f"{titled(signed)}  ·  signed" if signed else "Run not started"
    if nxt:
        return here, next_line(nxt)
    return here, "Ready"


def ensure_refresh(html: str) -> str:
    if REFRESH_RE.search(html):
        return REFRESH_RE.sub("\n" + REFRESH + "\n", html, count=1)
    return html.replace("<head>", "<head>\n" + REFRESH, 1)


def stamp_run_state(html: str, done: bool, *, yielding: bool = False) -> str:
    html = re.sub(r'(<body)\s+data-run="[^"]*"', r"\1", html, count=1)
    if done:
        html = html.replace("<body", '<body data-run="done"', 1)
        return REFRESH_RE.sub("\n", html, count=1)
    if yielding:
        html = html.replace("<body", '<body data-run="yield"', 1)
    return ensure_refresh(html)


def timeline_display_status(data: dict, sid: str, root: Path | None = None) -> str:
    """Board-only status: first pending step is up-next; JSON stays pending/active/done/skipped."""
    raw = data["steps"].get(sid, {}).get("status", "pending")
    if raw != "pending":
        return raw
    walk = counted_step_ids(root, data)
    first_pending = next(
        (step for step in walk if data["steps"][step]["status"] == "pending"),
        None,
    )
    return "up-next" if sid == first_pending else "pending"


def spine_status(data: dict, group: str) -> str:
    statuses = [data["steps"][sid]["status"] for sid in SPINE_GROUPS[group]]
    if all(status in {"done", "skipped"} for status in statuses):
        return "done"
    if any(status in {"active", "done", "skipped"} for status in statuses):
        return "active"
    return "pending"


def capture_tool_board_url(root: Path | None) -> str:
    """Stamped Capture Tool URL, or empty until Paper + the source URL exist."""
    if root is None:
        return ""
    try:
        return build_capture_tool_page_url(root)
    except ValueError:
        return ""


def capture_buttons_open(data: dict | None) -> bool:
    """Copy / Open exist only while the human is on step 1.4."""
    if not data:
        return False
    return (data.get("steps") or {}).get("1.4", {}).get("status") == "active"


def stamp_capture_pull(html: str, root: Path | None, data: dict | None = None) -> str:
    """Stash the pull URL once Paper exists. Reveal Copy / Open only on active 1.4."""
    url = capture_tool_board_url(root)
    show = bool(url) and capture_buttons_open(data)
    state = "ready" if show else ("held" if url else "waiting")
    html = re.sub(
        r'(data-pipeline-capture)(?:\s+data-state="[^"]*")?',
        lambda m: f'{m.group(1)} data-state="{state}"',
        html,
        count=1,
    )
    safe = html_escape(url, quote=True) if url else ""
    html = re.sub(
        r'(<a[^>]*data-pipeline-capture-url[^>]*href=")[^"]*(")',
        lambda m: m.group(1) + safe + m.group(2),
        html,
        count=1,
    )
    html = re.sub(
        r'(<a[^>]*data-pipeline-capture-url[^>]*>)(.*?)(</a>)',
        lambda m: m.group(1) + safe + m.group(3),
        html,
        count=1,
        flags=re.S,
    )

    def copy_button(match: re.Match) -> str:
        tag = re.sub(r"\s+disabled(?:=\"[^\"]*\")?", "", match.group(1))
        if not show:
            tag += " disabled"
        return tag + match.group(2)

    html = re.sub(
        r"(<button\b[^>]*data-pipeline-capture-(?:copy|open)[^>]*)(>)",
        copy_button,
        html,
    )
    return html


def stamp_run_mode(html: str, root: Path | None) -> str:
    """Board reflects the intake: title badge + which rows are human stops.

    data-mode on <body>: full | auto | fast. CSS hides the 1.4 / 2.4 grid rows
    and timeline items when checkpoints are automatic, and relabels the 1.3 /
    2.1 rows as skipped on a fast run. 3.4 is never touched — it is always a
    human stop. Counts stay honest: auto-accepted steps are still marked done.
    """
    config = run_config.load(root) if root is not None else run_config.default_config()
    fast = config.get("speed") == "fast"
    auto = config.get("checkpoints") == "auto"
    mode = "fast" if fast else ("auto" if auto else "full")
    html = re.sub(r'(<body)(\s+data-mode="[^"]*")?', r"\1", html, count=1)
    if mode != "full":
        html = html.replace("<body", f'<body data-mode="{mode}"', 1)
    # Per-row flags. Auto-accepting checkpoints hide; fast-skipped steps strike through.
    flags: dict[str, str] = {}
    if auto:
        flags.update({sid: "auto" for sid in run_config.AUTO_ACCEPTABLE if run_config.auto_accepts(root, sid)})
    if fast:
        flags.update({"1.3": "skipped", "2.1": "skipped"})
    if config.get("adopt"):
        flags["1.3"] = "skipped"
        for sid in ("2.1", "2.2", "2.3", "2.4"):
            flags[sid] = "off"
    assert "3.4" not in flags
    def flag_rows(m: re.Match) -> str:
        tag, attr, sid = m.group(1), m.group(2), m.group(3)
        flag = flags.get(sid)
        return f'{tag} {attr}="{sid}"' + (f' data-run-step="{flag}"' if flag else "")
    html = re.sub(
        r'(<article class="row[^"]*")\s+(data-step)="([^"]+)"(?:\s+data-run-step="[^"]*")?',
        flag_rows, html)
    html = re.sub(
        r'(<article class="timeline-item")\s+(data-progress-step)="([^"]+)"(?:\s+data-run-step="[^"]*")?',
        flag_rows, html)
    if config.get("adopt"):
        html = re.sub(
            r'<section class="card"(?: data-phase-state="off")?>\s*'
            r'(<div class="card-head"><span class="id">2</span>)',
            r'<section class="card" data-phase-state="off">\1',
            html,
            count=1,
        )
        html = re.sub(
            r'(data-step="4\.3"[^>]*>.*?<h4>)(.*?)(</h4>)',
            r"\1Author missing layouts\3",
            html,
            count=1,
            flags=re.S,
        )
        html = re.sub(
            r'(data-step="3\.2"[^>]*>.*?<h4>)(.*?)(</h4>)',
            r"\1A11y only\3",
            html,
            count=1,
            flags=re.S,
        )
    if fast:
        widths = "/".join(str(w) for w in config.get("widths") or [])
        badge = f'<span class="run-mode run-mode-fast">Fast Run</span>'
        if config.get("adopt"):
            sub = f"{widths} · no Design Library · Phase 4 required · stop at 4.4 · Phase 2 off · source-html is the ship"
        else:
            sub = f"{widths} · no Design Library · 3.4 is the only stop"
    elif config.get("adopt"):
        badge = '<span class="run-mode run-mode-adopt">Adopt</span>'
        sub = "Phase 2 off · source-html is the ship · Phase 4 required · stop at 4.4"
    elif auto:
        badge = '<span class="run-mode run-mode-auto">Auto Run</span>'
        sub = "1.4 / 2.4 auto-accept · 3.4 is the only stop"
    else:
        badge, sub = "", ""
    html = re.sub(
        r'(<h1 class="run-title">.*?<span>Run</span>)(<span class="run-mode[^"]*">[^<]*</span>)?(</h1>)',
        lambda m: m.group(1) + badge + m.group(3),
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'(<p class="run-mode-note"[^>]*>)(.*?)(</p>)',
        lambda m: m.group(1) + sub + m.group(3),
        html,
        count=1,
        flags=re.S,
    )
    return html


def step_time_copy(row: dict, *, long: bool) -> str:
    """Board copy for one step. Grid rows get the short form, timeline the long one."""
    status = row.get("status", "pending")
    if status in {"done", "skipped"}:
        dur = row.get("durationSeconds")
        took = fmt_duration(dur) if dur is not None else None
        if not long:
            if took is None:
                return fmt_clock(row.get("ended"), with_date=False) if row.get("ended") else ""
            return took + ("*" if row.get("startedInferred") else "")
        verb = "Skipped" if status == "skipped" else "Finished"
        line = f"{verb} {fmt_clock(row.get('ended'))}" if row.get("ended") else verb
        if took is not None:
            line += f" · took {took}"
            if row.get("startedInferred"):
                line += " (start inferred)"
        return line
    if status == "active" and row.get("started"):
        if not long:
            return "running"
        return f"Started {fmt_clock(row.get('started'))} · running"
    return ""


def stamp_timing(html: str, data: dict, root: Path | None = None) -> str:
    timing = refresh_timing(data)
    steps = data.get("steps") or {}

    def step_sub(m: re.Match) -> str:
        tag, attrs, sid = m.group(1), m.group(2), m.group(3)
        long = "timeline-time" in attrs
        return f"<{tag}{attrs}data-step-time=\"{sid}\">{step_time_copy(steps.get(sid) or {}, long=long)}</{tag}>"

    html = re.sub(
        r'<(span|p)((?:\s[^>]*?)?\s)data-step-time="([^"]+)">.*?</\1>',
        step_sub,
        html,
        flags=re.S,
    )

    def phase_sub(m: re.Match) -> str:
        secs = timing["phases"].get(m.group(2))
        copy = fmt_duration(secs) if secs else ""
        return f"{m.group(1)}{copy}</span>"

    html = re.sub(
        r'(<span class="card-time" data-phase-time="(\d)">).*?</span>',
        phase_sub,
        html,
        flags=re.S,
    )

    def phase_agents_sub(m: re.Match) -> str:
        phase = m.group(2)
        copy = phase_agent_copy(timing.get("phaseAgents", {}).get(phase), timing["phases"].get(phase))
        return f"{m.group(1)}{copy}</p>"

    html = re.sub(
        r'(<p class="card-agents" data-phase-agents="(\d)">).*?</p>',
        phase_agents_sub,
        html,
        flags=re.S,
    )

    session = current_session(data)
    html = re.sub(
        r'(<span class="hud-agent" data-pipeline-agent[^>]*>).*?</span>',
        lambda m: m.group(1) + agent_label(session.get("agent"), session.get("model")) + "</span>",
        html,
        count=1,
        flags=re.S,
    )
    total = timing["totalSeconds"]
    if total or timing["timedSteps"]:
        label = f"total {fmt_duration(total)}"
        if timing["humanSeconds"]:
            label += f" · agent {fmt_duration(timing['agentSeconds'])}"
        if timing["untimedSteps"]:
            label += f" · {timing['untimedSteps']} untimed"
    else:
        label = ""
    html = re.sub(
        r'(<span class="hud-time" data-pipeline-duration[^>]*>).*?</span>',
        lambda m: m.group(1) + label + "</span>",
        html,
        count=1,
        flags=re.S,
    )
    return html


def stamp_html(html: str, data: dict, root: Path | None = None) -> str:
    html = stamp_timing(html, data, root)
    done, total, current = counts(data, root)
    pct = round(100 * done / total) if total else 0
    complete = run_is_complete(data, root)
    label = hud_label(data, root)
    here, nxt = here_next_copy(data, root)
    html = stamp_run_state(html, complete, yielding=not complete and current is None)
    html = stamp_run_mode(html, root)
    html = re.sub(
        r'<article class="row([^"]*)" data-step="([^"]+)"(?: data-status="[^"]*")?',
        lambda m: (
            f'<article class="row{m.group(1) or ""}" data-step="{m.group(2)}" '
            f'data-status="{data["steps"].get(m.group(2), {}).get("status", "pending")}"'
        ),
        html,
    )
    html = re.sub(
        r'(<article class="timeline-item" data-progress-step="([^"]+)")(?: data-status="[^"]*")?(?: aria-disabled="[^"]*")?',
        lambda m: (
            lambda status: (
                f'{m.group(1)} data-status="{status}"'
                + (' aria-disabled="true"' if status in {"pending", "up-next", "skipped"} else "")
            )
        )(timeline_display_status(data, m.group(2), root)),
        html,
    )
    html = re.sub(
        r'<li data-spine="([^"]+)"(?: data-status="[^"]*")?',
        lambda m: f'<li data-spine="{m.group(1)}" data-status="{spine_status(data, m.group(1))}"',
        html,
    )
    html = re.sub(
        r"(<[^>]*data-pipeline-current[^>]*>)(.*?)(</[^>]+>)",
        lambda m: m.group(1) + label + m.group(3),
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r"(<[^>]*data-pipeline-count[^>]*>)(.*?)(</[^>]+>)",
        lambda m: m.group(1) + f"{done} / {total}" + m.group(3),
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'(data-pipeline-bar style=")--pct:[^"]*(")',
        lambda m: m.group(1) + f"--pct:{pct}%" + m.group(2),
        html,
        count=1,
    )
    html = re.sub(
        r'(<div class="here-next"[^>]*data-pipeline-here-next)(?:\s+hidden)?',
        r"\1",
        html,
        count=1,
    )
    html = re.sub(
        r"(<span[^>]*data-pipeline-here>)(.*?)(</span>)",
        lambda m: m.group(1) + here + m.group(3),
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r"(<span[^>]*data-pipeline-next>)(.*?)(</span>)",
        lambda m: m.group(1) + nxt + m.group(3),
        html,
        count=1,
        flags=re.S,
    )
    return stamp_capture_pull(html, root, data)


def run_is_complete(data: dict, root: Path | None = None) -> bool:
    required_done = all(
        data["steps"][sid]["status"] == "done" for sid in REQUIRED_STEPS
    )
    if not required_done:
        return False
    if root is not None and phase4_skipped(root):
        return True
    phase4_closed = data["steps"]["4.4"]["status"] in {"done", "skipped"}
    phase5_closed = data["steps"]["5.6"]["status"] in {"done", "skipped"}
    if root is not None and phase4_opted(root):
        if not phase4_closed:
            return False
        if phase5_skipped(root):
            return True
        if phase5_opted(root):
            return phase5_closed
        return False
    if phase4_closed:
        if root is not None and phase5_skipped(root):
            return True
        if root is not None and phase5_opted(root):
            return phase5_closed
        return phase5_closed or all(
            data["steps"][sid]["status"] == "pending" for sid in PHASE5_STEPS
        )
    return all(data["steps"][sid]["status"] == "pending" for sid in OPTIONAL_STEPS)


def board_is_finished(root: Path) -> bool:
    """True when the live board was stamped after every step 1.1–3.4."""
    path = live_html(root)
    if not path.is_file():
        return False
    try:
        return 'data-run="done"' in path.read_text()
    except OSError:
        return False


def run_may_tidy(root: Path) -> bool:
    """Tidy only after the entire 1.1–3.4 flow is finished.

    After the first sweep, qa/pipeline-progress.json is gone. A finished
    pipeline.html is then the receipt that a later finish may re-sweep.
    """
    progress = progress_path(root)
    if progress.is_file():
        try:
            return run_is_complete(load_progress(root), root)
        except (OSError, json.JSONDecodeError, KeyError):
            return False
    return board_is_finished(root)


def tidy_completed_run(root: Path) -> list[str]:
    """Drop QA shots, capture, scrape, and run files after 3.4.

    Keep rebuild/ and the finished pipeline.html. NEXT.html is retired.
    """
    root = root.resolve()
    if is_spec_repo(root):
        raise SystemExit("FAIL: do not tidy the web2html spec repo.")
    if not run_may_tidy(root):
        raise SystemExit(
            "FAIL: tidy only after 1.1–3.4 and Phase 4/5 is skipped or the last opted phase is done."
        )
    removed: list[str] = []

    def drop(path: Path) -> None:
        if not path.exists():
            return
        rel = str(path.relative_to(root))
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(rel)

    for name in NOISE_DIRS:
        drop(root / name)
    rebuild = root / "rebuild"
    if rebuild.is_dir():
        for name in NOISE_REBUILD_FILES:
            drop(rebuild / name)
        for pattern in NOISE_REBUILD_GLOBS:
            for hit in sorted(rebuild.glob(pattern)):
                drop(hit)
    # Nothing but the ship folder and the finished board survive at the root
    # (dotfiles stay — .git, .DS_Store).
    for entry in sorted(root.iterdir()):
        if entry.name.startswith(".") or entry.name in KEEP_ROOT:
            continue
        drop(entry)
    drop_next_doc(root)
    return removed


def drop_next_doc(root: Path) -> list[str]:
    """NEXT.html is retired. Delete leftover copies at the root and in rebuild/."""
    root = root.resolve()
    removed: list[str] = []
    for path in (root / NEXT_NAME, root / "rebuild" / NEXT_NAME):
        if not path.is_file():
            continue
        path.unlink()
        removed.append(str(path.relative_to(root)))
    return removed


def write_live(root: Path, data: dict, source: Path | None = None) -> Path:
    if is_spec_repo(root):
        raise SystemExit("FAIL: do not stamp the web2html spec repo. Pass the template project folder.")
    qa_dir(root).mkdir(parents=True, exist_ok=True)
    src = source or live_template()
    dest = live_html(root)
    dest.write_text(stamp_html(src.read_text(), data, root))
    drop_next_doc(root)
    return dest


def capture_tool_home() -> Path:
    override = os.environ.get("PAPER_CAPTURE_HOME", "").strip()
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Paper Capture Tool"
    return Path.home() / ".paper-capture-tool"


def paper_source_url(paper: dict) -> str:
    """The LIVE site URL the Capture Tool must open.

    `create-paper-file.mjs` writes `url` = the Paper file URL and `sourceUrl` =
    the site; `capture-session.mjs` later overwrites `url` with the site. A run
    that stopped between the two left `url` on app.paper.design, so `open-capture`
    stamped the wrong page and the content script never ran (Pitfall #217).
    """
    source = str(paper.get("sourceUrl") or "").strip()
    url = str(paper.get("url") or "").strip()
    if url and "app.paper.design" not in urlparse(url).netloc:
        return url
    return source or ""


def _is_temp_root(root: Path) -> bool:
    """Test fixtures and scratch runs live under the OS temp dir.

    They must never overwrite the ONE global `active-session.json` the Chrome
    extension reads — a stale tmp path there is why a fresh panel prefilled a
    dead project folder (Pitfall #217). `PAPER_CAPTURE_HOME` opts back in.
    """
    if os.environ.get("PAPER_CAPTURE_HOME", "").strip():
        return False
    try:
        real = str(root.resolve())
        tmp = str(Path(tempfile.gettempdir()).resolve())
    except OSError:
        return False
    return real.startswith(tmp) or real.startswith("/tmp/") or real.startswith("/private/tmp/")


def write_capture_tool_session(root: Path) -> Path | None:
    """Point the Capture Tool extension at this run's Paper file + project folder."""
    root = root.resolve()
    paper = read_paper_file(root)
    payload = {
        "paperFileId": str(paper.get("fileId") or paper.get("paperFileId") or "").strip(),
        "projectRoot": str(root),
        "url": paper_source_url(paper),
        "paperEndpoint": str(paper.get("paperEndpoint") or "").strip(),
        "updatedAt": now_iso(),
    }
    (root / "qa").mkdir(parents=True, exist_ok=True)
    (root / "qa" / "capture-tool-session.json").write_text(json.dumps(payload, indent=2) + "\n")
    if _is_temp_root(root):
        return None
    dest_dir = capture_tool_home()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "active-session.json"
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    return dest


def read_paper_file(root: Path) -> dict:
    paper_path = root.resolve() / "qa" / "paper-file.json"
    if not paper_path.is_file():
        return {}
    try:
        loaded = json.loads(paper_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def capture_tool_open_errors(root: Path) -> list[str]:
    paper = read_paper_file(root)
    errors: list[str] = []
    if not str(paper.get("fileId") or paper.get("paperFileId") or "").strip():
        errors.append("qa/paper-file.json is missing fileId (1.2 must write it)")
    if not paper_source_url(paper):
        errors.append("qa/paper-file.json is missing the source url (url / sourceUrl)")
    return errors


def paper_app_url(paper: dict) -> str:
    file_id = str(paper.get("fileId") or paper.get("paperFileId") or "").strip()
    return f"https://app.paper.design/file/{file_id}" if file_id else ""


PAPER_REVIEW_TEMPLATE = """# Paper human review (1.4)

Walk:
- home-desktop / home-768 / home-390
- FRAME Navigation (1600 / 768 / 390)
- FRAME Buttons (1.3 specimens)
- FRAME Components (1.3 specimens)
- Design Library

Pin comments on anything wrong. Capture Tool is optional leftover live hover
(`pipeline-progress.py open-capture`).
"""


def write_paper_human_review(root: Path) -> Path:
    dest = root.resolve() / "qa" / "paper-human-review.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.is_file():
        dest.write_text(PAPER_REVIEW_TEMPLATE, encoding="utf-8")
    return dest


def print_14_hard_stop(root: Path, *, paper_opened: bool = True, capture_url: str = "") -> None:
    """Always print copyable Paper URL at the 1.4 stop. Capture Tool is optional."""
    root = root.resolve()
    paper = read_paper_file(root)
    if not capture_url:
        try:
            capture_url = build_capture_tool_page_url(root, paper)
        except ValueError:
            capture_url = ""
    paper_url = paper_app_url(paper)
    print("")
    print("1.4 HARD STOP — copy these if Paper did not come forward:")
    if paper_url:
        print("Paper file")
        print(paper_url)
    if not paper_opened:
        print("Paper did not open. Open the Paper file URL, or open the Paper app.")
    print("")
    print("Walk 1600 / 768 / 390, FRAME Navigation, FRAME Buttons, FRAME Components, Design Library.")
    print("  Pin comments on anything wrong — 2.0 will not start until those threads are handled.")
    print("Capture Tool: the browser was opened on the stamped source URL (side panel reads")
    print("  paperFileId + projectRoot off that tab). Use it for leftover live hover only;")
    print("  it is not a 1.4 done-gate. Re-open / re-check the bridge:")
    print("  python3 $SKILLS/web2html/scripts/pipeline-progress.py open-capture <project>")
    print("  python3 $SKILLS/web2html/scripts/pipeline-progress.py capture-doctor <project>")
    if capture_url:
        print("Capture Tool URL")
        print(capture_url)
    print("Question modal — fire this harness's native choice / question tool:")
    print("  1. Done & continue to next step")
    print("  3. Provide hand-off prompt to start fresh session")
    print("No native tool? Print those labels and wait. Dismissed card → stay stopped.")
    print("")


def print_24_hard_stop(root: Path) -> None:
    """TAGS review. Continue starts Session 3 polish. Polish has not run."""
    ship = root.resolve() / "rebuild" / "index.html"
    print("")
    print("2.4 HARD STOP — TAGS review. Session 3 polish has not started.")
    print("YOU ARE HERE  2.4 Sign-off → 3.0 polish · in progress")
    print("NEXT          After Continue: Session 3 polish starting at 3.1")
    print("NOT YET       index-polish.html — created when 3.1 starts as an")
    print("               unpolished copy of the lock. Not polished until 3.1–3.3 run.")
    if ship.is_file():
        print(f"Ship lock     {ship.as_uri()}")
    print("Question modal — fire this harness's native choice / question tool:")
    print("  1. Continue to 3.0 polish (3.1–3.4)")
    print("The resume token is the word Continue.")
    print("Do not start 3.1 until Continue. Do not treat an existing")
    print("index-polish.html as finished polish.")
    print("")


def build_capture_tool_page_url(root: Path, paper: dict | None = None) -> str:
    """Stamp the live source URL with this run's Paper file and project folder."""
    root = root.resolve()
    paper = read_paper_file(root) if paper is None else paper
    file_id = str(paper.get("fileId") or paper.get("paperFileId") or "").strip()
    base = paper_source_url(paper)
    if not file_id or not base:
        raise ValueError("qa/paper-file.json must include fileId and a source url (url / sourceUrl)")
    parsed = urlparse(base)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["paperFileId"] = file_id
    query["projectRoot"] = str(root)
    stamped = urlencode(query)
    hashed = urlencode({"paperFileId": file_id, "projectRoot": str(root)})
    return urlunparse(parsed._replace(query=stamped, fragment=hashed))


CAPTURE_HOST_NAME = "com.kreativepro.paper_capture"
CAPTURE_EXTENSION_ID = "ecicfkapebfbpdgfaiadgfcghkpgmbem"
# (label, macOS app name, NativeMessagingHosts dir relative to ~/Library/Application Support)
CHROMIUM_BROWSERS = (
    ("Google Chrome", "Google Chrome", "Google/Chrome/NativeMessagingHosts"),
    ("Brave", "Brave Browser", "BraveSoftware/Brave-Browser/NativeMessagingHosts"),
    ("Chromium", "Chromium", "Chromium/NativeMessagingHosts"),
    ("Microsoft Edge", "Microsoft Edge", "Microsoft Edge/NativeMessagingHosts"),
    ("Arc", "Arc", "Arc/User Data/NativeMessagingHosts"),
)


def capture_extension_dir() -> Path:
    """The unpacked extension folder in this checkout (hover-reel package)."""
    for name in ("1.3 hover-reel", "hover-reel"):
        cand = skill_root() / name / "capture-extension"
        if (cand / "manifest.json").is_file():
            return cand
    return skill_root() / "1.3 hover-reel" / "capture-extension"


def capture_host_installer() -> Path:
    return capture_extension_dir() / "install-native-host.command"


def _installed_browser_apps() -> list[tuple[str, str, Path]]:
    """Chromium-family browsers present on this Mac, as (label, app, NativeMessagingHosts dir)."""
    if sys.platform != "darwin":
        return []
    out: list[tuple[str, str, Path]] = []
    support = Path.home() / "Library" / "Application Support"
    for label, app, rel in CHROMIUM_BROWSERS:
        if (Path("/Applications") / f"{app}.app").exists() or (Path.home() / "Applications" / f"{app}.app").exists():
            out.append((label, app, support / rel))
    return out


def preferred_capture_browser() -> str:
    """The macOS app name to open the Capture Tool in. Chrome first, else the first installed Chromium browser."""
    override = os.environ.get("PAPER_CAPTURE_BROWSER", "").strip()
    if override:
        return override
    apps = _installed_browser_apps()
    return apps[0][1] if apps else "Google Chrome"


def _read_host_version(path: Path) -> str:
    try:
        m = re.search(r'HOST_VERSION\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"))
    except OSError:
        return ""
    return m.group(1) if m else ""


def capture_doctor(root: Path | None = None) -> dict:
    """Check the Capture Tool bridge this machine will actually talk to.

    Every FAIL here shows up in the side panel as OFFLINE (Pitfall #217). The
    doctor never fixes anything — it prints the one command that does.
    Returns {"ok": bool, "problems": [str], "fixes": [str], "notes": [str]}.
    """
    problems: list[str] = []
    fixes: list[str] = []
    notes: list[str] = []
    installer = capture_host_installer()
    install_cmd = f'sh "{installer}" --quiet' if installer.is_file() else "run install-native-host.command from hover-reel/capture-extension"

    if sys.platform != "darwin":
        notes.append(f"capture doctor: bridge checks are macOS-only (platform {sys.platform}).")
        return {"ok": True, "problems": problems, "fixes": fixes, "notes": notes}

    home = capture_tool_home()
    launcher = home / "run-paper-capture-host"
    host_copy = home / "host.mjs"
    apps = _installed_browser_apps()

    if not apps:
        problems.append("no Chromium-family browser found in /Applications (Chrome, Brave, Chromium, Edge, Arc)")
        fixes.append("install Google Chrome, then " + install_cmd)

    # 1. Native-messaging manifest per installed browser.
    for label, _app, nm_dir in apps:
        manifest = nm_dir / f"{CAPTURE_HOST_NAME}.json"
        if not manifest.is_file():
            problems.append(f"{label}: native host manifest missing ({manifest})")
            continue
        try:
            data = json.loads(manifest.read_text())
        except (OSError, json.JSONDecodeError):
            problems.append(f"{label}: native host manifest is not valid JSON ({manifest})")
            continue
        origins = data.get("allowed_origins") or []
        if f"chrome-extension://{CAPTURE_EXTENSION_ID}/" not in origins:
            problems.append(f"{label}: manifest does not allow extension {CAPTURE_EXTENSION_ID}")
        path = str(data.get("path") or "")
        if path and not Path(path).is_file():
            problems.append(f"{label}: manifest points at a missing launcher ({path})")

    # 2. Launcher + pinned node.
    if not launcher.is_file():
        problems.append(f"bridge launcher missing ({launcher})")
    else:
        try:
            text = launcher.read_text(encoding="utf-8")
        except OSError:
            text = ""
        m = re.search(r'exec\s+"([^"]+)"', text)
        node = m.group(1) if m else ""
        if not node:
            problems.append("bridge launcher does not exec a node binary")
        elif not (Path(node).is_file() and os.access(node, os.X_OK)):
            problems.append(f"bridge launcher pins a node that no longer exists ({node})")
        if not os.access(launcher, os.X_OK):
            problems.append(f"bridge launcher is not executable ({launcher})")

    # 3. Host copy vs repo.
    if not host_copy.is_file():
        problems.append(f"bridge host.mjs missing ({host_copy})")
    else:
        repo_host = capture_extension_dir() / "bridge" / "host.mjs"
        installed_v, repo_v = _read_host_version(host_copy), _read_host_version(repo_host)
        if repo_v and installed_v and installed_v != repo_v:
            problems.append(f"bridge host.mjs is stale (installed {installed_v}, repo {repo_v})")

    if problems:
        fixes.append(install_cmd)
        fixes.append("then fully quit and reopen the browser, and reload the unpacked extension at chrome://extensions")

    # 4. Active session points at THIS project.
    if root is not None:
        root = root.resolve()
        session_file = home / "active-session.json"
        try:
            session = json.loads(session_file.read_text()) if session_file.is_file() else {}
        except (OSError, json.JSONDecodeError):
            session = {}
        if str(session.get("projectRoot") or "") != str(root):
            notes.append(f"active-session.json pointed elsewhere; rewriting for {root}")
        if not str(session.get("paperFileId") or "").strip() and not str(read_paper_file(root).get("fileId") or "").strip():
            notes.append("no paperFileId yet — 1.2 writes qa/paper-file.json")

    return {"ok": not problems, "problems": problems, "fixes": fixes, "notes": notes}


def print_capture_doctor(report: dict) -> None:
    for note in report.get("notes", []):
        print(f"capture doctor: {note}")
    if report.get("ok"):
        print("capture doctor: OK — native bridge installed for every Chromium browser found.")
        return
    print("capture doctor: FAIL — the Capture Tool side panel will show OFFLINE (Pitfall #217):", file=sys.stderr)
    for p in report.get("problems", []):
        print(f"  - {p}", file=sys.stderr)
    if report.get("fixes"):
        print("  fix:", file=sys.stderr)
        for f in report["fixes"]:
            print(f"    {f}", file=sys.stderr)


def cmd_capture_doctor(root: Path | None) -> int:
    report = capture_doctor(root)
    print_capture_doctor(report)
    return 0 if report["ok"] else 2


def _open_in_browser(uri: str) -> bool:
    try:
        if sys.platform == "darwin":
            result = subprocess.run(["open", "-a", preferred_capture_browser(), uri], check=False)
        elif sys.platform.startswith("linux"):
            result = subprocess.run(["xdg-open", uri], check=False)
        else:
            return False
        return result.returncode == 0
    except OSError:
        return False


def open_capture_tool(root: Path, *, quiet_stop: bool = False) -> bool:
    """Open the Chromium browser on the stamped source URL (paperFileId + projectRoot).

    Called by `mark 1.4 active` (always) and by `open-capture` (re-open). The
    doctor runs first so an OFFLINE bridge is reported next to the URL instead
    of being discovered in the side panel.
    """
    root = root.resolve()
    errors = capture_tool_open_errors(root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        print(
            "FAIL: cannot open the Capture Tool without a 1.2 Paper receipt (Pitfall #149).",
            file=sys.stderr,
        )
        return False
    print_capture_doctor(capture_doctor(root))
    write_capture_tool_session(root)
    uri = build_capture_tool_page_url(root)
    opened = _open_in_browser(uri)
    if not quiet_stop:
        print_14_hard_stop(root, paper_opened=True, capture_url=uri)
    if not opened:
        print("FAIL: the browser did not open the stamped Capture Tool URL (Pitfall #149).", file=sys.stderr)
        print(f"Paste the Capture Tool URL into {preferred_capture_browser()}:", file=sys.stderr)
        print(f"  {uri}", file=sys.stderr)
        return False
    paper = read_paper_file(root)
    receipt = {
        "openedAt": now_iso(),
        "url": uri,
        "browser": preferred_capture_browser() if sys.platform == "darwin" else "xdg-open",
        "paperFileId": str(paper.get("fileId") or paper.get("paperFileId") or "").strip(),
        "projectRoot": str(root),
    }
    (root / "qa").mkdir(parents=True, exist_ok=True)
    (root / "qa" / "capture-tool-opened.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return True


def open_paper_for_review(root: Path) -> bool:
    """1.4 active: write the review note, open Paper, AND open the browser on the stamped source URL.

    The Paper receipt (fileId) is the gate. The browser open is forced but
    non-fatal: a failure prints the URL + doctor fixes and 1.4 still goes active
    (Pitfall #217).
    """
    root = root.resolve()
    paper = read_paper_file(root)
    file_id = str(paper.get("fileId") or paper.get("paperFileId") or "").strip()
    if not file_id:
        print("FAIL: qa/paper-file.json is missing fileId (1.2 must write it)", file=sys.stderr)
        print("FAIL: cannot open the 1.4 Paper checkpoint without a 1.2 receipt.", file=sys.stderr)
        return False
    write_paper_human_review(root)
    opened = False
    try:
        if sys.platform == "darwin":
            result = subprocess.run(["open", "-a", "Paper"], check=False)
            opened = result.returncode == 0
        elif sys.platform.startswith("linux"):
            uri = paper_app_url(paper)
            if uri:
                result = subprocess.run(["xdg-open", uri], check=False)
                opened = result.returncode == 0
    except OSError:
        opened = False
    capture_url = ""
    try:
        capture_url = build_capture_tool_page_url(root, paper)
    except ValueError:
        capture_url = ""
    if capture_url:
        open_capture_tool(root, quiet_stop=True)
    else:
        print("WARN: qa/paper-file.json has no source url — Capture Tool browser tab not opened.", file=sys.stderr)
    print_14_hard_stop(root, paper_opened=opened, capture_url=capture_url)
    return True


SESSION_TITLE = {
    1: "CAPTURE (1.1 \u2192 1.4)",
    2: "BUILD (2.1 \u2192 2.4)",
    3: "QA & POLISH (3.1 \u2192 3.4)",
}
SESSION_TIER = {
    1: "operator tier",
    2: "recommended strong tier \u2014 vision + long horizon. Run on whichever model the operator chose; never stop to ask for a switch.",
    3: "operator tier. Escalate to the build tier only where noted below.",
}


def _handoff_2_adopt(root: Path, paper: dict, board: str) -> str:
    file_id = paper.get("fileId") or paper.get("id") or ""
    file_url = paper.get("fileUrl") or (f"https://app.paper.design/file/{file_id}" if file_id else "")
    return f"""/web2html 3.0 — continue this run. Phase 2 is not applicable.

Project: {root}
Board:   {board}
Paper:   {file_url or "(qa/paper-file.json)"}

source-html/ is the ship. Do not create rebuild/. Do not author a homepage.
Resume at 3.1. Light polish only: accessibility attributes (alt, aria-*, role, lang, label for).
Do not edit source CSS, JS, classes, or copy. qa/source-fidelity.json is the lock.
Do not stop at 3.4 and do not ask finish vs Phase 4. Phase 4 is required.
Continue through 4.1–4.3 and stop at 4.4. Phase 4 authors only the empty CMS layouts from Paper screenshots.
"""


def _handoff_2(root: Path, paper: dict, board: str) -> str:
    return f"""web2html \u2014 SESSION 2 of 3 \u00b7 {SESSION_TITLE[2]}
Model: {SESSION_TIER[2]}

Project   {root}
Source    {paper.get('url') or '<source url>'}
Paper     {paper.get('fileId') or paper.get('paperFileId') or '<paperFileId>'}
Board     {board}

Session 1 is complete and human-signed:
  1.1 contract \u00b7 1.2 capture 1600/768/390 + Navigation
  1.3 Design Library + tokens + Buttons/Components \u00b7 1.4 Human checkpoint
Paper is the source of truth. Do not recapture, re-mine, or reopen any 1.x step.

First actions, in order:
  1. Load the web2html skill.
  2. python3 "$SKILLS/web2html/scripts/pipeline-progress.py" resume . \\
       --at 2.1 --owner session-2
     NOT `start` \u2014 start resets the board and quarantines the run.
  3. Read the 2.1 / 2.2 / 2.3 / 2.4 rows in references/pillars.md.
  4. node "$SKILLS/web2html/scripts/list-paper-comments.mjs"   -> exit 0 required.

Then: 2.1 emit Design System (tokens + rebuild/design-system.html) ->
2.2 author index-semantic.html from Paper using those tokens -> 2.3 section loop
(disk clips + index-raw; no Paper MCP), then 2.3 VALIDATE LOOK
(paper_23_validate.py --shoot-open, then MUST wave.py prepare/start/wait/apply;
controller records; <= 3 rounds per band, Pitfall #216 #221)
-> 2.4 Human checkpoint.
Do not stop after 2.1, after 2.2, or mid-2.3. Sign every
homepage section at 1600/768/390 in this session. The only stop is 2.4.

Fidelity lock: Paper desktop is gold. 2.1 tokens/classes as-is. No new
palette, fonts, or copy. Homepage only, file://. No get_jsx dump. No
skip-link. Aesthetic-risk OFF.
"""


def snapshot_fidelity_freeze(root: Path) -> Path | None:
    """Pin 2.4 ship type / library classes / section ids before 3.x."""
    from fidelity_freeze import freeze_path, snapshot

    if freeze_path(root).is_file():
        return freeze_path(root)
    if not (root / "rebuild" / "index.html").is_file():
        return None
    dest = snapshot(root)
    print(f"fidelity freeze snapshot → {dest}")
    return dest


def seed_22_index(root: Path) -> Path | None:
    """Copy the 2.2 first pass to rebuild/index.html. Never overwrite."""
    dest_rel = root / "rebuild" / "index.html"
    existed = dest_rel.is_file()
    dest = seed_index_html(root)
    if dest is not None and not existed:
        print(f"index seed → {dest}")
    return dest


def seed_32_button_hover(root: Path) -> dict:
    """Write rebuild/css/hover.css from 1.3 qa/button-hover.json. 3.2 active."""
    receipt = _apply_hover_css.apply_hover_css(root)
    applied = len(receipt.get("applied") or [])
    print(f"3.2 hover CSS → {applied} applied  qa/button-hover-css.json")
    return receipt


def hover_light_script() -> Path:
    """hover-reel/scripts/source-hover-light.mjs — prefixed checkout or installed name."""
    for name in ("1.3 hover-reel", "hover-reel"):
        candidate = skill_root() / name / "scripts" / "source-hover-light.mjs"
        if candidate.is_file():
            return candidate
    return skill_root() / "hover-reel" / "scripts" / "source-hover-light.mjs"


def seed_32_light_hover(root: Path) -> dict:
    """Fast run (no 1.3): mine source CSS :hover onto qa/button-hover.json.

    Runs the hover-reel light pass so apply_hover_css has the same receipt it
    would have had after 1.3. Never invents a hover (Pitfall #33).
    """
    script = hover_light_script()
    if not script.is_file():
        raise FileNotFoundError(f"missing {script} — fast-run hover needs hover-reel/scripts/source-hover-light.mjs")
    proc = subprocess.run(
        ["node", str(script), "--project", str(root.resolve())],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        detail = tail[-1] if tail else "no output"
        raise FileNotFoundError(f"source-hover-light.mjs failed: {detail}")
    receipt = _json_or_empty(proc.stdout)
    print(f"3.2 light hover (no 1.3) → {len(receipt.get('applied') or [])} applied  qa/button-hover.json")
    return receipt


def write_auto_accept_14(root: Path) -> Path:
    """checkpoints=auto: 1.4 self-accepts. Nothing is opened; the receipt says so."""
    dest = root / "qa" / "paper-human-review.md"
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        config = run_config.load(root)
        dest.write_text(
            "# 1.4 — Paper checkpoint · AUTO-ACCEPTED\n\n"
            f"- recorded: {now_iso()}\n"
            f"- run-config: checkpoints={config.get('checkpoints')} speed={config.get('speed')}\n"
            "- Paper and the Capture Tool tab were NOT opened — the intake chose automatic checkpoints.\n"
            "- Frames 1600 / 768 / 390, FRAME Navigation, Buttons, Components, Design Library were not\n"
            f"  walked by a human. {'4.4' if run_config.adopt_mode(root) else '3.4'} is the next human stop in this run.\n",
            encoding="utf-8",
        )
    print("1.4 auto-accepted (checkpoints=auto) → qa/paper-human-review.md · no Paper / browser opened")
    return dest


def write_auto_accept_24(root: Path) -> Path:
    """checkpoints=auto: 2.4 self-accepts once the 2.3 gate is green. TAGS Chrome is not opened."""
    from section_22_gate import gate_errors as section_errors

    errors = section_errors(root)
    if errors:
        # Do not pretend the build is approved while 2.3 is red.
        raise SystemExit(
            "FAIL: 2.4 auto-accept refused — 2.3 is still red:\n  - " + "\n  - ".join(errors[:6])
        )
    dest = root / "qa" / "build-checkpoint.md"
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            "# 2.4 — TAGS checkpoint · AUTO-ACCEPTED\n\n"
            f"- recorded: {now_iso()}\n"
            "- section_22_gate: green at every configured width (2.3 receipts + wave findings on disk).\n"
            "- TAGS Chrome review was NOT opened — the intake chose automatic checkpoints.\n"
            "- rebuild/index.html is the lock from here. 3.4 is the first human stop.\n",
            encoding="utf-8",
        )
    print("2.4 auto-accepted (checkpoints=auto) → qa/build-checkpoint.md · TAGS review not opened")
    return dest


def seed_32_nav_drawer(root: Path) -> dict:
    """Author a painted burger drawer on index-polish.html. 3.2 active."""
    receipt = _author_nav_drawer.author_nav_drawer(root)
    applied = len(receipt.get("applied") or [])
    print(f"3.2 burger drawer → {applied} applied  qa/nav-drawer.json")
    return receipt


def seed_32_faq(root: Path) -> dict:
    """Author FAQ accordion + scrape answers on index-polish.html. 3.2 active."""
    receipt = _author_faq.author_faq(root)
    applied = len(receipt.get("applied") or [])
    print(f"3.2 FAQ accordion → {applied} applied  qa/faq.json")
    return receipt


def seed_32_nav_dropdown(root: Path) -> dict:
    """Author nav dropdown panels from polish + scrape. 3.2 active."""
    receipt = _author_nav_dropdown.author_nav_dropdown(root)
    applied = len(receipt.get("applied") or [])
    print(f"3.2 nav dropdown → {applied} applied  qa/nav-dropdown.json")
    return receipt


def seed_24_polish(root: Path) -> Path | None:
    """Copy the 2.4 lock to rebuild/index-polish.html. Never overwrite.

    Call only when 3.x goes active. 2.4 done must not create this file —
    an unpolished copy on disk reads as polish already done (Pitfall #203).
    """
    existed = polish_path(root).is_file()
    dest = seed_index_polish(root)
    if dest is not None and not existed:
        print(f"index-polish seed → {dest}  (unpolished copy; 3.1–3.3 write here)")
    return dest


def _handoff_3(root: Path, paper: dict, board: str) -> str:
    ship = (root / "rebuild" / "index.html")
    return f"""web2html \u2014 SESSION 3 of 3 \u00b7 {SESSION_TITLE[3]}
Model: {SESSION_TIER[3]}

YOU ARE HERE  2.4 done \u00b7 homepage signed \u00b7 index.html frozen
NEXT          Session 3 polish starting at 3.1
              resume . --at 3.1 --owner session-3
NOT YET       index-polish.html \u2014 created when 3.1 starts as an unpolished
              copy of the lock. It is not polished until 3.1\u20133.3 run.

Project   {root}
Ship      {ship.as_uri() if ship.is_file() else ship}
Board     {board}

Sessions 1\u20132 are complete. The page is authored from Paper, token-bound,
section-validated at 1600/768/390, and human-approved at the 2.4 checkpoint.
Do not re-author the page. Do not revisit Paper geometry or the token set.
2.4 is the fidelity freeze (qa/fidelity-freeze-24.json). rebuild/index.html
is the lock. Do not mutate it (Pitfall #203). Do not change font-size,
Design Library class names, or signed section ids.

First actions, in order:
  1. Load the web2html skill.
  2. python3 "$SKILLS/web2html/scripts/pipeline-progress.py" resume . \\
       --at 3.1 --owner session-3
     That mark copies index.html \u2192 index-polish.html (unpolished).
  3. Read references/polish-visual-restore.md, then the 3.1 \u2013 3.4 rows in
     references/pillars.md.

Then: 3.1 a11y + contrast + anti-slop (Impeccable + Taste) on
      index-polish.html ->
      3.2 hover from 1.3 source CSS (apply-hover-css.py on index-polish.html)
      + burger open drawer (author-nav-drawer.py; never skip for Capture Tool)
      + FAQ accordion (author-faq.py; scrape answers, never skip empty Paper bodies)
      + nav dropdowns (author-nav-dropdown.py; never skip for Capture Tool)
      + guidelines a11y + mandatory GSAP in-view
      (inject-gsap-reveal.py on index-polish.html; never skip from 1.4)
      + companion receipts qa/web-design-guidelines.md,
      qa/find-animation-opportunities.md, qa/apple-design.md (Pitfall #215) ->
      3.3 scrape-only SEO + a11y labels (semantics_pass --freeze-structure
      on index-polish.html) ->
      3.4 compare index.html (2.4) vs index-polish.html (QA, outlines off;
      ?qa-outlines=tags turns them on). Marking 3.4 done promotes the polish
      file to index.html and archives index-raw / index-semantic / the 2.4 lock
      under rebuild/archive/ (Pitfall #223).

Receipts land in qa/polish-passes/ plus the three 3.2 companion .md files
in qa/. verify-polish-passes.py green before 3.4.
Escalate: if a fix would change layout, type size, library class names,
section order, or the colour system, stop and hand back to the build tier.
"""


def _handoff_5(root: Path, paper: dict, board: str) -> str:
    file_id = str(paper.get("fileId") or paper.get("paperFileId") or "").strip() or "(missing)"
    return f"""web2html — SESSION 5 of 5 · SITE → ASTRO (5.1 → 5.6)
Model: recommended strong tier — vision + long horizon. Run on whichever model the operator chose; never stop to ask for a switch.

Project   {root}
Paper     {file_id}
Board     {board}

Sessions 1–4 are complete. The homepage ship is rebuild/index.html (3.4
promoted the polish; outlines off unless ?qa-outlines=). Extra routes are
Paper pages on the home canvas. Do not recapture, re-mine, open a second
Design Library, or rewrite the homepage. 5.1 reads index.html when
index-polish.html has been archived.

First actions, in order:
  1. Load the web2html skill.
  2. python3 "$SKILLS/web2html/scripts/pipeline-progress.py" resume . \\
       --at 5.1 --owner session-5
     NOT `start` — start resets the board and quarantines the run.
  3. Read references/phase-5-astro.md and the 5.1–5.6 rows in pillars.md.

Then: 5.1 scaffold astro/ + pull Header / Footer / Paper components ONCE from
rebuild/index.html (the promoted polish) + convert the homepage to src/pages/index.astro ->
5.2 serial get_jsx dumps + at most two author workers, each writing ONLY the
<main> body of src/pages/{{slug}}.astro on that shared chrome ->
5.3 astro build + desktop clip compare on astro/dist (4.2 1600 gold; no Paper MCP) ->
5.4 live 768/390 clips + responsive compare on astro/dist ->
5.5 wire sitemap paths / labels to Astro routes + scrape-only SEO per page + astro build ->
5.6 Human checkpoint (built routes on file://). The only stop is 5.6.
5.6 done tidies and keeps rebuild/ + astro/ + pipeline.html.

No React. No Tailwind CDN. No new tokens. No create_file. Do not start astro dev.
Controller owns Paper and astro/src/components. Workers write one page body each.
Hrefs stay # until 5.5.
"""


def emit_handoff(root: Path, data: dict, step: str) -> Path | None:
    """Write and print the copy-ready prompt that starts the next session.

    Fires only from `mark --step {1.4,2.4} --status done`, i.e. only after the
    human has approved that checkpoint. Also releases the controller lease so
    the next session can claim it (a held lease blocks every mark).
    """
    session = HANDOFF_AT.get(step)
    if session is None:
        return None
    root = root.resolve()
    if session == 5 and not phase5_opted(root):
        return None
    paper = read_paper_file(root)
    board = (root / "pipeline.html").resolve().as_uri()
    if session == 2 and run_config.adopt_mode(root):
        body = _handoff_2_adopt(root, paper, board)
    elif session == 2:
        body = _handoff_2(root, paper, board)
    elif session == 5:
        body = _handoff_5(root, paper, board)
    else:
        body = _handoff_3(root, paper, board)
    if session == 3:
        snapshot_fidelity_freeze(root)

    dest = root / HANDOFF_FILE[session]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")

    if run_config.auto_accepts(root, step):
        # Automatic checkpoint: the SAME session keeps going. Keep the lease,
        # skip the copy-me banner; the prompt still lands on disk for a relay.
        nxt = "2.1" if session == 2 else "3.1"
        print(f"{step} auto-accepted — continue into {nxt} in this session (lease kept). Prompt saved: {dest}")
        return dest

    controller = data.get("controller")
    if isinstance(controller, dict) and controller.get("status") == "active":
        owner = str(controller.get("owner") or "")
        data.pop("controller", None)
        controller_lease_path(root).unlink(missing_ok=True)
        print(f"controller released -> {owner or '(unnamed)'}")

    bar = "=" * 72
    print("")
    print(bar)
    print(f"  COPY THIS INTO A NEW SESSION  \u2014  recommended tier: {'strong' if session in {2, 5} else 'operator'} (any model may run it)")
    print(bar)
    print(body.rstrip())
    print(bar)
    print(f"also written to {dest}")
    print("")
    return dest

# ------------------------------------------------------------------ relay ----
# A relay is a mid-session handoff at a receipt boundary: the running agent is
# near its context ceiling, so it writes the next-owner prompt, releases the
# controller lease, and (when Orca is reachable) opens a fresh terminal for
# the SAME agent and sends the prompt. It is a change of agent, never a stop
# for the human (Pitfall #218). Without Orca it prints the prompt block, exactly
# like the 1.4 / 2.4 handoffs (Pitfall #219). Same-source rule: Pitfall #220.

RELAY_ADAPTERS = ("auto", "orca-terminal", "print-prompt")
RELAY_WAIT_MS = 120_000
STEP_REFERENCES = {
    "1.1": "step-11.md", "1.2": "12-desktop-source.md + stage-p-notes.md",
    "1.3": "pillars.md (1.3 rows) + 13-buttons-components.md", "1.4": "live-board.md",
    "2.1": "paper-design-to-code.md", "2.2": "paper-design-to-code.md",
    "2.3": "section-23-paper-loop.md + responsive-22d.md + orca-relay.md", "2.4": "paper-design-to-code.md",
    "3.1": "polish-visual-restore.md",
    "3.2": "gsap-inview.md + hover-22c.md + nav-drawer.md + faq.md + nav-dropdown.md + orca-relay.md",
    "3.3": "semantics-pass.md", "3.4": "live-board.md",
    "4.1": "scripts.md", "4.2": "scripts.md", "4.3": "scripts.md", "4.4": "live-board.md",
    "5.1": "phase-5-astro.md", "5.2": "phase-5-astro.md + orca-relay.md", "5.3": "section-23-paper-loop.md",
    "5.4": "section-23-paper-loop.md", "5.5": "phase-5-astro.md + semantics-pass.md", "5.6": "live-board.md",
}
SESSION_LOCK = {
    1: "Paper is being built; never reuse another project's capture, library, or Paper file (Pitfall #187).",
    2: "Paper desktop is gold. 2.1 tokens/classes as-is. No new palette, fonts, or copy. Homepage only, file://. "
       "No get_jsx dump as the ship. No skip-link. Aesthetic-risk OFF. The only human stop is 2.4 (Pitfall #192).",
    3: "2.4 is the fidelity freeze. rebuild/index.html is the lock — never mutate it (Pitfall #203). 3.x writes "
       "index-polish.html only. No type-scale, class rename, or visual restore (Pitfall #196). The only human stop is 3.4.",
    4: "Paper-only. Extra pages onto the HOME canvas of the 1.2 file; one sample per dynamic template; no second library.",
    5: "astro/ only. Chrome pulled once at 5.1; each page authors its <main> only. Geometry, type, and library classes frozen.",
}


def _orca_run(argv: list[str], timeout_s: int = 60) -> tuple[int, str]:
    """Module-level so tests can substitute a fake runner."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout


def _dig(obj: object, *names: str) -> object:
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


def _json_or_empty(text: str) -> dict:
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _budget_snapshot(root: Path) -> dict | None:
    """Best-effort context budget (context_budget.py). Never raises."""
    try:
        import context_budget

        return context_budget.budget(root)
    except Exception:  # noqa: BLE001
        return None


def _probe_report(root: Path, *, fresh: bool = False) -> dict | None:
    """Best-effort harness/Orca probe (harness_probe.py). Writes qa/harness-probe.json. Never raises."""
    try:
        import harness_probe

        report = None if fresh else harness_probe.load_report(root)
        if report is None:
            report = harness_probe.probe(root=root)
            harness_probe.write_report(root, report)
        return report
    except Exception:  # noqa: BLE001
        return None


def print_probe_line(root: Path) -> None:
    if os.environ.get("WEB2HTML_NO_PROBE"):
        return
    report = _probe_report(root, fresh=True)
    if not report:
        return
    try:
        import harness_probe

        print("probe: " + harness_probe.brief(report))
    except Exception:  # noqa: BLE001
        return


def next_relay_owner(owner: str) -> str:
    """session-2 → session-2b → session-2c … → session-2z → session-2z-r1 → -r2; anything else gets `b`."""
    owner = owner.strip()
    m = re.match(r"^(.*-r)(\d+)$", owner)
    if m:
        return m.group(1) + str(int(m.group(2)) + 1)
    m = re.match(r"^(.*\d)([a-y])$", owner)
    if m:
        return m.group(1) + chr(ord(m.group(2)) + 1)
    if re.match(r"^.*\dz$", owner):
        return owner + "-r1"
    return owner + "b"


def relay_step(data: dict) -> str | None:
    current = data.get("current")
    if current in TITLES:
        return str(current)
    return next_pending_step(data)


def relay_boundary_errors(root: Path, step: str) -> list[str]:
    """A relay happens only where the disk is the truth: no shot-but-unrecorded round, no wave in flight."""
    errors: list[str] = []
    root = root.resolve()
    if step == "2.3":
        try:
            import paper_23_validate as validate

            for row in validate.ship_sections(root):
                sid = str(row.get("id"))
                payload = validate.load(root, sid)
                last = validate.last_round(payload) if payload else None
                if last and not validate.round_recorded(last):
                    errors.append(f"band {sid}: round {last.get('round')} is shot but not recorded — --record it first")
        except SystemExit:
            pass
        except Exception:  # noqa: BLE001 — cannot check → allow
            pass
    runs = root / AGENT_RUNS
    if runs.is_dir():
        for wave_file in sorted(runs.glob(f"*/{step}/wave.json")):
            try:
                wave = json.loads(wave_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            running = [t.get("id") for t in wave.get("tasks") or [] if t.get("status") == "running"]
            if running:
                errors.append(f"wave {wave.get('runId')} has workers running ({', '.join(map(str, running))}) — wave.py wait / apply first")
    return errors


def _relay_state_lines(root: Path, data: dict, step: str) -> list[str]:
    lines: list[str] = []
    root = root.resolve()
    claimed = str((data.get("controller") or {}).get("claimedAt") or "")
    done_here = [
        sid for sid, row in (data.get("steps") or {}).items()
        if row.get("status") == "done" and str(row.get("ended") or "") >= claimed and sid.split(".")[0] == step.split(".")[0]
    ]
    if done_here:
        lines.append("done this session: " + ", ".join(sorted(done_here)))
    if step == "2.3":
        try:
            import paper_23_validate as validate

            for row in validate.status_rows(root):
                flag = "" if row["state"] in {"match", "residual"} else "  <- open"
                lines.append(f"band {row['id']:<24} {row['state']:<9} rounds={row['rounds']}{flag}")
        except (Exception, SystemExit):  # noqa: BLE001 — ship_sections exits when index.html is missing
            lines.append("bands: run  paper_23_validate.py <project> --status")
    if step == "3.2":
        for rel in ("qa/button-hover-css.json", "qa/nav-drawer.json", "qa/faq.json", "qa/nav-dropdown.json",
                    "qa/gsap-reveal-qa.json", *COMPANION_RECEIPTS):
            lines.append(f"{'have ' if (root / rel).is_file() else 'need '} {rel}")
    runs = root / AGENT_RUNS
    if runs.is_dir():
        for wave_file in sorted(runs.glob(f"*/{step}/wave.json")):
            try:
                wave = json.loads(wave_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            states = {}
            for task in wave.get("tasks") or []:
                states[task.get("status")] = states.get(task.get("status"), 0) + 1
            lines.append(f"wave {wave.get('runId')} ({wave.get('adapter')}): " + ", ".join(f"{k} {v}" for k, v in sorted(states.items())))
    return lines or ["(no receipts yet for this step — start it from its first command)"]


def _relay_prompt(root: Path, data: dict, step: str, next_owner: str, budget: dict | None, reason: str, agent: str | None) -> str:
    root = root.resolve()
    paper = read_paper_file(root)
    board = (root / "pipeline.html").resolve().as_uri()
    session = SESSION_OF.get(step, int(step.split(".")[0]))
    pct = f"{budget.get('usedPct')}% of {int(budget.get('window') or 0) // 1000}k ({budget.get('source')})" if budget and budget.get("usedPct") is not None else "unknown"
    started = str((data.get("steps") or {}).get(step, {}).get("started") or "—")
    state = "\n  ".join(_relay_state_lines(root, data, step))
    who = agent or "the same harness that ran the predecessor"
    return f"""web2html — RELAY · continue {step} {TITLES[step]} · owner {next_owner}
Model: same source as the predecessor ({who}). The tier is advice, never a gate.

THIS IS A RELAY, NOT A HUMAN CHECKPOINT (Pitfall #218). The previous agent was at
{pct} of its context and handed you the run mid-step{(' — ' + reason) if reason else ''}.
Do not fire a CTA, do not ask the human, do not restart the step, do not `start`.
Continue from the receipts on disk; they are the truth.

Project   {root}
Source    {paper.get('url') or paper.get('sourceUrl') or '<source url>'}
Paper     {paper.get('fileId') or paper.get('paperFileId') or '<paperFileId>'}
Board     {board}
Step      {step} {TITLES[step]} · active since {started}

First actions, in order:
  1. cd "{root}"   then load the web2html skill. Read references/{STEP_REFERENCES.get(step, 'pillars.md')}.
  2. python3 "$SKILLS/web2html/scripts/pipeline-progress.py" resume "{root}" \\
       --at {step} --owner {next_owner}
     NOT `start`. resume claims the controller lease the predecessor released.
  3. python3 "$SKILLS/web2html/scripts/harness_probe.py" "{root}" --brief

State on disk:
  {state}

Then finish {step} and walk to the session's only human stop
({SESSION_YIELD_STEP.get(session, 'the next human checkpoint')}). Mark every boundary. If your own budget
reaches the arm threshold, relay again: pipeline-progress.py relay "{root}" --owner {next_owner}.

Fidelity lock: {SESSION_LOCK.get(session, '')}
"""


def _relay_via_orca(root: Path, prompt: str, step: str, next_owner: str, probe: dict) -> dict:
    """Open a fresh terminal for the SAME agent in the coordinator's Orca worktree and send the prompt."""
    orca = probe.get("orca") or {}
    cli = str(orca.get("cli") or "orca")
    worktree = str(orca.get("worktree") or "")
    command = str(probe.get("agentCommand") or "")
    result: dict = {"adapter": "orca-terminal", "started": False, "agent": probe.get("agent"), "command": command}
    if not worktree or not command:
        result["error"] = "orca worktree or agent command unknown (Pitfall #220)"
        return result
    code, text = _orca_run([cli, "terminal", "create", "--worktree", f"id:{worktree}", "--title",
                            f"web2html · {step} relay · {next_owner}", "--command", command, "--json"])
    handle = _dig(_json_or_empty(text), "handle")
    if code != 0 or not handle:
        result["error"] = f"terminal create exit {code}"
        return result
    result["terminal"] = str(handle)
    satisfied = False
    for timeout in (RELAY_WAIT_MS, RELAY_WAIT_MS * 2):
        code, text = _orca_run([cli, "terminal", "wait", "--terminal", str(handle), "--for", "tui-idle",
                                "--timeout-ms", str(timeout), "--json"], timeout // 1000 + 30)
        satisfied = bool(_dig(_json_or_empty(text), "satisfied")) if code == 0 else False
        if satisfied:
            break
    if not satisfied:
        result["error"] = "agent TUI never became idle; a prompt typed into a starting TUI is lost"
        return result
    code, text = _orca_run([cli, "terminal", "send", "--terminal", str(handle), "--text", prompt, "--enter",
                            "--wait-submit", "10", "--json"], 60)
    receipt = _json_or_empty(text)
    accepted = bool(_dig(receipt, "accepted")) if code == 0 else False
    result["accepted"] = accepted
    result["turnStarted"] = bool(_dig(receipt, "turn_started", "turnStarted"))
    if not accepted:
        result["error"] = f"terminal send not accepted (exit {code})"
        return result
    result["started"] = True
    return result


def cmd_relay(root: Path, owner: str, adapter: str = "auto", reason: str = "", force: bool = False) -> int:
    """Hand the run to a fresh agent of the same source at a receipt boundary; never a human stop."""
    root = root.resolve()
    if is_spec_repo(root):
        print("FAIL: do not relay the web2html spec repo. Pass the template project folder.", file=sys.stderr)
        return 2
    if adapter not in RELAY_ADAPTERS:
        print(f"FAIL: --adapter must be one of {RELAY_ADAPTERS}", file=sys.stderr)
        return 2
    if not progress_path(root).is_file():
        print("FAIL: no run to relay (missing qa/pipeline-progress.json).", file=sys.stderr)
        return 2
    data = load_progress(root)
    controller = data.get("controller")
    held = str((controller or {}).get("owner") or "") if isinstance(controller, dict) else ""
    if not held or (controller or {}).get("status") != "active":
        print("FAIL: no active controller lease — nothing to relay. resume first.", file=sys.stderr)
        return 2
    if held != owner:
        print(f"FAIL: controller lease belongs to {held!r}; pass --owner {held}.", file=sys.stderr)
        return 2
    step = relay_step(data)
    if step is None:
        print("FAIL: run is complete — nothing to relay.", file=sys.stderr)
        return 2
    if step in HUMAN_CHECKPOINTS and (data.get("steps") or {}).get(step, {}).get("status") == "active":
        print(f"FAIL: {step} is a human checkpoint. Yield to the human there; relay is for agent work (Pitfall #218).", file=sys.stderr)
        return 2
    boundary = relay_boundary_errors(root, step)
    if boundary and not force:
        print("FAIL: not at a receipt boundary (Pitfall #218):", file=sys.stderr)
        for err in boundary:
            print(f"  - {err}", file=sys.stderr)
        print("  finish the open unit, or pass --force to relay anyway.", file=sys.stderr)
        return 2
    next_owner = next_relay_owner(owner)
    budget = _budget_snapshot(root)
    probe = _probe_report(root, fresh=True) or {}
    chosen = str((probe.get("adapters") or {}).get("relay") or "print-prompt")
    if adapter != "auto":
        chosen = adapter if adapter == "print-prompt" or chosen == "orca-terminal" else "print-prompt"
    prompt = _relay_prompt(root, data, step, next_owner, budget, reason, probe.get("agent"))
    seq = len([r for r in (data.get("relays") or []) if r.get("step") == step]) + 1
    dest = root / "qa" / f"handoff-{step}.relay{seq}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(prompt, encoding="utf-8")

    # Release the lease exactly as 1.4 / 2.4 done do, then record the relay.
    revision = _revision(data.get("revision"))
    data.pop("controller", None)
    controller_lease_path(root).unlink(missing_ok=True)
    record = {"step": step, "from": owner, "to": next_owner, "at": now_iso(), "adapter": chosen,
              "usedPct": (budget or {}).get("usedPct"), "source": (budget or {}).get("source"),
              "reason": reason or None, "prompt": dest.relative_to(root).as_posix()}
    data.setdefault("relays", []).append(record)
    try:
        save_progress(root, data, revision)
    except ProgressConflict as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"controller released -> {owner}   relay {owner} → {next_owner} at {step}")

    started = False
    record["started"] = False
    if chosen == "orca-terminal":
        result = _relay_via_orca(root, prompt, step, next_owner, probe)
        record.update({k: v for k, v in result.items() if k != "adapter"})
        started = bool(result.get("started"))
    data = load_progress(root)
    if chosen == "orca-terminal" and not started:
        # Fail closed toward continuity: take the lease back so the run is never ownerless.
        print(f"relay: Orca terminal did not start ({record.get('error')}). Falling back to print-prompt.", file=sys.stderr)
        data["controller"] = {"owner": owner, "status": "active", "claimedAt": now_iso()}
        record["leaseReturnedTo"] = owner
    data["relays"][-1] = record
    save_progress(root, data, _revision(data.get("revision")))
    if chosen == "orca-terminal" and not started:
        lease = controller_lease_path(root)
        lease.parent.mkdir(parents=True, exist_ok=True)
        lease.write_text(json.dumps({"role": "controller", "owner": owner, "status": "active",
                                     "revision": _revision(data.get("revision"))}, indent=2) + "\n")
        print(f"controller re-claimed -> {owner}. Continue in place, or paste the prompt below into a new session of the same agent.")
    if started:
        print(f"relay started \u2192 Orca terminal {record.get('terminal')} running {record.get('command')} "
              f"({probe.get('agent')}, same source as this orchestrator)")
        print("This session must now END ITS TURN with one line on the board. No CTA, no question (Pitfall #218).")
    if not started:
        bar = "=" * 72
        print("")
        print(bar)
        print(f"  COPY THIS INTO A NEW SESSION OF THE SAME AGENT  —  relay {owner} → {next_owner} at {step}")
        print(bar)
        print(prompt.rstrip())
        print(bar)
    print(f"also written to {dest}")
    write_live(root, load_progress(root))
    return 0 if (started or chosen == "print-prompt") else 3


SESSION_YIELD_STEP = {1: "1.4", 2: "2.4", 3: "3.4", 4: "4.4", 5: "5.6"}


def cmd_handoff(root: Path) -> int:
    """Print a copy-ready next-session prompt. Does not release the lease.

    1.4 still open → SESSION 2 draft (Done & continue, or the hand-off choice, still required).
    1.4 done, 2.4 open → SESSION 2. 2.4 done → SESSION 3.
    """
    root = root.resolve()
    if is_spec_repo(root):
        print("FAIL: do not stamp the web2html spec repo. Pass the template project folder.", file=sys.stderr)
        return 2
    if not (root / "qa" / "pipeline-progress.json").is_file():
        print("FAIL: no run to hand off (missing qa/pipeline-progress.json).", file=sys.stderr)
        return 2
    data = load_progress(root)
    paper = read_paper_file(root)
    board = (root / "pipeline.html").resolve().as_uri()
    s14 = str((data.get("steps") or {}).get("1.4", {}).get("status") or "")
    s24 = str((data.get("steps") or {}).get("2.4", {}).get("status") or "")
    if s24 == "done":
        session, body = 3, _handoff_3(root, paper, board)
        snapshot_fidelity_freeze(root)
    else:
        session, body = 2, _handoff_2(root, paper, board)
        if s14 != "done":
            print("DRAFT — 1.4 is not signed off yet. Paste this after")
            print("'Done & continue to next step', or pick the hand-off option once signed.")
            print("Pin Paper comments first. 2.1 will not start until those threads are handled.")
    dest = root / HANDOFF_FILE[session]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    bar = "=" * 72
    print("")
    print(bar)
    print(f"  COPY THIS INTO A NEW SESSION  —  recommended tier: {'strong' if session == 2 else 'operator'} (any model may run it)")
    print(bar)
    print(body.rstrip())
    print(bar)
    print(f"also written to {dest}")
    print("")
    return 0


def cmd_resume(
    root: Path,
    at: str | None,
    owner: str,
    agent: str | None = None,
    model: str | None = None,
) -> int:
    """Continue an existing run in a new session. Never resets, never quarantines.

    `start` is for a fresh run: it force-writes empty progress over the board.
    A second or third session must call this instead. Without `--at` the step
    is detected from the board (active step, else first pending), so a fresh
    terminal can always find where the run sits and keep timing it.
    """
    if is_spec_repo(root):
        print("FAIL: do not stamp the web2html spec repo. Pass the template project folder.", file=sys.stderr)
        return 2
    if at is not None and at not in TITLES:
        print(f"FAIL: unknown step {at}. Use: {' '.join(STEP_IDS)}", file=sys.stderr)
        return 2
    if not progress_path(root).is_file():
        print(
            "FAIL: no run to resume (missing qa/pipeline-progress.json). "
            "Use `start` for a new run.",
            file=sys.stderr,
        )
        return 2
    data = load_progress(root)
    detected = detect_resume_step(data, root)
    if at is None:
        if detected is None:
            print("FAIL: nothing left to resume — every counted step is done. Use `timing` or `finish`.", file=sys.stderr)
            return 2
        at = detected
        print(f"resume: no --at given — detected {at} {TITLES[at]} from the board")
    elif detected and detected != at:
        print(f"resume: board sits at {detected} {TITLES[detected]}; you asked for {at}. Timing continues from the board.")
    pending = pending_predecessors(data, at, for_active=True)
    if pending:
        print(
            f"FAIL: cannot resume at {at} \u2014 unfinished predecessors: {', '.join(pending)}.",
            file=sys.stderr,
        )
        return 2
    controller = data.get("controller")
    if isinstance(controller, dict) and controller.get("status") == "active":
        held = str(controller.get("owner") or "")
        if held != owner:
            print(
                f"FAIL: controller lease is held by {held!r}. The previous session must "
                "release it (mark 1.4 / 2.4 done does this automatically), or pass "
                f"--owner {held}.",
                file=sys.stderr,
            )
            return 2
    data["controller"] = {"owner": owner, "status": "active", "claimedAt": now_iso()}
    who, what = resolve_agent_model(root, agent, model)
    log_session(data, kind="resume", owner=owner, at=at, agent=who, model=what)
    try:
        save_progress(root, data, _revision(data.get("revision")))
    except ProgressConflict as exc:
        print(str(exc), file=sys.stderr)
        return 2
    lease = controller_lease_path(root)
    lease.parent.mkdir(parents=True, exist_ok=True)
    lease.write_text(
        json.dumps(
            {"role": "controller", "owner": owner, "status": "active", "revision": _revision(data.get("revision"))},
            indent=2,
        )
        + "\n"
    )
    dest = write_live(root, data)
    write_capture_tool_session(root)
    done, total, current = counts(data)
    uri = dest.resolve().as_uri()
    print(f"pipeline resume -> {dest}   {done}/{total} done   next {at}   owner {owner}")
    print(uri)
    print(timing_summary_line(data))
    if current:
        since = (data["steps"][current] or {}).get("started")
        print(f"{current} is still active since {fmt_clock(since)} — its clock keeps running until you mark it done.")
    else:
        print(f"mark --step {at} --status active before working so {at} is timed.")
    print("Live board was opened at start — leave that tab. resume does not reopen it.")
    print("Progress was NOT reset. Do not run `start` on a run in flight.")
    print("IDs: " + " ".join(STEP_IDS))
    print_probe_line(root)
    return 0


def cmd_open_capture(root: Path) -> int:
    if is_spec_repo(root):
        print("FAIL: do not stamp the web2html spec repo. Pass the template project folder.", file=sys.stderr)
        return 2
    return 0 if open_capture_tool(root) else 2


def cmd_start(root: Path, agent: str | None = None, model: str | None = None) -> int:
    if is_spec_repo(root):
        print("FAIL: do not stamp the web2html spec repo. Pass the template project folder.", file=sys.stderr)
        return 2
    if not live_template().is_file():
        print(f"FAIL: missing {live_template()}", file=sys.stderr)
        return 2
    moved = quarantine_unauthorized_ship(root)
    stale_paper = root / "qa" / "paper-file.json"
    if stale_paper.is_file():
        stale_paper.unlink()
        print("cleared qa/paper-file.json — this run creates one Paper file at 1.2")
    who, what = resolve_agent_model(root, agent, model)
    data = empty_progress(root.name)
    log_session(data, kind="start", owner="session-1", at="1.1", agent=who, model=what)
    save_progress(root, data, force=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        import orca_workspace

        if not (root / orca_workspace.WORKSPACE_FILE).is_file():
            orca_workspace.ensure(root.name, base=root.parent)
    except Exception:  # noqa: BLE001 — the workspace is an accelerator, never a gate
        pass
    dest = write_live(root, data, source=live_template())
    write_capture_tool_session(root)
    uri = dest.resolve().as_uri()
    print(f"pipeline start → {dest}")
    print(uri)
    print("KEEP THIS TAB OPEN — live board. Do not continue until it is visible.")
    print("IDs: " + " ".join(STEP_IDS))
    print("No step may be skipped (Pitfall #98).")
    print("Do not write rebuild HTML before 2.1 (Pitfall #148).")
    opened = open_live_board(dest)
    if moved:
        print(
            "FAIL: unauthorized rebuild HTML was quarantined (Pitfall #148). "
            "Do not restore or polish that page. Walk 1.1 → 1.4.",
            file=sys.stderr,
        )
        for path in moved:
            print(f"  - {path}", file=sys.stderr)
        return 2
    if not opened:
        print("FAIL: live board did not open. Open the URI above, then retry start.", file=sys.stderr)
        return 2
    print_probe_line(root)
    print_intake_prompt()
    return 0


def print_intake_prompt() -> None:
    """Exact questions. A folder choice must be followed by a path field."""
    print("")
    print("INTAKE — fire this harness's question tool, then record the answers.")
    print("Question 1, one choice:")
    print("  1. Live URL — author from Paper")
    print("  2. Webflow / HTML source")
    print("If they choose 2, fire a follow-up BEFORE the speed question.")
    print("  Question: Paste the absolute path to the HTML folder.")
    print("  The answer is the path, typed in the text field. Do not guess a folder.")
    print("  Do not record intake until that path exists on disk.")
    print("Question 2, one choice:")
    print("  1. Full")
    print("  2. Fast")
    print("Then:")
    print("  python3 $SKILLS/web2html/scripts/run_config.py intake <project> \\")
    print("    --source none|/abs/path --speed full|fast")
    print("")


def open_live_board(dest: Path) -> bool:
    """Open the live board once, when start writes it. resume/mark never call this."""
    path = dest.resolve()
    uri = path.as_uri()
    print(f"OPEN {uri}")
    if sys.platform == "darwin":
        fallback = ["open", str(path)]
    elif sys.platform.startswith("linux"):
        fallback = ["xdg-open", str(path)]
    else:
        fallback = None
    try:
        import open_doc

        result = open_doc.open_doc(uri, fallback)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: could not open board: {exc}", file=sys.stderr)
        return False
    if result.get("opened"):
        print(f"board → {open_doc.describe(result)}")
        return True
    print(f"FAIL: could not open board ({result.get('error')}). Open {uri} yourself.", file=sys.stderr)
    return False


def cmd_mark(
    root: Path,
    step: str,
    status: str,
    reason: str | None,
    expected_revision: int | None = None,
    owner: str | None = None,
    agent: str | None = None,
    model: str | None = None,
) -> int:
    if step not in TITLES:
        print(f"FAIL: unknown step {step}. Use: {' '.join(STEP_IDS)}", file=sys.stderr)
        return 2
    if status not in STATUSES:
        print(f"FAIL: status must be {sorted(STATUSES)}", file=sys.stderr)
        return 2
    if status == "skipped" and step not in OPTIONAL_STEPS:
        print("FAIL: never skip a required step (Pitfall #98). Run the step or stop the run.", file=sys.stderr)
        return 2
    if status == "skipped" and step.startswith("4.") and run_config.adopt_mode(root):
        print(
            "FAIL: Phase 4 is required on a Webflow / HTML folder run. "
            "Do not skip 4.1–4.4. The run stops at 4.4.",
            file=sys.stderr,
        )
        return 2
    if step in RETIRED_22:
        print(
            f"FAIL: {step} is retired. Live 2.0 children are 2.1 / 2.2 / 2.3 / 2.4. "
            "2.1 emits the Design System page, 2.2 authors the homepage from Paper, 2.3 signs sections against Paper, 2.4 injects TAGS.",
            file=sys.stderr,
        )
        return 2
    if status == "done" and step == "2.1" and not artifact_done(root, step):
        if run_config.adopt_mode(root):
            print(
                "FAIL: cannot mark 2.1 done — adopted source needs qa/design-system-skipped.json. "
                "Do not emit a Design System page or fonts.css.",
                file=sys.stderr,
            )
        elif run_config.design_system_enabled(root):
            print(
                "FAIL: cannot mark 2.1 done — rebuild/design-system.html is missing. "
                "2.1 emits the Design System from library.json (not the ship).",
                file=sys.stderr,
            )
        else:
            print(
                "FAIL: cannot mark 2.1 done — fast run still self-hosts fonts. "
                "Run emit_fonts.py . (writes rebuild/css/fonts.css from source-site/assets).",
                file=sys.stderr,
            )
        return 2
    if status == "done" and step == "2.2" and not artifact_done(root, step):
        if run_config.adopt_mode(root):
            print(
                "FAIL: cannot mark 2.2 done — the adopted export is not rebuild/index.html, "
                "or pipeline CSS was invented. mark 2.2 active copies source-html/. "
                "Do not author index-semantic.html.",
                file=sys.stderr,
            )
        else:
            print(
                "FAIL: cannot mark 2.2 done — rebuild/index-semantic.html is missing or is a "
                "get_jsx dump, or it is not bound to the 2.1 tokens. Author from "
                "Paper using design-system.html + tokens.css. No new --color/--font names.",
                file=sys.stderr,
            )
        return 2
    if status == "done" and step == "2.3" and not artifact_done(root, step):
        print(
            "FAIL: cannot mark 2.3 done — a section is still open against disk gold "
            "1600 / 768 / 390. Every section needs a measure receipt at all "
            "three widths plus a VALIDATE receipt (paper_23_validate.py: --shoot, "
            "Read the side-by-sides, patch, --record; every width match or a "
            "residual at round 3; no patch after the last look — Pitfall #216). "
            "Do not invent a 1320/1024 breakpoint. Run section_22_gate.py .",
            file=sys.stderr,
        )
        return 2
    if status == "done" and step == "2.4" and not artifact_done(root, step):
        if run_config.auto_accepts(root, "2.4"):
            print(
                "FAIL: cannot mark 2.4 done — the auto-accept receipt qa/build-checkpoint.md "
                "is missing. `mark --step 2.4 --status active` writes it (checkpoints=auto).",
                file=sys.stderr,
            )
        else:
            print(
                "FAIL: cannot mark 2.4 done — inject the QA overlay with TAGS on, "
                "run open-build-review.py . --stage 2.4, and write qa/build-checkpoint.md.",
                file=sys.stderr,
            )
        return 2
    data = load_progress(root)
    # Intake gate — the three run questions are answered before 1.1 goes
    # active (qa/run-config.json). A run without them is a run nobody scoped.
    if step == "1.1" and status == "active" and not run_config.exists(root):
        print(
            "FAIL: cannot mark 1.1 active — no run intake. Ask where the run starts "
            "(Live URL, or Webflow / HTML source). If they choose a folder, the next "
            "question is the absolute path. Then full or fast. Record them:\n"
            "  python3 $SKILLS/web2html/scripts/run_config.py intake <project> "
            "--source none|/abs/path --speed full|fast",
            file=sys.stderr,
        )
        return 2
    actual_revision = _revision(data.get("revision"))
    if expected_revision is not None and expected_revision != actual_revision:
        print(_progress_conflict(expected_revision, actual_revision), file=sys.stderr)
        return 2
    controller = data.get("controller")
    if isinstance(controller, dict) and controller.get("status") == "active":
        controller_owner = str(controller.get("owner") or "")
        if owner != controller_owner:
            print(f"FAIL: controller lease belongs to {controller_owner!r}; pass --owner to stamp progress.", file=sys.stderr)
            return 2
    if status == "done" and step == "3.4" and active_reviewer_leases(root):
        print("FAIL: cannot complete 3.4 while reviewer leases are active.", file=sys.stderr)
        return 2
    if status == "done" and step == "3.4" and not ship_ready(root):
        if run_config.adopt_mode(root):
            print(
                "FAIL: cannot mark 3.4 done — source-html/index.html is missing, "
                "or Phase 3 changed more than accessibility attributes. "
                "Do not create rebuild/.",
                file=sys.stderr,
            )
        else:
            print(
                "FAIL: cannot mark 3.4 done — missing rebuild/index-polish.html. "
                "3.x copies the 2.4 index and writes QA there. "
                "open-human-review.py compares both files (Pitfall #203). "
                "mark 3.4 done promotes that file to index.html.",
                file=sys.stderr,
            )
        return 2
    if status == "done" and step == "3.4" and run_config.adopt_mode(root) and phase4_skipped(root):
        print(
            "FAIL: cannot mark 3.4 done — Phase 4 is required on a Webflow / HTML folder run. "
            "Remove qa/phase-4-skipped.json. The run continues through 4.4.",
            file=sys.stderr,
        )
        return 2
    if status == "done" and step == "3.4" and run_config.adopt_mode(root) and not phase4_opted(root):
        write_phase4_required(root)
        print("phase 4 → required  qa/phase-4-opted.json  continue at 4.1  stop at 4.4  do not ask")
    if status == "done" and step == "3.4" and not phase4_receipt(root):
        print(
            "FAIL: cannot mark 3.4 done — record qa/phase-4-skipped.json (finish) "
            "or qa/phase-4-opted.json (continue to optional Phase 4).",
            file=sys.stderr,
        )
        return 2
    if step.startswith("4.") and not phase4_opted(root):
        print(
            "FAIL: Phase 4 is closed. Write qa/phase-4-opted.json at 3.4 to continue, "
            "or qa/phase-4-skipped.json to finish the homepage run.",
            file=sys.stderr,
        )
        return 2
    if status == "done" and step == "4.4" and not artifact_done(root, "4.4"):
        print("FAIL: cannot mark 4.4 done — write qa/phase-4-review.md and open Paper.", file=sys.stderr)
        return 2
    if status == "done" and step == "4.4" and not phase5_receipt(root):
        print(
            "FAIL: cannot mark 4.4 done — record qa/phase-5-skipped.json (finish) "
            "or qa/phase-5-opted.json (continue to optional Phase 5).",
            file=sys.stderr,
        )
        return 2
    if step.startswith("5.") and not phase5_opted(root):
        print(
            "FAIL: Phase 5 is closed. Write qa/phase-5-opted.json at 4.4 to continue, "
            "or qa/phase-5-skipped.json to finish after Paper review.",
            file=sys.stderr,
        )
        return 2
    if status == "done" and step == "5.6" and not artifact_done(root, "5.6"):
        print(
            "FAIL: cannot mark 5.6 done — run open-phase-5-review.py (writes qa/phase-5-review.md) "
            "and review the built Astro routes.",
            file=sys.stderr,
        )
        return 2
    pending = pending_predecessors(data, step, for_active=(status == "active"))
    if pending:
        print(
            f"FAIL: cannot mark {step} {status} — unfinished predecessors: "
            f"{', '.join(pending)}. Walk the numbered steps (Pitfall #148).",
            file=sys.stderr,
        )
        return 2
    if status == "done" and step == "4.1" and run_config.adopt_mode(root):
        if (root / "qa" / "phase-4-sitemap.json").is_file() and not (root / "qa" / "source-gaps.json").is_file():
            import source_fidelity

            payload = source_fidelity.review_gaps(root)
            print(f"source gaps → {len(payload.get('pages') or [])}  qa/source-gaps.json")
    if status == "done" and step in ARTIFACT_DONE_REQUIRED and not artifact_done(root, step):
        detail = ""
        if step == "1.3":
            detail = (
                " 1.3 mines the Design Library, then pulls unique buttons + "
                "components from token-seeded home-desktop onto FRAME Buttons "
                "and FRAME Components (qa/buttons-components-pull.json with "
                "geometry.ok — source pixel width, hugged rows, section order, "
                "Buttons clearance), then "
                "authors button hover from source CSS (qa/button-hover.json)."
            )
        if step == "1.4":
            detail = (
                " 1.4 is the human Paper checkpoint. It needs "
                "qa/paper-human-review.md. Capture Tool is optional "
                "(pipeline-progress.py open-capture). 1.4 done emits the "
                "session 2 handoff prompt."
            )
        if step == "2.1":
            detail = (
                " adopted source — Phase 2 is not applicable."
                if run_config.adopt_mode(root)
                else " 2.1 emits rebuild/design-system.html + css/tokens.css from library.json. Not the ship."
            )
        if step == "2.2":
            detail = (
                " adopted source — do not copy into rebuild/ and do not author a homepage."
                if run_config.adopt_mode(root)
                else (
                    " 2.2 authors rebuild/index-semantic.html from Paper using the 2.1 "
                    "tokens. Link tokens.css. No new --color/--font names. 2.3 seeds "
                    "index.html from that file."
                )
            )
        if step == "2.3":
            detail = (
                " After APPLY, walk VALIDATE top-to-bottom: paper_23_validate.py . --next, "
                "--id <band> --shoot, Read the three side PNGs, patch that band, --record; "
                "at most 3 rounds per band, then --residual (Pitfall #216). "
                "Then section_22_gate.py — every section must align at 1600 / 768 / 390."
            )
        if step == "3.2":
            detail = (
                " 3.2 writes hover CSS from 1.3 qa/button-hover.json "
                "(apply-hover-css.py → rebuild/css/hover.css on index-polish.html), "
                "authors a painted burger drawer (author-nav-drawer.py; "
                "Capture Tool is not required), FAQ accordion (author-faq.py), "
                "nav dropdowns (author-nav-dropdown.py), guidelines a11y, and mandatory "
                "GSAP in-view. Companion receipts qa/web-design-guidelines.md, "
                "qa/find-animation-opportunities.md, qa/apple-design.md are required "
                "to mark 3.2 done (Pitfall #215)."
            )
        if step == "4.1":
            detail = " 4.1 writes qa/phase-4-sitemap.json from the source sitemap."
        if step == "4.2":
            detail = " 4.2 writes qa/phase-4-pages.json after desktop Paper pages land."
        if step == "4.3":
            detail = (
                " adopted source — author qa/source-gaps.json pages from Paper into source-html/, then source_fidelity.py record-gaps."
                if run_config.adopt_mode(root)
                else " 4.3 writes qa/phase-4-token-seed.json after a serial token bind."
            )
        if step == "5.1":
            detail = (
                " 5.1 writes qa/phase-5-scaffold.json (scaffold-astro.py), "
                "qa/phase-5-components.json (extract-astro-components.py), and "
                "qa/phase-5-home.json (convert-astro-home.py)."
            )
        if step == "5.2":
            detail = " 5.2 writes qa/phase-5-pages.json (record-phase-5-pages.py) after src/pages/{slug}.astro bodies are authored."
        if step == "5.3":
            detail = " 5.3 writes qa/phase-5-clip-compare.json from desktop disk gold vs astro/dist shots."
        if step == "5.4":
            detail = " 5.4 writes qa/phase-5-responsive.json after live 768/390 compare vs astro/dist shots."
        if step == "5.5":
            detail = " 5.5 writes qa/phase-5-links.json after routes are wired, interior SEO runs, and astro build passes."
        print(
            f"FAIL: cannot mark {step} done — required capture/library artifacts are missing. "
            f"Do not stamp past an unfinished step (Pitfall #148).{detail}",
            file=sys.stderr,
        )
        return 2
    if status == "active" and step in BUILD_STEPS:
        if run_config.adopt_mode(root) and step.startswith("3."):
            run_config.write_adopt_qa(root)
            if step == "3.1":
                import source_fidelity

                if source_fidelity.load_snapshot(root) is None:
                    source_fidelity.snapshot(root)
                    print("fidelity snapshot → qa/source-fidelity.json  accessibility attributes only")
            allow = ALLOW_INDEX
        elif step.startswith("3."):
            seed_24_polish(root)
            allow = ALLOW_POLISH
        elif step.startswith("5."):
            allow = ALLOW_PAGES
        elif step == "2.1":
            allow = ALLOW_DESIGN_SYSTEM
        else:
            if step == "2.3":
                seed_22_index(root)
            allow = ALLOW_INDEX
        blocked = rebuild_write_errors(root, allow)
        if blocked:
            print(
                "FAIL: rebuild write gate is red. Do not author a page from the scrape "
                "(Pitfall #148).",
                file=sys.stderr,
            )
            for err in blocked:
                print(f"  - {err}", file=sys.stderr)
            return 2
    if status == "active":
        active_other = [sid for sid, row in data["steps"].items() if row.get("status") == "active" and sid != step]
        if active_other:
            print(
                f"FAIL: another step is active ({', '.join(active_other)}). Mark it done before activating {step}.",
                file=sys.stderr,
            )
            return 2
        if step == "3.1" and not run_config.adopt_mode(root):
            snapshot_fidelity_freeze(root)
        if step == "3.2" and not run_config.adopt_mode(root):
            try:
                if not run_config.design_library_enabled(root):
                    seed_32_light_hover(root)
                seed_32_button_hover(root)
                seed_32_nav_drawer(root)
                seed_32_faq(root)
                seed_32_nav_dropdown(root)
            except FileNotFoundError as exc:
                print(f"FAIL: cannot mark 3.2 active — {exc}", file=sys.stderr)
                return 2
        if step == "1.4":
            if run_config.auto_accepts(root, "1.4"):
                write_auto_accept_14(root)
            elif not open_paper_for_review(root):
                print(
                    "FAIL: cannot mark 1.4 active until Paper can open "
                    "(qa/paper-file.json fileId). 1.4 active opens Paper AND the "
                    "browser on the stamped source URL for the Capture Tool.",
                    file=sys.stderr,
                )
                return 2
        if step == "3.4" and run_config.adopt_mode(root):
            print("3.4 adopt — do not ask finish vs Phase 4.")
            print("Phase 4 is required. Mark 3.4 done and continue at 4.1. The next human stop is 4.4.")
        if step == "2.4" and run_config.adopt_mode(root):
            print("2.4 off — Phase 2 is not applicable. source-html/ is the ship. Continue at 3.1.")
        elif step == "2.4" and run_config.auto_accepts(root, "2.4"):
            write_auto_accept_24(root)
        if step == "2.2" and run_config.adopt_mode(root):
            print("2.2 off — do not copy source-html into rebuild/ and do not author a homepage.")
        if step == "4.3" and run_config.adopt_mode(root):
            import source_fidelity

            run_config.write_adopt_token_seed(root)
            gaps = source_fidelity.gap_slugs(root)
            if not gaps:
                plan = root / "qa" / "phase-4-gap-plan.json"
                plan.write_text(json.dumps({"pages": []}, indent=2) + "\n", encoding="utf-8")
                source_fidelity.record_gap_author(root)
                print("4.3 adopt — no empty CMS layouts. Token bind refused.")
            else:
                listed = ", ".join(gaps[:8])
                print(
                    "4.3 adopt — author these missing layouts from Paper screenshots into "
                    f"source-html/: {listed}. Write qa/phase-4-gap-plan.json then "
                    "source_fidelity.py record-gaps. Do not bind tokens. Do not rewrite pages the export already has."
                )
        data["current"] = step
        data["steps"][step]["started"] = data["steps"][step].get("started") or now_iso()
    if status in {"done", "skipped"}:
        # `done` is real work: backfill `started` when the agent never marked
        # active so the step still lands in the run total. `skipped` is not work.
        close_step_timing(data, step, infer=(status == "done"))
        if data.get("current") == step:
            data["current"] = None
    data["steps"][step]["status"] = status
    if reason:
        data["steps"][step]["reason"] = reason
    if status in {"active", "done"}:
        who, what = resolve_agent_model(root, agent, model)
        if who is None and what is None:
            session = current_session(data)
            who, what = session.get("agent"), session.get("model")
        # `active` is the attribution of record; `done` only fills a blank.
        stamp_step_who(data["steps"][step], who, what, overwrite=(status == "active"))
    budget_row = None
    try:
        import context_budget

        ledger = context_budget.ledger(data)
        ledger["spendTokens"] = int(ledger.get("spendTokens") or 0) + context_budget.SPEND["mark"]
        ledger["events"] = int(ledger.get("events") or 0) + 1
        budget_row = context_budget.budget(root)
        if budget_row:
            data["budgetState"] = budget_row
    except Exception:  # noqa: BLE001 — the budget never gates a mark
        budget_row = None
    if status == "done" and step == "3.4":
        try:
            receipt = promote_ship(root)
        except FileNotFoundError as exc:
            print(f"FAIL: cannot mark 3.4 done — {exc}", file=sys.stderr)
            return 2
        if not receipt.get("already"):
            if receipt.get("adopted"):
                print("ship stays source-html/index.html  no rebuild/")
            else:
                archived = ", ".join(receipt.get("archived") or []) or "none"
                print(f"ship promote → rebuild/index.html  outlines off  archived {archived}")
    if status == "done" and step == "1.4" and run_config.adopt_mode(root):
        for sid in ("2.1", "2.2", "2.3", "2.4"):
            row = data["steps"].get(sid)
            if not isinstance(row, dict):
                continue
            row["status"] = "done"
            row["reason"] = "source folder — phase 2 not applicable"
            row["ended"] = row.get("ended") or now_iso()
        print("phase 2 → off   source-html/ is the ship")
    try:
        save_progress(root, data, actual_revision if expected_revision is not None else None)
    except ProgressConflict as exc:
        print(str(exc), file=sys.stderr)
        return 2
    dest = write_live(root, data)
    write_capture_tool_session(root)
    done, total, current = counts(data, root)
    extra = f"   current {current}" if current else ""
    if not extra:
        nxt = next_pending_step(data, root)
        if nxt:
            extra = f"   NEXT {nxt} {TITLES[nxt]}"
    print(f"{step} → {status}   {done}/{total}{extra}")
    print(dest.resolve().as_uri())
    print_mark_timing(data, step, status)
    if status in {"done", "skipped"}:
        # Self-improving run report: refresh run-report.md as steps close (and
        # always at human checkpoints) so the timing / comment / note log
        # survives the tidy. Best effort — the report is an output, never a gate.
        try:
            import run_report

            if step in HUMAN_CHECKPOINTS or status == "done":
                print(f"run report → {run_report.build(root)}")
        except Exception:  # noqa: BLE001
            pass
    if budget_row and budget_row.get("usedPct") is not None:
        try:
            import context_budget

            print(context_budget.one_line(budget_row))
            if budget_row.get("state") in {"armed", "force"} and step not in HUMAN_CHECKPOINTS:
                print(f"  → pipeline-progress.py relay {root} --owner <this session>   at the next receipt boundary (Pitfall #218)")
        except Exception:  # noqa: BLE001
            pass
    if status == "active" and step == "2.4":
        if run_config.adopt_mode(root):
            print("2.4 off — Phase 2 is not applicable. Mark done and continue at 3.1.")
        elif run_config.auto_accepts(root, "2.4"):
            print("2.4 auto — no TAGS stop. Mark 2.4 done and continue into 3.1 in this session.")
        else:
            print_24_hard_stop(root)
    if status == "done" and step == "2.2" and not run_config.adopt_mode(root):
        seed_22_index(root)
    if status == "done" and step == "4.4" and run_config.adopt_mode(root):
        print(
            "adopt: missing layouts were authored at 4.3 from Paper screenshots.\n"
            "  Design System print is optional. Do not bind tokens onto frames.\n"
            "  python3 $SKILLS/web2html/scripts/run_config.py design-system . --choice skip|print|seed-from-source"
        )
    if status == "done" and step in HANDOFF_AT:
        had_lease = isinstance(data.get("controller"), dict)
        emit_handoff(root, data, step)
        if had_lease and "controller" not in data:
            # emit_handoff released the lease in memory; persist it so the next
            # session's `resume --owner <new>` is not refused by a stale claim.
            try:
                save_progress(root, data)
            except ProgressConflict as exc:
                print(str(exc), file=sys.stderr)
                return 2
    if run_is_complete(data, root):
        removed = tidy_completed_run(root)
        print(TIDY_SUMMARY)
        for rel in removed:
            print(f"  - {rel}")
    return 0


def print_mark_timing(data: dict, step: str, status: str) -> None:
    """One line per mark: when the step started / finished and how long it took."""
    row = data["steps"].get(step) or {}
    if status == "active":
        print(f"{step} started {fmt_clock(row.get('started'), with_date=False)}")
        return
    if status not in {"done", "skipped"}:
        return
    dur = row.get("durationSeconds")
    took = fmt_duration(dur) if dur is not None else "untimed"
    if row.get("startedInferred"):
        took += " (start inferred — mark active next time)"
    print(f"{step} finished {fmt_clock(row.get('ended'))}   took {took}")
    print(timing_summary_line(data))


def timing_rows(data: dict, root: Path | None = None) -> list[dict]:
    refresh_timing(data)
    ids = counted_step_ids(root, data) if root is not None else list(STEP_IDS)
    rows: list[dict] = []
    for sid in ids:
        row = data["steps"].get(sid) or {}
        rows.append(
            {
                "step": sid,
                "title": TITLES[sid],
                "status": row.get("status", "pending"),
                "started": row.get("started"),
                "ended": row.get("ended"),
                "durationSeconds": row.get("durationSeconds"),
                "startedInferred": bool(row.get("startedInferred")),
                "agent": row.get("agent"),
                "model": row.get("model"),
                "human": sid in HUMAN_CHECKPOINTS,
            }
        )
    return rows


def cmd_timing(root: Path, as_json: bool = False) -> int:
    """Per-step started / finished / duration and the run total (sum of steps)."""
    if is_spec_repo(root):
        print("FAIL: pass the template project folder, not the web2html spec repo.", file=sys.stderr)
        return 2
    if not progress_path(root).is_file():
        print("FAIL: no run here (missing qa/pipeline-progress.json).", file=sys.stderr)
        return 2
    data = load_progress(root)
    rows = timing_rows(data, root)
    timing = data["timing"]
    if as_json:
        print(
            json.dumps(
                {
                    "project": data.get("project"),
                    "runStarted": data.get("started"),
                    "sessions": data.get("sessions") or [],
                    "timing": timing,
                    "steps": rows,
                },
                indent=2,
            )
        )
        return 0
    print(f"{'step':<5} {'status':<8} {'started':<13} {'finished':<13} {'took':>9}  {'agent':<24}  title")
    for row in rows:
        took = fmt_duration(row["durationSeconds"]) if row["durationSeconds"] is not None else "—"
        if row["status"] == "active" and row["started"]:
            started_dt = parse_iso(row["started"])
            elapsed = (datetime.now(timezone.utc) - started_dt).total_seconds() if started_dt else None
            took = f"{fmt_duration(elapsed)}…"
        flag = "*" if row["startedInferred"] else " "
        human = " (human)" if row["human"] else ""
        who = agent_label(row.get("agent"), row.get("model")) or "—"
        print(
            f"{row['step']:<5} {row['status']:<8} {fmt_clock(row['started']):<13} "
            f"{fmt_clock(row['ended']):<13} {took:>9}{flag} {who:<24}  {row['title']}{human}"
        )
    print("")
    for phase in sorted(timing["phases"]):
        line = phase_agent_copy(timing["phaseAgents"].get(phase), timing["phases"][phase])
        print(f"phase {phase}   {line}")
    print(timing_summary_line(data))
    if any(row["startedInferred"] for row in rows):
        print("* start inferred — the step was marked done without a prior `mark --status active`.")
    sessions = data.get("sessions") or []
    if sessions:
        print("")
        print("sessions")
        for entry in sessions:
            if not isinstance(entry, dict):
                continue
            at = f" at {entry.get('at')}" if entry.get("at") else ""
            who = agent_label(entry.get("agent"), entry.get("model"))
            who = f"  [{who}]" if who else ""
            print(f"  {fmt_clock(entry.get('startedAt'))}  {entry.get('kind', '?'):<6} {entry.get('owner') or '—'}{at}{who}")
    return 0


def cmd_finish(root: Path) -> int:
    if is_spec_repo(root):
        print("FAIL: do not tidy the web2html spec repo.", file=sys.stderr)
        return 2
    if active_reviewer_leases(root):
        print("FAIL: finish refused while reviewer leases are active.", file=sys.stderr)
        return 2
    if not run_may_tidy(root):
        print(
            "FAIL: finish only after 1.1–3.4 and Phase 4/5 is skipped or the last opted phase is done.",
            file=sys.stderr,
        )
        return 2
    removed = tidy_completed_run(root)
    print(TIDY_SUMMARY)
    for rel in removed:
        print(f"  - {rel}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("start", help="Begin a NEW run — resets the board")
    st.add_argument("root", type=Path)
    st.add_argument("--agent", default=None, help="Harness running this session (defaults to the probe), e.g. opencode")
    st.add_argument("--model", default=None, help="Model id for this session (or WEB2HTML_MODEL), e.g. claude-fable-5.1")
    rs = sub.add_parser(
        "resume",
        help="Continue an existing run in a new session (never resets)",
    )
    rs.add_argument("root", type=Path)
    rs.add_argument("--at", default=None, help="Step this session picks up at, e.g. 2.1. Omit to detect it from the board (active step, else first pending)")
    rs.add_argument("--owner", required=True, help="Session name for the controller lease, e.g. session-2")
    rs.add_argument("--agent", default=None, help="Harness running this session (defaults to the probe), e.g. claude-code")
    rs.add_argument("--model", default=None, help="Model id for this session (or WEB2HTML_MODEL), e.g. claude-fable-5.1")
    tm = sub.add_parser("timing", help="Per-step started / finished / duration and the run total (sum of step durations, not wall clock)")
    tm.add_argument("root", type=Path)
    tm.add_argument("--json", action="store_true", dest="as_json")
    mk = sub.add_parser("mark")
    mk.add_argument("root", type=Path)
    mk.add_argument("--step", required=True)
    mk.add_argument("--status", required=True, choices=sorted(STATUSES - {"skipped"}))
    mk.add_argument("--reason", default=None)
    mk.add_argument("--expected-revision", type=int, default=None)
    mk.add_argument("--owner", default=None)
    mk.add_argument("--agent", default=None, help="Override the agent recorded for this step")
    mk.add_argument("--model", default=None, help="Override the model recorded for this step")
    sk = sub.add_parser("skip")
    sk.add_argument("root", type=Path)
    sk.add_argument("--step", required=True)
    sk.add_argument("--reason", default="skipped")
    ls = sub.add_parser("ids")
    oc = sub.add_parser("open-capture", help="Re-open the browser on the stamped Capture Tool URL (paperFileId + projectRoot); mark 1.4 active already does this once")
    oc.add_argument("root", type=Path)
    cd = sub.add_parser("capture-doctor", help="Check the Capture Tool native bridge (manifest per browser, launcher node, host version). FAIL = side panel OFFLINE")
    cd.add_argument("root", type=Path, nargs="?", default=None)
    ho = sub.add_parser("handoff", help="Print a copy-ready next-session prompt (does not mark the step done)")
    ho.add_argument("root", type=Path)
    rp = sub.add_parser("restamp", help="Rewrite pipeline.html without changing step status (Capture Tool URL)")
    rp.add_argument("root", type=Path)
    sy = sub.add_parser("sync", help="Catch the live board up from artifacts (never 1.4 / 3.4)")
    sy.add_argument("root", type=Path)
    fn = sub.add_parser(
        "finish",
        help="After 3.4: drop QA/capture/scrape trees; keep rebuild/ + pipeline.html",
    )
    fn.add_argument("root", type=Path)
    cl = sub.add_parser("claim-controller", help="Claim the sole run mutation lease")
    cl.add_argument("root", type=Path)
    cl.add_argument("--owner", required=True)
    cl.add_argument("--expected-revision", type=int, required=True)
    rl = sub.add_parser("release-controller", help="Release the run mutation lease after reviewer waves settle")
    rl.add_argument("root", type=Path)
    rl.add_argument("--owner", required=True)
    rl.add_argument("--expected-revision", type=int, required=True)
    ry = sub.add_parser(
        "relay",
        help="Mid-session handoff at a receipt boundary to a fresh agent of the SAME source (Orca terminal when reachable, else print the prompt). Not a human stop.",
    )
    ry.add_argument("root", type=Path)
    ry.add_argument("--owner", required=True, help="the controller lease you hold, e.g. session-2")
    ry.add_argument("--adapter", default="auto", choices=RELAY_ADAPTERS)
    ry.add_argument("--reason", default="", help="why (context budget, operator call)")
    ry.add_argument("--force", action="store_true", help="relay even with an unrecorded round or a wave in flight")
    args = ap.parse_args(argv)
    if args.cmd == "ids":
        for sid, title in STEPS:
            print(f"{sid}\t{title}")
        return 0
    if args.cmd == "start":
        return cmd_start(args.root, args.agent, args.model)
    if args.cmd == "resume":
        return cmd_resume(args.root, args.at, args.owner, args.agent, args.model)
    if args.cmd == "timing":
        return cmd_timing(args.root, args.as_json)
    if args.cmd == "skip":
        if args.step not in OPTIONAL_STEPS:
            print("FAIL: never skip a required step (Pitfall #98). Hover, 1.4, semantics, and polish are required.", file=sys.stderr)
            return 2
        return cmd_mark(args.root, args.step, "skipped", args.reason, None, None)
    if args.cmd == "open-capture":
        return cmd_open_capture(args.root)
    if args.cmd == "capture-doctor":
        return cmd_capture_doctor(args.root)
    if args.cmd == "handoff":
        return cmd_handoff(args.root)
    if args.cmd == "restamp":
        return cmd_restamp(args.root)
    if args.cmd == "sync":
        return cmd_sync(args.root)
    if args.cmd == "finish":
        return cmd_finish(args.root)
    if args.cmd == "claim-controller":
        return claim_controller(args.root, args.owner, args.expected_revision)
    if args.cmd == "release-controller":
        return release_controller(args.root, args.owner, args.expected_revision)
    if args.cmd == "relay":
        return cmd_relay(args.root, args.owner, args.adapter, args.reason, args.force)
    return cmd_mark(args.root, args.step, args.status, args.reason, args.expected_revision, args.owner, args.agent, args.model)


if __name__ == "__main__":
    raise SystemExit(main())
