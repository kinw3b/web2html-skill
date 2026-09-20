#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import paper_23_rebuild_shots as shots
import section_22_gate as gate


HTML = """<!doctype html><html><body>
<section id="hero"></section>
<section id="feature-section-01"></section>
</body></html>
"""


class Paper23ShotsTest(unittest.TestCase):
    def test_parses_section_ids(self) -> None:
        self.assertEqual(
            shots.ship_section_ids(HTML),
            ["hero", "feature-section-01"],
        )

    def test_includes_footer_without_id(self) -> None:
        self.assertEqual(
            shots.ship_section_ids(
                '<section id="hero"></section><footer></footer>'
            ),
            ["hero", "footer"],
        )

    def test_shot_path_sanitizes(self) -> None:
        path = shots.shot_path(Path("/tmp/proj"), "feature section/01", 1600)
        self.assertEqual(path.name, "feature-section-01-1600.png")

    def test_unknown_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(HTML)
            self.assertEqual(shots.main([str(root), "--id", "nope"]), 2)

    def test_missing_ship_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(shots.main([tmp, "--all"]), 2)

    def test_gate_requires_measure_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / gate.MEASURE_INDEX).unlink()
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("paper-measure/_index.json", errors)

    def test_gate_unmeasured_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            payload = (root / gate.MEASURE_INDEX).read_text()
            (root / gate.MEASURE_INDEX).write_text(
                payload.replace('"measured": true', '"measured": false')
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("hero", errors)

    def test_passing_measure_is_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            self.assertEqual(gate.gate_errors(root), [])


if __name__ == "__main__":
    unittest.main()
