#!/usr/bin/env python3
"""3.4 promote: one index.html, intermediates archived, outlines off."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import promote_ship  # noqa: E402


LOCK = "<html data-qa-outlines=\"tags\"><body>lock</body></html>"
RAW = "<html><body>raw</body></html>"
SEMANTIC = "<html><body>semantic</body></html>"
POLISH = (
    "<html data-qa-outlines=\"tags\"><head></head>"
    "<body><main>polish</main>"
    "<script src=\"js/qa-overlay.js\" defer></script></body></html>"
)


class PromoteShipTest(unittest.TestCase):
    def test_promotes_polish_and_archives_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rebuild = root / "rebuild"
            rebuild.mkdir()
            (rebuild / "index.html").write_text(LOCK, encoding="utf-8")
            (rebuild / "index-raw.html").write_text(RAW, encoding="utf-8")
            (rebuild / "index-semantic.html").write_text(SEMANTIC, encoding="utf-8")
            (rebuild / "index-polish.html").write_text(POLISH, encoding="utf-8")
            (rebuild / "polish-report.html").write_text("<html>report</html>", encoding="utf-8")

            receipt = promote_ship.promote(root)

            self.assertFalse(receipt.get("already"))
            self.assertFalse((rebuild / "index-polish.html").exists())
            self.assertFalse((rebuild / "index-raw.html").exists())
            self.assertFalse((rebuild / "index-semantic.html").exists())
            self.assertFalse((rebuild / "polish-report.html").exists())
            ship = (rebuild / "index.html").read_text(encoding="utf-8")
            self.assertIn("polish", ship)
            self.assertIn('data-qa-ship="final"', ship)
            self.assertIn('data-qa-outlines="off"', ship)
            self.assertNotIn('data-qa-outlines="tags"', ship)
            self.assertEqual((rebuild / "archive" / "index.html").read_text(encoding="utf-8"), LOCK)
            self.assertEqual((rebuild / "archive" / "index-raw.html").read_text(encoding="utf-8"), RAW)
            self.assertEqual(
                (rebuild / "archive" / "index-semantic.html").read_text(encoding="utf-8"),
                SEMANTIC,
            )
            self.assertTrue((rebuild / "js" / "qa-overlay.js").is_file())
            overlay = (rebuild / "js" / "qa-overlay.js").read_text(encoding="utf-8")
            self.assertIn('data-qa-ship") === "final"', overlay)
            ignore = (rebuild / ".vercelignore").read_text(encoding="utf-8")
            self.assertIn("archive", ignore.splitlines())
            on_disk = json.loads((root / "qa" / "ship-promote.json").read_text(encoding="utf-8"))
            self.assertEqual(on_disk["ship"], "rebuild/index.html")
            self.assertIn("index.html", on_disk["archived"])
            self.assertIn("index-raw.html", on_disk["archived"])

    def test_second_call_is_a_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rebuild = root / "rebuild"
            rebuild.mkdir()
            (rebuild / "index.html").write_text(LOCK, encoding="utf-8")
            (rebuild / "index-polish.html").write_text(POLISH, encoding="utf-8")
            promote_ship.promote(root)
            again = promote_ship.promote(root)
            self.assertTrue(again.get("already"))
            self.assertIn("polish", (rebuild / "index.html").read_text(encoding="utf-8"))
            self.assertEqual((rebuild / "archive" / "index.html").read_text(encoding="utf-8"), LOCK)

    def test_overlay_template_defaults_ship_off(self) -> None:
        js = (promote_ship.TEMPLATES / "qa-overlay.js").read_text(encoding="utf-8")
        self.assertIn("isShipFinal()", js)
        self.assertIn('getAttribute("data-qa-ship") === "final"', js)
        self.assertIn("if (isShipFinal()) return \"off\"", js)


if __name__ == "__main__":
    unittest.main()
