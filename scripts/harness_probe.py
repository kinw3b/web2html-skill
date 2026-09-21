#!/usr/bin/env python3
"""Detect the harness /web2html is running in, and whether Orca can accelerate it.

Run once after `pipeline-progress.py start|resume`. Prints JSON, writes
qa/harness-probe.json when a project root is given, and ALWAYS exits 0.
Nothing here is a gate: a missing `orca`, an unreachable runtime, or an
unknown harness only lowers the adapter rung. The pipeline's own rules
(lease, gates, receipts, human stops) are identical on every rung
(Pitfall #219).

  python3 harness_probe.py /path/to/templates/<project>          # JSON + qa/harness-probe.json
  python3 harness_probe.py --brief                               # one line

Adapter rungs (best available wins, never a question to the human):
  waves  orca-workers  → subagent → serial
  relay  orca-terminal → print-prompt

Same-source rule (Pitfall #220): Orca workers and relay terminals run the
SAME agent as the orchestrator that summoned /web2html. The agent comes from
Orca's own view of this terminal (`terminal show` → agentIdentity), else the
harness marker, else WEB2HTML_ORCA_AGENT. Unknown agent → Orca rungs are off.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

GENERATED_FROM = "web2html/harness-probe/v1"
CLI_TIMEOUT_S = 8

# harness id → Orca agent id that launches the same LLM source
HARNESS_AGENT = {
    "claude-code": "claude",
    "codex": "codex",
    "cursor": "cursor",
    "opencode": "opencode",
    "gemini": "gemini",
    "grok": "grok",
    "omp": "omp",
    "pi": "pi",
    "hermes": None,  # no Orca launcher id known; Orca rungs stay off
    "generic": None,
}
# Orca agent id → command that starts that agent in a fresh terminal
AGENT_COMMAND = {
    "claude": "claude",
    "codex": "codex",
    "cursor": "cursor-agent",
    "opencode": "opencode",
    "gemini": "gemini",
    "grok": "grok",
    "omp": "omp",
    "pi": "pi",
}
SKILL_DIRS = (
    "~/.claude/skills",
    "~/.agents/skills",
    "~/.codex/skills",
    "~/.cursor/skills",
    "~/.hermes/skills",
)

Runner = Callable[[list[str]], tuple[int, str]]


def _run(argv: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=CLI_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout


def _json(text: str) -> dict:
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def detect_harness(env: dict) -> str:
    """Explicit markers only. OPENCODE_* is exported by Orca too, so it never wins alone."""
    if env.get("CLAUDECODE") or env.get("CLAUDE_CODE_SESSION_ID") or env.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude-code"
    if any(k.startswith("CODEX_") for k in env):
        return "codex"
    if env.get("CURSOR_AGENT") or any(k.startswith("CURSOR_") for k in env):
        return "cursor"
    if any(k.startswith("HERMES_") for k in env):
        return "hermes"
    if env.get("GEMINI_CLI") or any(k.startswith("GEMINI_CLI") for k in env):
        return "gemini"
    if any(k.startswith("OPENCODE_") for k in env) and not env.get("ORCA_OPENCODE_CONFIG_DIR"):
        return "opencode"
    return "generic"


def resolve_orca_cli(env: dict, system: str | None = None) -> str | None:
    """The one executable to use for the whole session (orca-cli stub rules)."""
    system = system or platform.system()
    if env.get("ORCA_CLI_COMMAND"):
        return env["ORCA_CLI_COMMAND"]
    path = env.get("PATH", os.environ.get("PATH", ""))
    if not path:
        return None

    def which(name: str) -> str | None:
        return shutil.which(name, path=path)

    if env.get("ORCA_DEV_REPO_ROOT"):
        return which("orca-dev")
    if system == "Linux" and not env.get("ORCA_TERMINAL_HANDLE"):
        # Bare `orca` outside Orca's terminals is the GNOME screen reader.
        return which("orca-ide")
    return which("orca")


def skills_present(env: dict) -> dict:
    roots = [env.get("SKILLS")] if env.get("SKILLS") else []
    roots += [os.path.expanduser(p) for p in SKILL_DIRS]
    found = {"orchestration": False, "orca-cli": False}
    for root in roots:
        for name in found:
            if not found[name] and root and (Path(root) / name / "SKILL.md").is_file():
                found[name] = True
    return found


def probe_orca(env: dict, run: Runner = _run) -> dict:
    cli = resolve_orca_cli(env)
    out = {
        "present": bool(cli),
        "cli": cli,
        "reachable": False,
        "version": None,
        "worktree": env.get("ORCA_WORKTREE_ID") or None,
        "terminal": env.get("ORCA_TERMINAL_HANDLE") or None,
        "agentIdentity": None,
        "run": None,
        "capabilities": [],
        "skills": skills_present(env),
        "error": None,
    }
    if not cli:
        return out
    code, text = run([cli, "status", "--json"])
    status = _json(text)
    runtime = (status.get("result") or {}).get("runtime") or {}
    if code != 0 or not runtime.get("reachable"):
        out["error"] = "runtime not reachable" if code == 0 else f"status exit {code}"
        return out
    out["reachable"] = True
    out["version"] = runtime.get("appVersion") or env.get("ORCA_APP_VERSION")
    out["capabilities"] = [c for c in (runtime.get("capabilities") or []) if isinstance(c, str)]
    if out["terminal"]:
        code, text = run([cli, "terminal", "show", "--terminal", out["terminal"], "--json"])
        term = ((_json(text).get("result") or {}).get("terminal") or {}) if code == 0 else {}
        out["agentIdentity"] = term.get("agentIdentity") or None
        if not out["worktree"]:
            out["worktree"] = term.get("worktreeId") or None
    if not out["worktree"]:
        code, text = run([cli, "worktree", "current", "--json"])
        wt = ((_json(text).get("result") or {}).get("worktree") or {}) if code == 0 else {}
        out["worktree"] = wt.get("id") or None
    code, text = run([cli, "orchestration", "run-current", "--json"])
    if code == 0:
        run_row = (_json(text).get("result") or {}).get("run")
        out["run"] = (run_row or {}).get("id") if isinstance(run_row, dict) else None
    return out


def choose_agent(harness: str, orca: dict, env: dict) -> tuple[str | None, str]:
    """Same-source rule: which Orca agent id launches the orchestrator's own LLM."""
    if env.get("WEB2HTML_ORCA_AGENT"):
        return env["WEB2HTML_ORCA_AGENT"], "env WEB2HTML_ORCA_AGENT"
    if orca.get("agentIdentity"):
        return str(orca["agentIdentity"]), "orca terminal show → agentIdentity"
    mapped = HARNESS_AGENT.get(harness)
    if mapped:
        return mapped, f"harness marker {harness}"
    return None, "unknown — Orca rungs off (Pitfall #220)"


def choose_adapters(harness: str, orca: dict, agent: str | None) -> dict:
    orca_ok = bool(orca.get("reachable") and agent and orca.get("worktree"))
    waves = "orca" if orca_ok else ("subagent" if harness == "claude-code" else "serial")
    relay = "orca-terminal" if orca_ok else "print-prompt"
    return {"waves": waves, "relay": relay}


def probe(env: dict | None = None, run: Runner = _run, root: Path | None = None) -> dict:
    env = dict(os.environ if env is None else env)
    harness = detect_harness(env)
    orca = probe_orca(env, run)
    agent, agent_source = choose_agent(harness, orca, env)
    report = {
        "generatedFrom": GENERATED_FROM,
        "harness": harness,
        "agent": agent,
        "agentSource": agent_source,
        "agentCommand": (env.get("WEB2HTML_RELAY_COMMAND") or AGENT_COMMAND.get(agent or "", agent)) if agent else None,
        "orca": orca,
        "adapters": choose_adapters(harness, orca, agent),
        "context": None,
    }
    try:
        import context_budget  # sibling script; optional

        report["context"] = context_budget.budget(root, env)
    except Exception:  # noqa: BLE001 — the probe never fails
        report["context"] = None
    return report


def brief(report: dict) -> str:
    orca = report.get("orca") or {}
    orca_word = "reachable" if orca.get("reachable") else ("present, not reachable" if orca.get("present") else "absent")
    ctx = report.get("context") or {}
    ctx_word = f" · context {ctx.get('usedPct')}% ({ctx.get('source')})" if ctx.get("usedPct") is not None else ""
    ad = report.get("adapters") or {}
    return (
        f"harness {report.get('harness')} · agent {report.get('agent') or '?'} · orca {orca_word}"
        f" · waves {ad.get('waves')} · relay {ad.get('relay')}{ctx_word}"
    )


def write_report(root: Path, report: dict) -> Path | None:
    qa = root.resolve() / "qa"
    if not qa.is_dir():
        return None
    dest = qa / "harness-probe.json"
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return dest


def load_report(root: Path) -> dict | None:
    path = root.resolve() / "qa" / "harness-probe.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path, nargs="?", default=None, help="project root; writes qa/harness-probe.json")
    ap.add_argument("--brief", action="store_true", help="one line instead of JSON")
    args = ap.parse_args(argv)
    try:
        report = probe(root=args.root)
        if args.root is not None:
            write_report(args.root, report)
        print(brief(report) if args.brief else json.dumps(report, indent=2))
    except Exception as exc:  # noqa: BLE001 — never block the run
        print(json.dumps({"generatedFrom": GENERATED_FROM, "harness": "generic", "agent": None,
                          "adapters": {"waves": "serial", "relay": "print-prompt"}, "error": str(exc)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
