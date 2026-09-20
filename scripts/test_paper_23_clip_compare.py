#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import paper_23_clip_compare as compare
import section_22_gate as gate


def _plant(root: Path) -> None:
    (root / "rebuild").mkdir()
    (root / "rebuild" / "index.html").write_text(
        '<section id="hero"></section>',
        encoding="utf-8",
    )
    for folder in ("home-desktop", "home-768", "home-390"):
        dest = root / "capture" / folder / "source-sections"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "01-hero.png").write_bytes(gate.TINY_PNG)
        (dest / "01-hero.json").write_text(
            json.dumps({"id": "01", "slug": "hero", "png": "01-hero.png"}) + "\n",
            encoding="utf-8",
        )
    rebuild = root / "qa" / "paper-measure" / "rebuild"
    rebuild.mkdir(parents=True, exist_ok=True)
    for width in (1600, 768, 390):
        (rebuild / f"hero-{width}.png").write_bytes(gate.TINY_PNG)


class ClipCompareTest(unittest.TestCase):
    def test_pulls_numbered_1_2_clips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _plant(root)
            self.assertEqual(compare.main([str(root)]), 0)
            payload = json.loads((root / compare.OUT).read_text())
            self.assertTrue(payload["ok"])
            self.assertEqual(len(payload["pairs"]), 3)
            pulled = root / "qa" / "paper-measure" / "compare" / "01-hero-1600-source.png"
            side = root / "qa" / "paper-measure" / "compare" / "01-hero-1600-side.png"
            self.assertTrue(pulled.is_file())
            self.assertTrue(side.is_file())
            self.assertEqual(payload["pairs"][0]["nn"], "01")
            self.assertEqual(payload["pairs"][0]["slug"], "hero")
            self.assertGreaterEqual(payload["sides"], 1)

    def test_missing_clip_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text('<section id="hero"></section>')
            self.assertEqual(compare.main([str(root)]), 2)
            payload = json.loads((root / compare.OUT).read_text())
            self.assertFalse(payload["ok"])

    def test_gate_requires_clip_compare(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / gate.CLIP_COMPARE).unlink()
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("clip-compare.json", errors)

    def test_gate_requires_clip_compared_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            receipt = root / "qa" / "paper-measure" / "hero.json"
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    '"clipCompared": true',
                    '"clipCompared": false',
                ),
                encoding="utf-8",
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("clip compare", errors)

    def test_page_and_width_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "about.html").write_text(
                '<section id="hero"></section>',
                encoding="utf-8",
            )
            dest = root / "capture" / "about-desktop" / "source-sections"
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "01-hero.png").write_bytes(gate.TINY_PNG)
            (dest / "01-hero.json").write_text(
                json.dumps({"id": "01", "slug": "hero", "png": "01-hero.png"}) + "\n",
                encoding="utf-8",
            )
            skip = root / compare.SKIP
            skip.parent.mkdir(parents=True, exist_ok=True)
            skip.write_text(json.dumps({"skipped": True}) + "\n", encoding="utf-8")
            self.assertEqual(
                compare.main([str(root), "--page", "about", "--widths", "1600"]),
                0,
            )
            payload = json.loads((root / compare.OUT).read_text())
            self.assertEqual(payload["page"], "about")
            self.assertEqual(payload["widths"], [1600])
            self.assertEqual(len(payload["pairs"]), 1)


if __name__ == "__main__":
    unittest.main()
