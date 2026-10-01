#!/usr/bin/env python3
"""5.2 — receipt after interior bodies are authored as Astro pages.

Reads qa/phase-4-pages.json and checks, per slug:
  astro/src/pages/{slug}.astro   authored body on the 5.1 shared chrome
  rebuild/{slug}-raw.html        serial get_jsx structure reference (5.2 dump)

The page must import BaseLayout + Header + Footer, carry exactly one <main>,
and must NOT inline its own <header> / <footer> (chrome comes from 5.1), a
get_jsx dump, or source / external hrefs (hrefs stay `#` until 5.5).
Writes qa/phase-5-pages.json.

  python3 record-phase-5-pages.py /path/to/project
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import shared_sections
from astro_build import dist_page_rel
from author_21_gate import off_page_hrefs
from rebuild_write_gate import RAW_PAPER_EXPORT_RE, ship_markup_errors

MAIN_RE = re.compile(r"<main\b[^>]*>.*?</main>", re.I | re.S)
# lowercase only — <Header /> / <Footer /> are the shared Astro components
INLINE_CHROME_RE = re.compile(r"<(header|footer)\b")
REQUIRED_IMPORTS = ("BaseLayout", "Header", "Footer")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def page_errors(slug: str, text: str) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_IMPORTS:
        if re.search(rf"^import {name} from ", text, re.M) is None:
            errors.append(f"{slug}.astro does not import {name} — every interior sits on the 5.1 chrome")
    if "<Header" not in text or "<Footer" not in text:
        errors.append(f"{slug}.astro must render <Header /> and <Footer /> around <main>")
    mains = MAIN_RE.findall(text)
    if len(mains) != 1:
        errors.append(f"{slug}.astro needs exactly one <main>; found {len(mains)}")
    if RAW_PAPER_EXPORT_RE.search(text):
        errors.append(f"{slug}.astro still has get_jsx dump metadata")
    if INLINE_CHROME_RE.search(text):
        errors.append(f"{slug}.astro inlines <header>/<footer> — use the shared Header/Footer components")
    if mains:
        errors.extend(f"{slug}: {err}" for err in ship_markup_errors(mains[0]))
    leaked = off_page_hrefs(text)
    if leaked:
        errors.append(f"{slug}.astro has source/external hrefs {leaked[:4]} — hrefs stay # until 5.5")
    return errors


def reuse_errors(root: Path, slug: str, text: str, plan: dict | None) -> list[str]:
    """Pitfall #244 — a band the sitemap repeats is imported, never re-authored."""
    if not plan:
        return []
    errors: list[str] = []
    for group in plan.get("groups") or []:
        if slug not in (group.get("interiorPages") or []):
            continue
        name = group["name"]
        if re.search(rf"^import {name} from ", text, re.M) is None or f"<{name}" not in text:
            errors.append(
                f"{slug}.astro re-authors shared section {name} — import and render "
                f"<{name} /> ({group['file']}); a variant takes props or a slot, not a copy"
            )
    pasted = shared_sections.inline_copies(text, plan, slug)
    for name in pasted:
        if f"<{name}" not in text:
            continue  # already reported above
        errors.append(f"{slug}.astro renders <{name} /> AND pastes its copy inline — keep only the component")
    return errors


def record(root: Path) -> dict:
    root = root.resolve()
    src = root / "qa" / "phase-4-pages.json"
    if not src.is_file():
        raise FileNotFoundError("need qa/phase-4-pages.json from 4.2")
    if not (root / "astro" / "src" / "components" / "Header.astro").is_file():
        raise FileNotFoundError("need astro/src/components/Header.astro from 5.1")
    payload = json.loads(src.read_text(encoding="utf-8"))
    rows = payload.get("pages") if isinstance(payload, dict) else []
    pages = []
    errors: list[str] = []
    plan = shared_sections.load(root)
    if plan is None:
        errors.append("missing qa/phase-5-reuse.json — run shared_sections.py before authoring pages (Pitfall #244)")
    else:
        late = shared_sections.stale_pending(root, plan)
        if late:
            errors.append(
                "qa/phase-5-reuse.json predates the section source for "
                + ", ".join(late[:4])
                + " — re-run shared_sections.py, then reconcile pages (Pitfall #244)"
            )
        for group in plan.get("groups") or []:
            if (root / "astro" / group["file"]).is_file():
                continue
            if group.get("buildFirst"):
                errors.append(
                    f"build-first shared section {group['name']} is missing astro/{group['file']} "
                    f"— author it once before the pages that use it ({', '.join(group['interiorPages'][:4])})"
                )
            else:
                errors.append(
                    f"shared section {group['name']} repeats a homepage band but astro/{group['file']} "
                    "is missing — re-run extract-astro-components.py + convert-astro-home.py"
                )
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or "").strip()
        if not slug or slug in {"home", "index"}:
            continue
        try:
            import run_config

            if run_config.adopt_mode(root):
                allowed, why = run_config.author_page_allowed(root, slug)
                page = root / f"astro/src/pages/{slug}.astro"
                if not allowed:
                    if page.is_file() or "missing-pages" in why:
                        errors.append(why)
                    continue
        except ImportError:
            pass
        astro_rel = f"astro/src/pages/{slug}.astro"
        raw_rel = f"rebuild/{slug}-raw.html"
        page = root / astro_rel
        raw = root / raw_rel
        if not page.is_file():
            errors.append(f"missing {astro_rel}")
            continue
        if not raw.is_file():
            errors.append(f"missing {raw_rel}")
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        errors.extend(page_errors(slug, text))
        errors.extend(reuse_errors(root, slug, text, plan))
        try:
            import run_config

            if run_config.adopt_mode(root):
                leaked_css = run_config.uses_pipeline_css(text)
                if leaked_css:
                    errors.append(
                        f"{slug}.astro links pipeline CSS {leaked_css} — use the adopted source stylesheets"
                    )
        except ImportError:
            pass
        pages.append(
            {
                "slug": slug,
                "url": row.get("url"),
                "pageId": row.get("pageId"),
                "artboard": row.get("artboard") or f"{slug}-desktop",
                "astro": astro_rel,
                "route": f"/{slug}/",
                "raw": raw_rel,
                "dist": dist_page_rel(slug),
            }
        )
    receipt = {
        "generatedFrom": "web2html/phase-5-pages",
        "ok": bool(pages) and not errors,
        "serial": True,
        "maxWorkers": 2,
        "pages": pages,
        "shared": [g["name"] for g in (plan or {}).get("groups") or []],
        "errors": errors,
        "updated": _now_iso(),
    }
    dest = root / "qa" / "phase-5-pages.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    try:
        receipt = record(args.root.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if not receipt["ok"]:
        for err in receipt["errors"]:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "pages": len(receipt["pages"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
