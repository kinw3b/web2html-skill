#!/usr/bin/env python3
"""Open a pipeline document — live board, build review, polish report, built routes.

Order: Orca's embedded browser when this session runs inside a reachable Orca
(`orca tab create --url … --json`, file:// included), else the caller's own
fallback command (Chrome on macOS today, `open` / `xdg-open` otherwise).
Nothing here gates a step: a failed open only prints the URI (Pitfall #219).

  WEB2HTML_BROWSER=auto     Orca first, then the fallback (default)
  WEB2HTML_BROWSER=orca     Orca only; a miss prints the URI and returns False
  WEB2HTML_BROWSER=default  skip Orca, use the fallback

  python3 open_doc.py file:///path/to/pipeline.html [more URIs…]   # CLI: Orca else `open`

The Capture Tool (needs the Chromium extension) and Paper (its own app) keep
their own openers; this is for the HTML the pipeline itself writes.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

Runner = Callable[[list[str]], tuple[int, str]]
CLI_TIMEOUT_S = 15


def _run(argv: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=CLI_TIMEOUT_S)
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


def orca_cli(env: dict) -> str | None:
    """Only an Orca-managed terminal opens Orca tabs: the tab belongs to that worktree."""
    if not (env.get("ORCA_TERMINAL_HANDLE") or env.get("ORCA_WORKTREE_ID")):
        return None
    try:
        import harness_probe

        return harness_probe.resolve_orca_cli(env)
    except Exception:  # noqa: BLE001
        return env.get("ORCA_CLI_COMMAND") or None


def preference(env: dict) -> str:
    value = str(env.get("WEB2HTML_BROWSER") or "auto").strip().lower()
    return value if value in {"auto", "orca", "default"} else "auto"


def open_in_orca(uri: str, env: dict | None = None, run: Runner = _run) -> dict:
    env = dict(os.environ if env is None else env)
    cli = orca_cli(env)
    if not cli:
        return {"opened": False, "error": "not inside an Orca terminal"}
    argv = [cli, "tab", "create", "--url", uri, "--json"]
    if env.get("ORCA_WORKTREE_ID"):
        argv[3:3] = ["--worktree", f"id:{env['ORCA_WORKTREE_ID']}"]
    code, text = run(argv)
    try:
        body = json.loads(text)
    except (TypeError, ValueError):
        body = {}
    page = _dig(body, "browserPageId", "pageId", "page_id") if code == 0 else None
    if code != 0 or not page:
        return {"opened": False, "error": f"orca tab create exit {code}" if code else "no browserPageId in receipt"}
    return {"opened": True, "pageId": str(page)}


def default_fallback(uri: str) -> list[str] | None:
    if sys.platform == "darwin":
        return ["open", uri]
    if sys.platform.startswith("linux"):
        return ["xdg-open", uri]
    return None


def open_doc(
    uri: str,
    fallback: Sequence[str] | None = None,
    *,
    env: dict | None = None,
    run: Runner = _run,
    call: Callable[[list[str]], int] = lambda argv: subprocess.call(argv),
) -> dict:
    """Open one URI. Returns {"opened", "via": "orca"|"fallback"|"none", "pageId"?, "error"?}."""
    env = dict(os.environ if env is None else env)
    pref = preference(env)
    if pref != "default":
        result = open_in_orca(uri, env, run)
        if result.get("opened"):
            return {"opened": True, "via": "orca", "pageId": result.get("pageId")}
        if pref == "orca":
            return {"opened": False, "via": "none", "error": result.get("error")}
        orca_error = result.get("error")
    else:
        orca_error = "WEB2HTML_BROWSER=default"
    argv = list(fallback) if fallback else default_fallback(uri)
    if not argv:
        return {"opened": False, "via": "none", "error": f"no opener on {sys.platform}; {orca_error}"}
    try:
        code = call(argv)
    except OSError as exc:
        return {"opened": False, "via": "none", "error": str(exc)}
    return {"opened": code == 0, "via": "fallback" if code == 0 else "none", "error": None if code == 0 else f"fallback exit {code}"}


def open_docs(uris: Sequence[str], fallback: Sequence[str] | None = None, **kw) -> list[dict]:
    """Open several URIs. In Orca each gets its own tab; a multi-URI fallback (Chrome takes many) runs once."""
    env = dict(os.environ if kw.get("env") is None else kw["env"])
    kw["env"] = env
    if preference(env) != "default":
        results = [open_doc(uri, None, **{**kw, "call": lambda argv: 1}) for uri in uris]
        if all(r["via"] == "orca" for r in results):
            return results
        if preference(env) == "orca":
            return results
    argv = list(fallback) if fallback else None
    if argv is None:
        return [open_doc(uri, None, **{**kw, "env": {**env, "WEB2HTML_BROWSER": "default"}}) for uri in uris]
    call = kw.get("call") or (lambda a: subprocess.call(a))
    try:
        code = call(argv)
    except OSError as exc:
        return [{"opened": False, "via": "none", "error": str(exc)} for _ in uris]
    via = "fallback" if code == 0 else "none"
    return [{"opened": code == 0, "via": via, "error": None if code == 0 else f"fallback exit {code}"} for _ in uris]


def describe(result: dict) -> str:
    if result.get("via") == "orca":
        return "Orca browser"
    if result.get("via") == "fallback":
        return "default browser"
    return f"not opened ({result.get('error')})"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    uris = [Path(a).resolve().as_uri() if not a.startswith(("file:", "http:", "https:")) else a for a in args]
    rc = 0
    for uri, result in zip(uris, open_docs(uris)):
        print(f"{describe(result)}: {uri}")
        rc = rc or (0 if result.get("opened") else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
