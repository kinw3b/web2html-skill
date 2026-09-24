#!/usr/bin/env python3
"""Run intake — qa/run-config.json is the run's contract (2.26.0).

Three answers, collected ONCE right after `pipeline-progress.py start`, before
1.1 goes active: where the run starts (URL, or a Webflow / HTML folder + its
path), then speed (`full` or `fast`). `mark --step 1.1 --status active` refuses without this file.

  python3 run_config.py intake <project> --source none|/abs/path --speed full|fast
  python3 run_config.py show   <project>
  python3 run_config.py missing-pages <project>
  python3 run_config.py design-system <project> --choice skip|print|seed-from-source

Question 1 — where the run starts. One choice:
  1. Live URL — author from Paper (`--source none`)
  2. Webflow / HTML source
If they choose 2, the NEXT question is the absolute folder path (the
type-your-answer field). Do not record intake until that path exists.
`--source none` authors from Paper. `--source /abs/path` copies the folder into
<project>/source-html/ and classifies it:

  clean-html      Webflow export / static build. The copy in source-html/ IS the
                  ship. Do not create rebuild/. Phase 2 is not applicable.
                  Phase 3 may add accessibility attributes only. Phase 4 is
                  required: the run continues through 4.4 (no finish-vs-optional
                  question at 3.4). 4.4 still chooses whether to continue to
                  Phase 5. Tokens are never bound back onto Paper frames.
  framework-dump  _next/, __NEXT_DATA__, _nuxt/, Framer runtime, an empty React
                  root. Not adopted. 2.2 authors from Paper; the folder is a
                  copy/structure reference only.
  none            no source; 2.2 authors from Paper.

Question 2 — speed.  `full` stops at 1.4 / 2.4 / 3.4 and (when the agent
authors) keeps the Design Library. `fast` is today's fast run: checkpoints
auto, widths 1600/390, 1.3 and 2.1 skipped, no Buttons/Components pull.
The separate checkpoints question is retired. Full always means human stops.
Fast is the only automatic path. A URL run stops at 3.4. A Webflow / HTML
folder run does not: Phase 4 is required and the stop is 4.4.

`--checkpoints` is accepted for old commands. `auto` with `--speed full` is
refused. Fast still forces auto.
"""
from __future__ import annotations

import argparse
import hashlib
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
ADOPT_RECEIPT = Path("qa/adopt-rebuild.json")
ADOPT_QA = Path("qa/adopt-qa.json")
ADOPT_MISSING = Path("qa/adopt-missing-pages.json")
DESIGN_SYSTEM_PRINT = Path("qa/design-system-print.json")
SOURCE_FOLDER_TOKENS = Path("qa/source-folder-tokens.json")
DESIGN_SYSTEM_REFERENCE = Path("qa/design-system-reference.html")
TOKEN_SEED = Path("qa/phase-4-token-seed.json")

SOURCE_KINDS = ("none", "clean-html", "framework-dump")
CHECKPOINTS = ("human", "auto")
SPEEDS = ("full", "fast")
PRINT_CHOICES = ("skip", "print", "seed-from-source")
FULL_WIDTHS = (1600, 768, 390)
FAST_WIDTHS = (1600, 390)
# 3.4 is never automatic. Steps 4.x / 5.x author from the 3.4 result and need a
# human to sign it. Nothing in the config can add 3.4 to this set.
AUTO_ACCEPTABLE = frozenset({"1.4", "2.4"})

# Pipeline files an adopt run must not invent. A name that already lives in the
# export is kept; anything else in this list is a second site.
INVENTED_RELS = (
    "index-semantic.html",
    "index-polish.html",
    "index-raw.html",
    "design-system.html",
    "polish-report.html",
    "css/fonts.css",
    "css/hover.css",
    "css/nav-drawer.css",
    "css/nav-dropdown.css",
    "css/site.css",
    "css/tokens.css",
    "css/faq.css",
    "js/nav-drawer.js",
    "js/nav-dropdown.js",
    "js/faq.js",
    "js/qa-overlay.js",
    "css/qa-overlay.css",
)
PIPELINE_CSS_NAMES = frozenset({
    "fonts.css",
    "hover.css",
    "nav-drawer.css",
    "nav-dropdown.css",
    "site.css",
    "tokens.css",
    "faq.css",
})

FRAMEWORK_DIR_MARKERS = ("_next", "_nuxt", ".next", ".nuxt", "_astro", "__sveltekit", "_expo")
FRAMEWORK_HTML_RE = re.compile(
    r"__NEXT_DATA__|__NUXT__|__remixContext|__SVELTEKIT|__gatsby|"
    r"data-reactroot|id=[\"']__next[\"']|id=[\"']___gatsby[\"']|"
    r"framerusercontent\.com/sites|data-framer-|"
    r"<div id=[\"']root[\"']>\s*</div>|<div id=[\"']app[\"']>\s*</div>",
    re.I,
)
CLEAN_HTML_RE = re.compile(r"data-wf-page|data-wf-site|class=[\"'][^\"']*\bw-(?:container|section|nav)\b", re.I)
SECTION_RE = re.compile(r"<(?:section|header|footer|main|nav|article)\b", re.I)
COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FONT_RE = re.compile(r"font-family\s*:\s*([^;}{]+)", re.I)
DYN_EMPTY_RE = re.compile(r"w-dyn-empty|w-dyn-bind-empty", re.I)
DYN_LIST_RE = re.compile(r"w-dyn-list", re.I)
DYN_ITEM_RE = re.compile(r"w-dyn-item", re.I)


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
        "adopt": False,
        "bindTokens": True,
        "designSystemPrint": None,
        "phase4": "optional",
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
    if merged.get("adopt"):
        merged["bindTokens"] = False
        merged["phase4"] = "required"
        merged["humanStops"] = human_stops(
            adopt=True,
            checkpoints="auto" if merged.get("checkpoints") == "auto" else "human",
        )
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


def adopt_mode(root: Path) -> bool:
    """Clean HTML was adopted. Do not author a second homepage or CSS."""
    cfg = load(root)
    return bool(cfg.get("adopt")) and source_kind(root) == "clean-html" and source_index(root) is not None


def bind_tokens_allowed(root: Path) -> bool:
    """False on an adopted source. Never seed variables back onto Paper frames."""
    return bool(load(root).get("bindTokens", True)) and not adopt_mode(root)


def port_mode(root: Path) -> bool:
    """Retired (2.26.0). Clean HTML is adopted, not re-authored in PORT mode."""
    return False


def author_mode(root: Path) -> bool:
    return not adopt_mode(root)


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


def _skip_payload(step: str, reason: str, mode: str) -> str:
    return json.dumps(
        {
            "generatedFrom": GENERATED_FROM,
            "step": step,
            "mode": mode,
            "reason": reason,
            "recordedAt": _now_iso(),
        },
        indent=2,
    ) + "\n"


# ------------------------------------------------------------------ intake --


def human_stops(*, adopt: bool, checkpoints: str) -> list[str]:
    """URL runs stop at 3.4. A folder / Webflow run continues through 4.4."""
    if adopt:
        return ["4.4"] if checkpoints == "auto" else ["1.4", "4.4"]
    return ["3.4"] if checkpoints == "auto" else ["1.4", "2.4", "3.4"]


def build_config(*, source_kind_: str, source_path: str | None, source_meta: dict | None,
                 checkpoints: str, speed: str) -> dict:
    if checkpoints not in CHECKPOINTS:
        raise ValueError(f"checkpoints must be one of {CHECKPOINTS}")
    if speed not in SPEEDS:
        raise ValueError(f"speed must be one of {SPEEDS}")
    if source_kind_ not in SOURCE_KINDS:
        raise ValueError(f"source kind must be one of {SOURCE_KINDS}")
    if speed == "full" and checkpoints == "auto":
        raise ValueError(
            "checkpoints=auto is retired on a full run. Fast is the only automatic "
            "path. A full URL run stops at 1.4, 2.4, and 3.4."
        )
    fast = speed == "fast"
    if fast:
        checkpoints = "auto"
    adopt = source_kind_ == "clean-html"
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
        "designLibrary": not fast and not adopt,
        "designSystem": not fast and not adopt,
        "rawDump": not fast and not adopt,
        "adopt": adopt,
        "bindTokens": not adopt,
        "designSystemPrint": "after-4.4" if adopt else None,
        "humanStops": human_stops(adopt=adopt, checkpoints=checkpoints),
        "phase4": "required" if adopt else "optional",
        "recordedAt": _now_iso(),
    }


def write(root: Path, config: dict) -> Path:
    dest = config_path(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    adopt = bool(config.get("adopt"))
    mode = "adopt" if adopt else "fast"
    if not config.get("designLibrary", True):
        reason = (
            "adopted clean HTML — no Design Library on the homepage; optional print after 4.4; do not bind tokens onto frames"
            if adopt
            else "fast run — no Design Library"
        )
        (root / DESIGN_LIBRARY_SKIPPED).write_text(_skip_payload("1.3", reason, mode), encoding="utf-8")
    if not config.get("designSystem", True):
        reason = (
            "adopted clean HTML — no Design System page in the site; optional print after 4.4"
            if adopt
            else "fast run — no Design System page"
        )
        (root / DESIGN_SYSTEM_SKIPPED).write_text(_skip_payload("2.1", reason, mode), encoding="utf-8")
    if config.get("adopt"):
        import source_fidelity

        source_fidelity.write_phase_2_off(root)
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
    config = build_config(
        source_kind_=kind,
        source_path=path,
        source_meta=meta,
        checkpoints=checkpoints,
        speed=speed,
    )
    write(root, config)
    return config


def summary_lines(config: dict) -> list[str]:
    src = config.get("source") or {}
    kind = src.get("kind") or "none"
    lines = [
        f"run-config: speed={config.get('speed')}  checkpoints={config.get('checkpoints')}  widths={'/'.join(str(w) for w in config.get('widths') or [])}",
    ]
    if config.get("adopt") and kind == "clean-html":
        lines.append("source: clean-html ADOPT ← " + f"{src.get('path')}  ({src.get('reason')})")
        lines.append("ship: source-html/ — do not create rebuild/. Phase 2 is not applicable.")
        lines.append("3.x: accessibility attributes only. Phase 4 is required — continue through 4.4. Do not ask.")
    elif kind == "none":
        lines.append("source: none — 2.2 authors from Paper")
    elif kind == "framework-dump":
        lines.append(f"source: framework-dump ← {src.get('path')}  ({src.get('reason')})")
        lines.append("2.2: author from Paper; do not adopt a framework dump")
    else:
        lines.append(f"source: {kind} ← {src.get('path')}  ({src.get('reason')})")
    if config.get("speed") == "fast":
        lines.append("fast: 1.3 + 2.1 skipped · 1600/390 · no Buttons/Components pull · 1.4 / 2.4 auto-accept")
    if config.get("phase4") == "required":
        lines.append("phase 4: required — do not offer finish-homepage. Stop at 4.4.")
    stops = config.get("humanStops") or ["1.4", "2.4", "3.4"]
    lines.append("human stops: " + " ".join(stops) + ("   (1.4 / 2.4 auto-accept)" if config.get("checkpoints") == "auto" else ""))
    return lines


# -------------------------------------------------------------------- adopt --


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def adopt_receipt(root: Path) -> dict | None:
    data = _read_json(root.resolve() / ADOPT_RECEIPT)
    if not data or data.get("generatedFrom") != GENERATED_FROM:
        return None
    return data


def invented_ship_files(root: Path) -> list[str]:
    """Pipeline CSS/HTML that the export did not contain."""
    root = root.resolve()
    receipt = adopt_receipt(root) or {}
    exported = set(receipt.get("files") or [])
    rebuild = root / "rebuild"
    invented: list[str] = []
    for rel in INVENTED_RELS:
        if rel in exported:
            continue
        if (rebuild / rel).is_file():
            invented.append(rel)
    return invented


def adopt_into_rebuild(root: Path) -> dict:
    """Copy source-html/ into rebuild/. The export is the ship. No new CSS."""
    root = root.resolve()
    if not adopt_mode(root):
        raise ValueError("adopt only when the intake classified a clean HTML source")
    src = root / SOURCE_DIR
    if not src.is_dir():
        raise FileNotFoundError("source-html/ is missing — re-run intake with the folder")
    dest = root / "rebuild"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(".git", "node_modules", ".DS_Store", "__pycache__"),
        symlinks=False,
    )
    index = dest / "index.html"
    if not index.is_file():
        raise FileNotFoundError("adopted export has no rebuild/index.html")
    files = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    digest = hashlib.sha256(index.read_bytes()).hexdigest()
    receipt = {
        "generatedFrom": GENERATED_FROM,
        "mode": "adopt",
        "indexHtml": "rebuild/index.html",
        "indexSha256": digest,
        "files": files,
        "bindTokens": False,
        "recordedAt": _now_iso(),
    }
    dest_receipt = root / ADOPT_RECEIPT
    dest_receipt.parent.mkdir(parents=True, exist_ok=True)
    dest_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def adopt_rebuilt(root: Path) -> bool:
    """True when rebuild/index.html is still the adopted export and no pipeline CSS was invented."""
    root = root.resolve()
    if not adopt_mode(root):
        return False
    receipt = adopt_receipt(root)
    if not receipt or receipt.get("mode") != "adopt":
        return False
    index = root / "rebuild" / "index.html"
    src = source_index(root)
    if not index.is_file() or src is None:
        return False
    try:
        if hashlib.sha256(index.read_bytes()).hexdigest() != receipt.get("indexSha256"):
            return False
        if index.read_bytes() != src.read_bytes():
            return False
    except OSError:
        return False
    return not invented_ship_files(root)


def write_adopt_qa(root: Path) -> Path:
    """3.x on an adopted source does not write polish HTML or pipeline CSS."""
    root = root.resolve()
    dest = root / ADOPT_QA
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "mode": "adopt",
                "polish": False,
                "reason": "adopted source — do not write index-polish.html or pipeline CSS",
                "recordedAt": _now_iso(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def adopt_qa_done(root: Path) -> bool:
    data = _read_json(root.resolve() / ADOPT_QA)
    return bool(data) and data.get("polish") is False and data.get("mode") == "adopt"


def write_adopt_token_seed(root: Path) -> Path:
    """4.3 on an adopted source records that bind was refused."""
    root = root.resolve()
    dest = root / TOKEN_SEED
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "bind": False,
                "reason": "adopted source — do not seed variables onto Paper frames",
                "recordedAt": _now_iso(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def adopt_keep_html_names(root: Path) -> frozenset[str]:
    """Top-level HTML the export brought into rebuild/. The write gate must keep them."""
    receipt = adopt_receipt(root.resolve())
    if not receipt:
        return frozenset()
    names = []
    for rel in receipt.get("files") or []:
        if not isinstance(rel, str) or not rel.endswith(".html") or "/" in rel:
            continue
        names.append(rel)
    return frozenset(names)


# --------------------------------------------------------------- empty pages --


def page_is_empty(html: str) -> bool:
    """Webflow CMS shells: missing body, w-dyn-empty, or a collection list with no items."""
    if not html or not html.strip():
        return True
    if DYN_EMPTY_RE.search(html):
        return True
    if DYN_LIST_RE.search(html) and not DYN_ITEM_RE.search(html):
        return True
    return len(SECTION_RE.findall(html)) < 1


def find_export_page(root: Path, url_path: str) -> Path | None:
    folder = root.resolve() / SOURCE_DIR
    parts = [p for p in str(url_path).strip("/").split("/") if p]
    if not parts:
        for name in ("index.html", "index.htm"):
            hit = folder / name
            if hit.is_file():
                return hit
        return None
    rel = Path(*parts)
    for cand in (folder / f"{rel.as_posix()}.html", folder / rel / "index.html"):
        if cand.is_file():
            return cand
    return None


def missing_export_pages(root: Path, rows: list[dict]) -> list[dict]:
    """Sitemap rows the export did not ship, or shipped as an empty CMS shell."""
    missing: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "")
        if path in {"", "/"}:
            continue
        hit = find_export_page(root, path)
        if hit is None:
            reason = "absent"
        else:
            try:
                html = hit.read_text(encoding="utf-8", errors="replace")
            except OSError:
                html = ""
            if not page_is_empty(html):
                continue
            reason = "empty"
        slug = str(row.get("slug") or "").strip()
        if not slug:
            slug = path.strip("/").replace("/", "-") or "page"
        missing.append({
            "path": path,
            "url": row.get("url"),
            "slug": slug,
            "reason": reason,
        })
    return missing


def write_missing_pages(root: Path) -> dict:
    root = root.resolve()
    if not adopt_mode(root):
        raise ValueError("missing-pages is only for an adopted clean HTML source")
    sitemap = _read_json(root / "qa" / "phase-4-sitemap.json")
    if not sitemap:
        raise FileNotFoundError("need qa/phase-4-sitemap.json from 4.1")
    raw_pages = sitemap.get("pages")
    rows = [row for row in raw_pages if isinstance(row, dict)] if isinstance(raw_pages, list) else []
    missing = missing_export_pages(root, rows)
    payload = {
        "generatedFrom": GENERATED_FROM,
        "ok": True,
        "pages": missing,
        "recordedAt": _now_iso(),
    }
    dest = root / ADOPT_MISSING
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def missing_slugs(root: Path) -> set[str]:
    data = _read_json(root.resolve() / ADOPT_MISSING)
    if not data:
        return set()
    return {str(row.get("slug")) for row in data.get("pages") or [] if isinstance(row, dict) and row.get("slug")}


def author_page_allowed(root: Path, slug: str) -> tuple[bool, str]:
    """Phase 5 may author only CMS pages the export left empty. Static pages stay the export."""
    if not adopt_mode(root):
        return True, ""
    data = _read_json(root.resolve() / ADOPT_MISSING)
    if not data:
        return False, "run run_config.py missing-pages before authoring interiors"
    if slug not in missing_slugs(root):
        return False, f"{slug} is in the adopted export — do not author it; Phase 5 authors only qa/adopt-missing-pages.json"
    return True, ""


def uses_pipeline_css(text: str) -> list[str]:
    found = []
    for name in sorted(PIPELINE_CSS_NAMES):
        if name in text:
            found.append(name)
    return found


# --------------------------------------------------------- design system print --


def mine_source_folder_tokens(root: Path) -> dict:
    """Colors and font-families from the export CSS. Not written into rebuild/."""
    css_dir = root.resolve() / SOURCE_DIR / "css"
    colors: list[str] = []
    fonts: list[str] = []
    files: list[str] = []
    if css_dir.is_dir():
        for path in sorted(css_dir.glob("*.css")):
            files.append(path.relative_to(root.resolve()).as_posix())
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for color in COLOR_RE.findall(text):
                token = color.lower()
                if token not in colors:
                    colors.append(token)
            for family in FONT_RE.findall(text):
                name = " ".join(family.split()).strip().strip("'\"")
                if name and name not in fonts:
                    fonts.append(name)
    return {"colors": colors[:48], "fontFamilies": fonts[:16], "files": files}


def _reference_html(tokens: dict) -> str:
    colors = "".join(
        f'<li><span style="background:{color}"></span><code>{color}</code></li>'
        for color in tokens.get("colors") or []
    ) or "<li>none</li>"
    fonts = "".join(f"<li><code>{name}</code></li>" for name in tokens.get("fontFamilies") or []) or "<li>none</li>"
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>Design system reference — source folder</title>"
        "<style>body{font:16px/1.4 system-ui;margin:32px;color:#161616}"
        "ul{list-style:none;padding:0}li{display:flex;gap:12px;align-items:center;margin:6px 0}"
        "span{width:48px;height:24px;border:1px solid #ccc;display:inline-block}</style>"
        "</head><body><h1>Source folder</h1>"
        "<p>Printed reference. Not injected into the site. Tokens were not bound onto Paper frames.</p>"
        f"<h2>Colors</h2><ul>{colors}</ul><h2>Font families</h2><ul>{fonts}</ul></body></html>\n"
    )


def record_design_system_print(root: Path, choice: str) -> dict:
    root = root.resolve()
    if choice not in PRINT_CHOICES:
        raise ValueError(f"choice must be one of {PRINT_CHOICES}")
    if not adopt_mode(root):
        raise ValueError("design-system print is only for an adopted clean HTML source")
    if not (root / "qa" / "phase-4-review.md").is_file():
        raise ValueError("design-system print is optional after 4.4 — qa/phase-4-review.md is missing")
    payload: dict = {
        "generatedFrom": GENERATED_FROM,
        "choice": choice,
        "bindTokens": False,
        "recordedAt": _now_iso(),
    }
    if choice == "seed-from-source":
        tokens = mine_source_folder_tokens(root)
        payload["tokens"] = tokens
        payload["reference"] = DESIGN_SYSTEM_REFERENCE.as_posix()
        (root / SOURCE_FOLDER_TOKENS).write_text(json.dumps(tokens, indent=2) + "\n", encoding="utf-8")
        (root / DESIGN_SYSTEM_REFERENCE).write_text(_reference_html(tokens), encoding="utf-8")
    elif choice == "print":
        payload["note"] = (
            "Print a Paper reference sheet only. Do not call apply-theme-tokens. "
            "Do not write tokens.css into rebuild/."
        )
    else:
        payload["note"] = "skipped"
    dest = root / DESIGN_SYSTEM_PRINT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    it = sub.add_parser("intake", help="record the two intake answers")
    it.add_argument("root", type=Path)
    it.add_argument("--source", default="none", help="none | absolute path to an HTML export folder")
    it.add_argument("--checkpoints", choices=CHECKPOINTS, default=None,
                    help="retired as a question. auto + full is refused. omit to derive from --speed")
    it.add_argument("--speed", choices=SPEEDS, required=True)
    sh = sub.add_parser("show", help="print the recorded config")
    sh.add_argument("root", type=Path)
    mp = sub.add_parser("missing-pages", help="CMS pages the export left empty")
    mp.add_argument("root", type=Path)
    ds = sub.add_parser("design-system", help="optional printed reference after 4.4")
    ds.add_argument("root", type=Path)
    ds.add_argument("--choice", choices=PRINT_CHOICES, required=True)
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
        if args.cmd == "intake":
            checkpoints = args.checkpoints or ("auto" if args.speed == "fast" else "human")
            config = intake(args.root, source=args.source, checkpoints=checkpoints, speed=args.speed)
            for line in summary_lines(config):
                print(line)
            print(f"→ {config_path(args.root)}")
            return 0
        if args.cmd == "missing-pages":
            payload = write_missing_pages(args.root)
            print(f"missing pages → {len(payload['pages'])}  qa/adopt-missing-pages.json")
            return 0
        payload = record_design_system_print(args.root, args.choice)
        print(f"design-system {payload['choice']} · bindTokens=false → {DESIGN_SYSTEM_PRINT.as_posix()}")
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
