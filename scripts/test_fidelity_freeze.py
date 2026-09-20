#!/usr/bin/env python3
"""2.10.5 — 3.x must not drop 2.4 font-size / library classes / section ids."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import fidelity_freeze  # noqa: E402


SHIP = """<!doctype html>
<html lang="en"><head><title>Demo</title>
<style>h1{font-size:80px}p{font-size:var(--text-base)}</style>
</head><body>
<header><nav aria-label="Primary"><a class="navbar-link" href="#">Home</a></nav></header>
<main>
<section id="hero" aria-labelledby="hero-title">
  <h1 id="hero-title" class="btn-primary" style="font-size:80px">Welcome</h1>
  <a class="btn-primary" href="#">Start</a>
</section>
<section id="features"><h2>Features</h2><p>Body.</p></section>
</main>
</body></html>
"""


class FidelityFreezeTest(unittest.TestCase):
    def _root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "rebuild" / "css").mkdir(parents=True)
        (root / "design-library").mkdir()
        (root / "qa").mkdir()
        (root / "rebuild" / "index.html").write_text(SHIP, encoding="utf-8")
        (root / "rebuild" / "css" / "tokens.css").write_text(
            ":root{--text-base:16px}h1{font-size:80px}\n", encoding="utf-8"
        )
        (root / "rebuild" / "css" / "hover.css").write_text(
            ".btn-primary:hover{font-size:99px}\n", encoding="utf-8"
        )
        (root / "design-library" / "library.json").write_text(
            json.dumps({"components": [{"name": "btn-primary"}, {"name": "navbar-link"}]}),
            encoding="utf-8",
        )
        return root

    def test_snapshot_then_verify_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "fidelity_freeze.py"), "snapshot", str(root)]
            )
            self.assertEqual(rc, 0)
            data = json.loads((root / "qa" / "fidelity-freeze-24.json").read_text())
            self.assertGreaterEqual(data["library_classes"]["btn-primary"], 2)
            self.assertEqual(data["section_ids"], ["hero", "features"])
            self.assertNotIn("99px", data["font_sizes"])
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "fidelity_freeze.py"), "verify", str(root)]
            )
            self.assertEqual(rc, 0)

    def test_dropping_library_class_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            fidelity_freeze.snapshot(root)
            html = (root / "rebuild" / "index.html").read_text(encoding="utf-8")
            (root / "rebuild" / "index.html").write_text(
                html.replace("btn-primary", "hero-cta"), encoding="utf-8"
            )
            errors = fidelity_freeze.verify(root)
            self.assertTrue(any("btn-primary" in e for e in errors))

    def test_font_size_change_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            fidelity_freeze.snapshot(root)
            (root / "rebuild" / "css" / "tokens.css").write_text(
                ":root{--text-base:16px}h1{font-size:72px}\n", encoding="utf-8"
            )
            errors = fidelity_freeze.verify(root)
            self.assertTrue(any("font-size" in e for e in errors))

    def test_hover_css_font_size_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            fidelity_freeze.snapshot(root)
            (root / "rebuild" / "css" / "hover.css").write_text(
                ".btn-primary:hover{font-size:12px}\n", encoding="utf-8"
            )
            self.assertEqual(fidelity_freeze.verify(root), [])

    def test_mutating_index_after_snapshot_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            fidelity_freeze.snapshot(root)
            html = (root / "rebuild" / "index.html").read_text(encoding="utf-8")
            (root / "rebuild" / "index.html").write_text(
                html + "<!-- 3.x wrote the lock -->", encoding="utf-8"
            )
            errors = fidelity_freeze.verify(root)
            self.assertTrue(any("index.html changed" in e for e in errors))

    def test_polish_file_class_drop_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            fidelity_freeze.snapshot(root)
            (root / "rebuild" / "index-polish.html").write_text(
                SHIP.replace("btn-primary", "hero-cta"), encoding="utf-8"
            )
            errors = fidelity_freeze.verify(root)
            self.assertTrue(any("btn-primary" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
