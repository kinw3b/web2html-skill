#!/usr/bin/env python3
"""One primary workspace folder per run — in Orca when Orca is there.

The first action of a NEW run, before `pipeline-progress.py start`: create the
run's project folder. When the Orca CLI is reachable the folder is also
registered in Orca as a project (folder context) so the run shows up in the
Orca app and its terminals; when Orca is absent or unreachable this is a plain
folder and the current agent simply continues in it. Either way exactly ONE
folder is ever created per run slug — `ensure` reuses the recorded workspace on
every later call (continued sessions, retries), never a second worktree.

  python3 orca_workspace.py ensure <slug> [--base <dir>]   # create or reuse, print RUN ROOT
  python3 orca_workspace.py show   <slug>                  # print the recorded RUN ROOT

The session continues on the printed RUN ROOT: `start`, `resume`, `mark` and
every gate take that path. Registration is best effort — an Orca failure leaves
a plain folder and never fails the run (Pitfall #219).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import harness_probe

WORKSPACE_FILE = Path("qa") / "orca-workspace.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _json(text: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def index_path(env: dict) -> Path:
    home = env.get("WEB2HTML_HOME") or "~/.web2html"
    return Path(os.path.expanduser(home)) / "orca-workspaces.json"


def load_index(env: dict) -> dict:
    path = index_path(env)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_index(env: dict, index: dict) -> None:
    path = index_path(env)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def sanitize_slug(slug: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", slug.strip()).strip("-.")
    return clean or "run"


def _register_in_orca(cli: str, root: Path, run) -> tuple[str | None, str | None]:
    """`repo add` the folder once. Returns (repoId, error)."""
    code, text = run([cli, "repo", "add", "--path", str(root), "--json"])
    payload = _json(text)
    result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    repo = result.get("repo") if isinstance(result.get("repo"), dict) else result
    repo_id = repo.get("id") or repo.get("repoId") or None
    if code != 0:
        return (str(repo_id) if repo_id else None), (text.strip() or f"repo add exit {code}")
    return (str(repo_id) if repo_id else None), None


def ensure(slug: str, base: Path | None = None, env: dict | None = None, run=None) -> dict:
    """Create or reuse the single primary workspace for `slug`. Prints RUN ROOT."""
    env = dict(os.environ if env is None else env)
    run = run or harness_probe._run
    slug = sanitize_slug(slug)
    index = load_index(env)
    recorded = index.get(slug)
    root = Path(recorded["path"]).resolve() if isinstance(recorded, dict) and recorded.get("path") else None
    if root is None:
        base = base or Path(env.get("WEB2HTML_WORKSPACE_BASE") or os.getcwd())
        root = (base / slug).resolve()

    orca = harness_probe.probe_orca(env, run=run)
    cli = orca.get("cli")
    reachable = bool(orca.get("reachable") and cli)

    reused = root.is_dir() and (root / WORKSPACE_FILE).is_file()
    record = None
    if (root / WORKSPACE_FILE).is_file():
        try:
            record = json.loads((root / WORKSPACE_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            record = None
    if not isinstance(record, dict):
        record = {}

    repo_id = record.get("repoId")
    note = ""
    root.mkdir(parents=True, exist_ok=True)
    if reachable and not repo_id:
        repo_id, error = _register_in_orca(cli, root, run)
        if repo_id:
            note = f"folder context {repo_id} registered"
        else:
            note = f"registration failed ({(error or 'unknown')[:80]}) — plain folder"

    record = {
        "slug": slug,
        "path": str(root),
        "orca": bool(reachable),
        "repoId": repo_id,
        "createdAt": record.get("createdAt") or _now_iso(),
        "updatedAt": _now_iso(),
    }
    (root / "qa").mkdir(parents=True, exist_ok=True)
    (root / WORKSPACE_FILE).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    index[slug] = record
    save_index(env, index)

    if reachable:
        head = f"orca reachable · {note or ('folder context ' + str(repo_id) + ' already registered' if repo_id else 'plain folder')}"
    else:
        head = "orca absent · plain folder — the current agent continues here"
        if cli and not reachable:
            head = "orca present, runtime not reachable · plain folder — the current agent continues here"
    if reused:
        head += " · reusing the run's single primary workspace"
    print(head)
    print(f"RUN ROOT {root}")
    return record


def show(slug: str, env: dict | None = None) -> int:
    env = dict(os.environ if env is None else env)
    slug = sanitize_slug(slug)
    recorded = load_index(env).get(slug)
    if not isinstance(recorded, dict) or not recorded.get("path"):
        print(f"FAIL: no workspace recorded for slug {slug!r}.", file=sys.stderr)
        return 2
    root = Path(recorded["path"])
    if not root.is_dir():
        print(f"FAIL: recorded workspace is gone: {root}", file=sys.stderr)
        return 2
    print(f"RUN ROOT {root.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("ensure", help="Create or reuse the run's single primary workspace folder")
    e.add_argument("slug")
    e.add_argument("--base", default=None, help="Parent dir for a new folder (default $WEB2HTML_WORKSPACE_BASE or cwd)")
    s = sub.add_parser("show", help="Print the recorded RUN ROOT for a slug")
    s.add_argument("slug")
    args = ap.parse_args(argv)
    if args.cmd == "ensure":
        ensure(args.slug, base=Path(args.base) if args.base else None)
        return 0
    return show(args.slug)


if __name__ == "__main__":
    raise SystemExit(main())
