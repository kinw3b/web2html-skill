#!/usr/bin/env python3
"""2.21.0 — 2.3 VALIDATE walk: shoot, Read, record, cap, gate (Pitfall #216)."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import paper_23_validate as validate
import section_22_gate as gate

_INJECT_SPEC = importlib.util.spec_from_file_location(
    "inject_qa_overlay", Path(__file__).with_name("inject-qa-overlay.py")
)
inject_qa_overlay = importlib.util.module_from_spec(_INJECT_SPEC)
assert _INJECT_SPEC.loader
_INJECT_SPEC.loader.exec_module(inject_qa_overlay)


def _fake_capture(root: Path, ids: list[str], *, widths=validate.WIDTHS, **_: object) -> dict:
    rows = []
    for sid in ids:
        for width in widths:
            dest = validate.shots.shot_path(root, sid, width)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(gate.TINY_PNG)
            rows.append({"id": sid, "width": width, "path": dest.relative_to(root).as_posix()})
    return {"ok": True, "skipped": False, "shots": rows}


def _skipped_capture(root: Path, ids: list[str], **_: object) -> dict:
    return {"ok": True, "skipped": True, "shots": []}


def _plant(root: Path) -> None:
    gate.install_passing_artifacts(root)
    gate.validate_receipt_path(root, "hero").unlink()


def _edit(path: Path, marker: str) -> None:
    """Change file content the way a 2.3 patch would."""
    path.write_text(path.read_text(encoding="utf-8") + marker, encoding="utf-8")


class ValidateWalkTest(unittest.TestCase):
    def test_shoot_opens_round_with_side_by_sides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            payload = validate.open_round(root, "hero", capture=_fake_capture)
            self.assertEqual(payload["status"], "open")
            self.assertEqual(len(payload["rounds"]), 1)
            first = payload["rounds"][0]
            self.assertEqual(first["round"], 1)
            for key in ("1600", "768", "390"):
                self.assertTrue((root / first["shots"][key]).is_file())
                self.assertTrue((root / first["sides"][key]).is_file(), key)
                self.assertIn("01-hero", first["sides"][key])
            self.assertEqual(first["seen"], "")
            self.assertEqual(validate.main([str(root), "--status"]), 2)
            self.assertEqual(validate.main([str(root), "--next"]), 0)

    def test_second_shoot_before_record_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            validate.open_round(root, "hero", capture=_fake_capture)
            with self.assertRaises(SystemExit) as ctx:
                validate.open_round(root, "hero", capture=_fake_capture)
            self.assertIn("not recorded", str(ctx.exception))

    def test_record_requires_seen_and_full_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            validate.open_round(root, "hero", capture=_fake_capture)
            with self.assertRaises(SystemExit) as ctx:
                validate.record_round(
                    root, "hero", seen="ok", verdict=validate.parse_verdict("1600=match,768=match,390=match"),
                    misses=[], patched=False,
                )
            self.assertIn("--seen", str(ctx.exception))
            with self.assertRaises(SystemExit) as ctx:
                validate.parse_verdict("1600=match,768=match")
            self.assertIn("390", str(ctx.exception))
            with self.assertRaises(SystemExit):
                validate.parse_verdict("1600=close,768=match,390=match")

    def test_miss_needs_patch_then_next_round_until_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            validate.open_round(root, "hero", capture=_fake_capture)
            verdict = validate.parse_verdict("1600=match,768=miss,390=match")
            miss = [validate.parse_miss("768|cards stack 1-col, Paper 2-col|#hero .grid repeat(2,1fr) @768")]
            with self.assertRaises(SystemExit) as ctx:
                validate.record_round(
                    root, "hero", seen="768 stacks the feature cards in one column", verdict=verdict,
                    misses=[], patched=True,
                )
            self.assertIn("--miss", str(ctx.exception))
            with self.assertRaises(SystemExit) as ctx:
                validate.record_round(
                    root, "hero", seen="768 stacks the feature cards in one column", verdict=verdict,
                    misses=miss, patched=False,
                )
            self.assertIn("patched", str(ctx.exception))
            payload = validate.record_round(
                root, "hero", seen="768 stacks the feature cards in one column", verdict=verdict,
                misses=miss, patched=True,
            )
            self.assertEqual(payload["status"], "open")
            self.assertEqual(payload["rounds"][0]["misses"][0]["width"], 768)
            self.assertIn("hero", " ".join(gate.gate_errors(root)))
            payload = validate.open_round(root, "hero", capture=_fake_capture)
            self.assertEqual(len(payload["rounds"]), 2)
            payload = validate.record_round(
                root, "hero", seen="All three widths now match the 1.2 clip and index-raw numbers",
                verdict=validate.parse_verdict("1600=match,768=match,390=match"), misses=[], patched=False,
            )
            self.assertEqual(payload["status"], "match")
            self.assertEqual(gate.gate_errors(root), [])
            self.assertEqual(validate.main([str(root), "--status"]), 0)

    def test_round_cap_forces_a_residual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            verdict = validate.parse_verdict("1600=match,768=match,390=miss")
            miss = [validate.parse_miss("390|nav wraps to two lines|shrink logo at 390")]
            for number in (1, 2):
                validate.open_round(root, "hero", capture=_fake_capture)
                validate.record_round(
                    root, "hero", seen=f"round {number}: 390 nav still wraps under the logo",
                    verdict=verdict, misses=miss, patched=True,
                )
            validate.open_round(root, "hero", capture=_fake_capture)
            with self.assertRaises(SystemExit) as ctx:
                validate.record_round(
                    root, "hero", seen="round 3: 390 nav still wraps under the logo",
                    verdict=verdict, misses=miss, patched=True,
                )
            self.assertIn("last look", str(ctx.exception))
            with self.assertRaises(SystemExit) as ctx:
                validate.record_round(
                    root, "hero", seen="round 3: 390 nav still wraps under the logo",
                    verdict=verdict, misses=miss, patched=False,
                )
            self.assertIn("--residual", str(ctx.exception))
            payload = validate.record_round(
                root, "hero", seen="round 3: 390 nav still wraps under the logo",
                verdict=verdict, misses=miss, patched=False,
                residual="390 nav label wraps; Paper 390 frame has a shorter label the scrape lacks",
            )
            self.assertEqual(payload["status"], "residual")
            self.assertEqual(gate.gate_errors(root), [])
            with self.assertRaises(SystemExit) as ctx:
                validate.open_round(root, "hero", capture=_fake_capture)
            self.assertIn("3 rounds", str(ctx.exception))

    def test_residual_before_cap_is_refused_by_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            path = gate.validate_receipt_path(root, "hero")
            payload = json.loads(path.read_text())
            payload["status"] = "residual"
            payload["residual"] = "gave up early"
            payload["rounds"][0]["verdict"]["768"] = "miss"
            path.write_text(json.dumps(payload))
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("residual after 1 round", errors)

    def test_patch_after_last_look_fails_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            self.assertEqual(gate.gate_errors(root), [])
            _edit(root / "rebuild" / "index.html", "<!-- late patch -->\n")
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("changed after the last look", errors)
            validate.open_round(root, "hero", capture=_fake_capture)
            validate.record_round(
                root, "hero", seen="Re-shot after the patch; all three widths match the clip",
                verdict=validate.parse_verdict("1600=match,768=match,390=match"), misses=[], patched=False,
            )
            self.assertEqual(gate.gate_errors(root), [])
            css = root / "rebuild" / "css"
            css.mkdir(exist_ok=True)
            (css / "home.css").write_text("#hero{padding:0}", encoding="utf-8")
            self.assertIn("changed after the last look", " ".join(gate.gate_errors(root)))

    def test_overlay_and_3x_sheets_do_not_change_the_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            before = gate.ship_fingerprint(root)
            ship = root / "rebuild" / "index.html"
            ship.write_text(
                inject_qa_overlay.inject(
                    ship.read_text(encoding="utf-8"), "css/qa-overlay.css", "js/qa-overlay.js"
                ),
                encoding="utf-8",
            )
            self.assertIn("qa-overlay", ship.read_text(encoding="utf-8"))
            css = root / "rebuild" / "css"
            css.mkdir(exist_ok=True)
            for name in ("qa-overlay.css", "hover.css", "faq.css", "nav-drawer.css", "nav-dropdown.css"):
                (css / name).write_text(f"/* {name} */", encoding="utf-8")
            self.assertEqual(gate.ship_fingerprint(root), before)
            self.assertEqual(gate.gate_errors(root), [])
            (css / "tokens.css").write_text(":root{--x:1}", encoding="utf-8")
            self.assertNotEqual(gate.ship_fingerprint(root), before)

    def test_skipped_playwright_still_records_and_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            payload = validate.open_round(root, "hero", capture=_skipped_capture)
            self.assertTrue(payload["shotsSkipped"])
            validate.record_round(
                root, "hero", seen="DevTools at 1600/768/390 matches the 1.2 clip; no shots (no Playwright)",
                verdict=validate.parse_verdict("1600=match,768=match,390=match"), misses=[], patched=False,
            )
            self.assertEqual(gate.gate_errors(root), [])
            _edit(root / "rebuild" / "index.html", "<!-- late patch -->\n")
            self.assertIn("changed after the last look", " ".join(gate.gate_errors(root)))

    def test_next_walks_in_ship_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / "rebuild" / "index.html").write_text(
                '<html><body><main><section id="hero"></section>'
                '<section id="pricing"></section></main><footer></footer></body></html>\n'
            )
            for folder in gate.SOURCE_DIRS:
                for nn, slug in (("02", "pricing"), ("03", "footer")):
                    (root / folder / f"{nn}-{slug}.png").write_bytes(gate.TINY_PNG)
            row = validate.next_open(root)
            self.assertEqual(row["id"], "pricing")
            validate.open_round(root, "pricing", capture=_fake_capture)
            validate.record_round(
                root, "pricing", seen="Three tiers side by side at 1600, stacked at 390 like the clip",
                verdict=validate.parse_verdict("1600=match,768=match,390=match"), misses=[], patched=False,
            )
            self.assertEqual(validate.next_open(root)["id"], "footer")
            with self.assertRaises(SystemExit) as ctx:
                validate.open_round(root, "nope", capture=_fake_capture)
            self.assertIn("unknown band", str(ctx.exception))

    def test_cli_record_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            validate.open_round(root, "hero", capture=_fake_capture)
            rc = validate.main(
                [
                    str(root), "--id", "hero", "--record",
                    "--seen", "1.2 clip and rebuild agree at every width",
                    "--verdict", "1600=match,768=match,390=match",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertEqual(validate.band_state(root, "hero"), "match")
            self.assertEqual(validate.main([str(root), "--status"]), 0)
            self.assertEqual(validate.main([str(root), "--next"]), 0)


if __name__ == "__main__":
    unittest.main()
