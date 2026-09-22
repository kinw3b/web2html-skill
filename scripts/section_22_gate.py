#!/usr/bin/env python3
"""HARD GATE — 2.3 walked each section against disk gold at 1600 / 768 / 390.

Gold is the 1.2 source-section clips plus rebuild/index-raw.html — not a live
Paper MCP fan-out. Do not invent a 1320 or 1024 breakpoint.

2.21.0: every band also needs a VALIDATE receipt (qa/paper-measure/<id>.validate.json,
paper_23_validate.py): at least one recorded round, a non-empty `seen`, a last
round that is match at every width or a residual at the round cap, and a ship
fingerprint (rebuild/index.html + rebuild/css, minus the QA overlay and the 3.x
sheets) equal to the one taken when that round was shot — no patch after the
last look. Pitfall #216.

2.23.0: LOOK is wave.py. An applied qa/agent-runs/<run>/2.3/wave.json must cover
every ship band (findings on disk). Adapter orca / subagent / serial is how
LOOK ran; skipping wave.py and --record'ing from the controller fails
(Pitfall #221).

  python3 section_22_gate.py /path/to/project

Exit 0 ok · 2 missing receipt / invented width / a section still open
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import paper_23_rebuild_shots as shots

try:  # same ignore list as the 2.4 freeze: overlay + 3.x sheets are not 2.3 patches
    from fidelity_freeze import IGNORE_CSS as FINGERPRINT_IGNORE_CSS
except Exception:  # pragma: no cover - fallback if the freeze module moves
    FINGERPRINT_IGNORE_CSS = {"hover.css", "qa-overlay.css", "faq.css", "nav-dropdown.css", "nav-drawer.css"}

GENERATED_FROM = "web2html/section-22"
RECEIPT = Path("qa/section-align-22.json")
NOTES = Path("qa/section-align-22.md")
QA = Path("qa/section-22-qa.json")
SHIP = Path("rebuild/index.html")
RAW = Path("rebuild/index-raw.html")
MEASURE_INDEX = Path("qa/paper-measure/_index.json")
MEASURE_FROM = "web2html/section-23-paper-loop"
RAW_CENSUS = Path("qa/paper-measure/raw-census.json")
RAW_CENSUS_FROM = "web2html/section-23-raw-census"
DISK_GOLD = Path("qa/paper-measure/disk-gold.json")
DISK_GOLD_FROM = "web2html/section-23-disk-gold"
CLIP_COMPARE = Path("qa/paper-measure/clip-compare.json")
CLIP_COMPARE_FROM = "web2html/section-23-clip-compare"
REBUILD_SKIP = Path("qa/paper-measure/rebuild-shots-skip.json")
VALIDATE_FROM = "web2html/section-23-validate"
VALIDATE_MAX_ROUNDS = 3
VALIDATE_MIN_SEEN = 12
WAVE_FROM = "web2html/wave/v1"
FINDINGS_FROM = "web2html/agent-findings/v1"
WIDTHS = (1600, 768, 390)
WIDTH_KEYS = tuple(str(width) for width in WIDTHS)
FORBIDDEN_WIDTHS = frozenset({1320, 1024, 1440, 1280, 1920})
PASS = frozenset({"aligned", "matched", "pass"})
CAPTURE_DIRS = (
    Path("capture/home-desktop"),
    Path("capture/home-768"),
    Path("capture/home-390"),
)
SOURCE_DIRS = (
    Path("capture/home-desktop/source-sections"),
    Path("capture/home-768/source-sections"),
    Path("capture/home-390/source-sections"),
)


def capture_dir(width: int) -> Path:
    return Path("capture/home-desktop" if width >= 1400 else f"capture/home-{width}")


def run_widths(root: Path) -> tuple[int, ...]:
    """Configured widths (qa/run-config.json); fast run = 1600 + 390."""
    try:
        import run_config

        return tuple(run_config.widths(root))
    except Exception:  # noqa: BLE001 — a missing module reads as the full set
        return WIDTHS


def run_width_keys(root: Path) -> tuple[str, ...]:
    return tuple(str(width) for width in run_widths(root))


def run_capture_dirs(root: Path) -> tuple[Path, ...]:
    return tuple(capture_dir(width) for width in run_widths(root))


def run_source_dirs(root: Path) -> tuple[Path, ...]:
    return tuple(capture_dir(width) / "source-sections" for width in run_widths(root))


def widths_label(root: Path) -> str:
    return " / ".join(str(width) for width in run_widths(root))


def raw_required(root: Path) -> bool:
    try:
        import run_config

        return run_config.raw_dump_enabled(root)
    except Exception:  # noqa: BLE001
        return True
# 1×1 PNG so tests can plant disk gold without Playwright.
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
    "0000000c49444154789c6310119100000080004134a7a92f0000000049454e44ae426082"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _as_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def gate_errors(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    if not (root / SHIP).is_file():
        semantic = root / "rebuild" / "index-semantic.html"
        if semantic.is_file():
            errors.append(
                "missing rebuild/index.html — 2.3 seeds it from "
                "index-semantic.html (seed_index.py). Do not author index.html at 2.2."
            )
        else:
            errors.append(
                "missing rebuild/index.html — finish 2.2 (index-semantic.html) "
                "then seed_index.py before the 2.3 loop"
            )
    if not (root / "rebuild" / "index-semantic.html").is_file():
        errors.append(
            "missing rebuild/index-semantic.html — 2.2 first pass must stay on disk. "
            "Do not delete it after seeding index.html."
        )
    if raw_required(root) and not (root / RAW).is_file():
        errors.append(
            "missing rebuild/index-raw.html — 2.3 compares the authored page "
            "to Paper and the 2.2 get_jsx dump. Do not skip 2.3."
        )
    widths = run_widths(root)
    width_keys = run_width_keys(root)
    label = widths_label(root)
    for folder in run_capture_dirs(root):
        if not (root / folder).is_dir():
            errors.append(
                f"missing {folder.as_posix()} — 2.3 compares rebuild shots to 1.2 source clips"
            )
    for folder in run_source_dirs(root):
        if not (root / folder).is_dir():
            errors.append(
                f"missing {folder.as_posix()} — 1.2 already parked NN-*.png clips; "
                "2.3 does not re-query Paper MCP"
            )
    payload = _read_json(root / RECEIPT)
    if payload is None:
        errors.append(
            f"missing {RECEIPT} — walk each section against Paper {label}, "
            "write a receipt, then the next section"
        )
        return errors
    if payload.get("generatedFrom") not in {GENERATED_FROM, "web2html/section-22"}:
        errors.append(
            f"{RECEIPT} generatedFrom={payload.get('generatedFrom')!r} — "
            "must be the 2.3 section-vs-Paper loop"
        )
    claimed = payload.get("widths") or []
    claimed_ints = [width for width in (_as_int(item) for item in claimed) if width is not None]
    extra = sorted({width for width in claimed_ints if width in FORBIDDEN_WIDTHS or width not in widths})
    if extra:
        errors.append(
            f"invented breakpoint(s) {extra} — only {label}. Do not add 1320 or 1024"
        )
    if not all(width in claimed_ints for width in widths):
        errors.append(f"receipt widths must include {', '.join(width_keys)}")
    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("receipt has no sections — walk the page band by band")
        return errors
    open_rows: list[str] = []
    for index, row in enumerate(sections):
        if not isinstance(row, dict):
            open_rows.append(f"sections[{index}]")
            continue
        sid = str(row.get("id") or row.get("slug") or f"section-{index}")
        for key in width_keys:
            status = str(row.get(key) or row.get(int(key)) or "").strip().lower()
            if status not in PASS:
                open_rows.append(f"{sid}@{key}")
    if open_rows:
        errors.append(
            "sections still open: "
            + ", ".join(open_rows[:8])
            + f" — every section needs aligned at {label}"
        )
    if payload.get("ok") is not True and not open_rows:
        errors.append(f"{RECEIPT} ok is not true")
    errors.extend(_measure_errors(root, sections))
    return errors


def _measure_errors(root: Path, sections: list) -> list[str]:
    """Proof the aligned rows were measured from Paper, not eyeballed."""
    errors: list[str] = []
    measure = _read_json(root / MEASURE_INDEX)
    if measure is None:
        errors.append(
            f"missing {MEASURE_INDEX} — measure from index-raw + 1.2 source clips "
            "(references/section-23-paper-loop.md), then write the index"
        )
        return errors
    if measure.get("generatedFrom") != MEASURE_FROM:
        errors.append(
            f"{MEASURE_INDEX} generatedFrom={measure.get('generatedFrom')!r} — "
            f"must be {MEASURE_FROM}"
        )
    rows = measure.get("sections")
    if not isinstance(rows, list) or not rows:
        errors.append(f"{MEASURE_INDEX} has no sections")
        return errors
    by_id: dict[str, dict] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("id"):
            by_id[str(row["id"])] = row
    for index, row in enumerate(sections):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or row.get("slug") or f"section-{index}")
        measured = by_id.get(sid)
        if measured is None:
            errors.append(
                f"{sid} missing from {MEASURE_INDEX} — census type/buttons/"
                "overlays/list vectors before signing aligned"
            )
            continue
        if measured.get("measured") is not True:
            errors.append(f"{sid} measured is not true — stay on the Paper loop")
            continue
        receipt = measured.get("receipt")
        if not receipt or not (root / str(receipt)).is_file():
            errors.append(
                f"{sid} missing measure receipt {receipt!r} — "
                "write qa/paper-measure/<id>.json from index-raw + source clips"
            )
            continue
        payload = _read_json(root / str(receipt)) or {}
        if payload.get("rawCompared") is not True:
            errors.append(
                f"{sid} did not census rebuild/index-raw.html — 2.3 ports "
                "dump SVG/icon fills the author dropped (Pitfall #201)"
            )
        if payload.get("diskCompared") is not True:
            errors.append(
                f"{sid} did not compare rebuild shots to 1.2 source-section clips "
                "(Pitfall #202)"
            )
        if payload.get("clipCompared") is not True:
            errors.append(
                f"{sid} did not read the numbered 1.2 clip compare "
                "(qa/paper-measure/compare/NN-slug-1600-side.png)"
            )
    errors.extend(_raw_census_errors(root))
    errors.extend(_disk_gold_errors(root, sections))
    errors.extend(_rebuild_shot_errors(root, sections))
    errors.extend(_clip_compare_errors(root, sections))
    errors.extend(_validate_errors(root, sections))
    errors.extend(_wave_errors(root, sections))
    return errors


def _applied_waves(root: Path) -> list[dict]:
    runs = root / "qa" / "agent-runs"
    if not runs.is_dir():
        return []
    waves: list[dict] = []
    for path in sorted(runs.glob("*/2.3/wave.json")):
        payload = _read_json(path)
        if payload and payload.get("appliedAt"):
            waves.append(payload)
    return waves


def _wave_errors(root: Path, sections: list) -> list[str]:
    """VALIDATE LOOK ran through wave.py for every band (Pitfall #221)."""
    waves = _applied_waves(root)
    if not waves:
        return [
            "missing 2.3 wave — after --shoot-open, run wave.py prepare/start/wait/apply. "
            "LOOK is the wave (orca terminals / subagent / serial specs); the controller "
            "records. Do not --record from a solo Read loop (Pitfall #221)"
        ]
    errors: list[str] = []
    covered: set[str] = set()
    for wave in waves:
        for task in wave.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            band = str(task.get("band") or "").strip()
            if band:
                covered.add(band)
            rel = str(task.get("findings") or "").strip()
            if rel and not (root / rel).is_file():
                errors.append(
                    f"{task.get('id') or band}: missing wave finding {rel} (Pitfall #221)"
                )
    for index, row in enumerate(sections):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or row.get("slug") or f"section-{index}")
        if sid not in covered:
            errors.append(
                f"{sid} has no 2.3 wave finding — LOOK is wave.py, not a solo "
                "--record (Pitfall #221)"
            )
    return errors


def validate_receipt_path(root: Path, section_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", section_id).strip("-") or "section"
    return root / "qa" / "paper-measure" / f"{safe}.validate.json"


# What inject-qa-overlay.py adds at 2.4: an <html> attribute, a <link>, a <script>.
_OVERLAY_RE = re.compile(
    r'\s*data-qa-outlines="[^"]*"'
    r"|<link\b[^>]*qa-overlay[^>]*>"
    r"|<script\b[^>]*qa-overlay[^>]*>\s*</script>",
    re.I,
)


def normalized_ship_html(text: str) -> str:
    """Ship markup without the 2.4 QA overlay; whitespace collapsed, none between tags."""
    text = re.sub(r"\s+", " ", _OVERLAY_RE.sub("", text)).strip()
    return re.sub(r">\s+<", "><", text)


def ship_fingerprint(root: Path) -> str:
    """sha256 of what a 2.3 patch can touch: rebuild/index.html (minus the 2.4 QA
    overlay) + rebuild/css/*.css (minus the overlay and the 3.x sheets)."""
    import hashlib

    digest = hashlib.sha256()
    ship = root / SHIP
    try:
        text = ship.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    digest.update(normalized_ship_html(text).encode("utf-8"))
    css_dir = root / "rebuild" / "css"
    if css_dir.is_dir():
        for path in sorted(css_dir.rglob("*.css")):
            if path.name in FINGERPRINT_IGNORE_CSS:
                continue
            digest.update(b"\0" + path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            try:
                digest.update(path.read_bytes())
            except OSError:
                continue
    return digest.hexdigest()


def _validate_errors(root: Path, sections: list) -> list[str]:
    """VALIDATE ran on every band: shot, seen, verdict, fresh (Pitfall #216)."""
    errors: list[str] = []
    skip = _read_json(root / REBUILD_SKIP)
    shots_skipped = bool(skip and skip.get("skipped") is True)
    current_fingerprint = ship_fingerprint(root)
    for index, row in enumerate(sections):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or row.get("slug") or f"section-{index}")
        payload = _read_json(validate_receipt_path(root, sid))
        if payload is None:
            errors.append(
                f"{sid} has no VALIDATE receipt — paper_23_validate.py . --shoot-open, "
                "then wave.py prepare/start/wait/apply, then --record (Pitfall #216 #221)"
            )
            continue
        if payload.get("generatedFrom") != VALIDATE_FROM:
            errors.append(f"{sid} validate receipt generatedFrom must be {VALIDATE_FROM}")
        rounds = payload.get("rounds")
        if not isinstance(rounds, list) or not rounds or not all(isinstance(r, dict) for r in rounds):
            errors.append(f"{sid} VALIDATE has no recorded round — --shoot then --record")
            continue
        cap = _as_int(payload.get("maxRounds")) or VALIDATE_MAX_ROUNDS
        if len(rounds) > cap:
            errors.append(f"{sid} VALIDATE ran {len(rounds)} rounds — cap is {cap}. Record the residual")
        for r in rounds:
            seen = " ".join(str(r.get("seen") or "").split())
            if len(seen) < VALIDATE_MIN_SEEN:
                errors.append(
                    f"{sid} VALIDATE round {r.get('round')} has no `seen` — say what the "
                    "side-by-sides showed before signing (Pitfall #216)"
                )
            verdict = r.get("verdict") if isinstance(r.get("verdict"), dict) else {}
            bad = [key for key in run_width_keys(root) if str(verdict.get(key) or "").lower() not in {"match", "miss"}]
            if bad:
                errors.append(f"{sid} VALIDATE round {r.get('round')} has no verdict at {bad}")
        last = rounds[-1]
        verdict = last.get("verdict") if isinstance(last.get("verdict"), dict) else {}
        all_match = all(str(verdict.get(key) or "").lower() == "match" for key in run_width_keys(root))
        status = str(payload.get("status") or "open")
        if status == "match" and not all_match:
            errors.append(f"{sid} VALIDATE says match but the last round still misses")
        elif status == "residual":
            if len(rounds) < cap:
                errors.append(
                    f"{sid} VALIDATE recorded a residual after {len(rounds)} round(s) — "
                    f"walk it to round {cap} first"
                )
            if not str(payload.get("residual") or "").strip():
                errors.append(f"{sid} VALIDATE residual has no reason")
        elif status != "match":
            errors.append(
                f"{sid} VALIDATE is still open — patch, --shoot, Read, --record until "
                "every width is match or round {cap}".replace("{cap}", str(cap))
            )
        looked_at = str(last.get("shipFingerprint") or "")
        if not looked_at:
            errors.append(f"{sid} VALIDATE last round has no ship fingerprint — --shoot again")
        elif looked_at != current_fingerprint:
            errors.append(
                f"{sid} VALIDATE: rebuild/index.html or rebuild/css changed after the last "
                "look (round {n}). A patch you did not re-shoot is invisible — --shoot and "
                "Read again".replace("{n}", str(last.get("round")))
            )
        round_skipped = bool(last.get("shotsSkipped")) or bool(payload.get("shotsSkipped"))
        if shots_skipped or round_skipped:
            continue
        shot_rows = last.get("shots") if isinstance(last.get("shots"), dict) else {}
        for key in run_width_keys(root):
            rel = shot_rows.get(key)
            if not rel or not (root / str(rel)).is_file():
                errors.append(f"{sid} VALIDATE last round has no shot at {key} — --shoot again")
    return errors


def _disk_gold_errors(root: Path, sections: list) -> list[str]:
    gold = _read_json(root / DISK_GOLD)
    if gold is None:
        return [
            f"missing {DISK_GOLD} — run paper_23_disk_gold.py so 2.3 workers "
            "compare against 1.2 source-section clips, not live Paper MCP"
        ]
    errors: list[str] = []
    if gold.get("generatedFrom") != DISK_GOLD_FROM:
        errors.append(
            f"{DISK_GOLD} generatedFrom={gold.get('generatedFrom')!r} — "
            f"must be {DISK_GOLD_FROM}"
        )
    if gold.get("ok") is not True:
        errors.append(
            f"{DISK_GOLD} ok is not true — a homepage band is missing "
            f"source clips at {widths_label(root)}"
        )
    rows = gold.get("sections")
    by_id: dict[str, dict] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                by_id[str(row["id"])] = row
    for index, row in enumerate(sections):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or row.get("slug") or f"section-{index}")
        mapped = by_id.get(sid)
        if mapped is None:
            errors.append(f"{sid} missing from {DISK_GOLD}")
            continue
        source = mapped.get("source") if isinstance(mapped.get("source"), dict) else {}
        for key in run_width_keys(root):
            path = source.get(key)
            if not path or not (root / str(path)).is_file():
                errors.append(f"{sid} missing 1.2 source clip at {key}")
    return errors


def _rebuild_shot_errors(root: Path, sections: list) -> list[str]:
    skip = _read_json(root / REBUILD_SKIP)
    if skip and skip.get("skipped") is True:
        return []
    errors: list[str] = []
    for index, row in enumerate(sections):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or row.get("slug") or f"section-{index}")
        for width in run_widths(root):
            dest = shots.shot_path(root, sid, width)
            if not dest.is_file():
                errors.append(
                    f"{sid} missing rebuild shot at {width} — run "
                    "paper_23_rebuild_shots.py or write the Playwright skip receipt"
                )
    return errors


def _clip_compare_errors(root: Path, sections: list) -> list[str]:
    compare = _read_json(root / CLIP_COMPARE)
    if compare is None:
        return [
            f"missing {CLIP_COMPARE} — run paper_23_clip_compare.py to pull "
            f"the numbered 1.2 source-section clips (01-slug.png at {widths_label(root)}) "
            "and pair them with rebuild shots"
        ]
    errors: list[str] = []
    if compare.get("generatedFrom") != CLIP_COMPARE_FROM:
        errors.append(
            f"{CLIP_COMPARE} generatedFrom={compare.get('generatedFrom')!r} — "
            f"must be {CLIP_COMPARE_FROM}"
        )
    if compare.get("ok") is not True:
        errors.append(
            f"{CLIP_COMPARE} ok is not true — a band is missing its 1.2 "
            "NN-slug.png clip or rebuild pair"
        )
    rows = compare.get("pairs")
    by_id: dict[str, dict[str, dict]] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            sid = str(row["id"])
            by_id.setdefault(sid, {})[str(row.get("width") or "")] = row
    for index, row in enumerate(sections):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or row.get("slug") or f"section-{index}")
        pairs = by_id.get(sid) or {}
        for key in run_width_keys(root):
            pair = pairs.get(key)
            if pair is None:
                errors.append(f"{sid} missing clip-compare pair at {key}")
                continue
            pulled = pair.get("pulledSource")
            if not pulled or not (root / str(pulled)).is_file():
                errors.append(
                    f"{sid} did not pull the 1.2 {key} source-section clip "
                    "(NN-slug.png)"
                )
    return errors


def _raw_census_errors(root: Path) -> list[str]:
    census = _read_json(root / RAW_CENSUS)
    if census is None:
        return [
            f"missing {RAW_CENSUS} — run raw_23_census.py so 2.3 workers "
            "see dump SVG/icon fills vs the authored page"
        ]
    if census.get("generatedFrom") != RAW_CENSUS_FROM:
        return [
            f"{RAW_CENSUS} generatedFrom={census.get('generatedFrom')!r} — "
            f"must be {RAW_CENSUS_FROM}"
        ]
    return []


def ready(root: Path) -> bool:
    return not gate_errors(root)


def install_passing_artifacts(root: Path) -> None:
    root = root.resolve()
    (root / "rebuild").mkdir(parents=True, exist_ok=True)
    (root / "qa").mkdir(parents=True, exist_ok=True)
    for folder in CAPTURE_DIRS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    for folder in SOURCE_DIRS:
        dest = root / folder
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "01-hero.png").write_bytes(TINY_PNG)
        (dest / "01-hero.json").write_text(
            json.dumps({"id": "01", "slug": "hero", "png": "01-hero.png", "tag": "section"})
            + "\n",
            encoding="utf-8",
        )
    if not (root / SHIP).is_file():
        (root / SHIP).write_text("<html><body><main><section id=\"hero\"></section></main></body></html>\n")
    semantic = root / "rebuild" / "index-semantic.html"
    if not semantic.is_file():
        semantic.write_text((root / SHIP).read_text(encoding="utf-8"), encoding="utf-8")
    if not (root / RAW).is_file():
        (root / RAW).write_text(
            '<html data-export="get_jsx-inline-styles"><body>'
            '<div data-paper-section="hero">raw</div></body></html>\n'
        )
    (root / RECEIPT).write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "ok": True,
                "widths": list(WIDTHS),
                "sections": [
                    {
                        "id": "hero",
                        "1600": "aligned",
                        "768": "aligned",
                        "390": "aligned",
                        "receipt": "qa/section-22/hero.md",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / NOTES).write_text("# 2.3 section loop\n\nhero aligned at 1600 / 768 / 390.\n")
    measure_dir = root / "qa" / "paper-measure"
    measure_dir.mkdir(parents=True, exist_ok=True)
    (measure_dir / "hero.json").write_text(
        json.dumps(
            {
                "id": "hero",
                "paperNodeId": "hero-section",
                "rawCompared": True,
                "diskCompared": True,
                "clipCompared": True,
                "gold": "disk",
                "raw": {"svg": 1, "bgSvg": 0, "ported": []},
                "type": {"h1": {"fontSize": "72px", "lineHeight": "92px"}},
                "buttons": [{"label": "Get Started Now", "borderRadius": "10px"}],
                "overlays": [],
                "lists": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (measure_dir / "raw-census.json").write_text(
        json.dumps(
            {
                "generatedFrom": RAW_CENSUS_FROM,
                "ok": True,
                "raw": {"svg": 1, "img": 0, "bg": 0, "bgSvg": 0},
                "ship": {"svg": 1, "img": 0, "bg": 0, "bgSvg": 0},
                "missing": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rebuild_dir = measure_dir / "rebuild"
    rebuild_dir.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        (rebuild_dir / f"hero-{width}.png").write_bytes(TINY_PNG)
    (root / DISK_GOLD).write_text(
        json.dumps(
            {
                "generatedFrom": DISK_GOLD_FROM,
                "ok": True,
                "widths": list(WIDTHS),
                "sections": [
                    {
                        "id": "hero",
                        "source": {
                            "1600": "capture/home-desktop/source-sections/01-hero.png",
                            "768": "capture/home-768/source-sections/01-hero.png",
                            "390": "capture/home-390/source-sections/01-hero.png",
                        },
                    }
                ],
                "missing": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    compare_dir = measure_dir / "compare"
    compare_dir.mkdir(parents=True, exist_ok=True)
    compare_pairs: list[dict] = []
    for width in WIDTHS:
        pulled = compare_dir / f"01-hero-{width}-source.png"
        pulled.write_bytes(TINY_PNG)
        compare_pairs.append(
            {
                "id": "hero",
                "nn": "01",
                "slug": "hero",
                "width": width,
                "source": f"capture/home-desktop/source-sections/01-hero.png"
                if width == 1600
                else f"capture/home-{width}/source-sections/01-hero.png",
                "pulledSource": pulled.relative_to(root).as_posix(),
            }
        )
    (root / CLIP_COMPARE).write_text(
        json.dumps(
            {
                "generatedFrom": CLIP_COMPARE_FROM,
                "ok": True,
                "widths": list(WIDTHS),
                "pairs": compare_pairs,
                "missing": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / MEASURE_INDEX).write_text(
        json.dumps(
            {
                "generatedFrom": MEASURE_FROM,
                "ok": True,
                "widths": list(WIDTHS),
                "sections": [
                    {
                        "id": "hero",
                        "measured": True,
                        "receipt": "qa/paper-measure/hero.json",
                        "1600": "aligned",
                        "768": "aligned",
                        "390": "aligned",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    install_passing_validate(root, "hero", nn="01")
    install_passing_wave(root, ["hero"])


def install_passing_validate(root: Path, section_id: str, *, nn: str | None = None) -> Path:
    """Plant a one-round, all-match VALIDATE receipt fingerprinted on the current ship."""
    root = root.resolve()
    compare_dir = root / "qa" / "paper-measure" / "compare"
    compare_dir.mkdir(parents=True, exist_ok=True)
    shot_rows: dict[str, str] = {}
    sides: dict[str, str] = {}
    for width in WIDTHS:
        shot = shots.shot_path(root, section_id, width)
        shot.parent.mkdir(parents=True, exist_ok=True)
        shot.write_bytes(TINY_PNG)
        shot_rows[str(width)] = shot.relative_to(root).as_posix()
        side = compare_dir / f"{nn or '00'}-{section_id}-{width}-side.png"
        side.write_bytes(TINY_PNG)
        sides[str(width)] = side.relative_to(root).as_posix()
    payload = {
        "generatedFrom": VALIDATE_FROM,
        "id": section_id,
        "nn": nn,
        "slug": section_id,
        "widths": list(WIDTHS),
        "maxRounds": VALIDATE_MAX_ROUNDS,
        "status": "match",
        "residual": "",
        "shotsSkipped": False,
        "rounds": [
            {
                "round": 1,
                "shotAt": _now_iso(),
                "shotsSkipped": False,
                "shipFingerprint": ship_fingerprint(root),
                "shots": shot_rows,
                "sides": sides,
                "seen": "All three side-by-sides match the 1.2 clip: split hero, 2 CTAs, overlay card.",
                "verdict": {"1600": "match", "768": "match", "390": "match"},
                "misses": [],
                "patched": False,
                "recordedAt": _now_iso(),
            }
        ],
        "updated": _now_iso(),
    }
    dest = validate_receipt_path(root, section_id)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def install_passing_wave(root: Path, section_ids: list[str] | None = None) -> Path:
    """Plant an applied 2.3 wave covering `section_ids` (default: hero)."""
    root = root.resolve()
    ids = list(section_ids or ["hero"])
    run_id = "r1"
    phase = "2.3"
    dest_dir = root / "qa" / "agent-runs" / run_id / phase
    dest_dir.mkdir(parents=True, exist_ok=True)
    tasks: list[dict] = []
    for sid in ids:
        agent = f"band-{sid}"
        finding_rel = f"qa/agent-findings/{run_id}/{phase}/{agent}.json"
        finding_path = root / finding_rel
        finding_path.parent.mkdir(parents=True, exist_ok=True)
        finding_path.write_text(
            json.dumps(
                {
                    "generatedFrom": FINDINGS_FROM,
                    "phase": phase,
                    "agent": agent,
                    "inputSha256": "test",
                    "band": sid,
                    "verdict": {"1600": "match", "768": "match", "390": "match"},
                    "seen": "All three side-by-sides match the 1.2 clip: split hero, two CTAs, overlay card.",
                    "misses": [],
                    "patch": "",
                    "findings": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        tasks.append(
            {
                "id": agent,
                "kind": "validate-band",
                "band": sid,
                "findings": finding_rel,
                "status": "applied",
            }
        )
    path = dest_dir / "wave.json"
    path.write_text(
        json.dumps(
            {
                "generatedFrom": WAVE_FROM,
                "runId": run_id,
                "phase": phase,
                "appliedAt": _now_iso(),
                "tasks": tasks,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_receipt(root: Path, errors: list[str]) -> Path:
    dest = root / QA
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "generatedFrom": GENERATED_FROM,
                "ok": not errors,
                "errors": errors,
                "updated": _now_iso(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def page_clip_errors(root: Path, page: str, widths: tuple[int, ...]) -> list[str]:
    """5.2 / 5.3 — confirm disk gold exists for one interior page."""
    import paper_23_disk_gold as gold

    ship = gold.ship_rel_for(page)
    if not (root / ship).is_file():
        return [f"missing {ship.as_posix()}"]
    missing_dirs = [
        gold.lander_dir(page, width).as_posix()
        for width in widths
        if not (root / gold.lander_dir(page, width)).is_dir()
    ]
    if missing_dirs:
        return [f"{page} missing {', '.join(missing_dirs)}"]
    mapped = gold.build_index(root, page=page, widths=widths)
    if not mapped.get("ok"):
        return [f"{page} missing clips {mapped.get('missing')}"]
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path)
    ap.add_argument("--page", default="home")
    ap.add_argument("--widths", default="")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.page != "home" or args.widths:
        import paper_23_disk_gold as gold
        widths = gold.parse_widths(args.widths or None)
        errors = page_clip_errors(root, args.page, widths)
        if errors:
            for err in errors:
                print(f"FAIL: {err}", file=sys.stderr)
            return 2
        print(f"section-22: ok {args.page} {list(widths)}")
        return 0
    errors = gate_errors(root)
    write_receipt(root, errors)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 2
    print("section-22: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
