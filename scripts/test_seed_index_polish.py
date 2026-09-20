#!/usr/bin/env python3
"""2.10.10 — 3.x polish file is a 2.4 copy, never a second overwrite."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import seed_index_polish as seed  # noqa: E402


class SeedIndexPolishTest(unittest.TestCase):
    def test_copies_index_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html>lock</html>", encoding="utf-8")
            dest = seed.seed(root)
            self.assertEqual(dest, root / "rebuild" / "index-polish.html")
            self.assertEqual(dest.read_text(encoding="utf-8"), "<html>lock</html>")
            (root / "rebuild" / "index.html").write_text("<html>mutated</html>", encoding="utf-8")
            again = seed.seed(root)
            self.assertEqual(again.read_text(encoding="utf-8"), "<html>lock</html>")

    def test_cli_seeds_and_live_html_prefers_polish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html>lock</html>", encoding="utf-8")
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "seed_index_polish.py"), str(root)]
            )
            self.assertEqual(rc, 0)
            self.assertEqual(seed.live_html(root).name, "index-polish.html")

    def test_missing_index_fails_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "seed_index_polish.py"), tmp]
            )
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
