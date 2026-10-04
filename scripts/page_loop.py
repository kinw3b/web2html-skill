#!/usr/bin/env python3
"""5.4+ — per-page section loop: one worker OWNS one interior page and keeps
authoring / comparing it, section by section, until every section matches.

Stage 5 exists to author each interior page from what stage 4 pulled — the
Paper page (`rebuild/{slug}-raw.html`, the get_jsx dump of `{slug}-desktop`)
and the source clips (`capture/{slug}-desktop|768|390/source-sections/`).
A read-only review wave could only *report* a mismatch; nobody owned the fix,
so interiors shipped broken (Pitfall #249). `wave.py --phase page-loop`
dispatches one Orca worker per page (`subagent` / `serial` on other rungs);
each worker drives this script:

  python3 page_loop.py shoot  ROOT --page {slug} [--id band]   # locked astro build + side-by-sides
  python3 page_loop.py record ROOT --page {slug} --band ID --verdict match|miss|residual --seen "…"
  python3 page_loop.py check  ROOT --page {slug}                # exit 0 = page done
  python3 page_loop.py status ROOT                               # every page, one line each

Rules the checker enforces (a page is done only when ALL hold):
  - every source clip maps to a built `<section id>` band and every band maps
    to a clip — no uncovered source section, no extra band
  - no demoted section: a `<div aria-labelledby>` inside <main> is a
    `<section>` hidden from the compare (the kp-avanta dodge) → fail
  - every band's latest verdict is `match`, or `residual` after ≥ MAX_ROUNDS
    `miss` rounds (with a `seen` that says what is still off)
  - the latest record is newer than the page file and the last shoot: an
    edit after the last look reopens the page

Receipt: qa/phase-5-loop/{slug}.json.  Gate helper: gate_errors(root).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import paper_23_disk_gold as gold  # noqa: E402
import paper_23_rebuild_shots as shots  # noqa: E402
from astro_build import dist_page_rel  # noqa: E402

LOOP_DIR = Path("qa/phase-5-loop")
MAX_ROUNDS = 4
VERDICTS = ("match", "miss", "residual")
DEMOTED_RE = re.compile(r"<div\b[^>]*\baria-labelledby=", re.I)
MAIN_RE = re.compile(r"<main\b.*?</main>", re.I | re.S)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt_path(root: Path, slug: str) -> Path:
    return root / LOOP_DIR / f"{slug}.json"


def page_src(root: Path, slug: str) -> Path:
    return root / "astro" / "src" / "pages" / f"{slug}.astro"


def interior_slugs(root: Path) -> list[str]:
    try:
        payload = json.loads((root / "qa" / "phase-4-pages.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = payload.get("pages") if isinstance(payload, dict) else []
    out = []
    for row in rows or []:
        slug = str((row or {}).get("slug") or "").strip() if isinstance(row, dict) else ""
        if slug and slug not in {"home", "index"}:
            out.append(slug)
    return out


def load(root: Path, slug: str) -> dict:
    try:
        data = json.loads(receipt_path(root, slug).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("page", slug)
    data.setdefault("bands", {})
    return data


def save(root: Path, slug: str, data: dict) -> Path:
    dest = receipt_path(root, slug)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = _now_iso()
    dest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return dest


def coverage(root: Path, slug: str) -> dict:
    """Source clips vs built bands, plus demoted sections."""
    ship = root / dist_page_rel(slug)
    html = ship.read_text(encoding="utf-8", errors="replace") if ship.is_file() else ""
    ids = shots.ship_section_ids(html)
    clips = gold.list_clips(root / gold.lander_dir(slug, 1600))
    assigned = gold.assign_clips(ids, clips, page=slug)
    used = {clip["stem"] for clip in assigned.values() if clip}
    main = MAIN_RE.search(html)
    return {
        "built": ship.is_file(),
        "bands": ids,
        "clips": [clip["stem"] for clip in clips],
        "uncoveredClips": [clip["stem"] for clip in clips if clip["stem"] not in used],
        "extraBands": [sid for sid, clip in assigned.items() if not clip],
        "demoted": len(DEMOTED_RE.findall(main.group(0))) if main else 0,
    }


# ------------------------------------------------------------------ shoot ----

def shoot(root: Path, slug: str, ids: list[str] | None = None, *, skip_build: bool = False) -> dict:
    """Locked astro build (shared dist, one builder at a time) + this page's
    side-by-sides at the run widths. Returns the coverage + report summary."""
    import astro_build
    import paper_23_side_by_side as sbs

    root = root.resolve()
    if not page_src(root, slug).is_file():
        raise FileNotFoundError(f"missing astro/src/pages/{slug}.astro — author it first (5.2)")
    if not skip_build:
        result = astro_build.build(root)
        if result["errors"]:
            log = astro_build.write_build_log(root, result["log"]) or ""
            raise RuntimeError(f"astro build failed: {result['errors']} ({log})")
    argv = [str(root), "--page", slug, "--ship", dist_page_rel(slug)]
    for band in ids or []:
        argv += ["--id", band]
    code = sbs.main(argv)
    if code not in (0,):
        raise RuntimeError(f"paper_23_side_by_side.py exited {code} for {slug}")
    report = json.loads((root / "qa" / "side-by-side" / slug / "report.json").read_text(encoding="utf-8"))
    data = load(root, slug)
    data["lastShoot"] = {
        "at": _now_iso(),
        "pageSha": _sha(page_src(root, slug)),
        "shipFingerprint": report.get("shipFingerprint"),
    }
    cov = coverage(root, slug)
    data["coverage"] = cov
    save(root, slug, data)
    pairs: dict[str, list[str]] = {}
    for row in report.get("stops") or []:
        if row.get("side"):
            pairs.setdefault(str(row["id"]), []).append(str(row["side"]))
    return {"page": slug, "coverage": cov, "pairs": pairs}


# ----------------------------------------------------------------- record ----

def record(root: Path, slug: str, band: str, verdict: str, seen: str) -> dict:
    root = root.resolve()
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    if len(seen.split()) < 8:
        raise ValueError("--seen needs at least 8 words: what each width shows, concretely")
    data = load(root, slug)
    shot = data.get("lastShoot") or {}
    page_sha = _sha(page_src(root, slug))
    if not shot or shot.get("pageSha") != page_sha:
        raise ValueError(
            f"{slug}.astro changed since the last shoot — run `page_loop.py shoot . --page {slug}` "
            "and look at the NEW pairs before recording"
        )
    if band not in (data.get("coverage") or {}).get("bands", []):
        raise ValueError(f"#{band} is not a band on the built {slug} page")
    rounds = data["bands"].setdefault(band, [])
    misses = sum(1 for r in rounds if r["verdict"] == "miss")
    if verdict == "residual" and misses < MAX_ROUNDS:
        raise ValueError(
            f"#{band}: residual only after {MAX_ROUNDS} miss rounds ({misses} so far) — keep fixing"
        )
    rounds.append({"round": len(rounds) + 1, "verdict": verdict, "seen": seen,
                   "pageSha": page_sha, "at": _now_iso()})
    save(root, slug, data)
    return {"band": band, "round": len(rounds), "verdict": verdict, "misses": misses + (verdict == "miss")}


# ------------------------------------------------------------------ check ----

def page_errors(root: Path, slug: str) -> list[str]:
    root = root.resolve()
    data = load(root, slug)
    if not receipt_path(root, slug).is_file():
        return [f"{slug}: no page loop yet — `wave.py --phase page-loop` (one worker per page)"]
    errors: list[str] = []
    cov = coverage(root, slug)
    if not cov["built"]:
        errors.append(f"{slug}: not built — page_loop.py shoot . --page {slug}")
        return errors
    if not cov["clips"]:
        errors.append(f"{slug}: no source clips in {gold.lander_dir(slug, 1600).as_posix()} — nothing to author against")
    if not cov["bands"]:
        errors.append(f"{slug}: built <main> has no <section id> bands")
    if cov["uncoveredClips"]:
        errors.append(f"{slug}: source sections with no built band: {', '.join(cov['uncoveredClips'])} — author them")
    if cov["extraBands"]:
        errors.append(
            f"{slug}: built bands with no source section: {', '.join(cov['extraBands'])} — "
            "merge them into the right section or remove them; never demote to <div>"
        )
    if cov["demoted"]:
        errors.append(f"{slug}: {cov['demoted']} <div aria-labelledby> in <main> — a section hidden from the compare")
    page_sha = _sha(page_src(root, slug))
    for band in cov["bands"]:
        rounds = (data.get("bands") or {}).get(band) or []
        if not rounds:
            errors.append(f"{slug}#{band}: never looked at")
            continue
        last = rounds[-1]
        if last["verdict"] == "miss":
            errors.append(f"{slug}#{band}: last verdict miss (round {last['round']}) — fix, shoot, look again")
        if last.get("pageSha") != page_sha:
            errors.append(f"{slug}#{band}: page edited after the last look — reshoot and re-record")
    return errors


def gate_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for slug in interior_slugs(root.resolve()):
        errors.extend(page_errors(root, slug))
    return errors


def page_done(root: Path, slug: str) -> bool:
    return not page_errors(root, slug)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sh = sub.add_parser("shoot")
    sh.add_argument("root", type=Path)
    sh.add_argument("--page", required=True)
    sh.add_argument("--id", action="append", dest="ids")
    sh.add_argument("--skip-build", action="store_true")
    rc = sub.add_parser("record")
    rc.add_argument("root", type=Path)
    rc.add_argument("--page", required=True)
    rc.add_argument("--band", required=True)
    rc.add_argument("--verdict", required=True, choices=VERDICTS)
    rc.add_argument("--seen", required=True)
    ck = sub.add_parser("check")
    ck.add_argument("root", type=Path)
    ck.add_argument("--page", required=True)
    st = sub.add_parser("status")
    st.add_argument("root", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "shoot":
            print(json.dumps(shoot(args.root, args.page, args.ids, skip_build=args.skip_build), indent=2))
            return 0
        if args.cmd == "record":
            print(json.dumps(record(args.root, args.page, args.band, args.verdict, args.seen)))
            return 0
        if args.cmd == "check":
            errors = page_errors(args.root, args.page)
            for err in errors:
                print(f"FAIL: {err}", file=sys.stderr)
            if not errors:
                print(f"page-loop: {args.page} done")
            return 0 if not errors else 2
        bad = 0
        for slug in interior_slugs(args.root.resolve()):
            errors = page_errors(args.root, slug)
            bad += bool(errors)
            print(f"{'ok  ' if not errors else 'OPEN'} {slug}" + (f"  — {errors[0]}" if errors else ""))
        return 0 if not bad else 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
