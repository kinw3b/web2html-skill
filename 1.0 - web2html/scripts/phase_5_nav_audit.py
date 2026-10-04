#!/usr/bin/env python3
"""5.4+ — hidden-nav-item audit on the BUILT phase-5 pages (Pitfall #247).

Stage 5 lifted the Header once at 5.1 and QA'd interiors with static clips —
a closed dropdown and a MISSING dropdown look identical there, so subnavs,
megamenus, and burger drawers silently vanished on interior runs. This audit
builds a per-page inventory of every hidden-until-interaction nav item from
the evidence that already exists on disk, then checks each one against the
BUILT page (astro/dist/{slug}/index.html) + astro/src/components/Header.astro:

  evidence (inventory)                       where it comes from
  -----------------------------------------  ----------------------------------
  hover-reel dropdown manifests              source-site/components/*/dropdown/
  hover-reel burger manifests                source-site/components/*/nav-mobile-*/
  scrape submenu (nav label + 2+ children)   source-site/{slug}.html (else home)
  painted trigger in the raw dump            rebuild/{slug}-raw.html / index.html

  state (built page)
  ---------  ---------------------------------------------------------------
  wired      trigger + panel present, panel carries the expected items
  unwired    trigger painted, panel missing or empty
  missing    the source paints it; the built page has no trigger at all

Home's inventory applies to EVERY page (the Header is shared). Receipt
qa/phase-5-nav.json — ok:true only when every inventoried item is wired on
every page. wire-astro-routes.py refuses to run without a fresh ok receipt.
Capture Tool / --allow-dropdown / "do not hunt" skips FAIL, exactly like
Pitfall #210. Do not invent a nav label the source never painted.

  python3 phase_5_nav_audit.py /path/to/project

Exit 0 ok · 2 any missing/unwired item, banned skip, stale/absent build.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# author-nav-dropdown.py carries a hyphen — load it by path (same pattern as
# the test suites) and reuse its scrape-submenu + trigger detection so the
# audit and the 3.2 author can never drift apart.
_spec = importlib.util.spec_from_file_location(
    "author_nav_dropdown", _SCRIPTS / "author-nav-dropdown.py"
)
assert _spec is not None and _spec.loader is not None
and_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(and_mod)

from astro_build import dist_page_rel

WRITER = "phase_5_nav_audit.py"
OUT = Path("qa/phase-5-nav.json")
BANNED_SKIP = and_mod.BANNED_SKIP
TOGGLE_CLASS = re.compile(
    r"\b(burger|hamburger|nav-toggle|menu-toggle|nav-burger)\b", re.I
)
DRAWER_PANEL = re.compile(
    r"""<(nav|div)\b([^>]*(?:id=["']nav-panel["']|data-nav-panel)[^>]*)>""",
    re.I,
)
LOCAL_SCRAPE = (
    "source-site/{slug}.html",
    "capture/{slug}-desktop/captured.html",
    "capture/{slug}-desktop/page.html",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def normalized_nav_html(text: str) -> str:
    """Structure-only ship hash: whitespace collapsed, href/src/action values
    blanked, comments stripped. 5.5 rewrites hrefs onto panel items — that is
    not a nav-wiring change and must not stale the receipt."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(
        r"""\b(href|src|action)\s*=\s*(['"])[^'"]*\2""",
        r'\1="#"',
        text,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", text).strip()


def nav_sha(root: Path, rel: str) -> str | None:
    path = root / rel
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return hashlib.sha256(normalized_nav_html(text).encode("utf-8")).hexdigest()


def page_slugs(root: Path) -> list[str]:
    """home + every interior slug from 4.2."""
    src = root / "qa" / "phase-4-pages.json"
    if not src.is_file():
        raise FileNotFoundError("need qa/phase-4-pages.json from 4.2")
    payload = json.loads(src.read_text(encoding="utf-8"))
    rows = payload.get("pages") if isinstance(payload, dict) else []
    slugs = ["home"]
    for row in rows or []:
        if isinstance(row, dict):
            slug = str(row.get("slug") or "").strip()
            if slug and slug not in {"home", "index"}:
                slugs.append(slug)
    return slugs


def scrape_html_for(root: Path, slug: str) -> str:
    """The page's own scrape when present, else the homepage scrape (shared nav)."""
    candidates: list[str] = []
    if slug != "home":
        candidates += [tpl.format(slug=slug) for tpl in LOCAL_SCRAPE]
    candidates.append("source-site/index.html")
    for rel in candidates:
        path = root / rel
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def hover_reel_items(root: Path) -> list[dict]:
    """Dropdown + burger manifests from hover-reel (1.3 / 4.x captures)."""
    items: list[dict] = []
    base = root / "source-site" / "components"
    if not base.is_dir():
        return items
    for manifest in sorted(base.rglob("manifest.json")):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        kind = str(payload.get("kind") or "")
        mode = str(payload.get("mode") or "")
        if mode == "dropdown" or kind == "dropdown":
            row_kind = "dropdown"
        elif mode == "hamburger" or kind in {"nav-mobile", "nav-mobile-768", "nav-mobile-390", "hamburger"}:
            row_kind = "drawer"
        else:
            continue
        states = payload.get("states") or []
        labels: list[str] = []
        for state in states:
            if not isinstance(state, dict):
                continue
            trigger = str(state.get("triggerLabel") or state.get("label") or "").strip()
            if trigger:
                labels.append(trigger)
            for item in state.get("items") or []:
                if isinstance(item, dict) and str(item.get("label") or "").strip():
                    labels.append(str(item["label"]).strip())
        if not labels and row_kind == "drawer":
            labels = ["Menu"]
        page_slug = str(payload.get("pageSlug") or payload.get("page") or "home").strip() or "home"
        if page_slug in {"", "index"}:
            page_slug = "home"
        items.append({
            "trigger": labels[0] if labels else "Menu",
            "kind": row_kind,
            "items": sorted(set(labels)),
            "page": page_slug,
            "evidence": manifest.relative_to(root).as_posix(),
        })
    return items


def raw_dump_for(root: Path, slug: str) -> Path:
    if slug == "home":
        return root / "rebuild" / "index.html"
    return root / "rebuild" / f"{slug}-raw.html"


def inventory_for(root: Path, slug: str, reel: list[dict]) -> list[dict]:
    """Every hidden nav item this page must carry. Home's items apply to every
    page — the Header is shared (5.1)."""
    rows: dict[str, dict] = {}

    def add(row: dict) -> None:
        qk = and_mod.key(row["trigger"])
        if not qk:
            return
        dedupe = f"{row['kind']}:{qk}"
        if dedupe in rows:
            seen = rows[dedupe]
            seen["items"] = sorted(set(seen.get("items") or []) | set(row.get("items") or []))
            seen["evidence"] = sorted(set(seen["evidence"].split("; ")) | {row["evidence"]})
            seen["evidence"] = "; ".join(seen["evidence"])
            return
        rows[dedupe] = row

    for item in reel:
        if item["page"] in {"home", slug}:
            add({
                "trigger": item["trigger"],
                "kind": item["kind"],
                "items": item.get("items") or [],
                "evidence": item["evidence"],
            })
    scrape = scrape_html_for(root, slug)
    for menu in and_mod.scrape_dropdowns(scrape):
        add({
            "trigger": menu["label"],
            "kind": "submenu",
            "items": [str(item.get("label") or "") for item in menu.get("items") or []],
            "evidence": "scrape submenu (source-site)",
        })
    dump = raw_dump_for(root, slug)
    if dump.is_file():
        soup = and_mod.soup_of(dump.read_text(encoding="utf-8", errors="replace"))
        for trigger in and_mod.painted_triggers(soup):
            add({
                "trigger": and_mod.text_of(trigger),
                "kind": "dropdown",
                "items": [],
                "evidence": dump.relative_to(root).as_posix(),
            })
        header_blob = ""
        scope = and_mod.nav_scope(soup)
        if scope is not None:
            header_blob = " ".join(
                " ".join(el.get("class") or []) for el in scope.find_all(True)
            )
        if TOGGLE_CLASS.search(header_blob):
            add({
                "trigger": "Menu",
                "kind": "drawer",
                "items": [],
                "evidence": f"{dump.relative_to(root).as_posix()} (painted burger)",
            })
    return list(rows.values())


def state_of(root: Path, slug: str, row: dict) -> dict:
    """wired | unwired | missing on the BUILT page."""
    ship_rel = dist_page_rel(slug)
    ship = root / ship_rel
    result = dict(row)
    result["ship"] = ship_rel
    if not ship.is_file():
        result["state"] = "missing"
        result["detail"] = f"missing {ship_rel} — run build-astro-dist.py first"
        return result
    soup = and_mod.soup_of(ship.read_text(encoding="utf-8", errors="replace"))
    scope = and_mod.nav_scope(soup)
    if row["kind"] == "drawer":
        toggle = None
        if scope is not None:
            for el in scope.find_all(["button", "a", "div", "span"]):
                blob = " ".join(el.get("class") or []) + " " + str(el.get("aria-label") or "")
                if el.get("data-nav-toggle") is not None or TOGGLE_CLASS.search(blob):
                    toggle = el
                    break
        panel = soup.find(id="nav-panel") or soup.find(attrs={"data-nav-panel": True})
        if toggle is None and panel is None:
            result["state"] = "missing"
            result["detail"] = "source captures a burger; built page has no toggle or drawer panel"
        elif toggle is not None and panel is not None:
            result["state"] = "wired"
            result["detail"] = "data-nav-toggle + nav-panel present"
        else:
            result["state"] = "unwired"
            result["detail"] = "burger toggle without a nav-panel (or panel without a toggle)"
        return result
    trigger = and_mod.find_trigger(scope, row["trigger"]) if scope is not None else None
    panel = None
    if trigger is not None:
        host = trigger.find_parent(attrs={"data-nav-dropdown": True}) or trigger.parent
        nxt = trigger.find_next_sibling()
        if nxt is not None and (
            nxt.get("data-nav-dropdown-panel") is not None or nxt.name == "ul"
        ):
            panel = nxt
        elif host is not None:
            panel = host.find(attrs={"data-nav-dropdown-panel": True}) or host.find("ul")
        if (
            panel is not None
            and trigger.get("data-nav-dropdown-trigger") is None
            and trigger.get("aria-haspopup") is None
        ):
            # panel markup exists but nothing opens it
            panel = None
    expected = [lbl for lbl in row.get("items") or [] if and_mod.key(lbl)]
    if trigger is None:
        result["state"] = "missing"
        result["detail"] = "built nav has no trigger for this label"
    elif panel is None:
        result["state"] = "unwired"
        result["detail"] = "trigger painted, no [data-nav-dropdown-panel] wired to it"
    else:
        panel_labels = {and_mod.key(and_mod.text_of(a)) for a in panel.find_all("a")}
        absent = [lbl for lbl in expected if and_mod.key(lbl) not in panel_labels]
        if expected and len(absent) == len(expected):
            result["state"] = "unwired"
            result["detail"] = f"panel is empty — source items never filled: {', '.join(expected[:6])}"
        else:
            result["state"] = "wired"
            result["detail"] = (
                "trigger + panel wired"
                + (f"; panel lacks {', '.join(absent[:4])}" if absent else "")
            )
    return result


def audit(root: Path) -> dict:
    root = root.resolve()
    if not (root / "astro" / "src" / "components" / "Header.astro").is_file():
        raise FileNotFoundError("need astro/src/components/Header.astro from 5.1")
    slugs = page_slugs(root)
    reel = hover_reel_items(root)
    pages: list[dict] = []
    errors: list[str] = []
    skipped: list[dict] = []
    for slug in slugs:
        ship_rel = dist_page_rel(slug)
        if not (root / ship_rel).is_file():
            errors.append(
                f"{slug}: missing {ship_rel} — run build-astro-dist.py first "
                "(the audit checks the BUILT pages)"
            )
        rows = [state_of(root, slug, row) for row in inventory_for(root, slug, reel)]
        broken = [row for row in rows if row["state"] != "wired"]
        page_row = {
            "slug": slug,
            "ship": dist_page_rel(slug),
            "items": rows,
            "broken": [
                {"trigger": row["trigger"], "kind": row["kind"], "state": row["state"],
                 "detail": row.get("detail"), "evidence": row.get("evidence")}
                for row in broken
            ],
        }
        if not rows:
            skipped.append({
                "slug": slug,
                "finding": "nav hidden items",
                "reason": "No hover-reel dropdown/burger capture, no scrape submenu, and "
                          "no painted trigger for this page. Do not invent a menu.",
            })
        pages.append(page_row)
        for row in broken:
            errors.append(
                f"{slug}: {row['kind']} '{row['trigger']}' is {row['state']} — "
                f"{row.get('detail')} (evidence: {row.get('evidence')})"
            )
    fingerprints: dict[str, str] = {}
    header = nav_sha(root, "astro/src/components/Header.astro")
    if header:
        fingerprints["astro/src/components/Header.astro"] = header
    for slug in slugs:
        rel = dist_page_rel(slug)
        digest = nav_sha(root, rel)
        if digest:
            fingerprints[rel] = digest
    banned = [
        row for row in skipped
        if BANNED_SKIP.search(str(row.get("reason") or ""))
    ]
    if banned:
        errors.extend(f"banned skip reason: {row['reason']}" for row in banned)
    receipt = {
        "generatedFrom": "web2html/phase-5-nav",
        "ok": not errors,
        "writer": WRITER,
        "pages": pages,
        "fingerprints": fingerprints,
        "skipped": skipped,
        "errors": errors,
        "updated": _now_iso(),
    }
    dest = root / OUT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def compare_wave_errors(root: Path) -> list[str]:
    """The 5.4+ self-validation loop actually ran (Pitfall #248).

    Per interior slug: a fresh qa/side-by-side/{slug}/report.json with at
    least one side-by-side, AND an APPLIED `wave.py --phase compare --page
    {slug}` whose tasks cover every band in that report. Before this check a
    run could write phase-5-nav.json and go straight to 5.5 without ever
    dispatching a reviewer — the loop silently never kicked in."""
    root = root.resolve()
    try:
        slugs = [slug for slug in page_slugs(root) if slug != "home"]
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [str(exc)]
    covered: dict[str, set[str]] = {}
    for path in sorted((root / "qa" / "agent-runs").glob("*/compare/wave.json")):
        try:
            wave = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(wave, dict) or not wave.get("appliedAt"):
            continue
        page = str(wave.get("page") or "home")
        bands = covered.setdefault(page, set())
        for task in wave.get("tasks") or []:
            if isinstance(task, dict) and task.get("band"):
                bands.add(str(task["band"]))
    import page_loop

    errors: list[str] = []
    for slug in slugs:
        if page_loop.receipt_path(root, slug).is_file() and page_loop.page_done(root, slug):
            continue  # the page loop (author + compare until match) supersedes the review wave
        report_path = root / "qa" / "side-by-side" / slug / "report.json"
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append(
                f"{slug}: no qa/side-by-side/{slug}/report.json — shoot it: paper_23_side_by_side.py . "
                f"--page {slug} --ship astro/dist/{slug}/index.html"
            )
            continue
        stops = [row for row in report.get("stops") or [] if isinstance(row, dict)]
        if not any(row.get("side") for row in stops):
            errors.append(
                f"{slug}: report has 0 side-by-sides (every source pane missing) — nothing for the "
                "reviewers to compare; check capture/{slug}-desktop/source-sections"
            )
        wanted = {str(row.get("id")) for row in stops if row.get("id")}
        missing = sorted(wanted - covered.get(slug, set()))
        if missing:
            errors.append(
                f"{slug}: no applied compare wave for band(s) {', '.join(missing[:6])} — run "
                f"wave.py prepare/start/wait/apply . --phase compare --page {slug} (one subagent per band)"
            )
    return errors


def plant_compare_loop(root: Path, slug: str, bands: list[str], run_id: str = "t1") -> None:
    """TEST FIXTURE ONLY — a side-by-side report + an applied compare wave for
    `slug`, i.e. the evidence compare_wave_errors() demands."""
    root = root.resolve()
    pairs = root / "qa" / "side-by-side" / slug
    pairs.mkdir(parents=True, exist_ok=True)
    (pairs / "report.json").write_text(json.dumps({
        "page": slug,
        "stops": [{"id": b, "width": 1600, "side": f"qa/side-by-side/{slug}/1600/{b}-side.png"} for b in bands],
    }), encoding="utf-8")
    wave_dir = root / "qa" / "agent-runs" / f"{run_id}-{slug}" / "compare"
    wave_dir.mkdir(parents=True, exist_ok=True)
    (wave_dir / "wave.json").write_text(json.dumps({
        "phase": "compare", "page": slug, "appliedAt": _now_iso(),
        "tasks": [{"id": f"{slug}--band-{b}", "band": b} for b in bands],
    }), encoding="utf-8")


def gate_errors(root: Path) -> list[str]:
    """5.5 entry gate: a fresh, ok, complete qa/phase-5-nav.json (Pitfall #247)
    plus an applied interior /compare wave per slug (Pitfall #248)."""
    root = root.resolve()
    loop = compare_wave_errors(root)
    path = root / OUT
    if not path.is_file():
        return [
            "missing qa/phase-5-nav.json — run phase_5_nav_audit.py after the 5.4+ "
            "/compare interior pass (hidden nav items — Pitfall #247)"
        ]
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"qa/phase-5-nav.json unreadable ({exc})"]
    if not isinstance(receipt, dict) or receipt.get("writer") != WRITER:
        return ["qa/phase-5-nav.json was not written by phase_5_nav_audit.py"]
    errors: list[str] = []
    if receipt.get("ok") is not True:
        errors.extend(str(row) for row in receipt.get("errors") or ["qa/phase-5-nav.json is not ok"])
    try:
        slugs = set(page_slugs(root))
    except (FileNotFoundError, json.JSONDecodeError):
        slugs = set()
    covered = {str(row.get("slug")) for row in receipt.get("pages") or [] if isinstance(row, dict)}
    for slug in sorted(slugs - covered):
        errors.append(f"qa/phase-5-nav.json does not cover {slug} — re-run phase_5_nav_audit.py")
    banned = [
        row for row in (receipt.get("skipped") or [])
        if BANNED_SKIP.search(str(row.get("reason") or ""))
    ]
    if banned:
        errors.extend(f"banned skip reason: {row.get('reason')}" for row in banned)
    stale = []
    for rel, digest in (receipt.get("fingerprints") or {}).items():
        current = nav_sha(root, rel)
        if current is not None and current != digest:
            stale.append(rel)
    if stale:
        errors.append(
            "qa/phase-5-nav.json is stale (changed since the audit: "
            + ", ".join(stale[:4])
            + ") — re-run phase_5_nav_audit.py"
        )
    return errors + loop


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = ap.parse_args(argv)
    try:
        receipt = audit(args.root)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        fail(str(exc))
        return 2
    if not receipt["ok"]:
        for err in receipt["errors"]:
            fail(err)
        return 2
    total = sum(len(page["items"]) for page in receipt["pages"])
    print(json.dumps({
        "ok": True,
        "pages": len(receipt["pages"]),
        "hiddenNavItems": total,
        "receipt": OUT.as_posix(),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
