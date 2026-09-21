#!/usr/bin/env python3
"""2.3 VALIDATE — shoot every open band, then wave.py LOOK (2.23.0).

The one-pass section loop leaves layout misses that used to surface at 2.4.
VALIDATE does that walk inside 2.3. The controller shoots and records.
LOOK is wave.py (orca terminals / subagent / serial specs) — the controller
does not Read the sides itself on the orca or subagent rungs.

  python3 paper_23_validate.py . --shoot-open           # shoot every open band
  python3 $SKILLS/web2html/scripts/wave.py prepare . --phase 2.3 --run-id r1
  python3 $SKILLS/web2html/scripts/wave.py start   . --phase 2.3 --run-id r1
  python3 $SKILLS/web2html/scripts/wave.py wait    . --phase 2.3 --run-id r1
  python3 $SKILLS/web2html/scripts/wave.py apply   . --phase 2.3 --run-id r1
  # apply printed `patch` onto rebuild/, then each printed --record
  python3 paper_23_validate.py . --status               # exit 2 while any band is open
  python3 paper_23_validate.py . --next                 # first open band (legacy pointer)

Receipt: qa/paper-measure/<id>.validate.json (generatedFrom web2html/section-23-validate)
plus an applied qa/agent-runs/<run>/2.3/wave.json covering every band.
section_22_gate.py fails a band without the receipt, with an empty `seen`,
an open last round, more than --max-rounds rounds, a ship that changed after
the last look, or a missing wave (Pitfall #216 #221).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import paper_23_clip_compare as compare
import paper_23_disk_gold as gold
import paper_23_rebuild_shots as shots
from section_22_gate import ship_fingerprint

GENERATED_FROM = "web2html/section-23-validate"
WIDTHS = (1600, 768, 390)
WIDTH_KEYS = tuple(str(width) for width in WIDTHS)
MEASURE_DIR = Path("qa/paper-measure")
DEFAULT_MAX_ROUNDS = 3
MIN_SEEN = 12
VERDICTS = frozenset({"match", "miss"})
STATUSES = frozenset({"open", "match", "residual"})


def _spend(root: Path, kind: str) -> None:
    """Best-effort context-budget ledger (context_budget.py). Never raises, never gates."""
    try:
        import context_budget

        context_budget.add_spend(root, kind)
    except Exception:  # noqa: BLE001
        return


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _safe(section_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", section_id).strip("-") or "section"


def receipt_path(root: Path, section_id: str) -> Path:
    return root / MEASURE_DIR / f"{_safe(section_id)}.validate.json"


def load(root: Path, section_id: str) -> dict | None:
    path = receipt_path(root, section_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save(root: Path, payload: dict) -> Path:
    payload["updated"] = _now_iso()
    dest = receipt_path(root, str(payload["id"]))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def ship_sections(root: Path) -> list[dict]:
    """Ship bands in document order with their 1.2 clip mapping."""
    ship = root / gold.ship_rel_for("home")
    if not ship.is_file():
        raise SystemExit("FAIL: missing rebuild/index.html — seed_index.py first")
    return list(gold.build_index(root).get("sections") or [])


def _section_row(root: Path, section_id: str) -> dict:
    for row in ship_sections(root):
        if str(row.get("id")) == section_id:
            return row
    raise SystemExit(
        f"FAIL: unknown band {section_id!r} — ship bands are "
        f"{[str(r.get('id')) for r in ship_sections(root)]}"
    )


def _new_receipt(row: dict, max_rounds: int) -> dict:
    return {
        "generatedFrom": GENERATED_FROM,
        "id": str(row.get("id")),
        "nn": row.get("nn"),
        "slug": row.get("slug") or row.get("id"),
        "widths": list(WIDTHS),
        "maxRounds": max_rounds,
        "status": "open",
        "residual": "",
        "shotsSkipped": False,
        "rounds": [],
    }


def last_round(payload: dict) -> dict | None:
    rounds = payload.get("rounds")
    if isinstance(rounds, list) and rounds and isinstance(rounds[-1], dict):
        return rounds[-1]
    return None


def round_recorded(round_row: dict | None) -> bool:
    return bool(round_row) and bool(str(round_row.get("seen") or "").strip()) and bool(
        round_row.get("verdict")
    )


def open_round(
    root: Path,
    section_id: str,
    *,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    capture=None,
) -> dict:
    """Re-shoot one band at 1600 / 768 / 390, rebuild its side-by-sides, open a round."""
    root = root.resolve()
    capture = capture or shots.capture
    row = _section_row(root, section_id)
    payload = load(root, section_id) or _new_receipt(row, max_rounds)
    rounds = payload.setdefault("rounds", [])
    cap = int(payload.get("maxRounds") or max_rounds)
    previous = last_round(payload)
    if previous is not None and not round_recorded(previous):
        raise SystemExit(
            f"FAIL: {section_id} round {previous.get('round')} is not recorded — "
            "Read its side-by-sides, patch, then --record before another --shoot"
        )
    if len(rounds) >= cap:
        raise SystemExit(
            f"FAIL: {section_id} already used {cap} rounds — record the residual "
            f"(--record … --residual \"…\") instead of a round {cap + 1}. Pitfall #216."
        )
    result = capture(root, [section_id], widths=WIDTHS)
    skipped = bool(result.get("skipped"))
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    compare_dir = root / compare.COMPARE_DIR
    shot_paths: dict[str, str | None] = {}
    sides: dict[str, str | None] = {}
    for width in WIDTHS:
        key = str(width)
        shot = shots.shot_path(root, section_id, width)
        shot_paths[key] = shot.relative_to(root).as_posix() if shot.is_file() else None
        stem = compare.safe_stem(
            row.get("nn") if isinstance(row.get("nn"), str) else None,
            str(row.get("slug") or section_id),
            width,
        )
        side = None
        src_rel = source.get(key)
        if src_rel and shot.is_file() and (root / str(src_rel)).is_file():
            compare.pull(root, shot, compare_dir / f"{stem}-rebuild.png")
            side_abs = compare_dir / f"{stem}-side.png"
            if compare.side_by_side(root / str(src_rel), shot, side_abs):
                side = side_abs.relative_to(root).as_posix()
        sides[key] = side
    rounds.append(
        {
            "round": len(rounds) + 1,
            "shotAt": _now_iso(),
            "shotsSkipped": skipped,
            "shipFingerprint": ship_fingerprint(root),
            "shots": shot_paths,
            "sides": sides,
            "seen": "",
            "verdict": {},
            "misses": [],
            "patched": None,
        }
    )
    payload["shotsSkipped"] = skipped
    payload["status"] = "open"
    save(root, payload)
    return payload


def parse_verdict(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise SystemExit(f"FAIL: verdict {part!r} — use 1600=match,768=miss,390=match")
        key, value = (item.strip().lower() for item in part.split("=", 1))
        if key not in WIDTH_KEYS or value not in VERDICTS:
            raise SystemExit(f"FAIL: verdict {part!r} — widths 1600/768/390, values match|miss")
        out[key] = value
    missing = [key for key in WIDTH_KEYS if key not in out]
    if missing:
        raise SystemExit(f"FAIL: verdict missing {missing} — every width gets match or miss")
    return out


def parse_miss(raw: str) -> dict:
    parts = [item.strip() for item in (raw or "").split("|")]
    if len(parts) < 2 or not parts[1]:
        raise SystemExit(f"FAIL: miss {raw!r} — use \"<width>|<what differs>|<scoped fix>\"")
    width = parts[0]
    if width not in WIDTH_KEYS:
        raise SystemExit(f"FAIL: miss width {width!r} — 1600, 768, or 390")
    return {"width": int(width), "what": parts[1], "fix": parts[2] if len(parts) > 2 else ""}


def record_round(
    root: Path,
    section_id: str,
    *,
    seen: str,
    verdict: dict[str, str],
    misses: list[dict],
    patched: bool,
    residual: str = "",
) -> dict:
    root = root.resolve()
    payload = load(root, section_id)
    current = last_round(payload) if payload else None
    if payload is None or current is None:
        raise SystemExit(f"FAIL: {section_id} has no open round — run --shoot first")
    if round_recorded(current):
        raise SystemExit(
            f"FAIL: {section_id} round {current.get('round')} is already recorded — "
            "--shoot opens the next one"
        )
    seen = " ".join(str(seen or "").split())
    if len(seen) < MIN_SEEN:
        raise SystemExit(
            "FAIL: --seen must say what the side-by-sides showed (what differs, or "
            f"why all three match), at least {MIN_SEEN} characters. Pitfall #216."
        )
    if any(value == "miss" for value in verdict.values()) and not misses:
        raise SystemExit("FAIL: a miss needs at least one --miss \"<width>|<what>|<fix>\"")
    cap = int(payload.get("maxRounds") or DEFAULT_MAX_ROUNDS)
    number = int(current.get("round") or len(payload["rounds"]))
    all_match = all(value == "match" for value in verdict.values())
    if all_match:
        status = "match"
    elif number >= cap:
        if patched:
            raise SystemExit(
                f"FAIL: round {number} is the last look — a patch after it cannot be re-shot "
                "and would fail the gate. Revert it, or record the residual without --patched. "
                "Pitfall #216."
            )
        if not residual.strip():
            raise SystemExit(
                f"FAIL: round {number} of {cap} still misses — record the residual "
                "(--residual \"what stays off and why\") so 2.4 sees it. Pitfall #216."
            )
        status = "residual"
    else:
        if not patched:
            raise SystemExit(
                "FAIL: a miss before the last round must be patched — fix this band, "
                "then --record --patched, then --shoot the next round. Pitfall #216."
            )
        status = "open"
    current["seen"] = seen
    current["verdict"] = verdict
    current["misses"] = misses
    current["patched"] = bool(patched)
    current["recordedAt"] = _now_iso()
    payload["status"] = status
    payload["residual"] = residual.strip() if status == "residual" else ""
    save(root, payload)
    return payload


def band_state(root: Path, section_id: str) -> str:
    payload = load(root, section_id)
    if payload is None:
        return "missing"
    status = str(payload.get("status") or "open")
    return status if status in STATUSES else "open"


def shoot_open(root: Path, *, max_rounds: int = DEFAULT_MAX_ROUNDS, capture=None) -> tuple[list[str], list[str]]:
    """Open a round on every band that is missing or still open.

    Skips a band whose last round is unrecorded (already shot). Returns
    (shot ids, skipped ids).
    """
    root = root.resolve()
    shot: list[str] = []
    skipped: list[str] = []
    for row in status_rows(root):
        if row["state"] in {"match", "residual"}:
            continue
        sid = str(row["id"])
        payload = load(root, sid)
        previous = last_round(payload) if payload else None
        if previous is not None and not round_recorded(previous):
            skipped.append(sid)
            continue
        open_round(root, sid, max_rounds=max_rounds, capture=capture)
        shot.append(sid)
    return shot, skipped


def next_open(root: Path) -> dict | None:
    for row in ship_sections(root):
        sid = str(row.get("id"))
        if band_state(root, sid) in {"missing", "open"}:
            return row
    return None


def status_rows(root: Path) -> list[dict]:
    rows: list[dict] = []
    for row in ship_sections(root):
        sid = str(row.get("id"))
        payload = load(root, sid)
        rows.append(
            {
                "id": sid,
                "state": band_state(root, sid),
                "rounds": len((payload or {}).get("rounds") or []),
                "residual": (payload or {}).get("residual") or "",
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path)
    ap.add_argument("--id", help="band id from rebuild/index.html (<section id> or footer)")
    ap.add_argument("--shoot", action="store_true", help="re-shoot the band and open a round")
    ap.add_argument("--record", action="store_true", help="record the open round")
    ap.add_argument("--seen", default="", help="what the side-by-sides showed")
    ap.add_argument("--verdict", default="", help="1600=match,768=miss,390=match")
    ap.add_argument("--miss", action="append", default=[], help='"<width>|<what>|<fix>" (repeatable)')
    ap.add_argument("--patched", action="store_true", help="this band's CSS/HTML was patched")
    ap.add_argument("--residual", default="", help="last round only: what stays off and why")
    ap.add_argument("--next", action="store_true", help="print the first open band in ship order")
    ap.add_argument("--shoot-open", action="store_true", help="shoot every open band, then run wave.py")
    ap.add_argument("--status", action="store_true", help="table of every band; exit 2 while any is open")
    ap.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    args = ap.parse_args(argv)
    root = args.root.resolve()

    if args.shoot_open:
        if args.id:
            print("FAIL: --shoot-open shoots every open band; drop --id", file=sys.stderr)
            return 2
        shot, skipped = shoot_open(root, max_rounds=args.max_rounds)
        for _ in shot:
            _spend(root, "shoot")
        if shot:
            print("validate: shot " + ", ".join(shot))
        if skipped:
            print("validate: skipped (unrecorded round): " + ", ".join(skipped))
        if not shot and not skipped:
            print("validate: no open bands — run section_22_gate.py .")
        else:
            print("validate: next is wave.py prepare . --phase 2.3 --run-id rN")
        return 0

    if args.next:
        row = next_open(root)
        if row is None:
            print("validate: every band is match or residual — run section_22_gate.py .")
            return 0
        sid = str(row.get("id"))
        state = band_state(root, sid)
        print(f"validate: next {sid} ({state}) — paper_23_validate.py . --id {sid} --shoot")
        return 0

    if args.status:
        rows = status_rows(root)
        open_count = 0
        for row in rows:
            flag = "" if row["state"] in {"match", "residual"} else "  <- open"
            if flag:
                open_count += 1
            tail = f'  residual: {row["residual"]}' if row["residual"] else ""
            print(f'{row["id"]:<28} {row["state"]:<9} rounds={row["rounds"]}{tail}{flag}')
        if open_count:
            print(f"validate: {open_count} band(s) still open", file=sys.stderr)
            return 2
        print("validate: ok")
        return 0

    if not args.id:
        print("FAIL: pass --id <band> with --shoot or --record, or --next / --status", file=sys.stderr)
        return 2

    if args.shoot:
        payload = open_round(root, args.id, max_rounds=args.max_rounds)
        _spend(root, "shoot")
        current = last_round(payload) or {}
        number = current.get("round")
        cap = payload.get("maxRounds")
        print(f"validate: {args.id} round {number}/{cap} — Read these, then --record:")
        for key in WIDTH_KEYS:
            side = (current.get("sides") or {}).get(key)
            shot = (current.get("shots") or {}).get(key)
            if side:
                print(f"  {side}")
            elif shot:
                print(f"  {shot}  (no side-by-side; Read it next to the 1.2 clip)")
            else:
                print(f"  {key}: no shot (Playwright skipped — compare in DevTools on the file:// tab)")
        return 0

    if args.record:
        payload = record_round(
            root,
            args.id,
            seen=args.seen,
            verdict=parse_verdict(args.verdict),
            misses=[parse_miss(item) for item in args.miss],
            patched=args.patched,
            residual=args.residual,
        )
        _spend(root, "record")
        status = payload.get("status")
        number = (last_round(payload) or {}).get("round")
        if status == "match":
            print(f"validate: {args.id} match after round {number} — paper_23_validate.py . --next")
        elif status == "residual":
            print(f"validate: {args.id} residual after round {number}: {payload.get('residual')}")
        else:
            print(f"validate: {args.id} round {number} recorded — patch landed? --shoot round {int(number) + 1}")
        return 0

    print("FAIL: pass --shoot or --record with --id", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
