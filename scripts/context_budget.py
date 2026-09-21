#!/usr/bin/env python3
"""How much of this session's context window is spent — best available signal.

No harness hands a running skill a clean "percent used". So this reads a
ladder of optional signals and reports the first that answers; every rung
is optional and the script never raises (Pitfall #219).

  1  transcript   Claude Code only. Last assistant `usage` in
                  ~/.claude/projects/*/$CLAUDE_CODE_SESSION_ID.jsonl:
                  input + cache_read + cache_creation ≈ live context.
                  Format is undocumented → parsed defensively.
  2  sidecar      Opt-in. WEB2HTML_CONTEXT_SIDECAR or
                  ~/.web2html/ctx/<session>.json written by a statusline wrapper.
  3  estimator    Every harness. A spend ledger in qa/pipeline-progress.json
                  fed by the pipeline's own boundaries (shoot / record / mark /
                  reference loads). Self-calibrates against rung 1 when present.

Window: WEB2HTML_CONTEXT_WINDOW, else `[1m]` on the Claude Code model setting
→ 1,000,000, else 200,000. Thresholds: WEB2HTML_RELAY_ARM (50) arms a relay at
the next receipt boundary; WEB2HTML_RELAY_FORCE (75) relays right after the
current record.

  python3 context_budget.py /path/to/project            # JSON
  python3 context_budget.py /path/to/project --add-spend shoot
  python3 context_budget.py /path/to/project --add-spend reference --bytes 18000
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_WINDOW = 200_000
BIG_WINDOW = 1_000_000
ARM_PCT = 50
FORCE_PCT = 75
BASE_TOKENS = 40_000  # system prompt + skill + first references, before any step
# Rough per-event costs in tokens. A 1600px side-by-side read ≈ 2.5k; kept
# deliberately coarse and corrected by calibration when a real signal exists.
SPEND = {
    "shoot": 3 * 2_500,   # three side PNGs Read
    "record": 800,
    "mark": 600,
    "reference": 0,       # bytes / 4
    "dump": 0,            # bytes / 4
    "tool": 300,
}
TAIL_BYTES = 768 * 1024


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resolve_window(env: dict, settings_path: Path | None = None) -> tuple[int, str]:
    raw = env.get("WEB2HTML_CONTEXT_WINDOW")
    if raw:
        try:
            return max(int(raw), 1), "env WEB2HTML_CONTEXT_WINDOW"
        except ValueError:
            pass
    path = settings_path or Path(env.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")) / "settings.json"
    try:
        model = str(json.loads(path.read_text(encoding="utf-8")).get("model") or "")
    except (OSError, ValueError, AttributeError):
        model = ""
    if "[1m]" in model.lower():
        return BIG_WINDOW, f"model {model}"
    return DEFAULT_WINDOW, "default"


def _last_assistant_usage(path: Path) -> dict | None:
    """Read the tail of a Claude Code transcript; return the last assistant usage."""
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            fh.seek(max(0, size - TAIL_BYTES))
            chunk = fh.read()
    except OSError:
        return None
    for raw in reversed(chunk.split(b"\n")):
        if b'"assistant"' not in raw or b'"usage"' not in raw:
            continue
        try:
            row = json.loads(raw.decode("utf-8", errors="replace"))
        except ValueError:
            continue
        if row.get("type") != "assistant":
            continue
        usage = (row.get("message") or {}).get("usage")
        if isinstance(usage, dict):
            return usage
    return None


def transcript_tokens(env: dict) -> int | None:
    sid = env.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        return None
    base = env.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    for path in glob.glob(os.path.join(base, "projects", "*", f"{sid}.jsonl")):
        usage = _last_assistant_usage(Path(path))
        if usage is None:
            continue
        total = 0
        for key in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            value = usage.get(key)
            if isinstance(value, (int, float)):
                total += int(value)
        if total > 0:
            return total
    return None


def sidecar_tokens(env: dict, window: int) -> int | None:
    sid = env.get("CLAUDE_CODE_SESSION_ID") or env.get("WEB2HTML_SESSION_ID") or ""
    candidates = [env.get("WEB2HTML_CONTEXT_SIDECAR")] if env.get("WEB2HTML_CONTEXT_SIDECAR") else []
    if sid:
        candidates.append(os.path.expanduser(f"~/.web2html/ctx/{sid}.json"))
    for cand in candidates:
        try:
            data = json.loads(Path(cand).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        cw = data.get("context_window") if isinstance(data.get("context_window"), dict) else data
        for key in ("used_tokens", "current_usage", "usedTokens"):
            value = cw.get(key) if isinstance(cw, dict) else None
            if isinstance(value, dict):
                value = sum(v for v in value.values() if isinstance(v, (int, float)))
            if isinstance(value, (int, float)) and value > 0:
                return int(value)
        for key in ("used_percentage", "usedPct"):
            value = cw.get(key) if isinstance(cw, dict) else None
            if isinstance(value, (int, float)) and value > 0:
                return int(window * float(value) / 100)
    return None


# ---------------------------------------------------------------- ledger ----

def _progress_path(root: Path) -> Path:
    return root.resolve() / "qa" / "pipeline-progress.json"


def _load(root: Path) -> dict | None:
    try:
        data = json.loads(_progress_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _save_ledger_only(root: Path, data: dict) -> None:
    """Write the ledger without bumping the controller revision (not a step mutation)."""
    path = _progress_path(root)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".budget-", delete=False) as tmp:
        tmp.write(json.dumps(data, indent=2) + "\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def ledger(data: dict) -> dict:
    owner = str((data.get("controller") or {}).get("owner") or "")
    row = data.get("budget")
    if not isinstance(row, dict) or row.get("owner") != owner:
        row = {"owner": owner, "spendTokens": 0, "events": 0, "calibration": 1.0, "startedAt": _now_iso()}
        data["budget"] = row
    return row


def add_spend(root: Path, kind: str, n: int = 1, nbytes: int = 0) -> int | None:
    """Best-effort ledger increment. Returns the new spend, or None if no run here."""
    try:
        data = _load(root)
        if data is None:
            return None
        row = ledger(data)
        cost = SPEND.get(kind, SPEND["tool"]) * max(n, 1) + (nbytes // 4)
        row["spendTokens"] = int(row.get("spendTokens") or 0) + cost
        row["events"] = int(row.get("events") or 0) + max(n, 1)
        row["updatedAt"] = _now_iso()
        _save_ledger_only(root, data)
        return row["spendTokens"]
    except Exception:  # noqa: BLE001
        return None


def estimator_tokens(root: Path | None) -> int | None:
    if root is None:
        return None
    data = _load(root)
    if data is None or not data.get("controller"):
        return None
    row = ledger(data)
    try:
        return int(BASE_TOKENS + float(row.get("calibration") or 1.0) * int(row.get("spendTokens") or 0))
    except (TypeError, ValueError):
        return BASE_TOKENS


def _calibrate(root: Path | None, truth: int) -> None:
    """When a real signal exists, remember truth/estimate so rung 3 tracks it later."""
    if root is None:
        return
    try:
        data = _load(root)
        if data is None or not data.get("controller"):
            return
        row = ledger(data)
        spend = int(row.get("spendTokens") or 0)
        if spend >= 5_000:
            row["calibration"] = round(max(0.2, min(5.0, (truth - BASE_TOKENS) / spend)), 3)
            row["calibratedAt"] = _now_iso()
            _save_ledger_only(root, data)
    except Exception:  # noqa: BLE001
        return


def thresholds(env: dict) -> tuple[int, int]:
    def pct(key: str, default: int) -> int:
        try:
            return min(max(int(env.get(key, default)), 1), 100)
        except (TypeError, ValueError):
            return default

    arm = pct("WEB2HTML_RELAY_ARM", ARM_PCT)
    force = max(pct("WEB2HTML_RELAY_FORCE", FORCE_PCT), arm)
    return arm, force


def budget(root: Path | None = None, env: dict | None = None) -> dict:
    """Never raises. {source, window, usedTokens, usedPct, arm, force, state, recommendation}."""
    env = dict(os.environ if env is None else env)
    try:
        window, window_source = resolve_window(env)
        arm, force = thresholds(env)
        source, used = "none", None
        tokens = transcript_tokens(env)
        if tokens is not None:
            source, used = "transcript", tokens
            _calibrate(root, tokens)
        if used is None:
            tokens = sidecar_tokens(env, window)
            if tokens is not None:
                source, used = "sidecar", tokens
        if used is None:
            tokens = estimator_tokens(root)
            if tokens is not None:
                source, used = "estimator", tokens
        pct = round(100.0 * used / window, 1) if used is not None else None
        if pct is None:
            state, rec = "unknown", "no context signal; relay only on step-count or operator call"
        elif pct >= force:
            state, rec = "force", f"relay now — {pct}% ≥ {force}% (finish the current record first)"
        elif pct >= arm:
            state, rec = "armed", f"relay at the next receipt boundary — {pct}% ≥ {arm}%"
        else:
            state, rec = "ok", "continue"
        return {
            "source": source, "window": window, "windowSource": window_source,
            "usedTokens": used, "usedPct": pct, "arm": arm, "force": force,
            "state": state, "recommendation": rec,
        }
    except Exception as exc:  # noqa: BLE001
        return {"source": "none", "window": None, "usedTokens": None, "usedPct": None,
                "arm": ARM_PCT, "force": FORCE_PCT, "state": "unknown", "recommendation": f"budget error: {exc}"}


def one_line(report: dict) -> str:
    pct = report.get("usedPct")
    if pct is None:
        return "budget: unknown (no context signal)"
    flag = {"armed": "  RELAY armed", "force": "  RELAY now"}.get(str(report.get("state")), "")
    return f"budget: {pct}% of {int(report.get('window') or 0) // 1000}k ({report.get('source')}){flag}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path, nargs="?", default=None)
    ap.add_argument("--add-spend", metavar="KIND", help=f"one of {sorted(SPEND)}")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--bytes", type=int, default=0)
    ap.add_argument("--brief", action="store_true")
    args = ap.parse_args(argv)
    if args.add_spend:
        total = add_spend(args.root, args.add_spend, args.n, args.bytes) if args.root else None
        print(f"spend +{args.add_spend} → {total if total is not None else 'no run here'}")
    report = budget(args.root)
    print(one_line(report) if args.brief else json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
