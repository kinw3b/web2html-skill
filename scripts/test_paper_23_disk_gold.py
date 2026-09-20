#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import paper_23_disk_gold as gold
import section_22_gate as gate


def _plant_clip(root: Path, folder: str, stem: str, slug: str) -> None:
    dest = root / "capture" / folder / "source-sections"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{stem}.png").write_bytes(gate.TINY_PNG)
    (dest / f"{stem}.json").write_text(
        json.dumps({"id": stem.split("-", 1)[0], "slug": slug, "png": f"{stem}.png"})
        + "\n",
        encoding="utf-8",
    )


class DiskGoldTest(unittest.TestCase):
    def test_maps_ship_ids_to_numbered_clips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(
                '<section id="hero"></section><footer id="site-footer"></footer>'
            )
            for folder in ("home-desktop", "home-768", "home-390"):
                _plant_clip(root, folder, "01-hero", "hero")
                _plant_clip(root, folder, "02-footer", "site-footer")
            self.assertEqual(gold.main([str(root)]), 0)
            payload = json.loads((root / gold.OUT).read_text())
            self.assertTrue(payload["ok"])
            self.assertEqual([row["id"] for row in payload["sections"]], ["hero", "site-footer"])
            self.assertEqual(payload["sections"][0]["nn"], "01")
            self.assertEqual(payload["sections"][0]["slug"], "hero")
            self.assertTrue(payload["sections"][0]["source"]["1600"].endswith("01-hero.png"))

    def test_missing_clip_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text('<section id="hero"></section>')
            self.assertEqual(gold.main([str(root)]), 2)
            payload = json.loads((root / gold.OUT).read_text())
            self.assertFalse(payload["ok"])
            self.assertIn("hero@1600", payload["missing"])

    def test_gate_requires_disk_compared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            receipt = root / "qa" / "paper-measure" / "hero.json"
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    '"diskCompared": true',
                    '"diskCompared": false',
                ),
                encoding="utf-8",
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("source-section", errors)

    def test_gate_requires_disk_gold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / gate.DISK_GOLD).unlink()
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("disk-gold.json", errors)

    def test_page_and_width_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "about.html").write_text('<section id="hero"></section>')
            _plant_clip(root, "about-desktop", "01-hero", "hero")
            self.assertEqual(
                gold.main([str(root), "--page", "about", "--widths", "1600"]),
                0,
            )
            payload = json.loads((root / gold.OUT).read_text())
            self.assertEqual(payload["page"], "about")
            self.assertEqual(payload["widths"], [1600])
            self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()

