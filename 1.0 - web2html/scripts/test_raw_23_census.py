#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import raw_23_census as census
import section_22_gate as gate


class Raw23CensusTest(unittest.TestCase):
    def test_flags_dump_svg_assets_missing_from_ship(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "qa" / "paper-measure").mkdir(parents=True)
            (root / "rebuild" / "index-raw.html").write_text(
                '<html data-export="get_jsx-inline-styles"><body>'
                "<div>All Pages</div>"
                '<div style="background-image: url(https://app.paper.design/file-assets/x/chevron.svg)"></div>'
                '<svg viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9" /></svg>'
                "</body></html>\n",
                encoding="utf-8",
            )
            (root / "rebuild" / "index.html").write_text(
                "<html><body><section id=\"hero\"><h1>Home</h1></section></body></html>\n",
                encoding="utf-8",
            )
            payload = census.run_census(root)
            files = [row["file"] for row in payload["missing"] if row.get("kind") == "svg-asset"]
            self.assertIn("chevron.svg", files)
            self.assertGreaterEqual(payload["raw"]["bgSvg"], 1)
            self.assertGreaterEqual(payload["raw"]["svg"], 1)

    def test_matched_filename_is_not_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index-raw.html").write_text(
                '<div style="background-image: url(https://app.paper.design/star.svg)"></div>',
                encoding="utf-8",
            )
            (root / "rebuild" / "index.html").write_text(
                '<img src="images/star.svg" alt="">',
                encoding="utf-8",
            )
            payload = census.run_census(root)
            self.assertEqual(payload["missing"], [])


class Section22RawComparedTest(unittest.TestCase):
    def test_missing_census_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / gate.RAW_CENSUS).unlink()
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("raw-census.json", errors)

    def test_missing_raw_compared_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            receipt = root / "qa" / "paper-measure" / "hero.json"
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    '"rawCompared": true',
                    '"rawCompared": false',
                ),
                encoding="utf-8",
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("index-raw.html", errors)


if __name__ == "__main__":
    unittest.main()
