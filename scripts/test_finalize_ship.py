#!/usr/bin/env python3
"""3.4 finalize: one index.html, overlay stripped in place (legacy bridge keeps promote)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import finalize_ship  # noqa: E402


FINAL_POLISH = (
    '<html data-qa-outlines="tags" data-qa-ship="final"><head>'
    '<script id="qa-outlines-boot">(function(){})();</script>'
    '<link rel="stylesheet" href="css/qa-overlay.css"/>'
    "</head>"
    "<body><main>polish</main>"
    '<script src="js/qa-overlay.js" defer></script></body></html>'
)


class FinalizeShipTest(unittest.TestCase):
    def _overlay_ship(self, root: Path) -> None:
        rebuild = root / "rebuild"
        rebuild.mkdir()
        (rebuild / "index.html").write_text(FINAL_POLISH, encoding="utf-8")
        (rebuild / "css").mkdir()
        (rebuild / "js").mkdir()
        (rebuild / "css" / "qa-overlay.css").write_text("/* overlay */\n", encoding="utf-8")
        (rebuild / "js" / "qa-overlay.js").write_text("/* overlay */\n", encoding="utf-8")
        (rebuild / "js" / "gsap-reveal.js").write_text("/* keep */\n", encoding="utf-8")

    def test_strips_overlay_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._overlay_ship(root)
            rebuild = root / "rebuild"

            receipt = finalize_ship.finalize(root)

            self.assertFalse(receipt.get("already"))
            self.assertEqual(receipt["ship"], "rebuild/index.html")
            # nothing archived — there are no variants in the single-file model
            self.assertFalse((rebuild / "archive").exists())
            self.assertFalse((rebuild / "css" / "qa-overlay.css").exists())
            self.assertFalse((rebuild / "js" / "qa-overlay.js").exists())
            self.assertTrue((rebuild / "js" / "gsap-reveal.js").exists())

            ship = (rebuild / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("qa-overlay", ship)
            self.assertNotIn("qa-outlines-boot", ship)
            self.assertNotIn("data-qa-outlines", ship)
            self.assertIn("<main>polish</main>", ship)

            saved = json.loads((root / "qa" / "ship-promote.json").read_text(encoding="utf-8"))
            self.assertTrue(saved["ok"])
            self.assertEqual(saved["writer"], "finalize_ship.py")
            self.assertEqual(saved["archived"], [])

            # idempotent
            again = finalize_ship.finalize(root)
            self.assertTrue(again.get("already"))
            self.assertEqual((rebuild / "index.html").read_text(encoding="utf-8"), ship)

    def test_legacy_variants_are_promoted_and_archived(self) -> None:
        """A resumed pre-2.34 run: index-polish/semantic/raw still on disk."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rebuild = root / "rebuild"
            rebuild.mkdir()
            (rebuild / "index.html").write_text("<html><body>lock</body></html>", encoding="utf-8")
            (rebuild / "index-raw.html").write_text("<html><body>raw</body></html>", encoding="utf-8")
            (rebuild / "index-semantic.html").write_text("<html><body>sem</body></html>", encoding="utf-8")
            (rebuild / "index-polish.html").write_text(FINAL_POLISH, encoding="utf-8")

            receipt = finalize_ship.finalize(root)

            self.assertFalse((rebuild / "index-polish.html").exists())
            self.assertFalse((rebuild / "index-raw.html").exists())
            self.assertFalse((rebuild / "index-semantic.html").exists())
            self.assertEqual((rebuild / "archive" / "index-raw.html").read_text(encoding="utf-8"), "<html><body>raw</body></html>")
            self.assertIn("index-raw.html", json.loads((root / "qa" / "ship-promote.json").read_text())["archived"])
            ship = (rebuild / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("qa-overlay", ship)
            self.assertIn("polish", ship)
            self.assertIn("archive", (rebuild / ".vercelignore").read_text(encoding="utf-8"))

    def test_missing_ship_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            with self.assertRaises(FileNotFoundError):
                finalize_ship.finalize(root)

    def test_ship_ready_and_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._overlay_ship(root)
            self.assertTrue(finalize_ship.ship_ready(root))
            self.assertFalse(finalize_ship.ship_is_final(root))
            finalize_ship.finalize(root)
            self.assertTrue(finalize_ship.ship_is_final(root))

    def test_overlay_js_keeps_outline_toggle_contract(self) -> None:
        js = (finalize_ship.HERE.parent / "templates" / "qa-overlay.js").read_text(encoding="utf-8")
        self.assertIn("qa-outlines", js)
        self.assertIn("data-qa-outlines", js)


if __name__ == "__main__":
    unittest.main()
