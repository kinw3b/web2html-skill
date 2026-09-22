#!/usr/bin/env python3
"""Run intake — qa/run-config.json is the run's contract (2.24.0).

Three questions, asked ONCE right after `pipeline-progress.py start`, before
1.1 goes active. `mark --step 1.1 --status active` refuses without this file.

  python3 run_config.py intake <project> --source none|/abs/path --checkpoints human|auto --speed full|fast
  python3 run_config.py show   <project>

Question 1 — source folder.  `--source none` (pull from the public URL) or an
absolute folder holding the site's HTML export. The folder is COPIED into
<project>/source-html/ so the project is self-contained (tidy keeps it) and
classified:

  clean-html      Webflow export / static build: an index.html whose markup is
                  the page (data-wf-page, plain sections). 2.2 authors in PORT
                  mode — source DOM order, copy, links, alt text are the
                  structural truth; Paper stays the visual truth.
  framework-dump  _next/, __NEXT_DATA__, _nuxt/, Framer runtime, an empty React
                  root. Not portable markup. 2.2 authors as usual; the folder is
                  a copy/structure reference only.
  none            no source; 2.2 authors from Paper (today's behaviour).

Question 2 — checkpoints.  `human` keeps 1.4 / 2.4 / 3.4 as stops. `auto`
self-accepts 1.4 and 2.4 (receipts stamped auto-accepted, nothing opened for
nobody, the handoff prompt still lands in qa/ for a relay). 3.4 ALWAYS stops —
no flag turns it off; 4.x / 5.x build on the 3.4 result and need a human.

Question 3 — speed.  `full` is the whole pipeline. `fast` forces
checkpoints=auto and:

  1.2   captures 1600 + 390 only (no tablet); Screenshots board + section clips
        + stretch-root postflight stay.
  1.3   skipped (qa/design-library-skipped.json). No Design Library, no
        Buttons/Components pull.
  2.1   skipped. Fonts still self-host from source-site/assets (emit_fonts
        fast path) into rebuild/css/fonts.css.
  2.2   strict author: no get_jsx / index-raw.html; the token-binding gate is
        off (there are no 1.3 tokens). Markup gates stay on.
  2.3   kept, at the configured widths, disk clips + wave.py LOOK; the
        raw-census requirement is off.
  3.2   button hover comes from source CSS directly (source_hover_light.py)
        instead of the 1.3 receipt.
  3.1 / 3.3 / 3.4 unchanged.

Widths become data: `widths` in the config (default [1600, 768, 390]; fast
[1600, 390]). Every 2.3 gate reads them from here instead of a constant.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

GENERATED_FROM = "web2html/run-config/v1"
CONFIG = Path("qa/run-config.json")
SOURCE_DIR = Path("source-html")
DESIGN_LIBRARY_SKIPPED = Path("qa/design-library-skipped.json")
DESIGN_SYSTEM_SKIPPED = Path("qa/design-system-skipped.json")

SOURCE_KINDS = ("none", "clean-html", "framework-dump")
CHECKPOINTS = ("human", "auto")
SPEEDS = ("full", "fast")
FULL_WIDTHS = (1600, 768, 390)
FAST_WIDTHS = (1600, 390)
# 3.4 is never automatic. Steps 4.x / 5.x author from the 3.4 result and need a
# human to sign it. Nothing in the config can add 3.4 to this set.
AUTO_ACCEPTABLE = frozenset({"1.4", "2.4"})

# Markers that mean "the HTML on disk is not the page" — a framework runtime
# hydrates it, so its DOM is not portable structure.
FRAMEWORK_DIR_MARKERS = ("_next", "_nuxt", ".next", ".nuxt", "_astro", "__sveltekit", "_expo")
FRAMEWORK_HTML_RE = re.compile(
    r"__NEXT_DATA__|__NUXT__|__remixContext|__SVELTEKIT|__gatsby|"
    r"data-reactroot|id=[\"']__next[\"']|id=[\"']___gatsby[\"']|"
    r"framerusercontent\.com/sites|data-framer-|"
    r"<div id=[\"']root[\"']>\s*</div>|<div id=[\"']app[\"']>\s*</div>",
    re.I,
)
# Webflow exports carry these on <html> / sections. A plain static build has
# none of them but still passes as clean when its body has real sections.
CLEAN_HTML_RE = re.compile(r"data-wf-page|data-wf-site|class=[\"'][^\"']*\bw-(?:container|section|nav)\b", re.I)
SECTION_RE = re.compile(r"<(?:section|header|footer|main|nav|article)\b", re.I)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def config_path(root: Path) -> Path:
    return root.resolve() / CONFIG


def default_config() -> dict:
    """What a run behaves like when no intake was recorded (legacy boards)."""
    return {
        "generatedFrom": GENERATED_FROM,
        "source": {"kind": "none", "path": None, "dir": None, "indexHtml": None, "markers": []},
        "checkpoints": "human",
        "speed": "full",
        "widths": list(FULL_WIDTHS),
        "designLibrary": True,
        "designSystem": True,
        "rawDump": True,
        "recordedAt": None,
    }


def load(root: Path) -> dict:
    """Config or the default. Never raises; a malformed file reads as default."""
    path = config_path(root)
    base = default_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return base
    if not isinstance(data, dict) or data.get("generatedFrom") != GENERATED_FROM:
        return base
    merged = {**base, **data}
    merged["widths"] = normalize_widths(merged.get("widths"))
    if merged.get("speed") == "fast":
        merged["checkpoints"] = "auto"
    return merged


def exists(root: Path) -> bool:
    return config_path(root).is_file() and load(root).get("recordedAt") is not None


def normalize_widths(raw: object) -> list[int]:
    out: list[int] = []
    if isinstance(raw, (list, tuple)):
        for item in raw:
            try:
                width = int(item)
            except (TypeError, ValueError):
                continue
            if width > 0 and width not in out:
                out.append(width)
    out.sort(reverse=True)
    return out or list(FULL_WIDTHS)


def widths(root: Path) -> tuple[int, ...]:
    return tuple(load(root)["widths"])


def width_keys(root: Path) -> tuple[str, ...]:
    return tuple(str(w) for w in widths(root))


def is_fast(root: Path) -> bool:
    return load(root).get("speed") == "fast"


def checkpoints_auto(root: Path) -> bool:
    return load(root).get("checkpoints") == "auto"


def auto_accepts(root: Path, step: str) -> bool:
    """True when this checkpoint self-accepts. 3.4 never does."""
    return step in AUTO_ACCEPTABLE and checkpoints_auto(root)


def design_library_enabled(root: Path) -> bool:
    return bool(load(root).get("designLibrary", True))


def design_system_enabled(root: Path) -> bool:
    return bool(load(root).get("designSystem", True))


def raw_dump_enabled(root: Path) -> bool:
    return bool(load(root).get("rawDump", True))


def source_kind(root: Path) -> str:
    return str((load(root).get("source") or {}).get("kind") or "none")


def source_index(root: Path) -> Path | None:
    rel = (load(root).get("source") or {}).get("indexHtml")
    if not rel:
        return None
    path = root.resolve() / str(rel)
    return path if path.is_file() else None


def port_mode(root: Path) -> bool:
    """2.2 authors in PORT mode: a clean HTML source is the structural truth."""
    return source_kind(root) == "clean-html" and source_index(root) is not None


# ---------------------------------------------------------------- classify --


def _find_index(folder: Path) -> Path | None:
    for name in ("index.html", "index.htm"):
        hit = folder / name
        if hit.is_file():
            return hit
    hits = sorted(folder.rglob("index.html"))
    return hits[0] if hits else None


def classify_source(folder: Path) -> dict:
    """Decide clean-html vs framework-dump for a folder on disk."""
    folder = folder.resolve()
    markers: list[str] = []
    for name in FRAMEWORK_DIR_MARKERS:
        if (folder / name).is_dir():
            markers.append(f"dir:{name}")
    index = _find_index(folder)
    html = ""
    if index is not None:
        try:
            html = index.read_text(encoding="utf-8", errors="replace")
        except OSError:
            html = ""
    for match in FRAMEWORK_HTML_RE.finditer(html):
        token = match.group(0)[:40]
        if f"html:{token}" not in markers:
            markers.append(f"html:{token}")
    sections = len(SECTION_RE.findall(html))
    webflow = bool(CLEAN_HTML_RE.search(html))
    if index is None or not html.strip():
        kind = "framework-dump"
        reason = "no readable index.html"
    elif markers:
        kind = "framework-dump"
        reason = "framework runtime markers: " + ", ".join(markers[:4])
    elif webflow or sections >= 2:
        kind = "clean-html"
        reason = "Webflow export" if webflow else f"{sections} semantic landmarks in static markup"
    else:
        kind = "framework-dump"
        reason = f"only {sections} landmark(s); markup does not read as the page"
    return {
        "kind": kind,
        "reason": reason,
        "markers": markers,
        "indexHtml": index.relative_to(folder).as_posix() if index else None,
        "webflow": webflow,
        "landmarks": sections,
    }


def copy_source(root: Path, src: Path) -> Path:
    """Copy the human's folder into <project>/source-html/ (fresh each intake)."""
    root = root.resolve()
    src = src.resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"source folder does not exist: {src}")
    if root == src or root in src.parents:
        raise ValueError("source folder must live outside the project folder")
    dest = root / SOURCE_DIR
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(".git", "node_modules", ".DS_Store", "__pycache__"),
        symlinks=False,
    )
    return dest


# ------------------------------------------------------------------ intake --


def build_config(*, source_kind_: str, source_path: str | None, source_meta: dict | None,
                 checkpoints: str, speed: str) -> dict:
    if checkpoints not in CHECKPOINTS:
        raise ValueError(f"checkpoints must be one of {CHECKPOINTS}")
    if speed not in SPEEDS:
        raise ValueError(f"speed must be one of {SPEEDS}")
    if source_kind_ not in SOURCE_KINDS:
        raise ValueError(f"source kind must be one of {SOURCE_KINDS}")
    fast = speed == "fast"
    if fast:
        checkpoints = "auto"  # a fast run never stops before 3.4
    meta = source_meta or {}
    return {
        "generatedFrom": GENERATED_FROM,
        "source": {
            "kind": source_kind_,
            "path": source_path,
            "dir": SOURCE_DIR.as_posix() if source_kind_ != "none" else None,
            "indexHtml": (
                f"{SOURCE_DIR.as_posix()}/{meta['indexHtml']}" if meta.get("indexHtml") and source_kind_ != "none" else None
            ),
            "reason": meta.get("reason"),
            "markers": list(meta.get("markers") or []),
        },
        "checkpoints": checkpoints,
        "speed": speed,
        "widths": list(FAST_WIDTHS if fast else FULL_WIDTHS),
        "designLibrary": not fast,
        "designSystem": not fast,
        "rawDump": not fast,
        "humanStops": ["3.4"] if checkpoints == "auto" else ["1.4", "2.4", "3.4"],
        "recordedAt": _now_iso(),
    }


def write(root: Path, config: dict) -> Path:
    dest = config_path(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    if not config.get("designLibrary", True):
        (root / DESIGN_LIBRARY_SKIPPED).write_text(
            json.dumps({"generatedFrom": GENERATED_FROM, "step": "1.3", "reason": "fast run — no Design Library", "recordedAt": _now_iso()}, indent=2) + "\n",
            encoding="utf-8",
        )
    if not config.get("designSystem", True):
        (root / DESIGN_SYSTEM_SKIPPED).write_text(
            json.dumps({"generatedFrom": GENERATED_FROM, "step": "2.1", "reason": "fast run — no Design System page", "recordedAt": _now_iso()}, indent=2) + "\n",
            encoding="utf-8",
        )
    return dest


def intake(root: Path, *, source: str, checkpoints: str, speed: str) -> dict:
    root = root.resolve()
    source = (source or "none").strip()
    if source.lower() in {"", "none", "no", "public", "url"}:
        kind, path, meta = "none", None, None
    else:
        src = Path(source).expanduser()
        copy_source(root, src)
        meta = classify_source(root / SOURCE_DIR)
        kind, path = meta["kind"], str(src.resolve())
    config = build_config(source_kind_=kind, source_path=path, source_meta=meta, checkpoints=checkpoints, speed=speed)
    write(root, config)
    return config


def summary_lines(config: dict) -> list[str]:
    src = config.get("source") or {}
    kind = src.get("kind") or "none"
    lines = [
        f"run-config: speed={config.get('speed')}  checkpoints={config.get('checkpoints')}  widths={'/'.join(str(w) for w in config.get('widths') or [])}",
    ]
    if kind == "none":
        lines.append("source: none — 2.2 authors from Paper")
    else:
        lines.append(f"source: {kind} ← {src.get('path')}  ({src.get('reason')})")
        lines.append(
            "2.2: PORT mode — source DOM order / copy / links are structural truth; Paper is visual truth"
            if kind == "clean-html"
            else "2.2: author from Paper; source-html/ is a copy + structure reference only"
        )
    if config.get("speed") == "fast":
        lines.append("fast: 1.3 + 2.1 skipped · no index-raw · 2.3 at 1600/390 · 3.2 hover from source CSS")
    stops = config.get("humanStops") or ["1.4", "2.4", "3.4"]
    lines.append("human stops: " + " ".join(stops) + ("   (1.4 / 2.4 auto-accept)" if config.get("checkpoints") == "auto" else ""))
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    it = sub.add_parser("intake", help="record the three intake answers")
    it.add_argument("root", type=Path)
    it.add_argument("--source", default="none", help="none | absolute path to an HTML export folder")
    it.add_argument("--checkpoints", choices=CHECKPOINTS, required=True)
    it.add_argument("--speed", choices=SPEEDS, required=True)
    sh = sub.add_parser("show", help="print the recorded config")
    sh.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "show":
        config = load(args.root)
        if config.get("recordedAt") is None:
            print("run-config: none recorded (defaults: full / human / 1600/768/390)")
            return 2
        for line in summary_lines(config):
            print(line)
        return 0
    try:
        config = intake(args.root, source=args.source, checkpoints=args.checkpoints, speed=args.speed)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    for line in summary_lines(config):
        print(line)
    print(f"→ {config_path(args.root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
