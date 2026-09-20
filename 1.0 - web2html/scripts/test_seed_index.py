#!/usr/bin/env python3
"""2.13.0 — 2.3 index.html is a 2.2 copy, never a second overwrite."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import seed_index as seed  # noqa: E402


class SeedIndexTest(unittest.TestCase):
    def test_copies_semantic_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index-semantic.html").write_text(
                "<html>first-pass</html>", encoding="utf-8"
            )
            dest = seed.seed(root)
            self.assertEqual(dest, root / "rebuild" / "index.html")
            self.assertEqual(dest.read_text(encoding="utf-8"), "<html>first-pass</html>")
            (root / "rebuild" / "index-semantic.html").write_text(
                "<html>mutated-pass</html>", encoding="utf-8"
            )
            again = seed.seed(root)
            self.assertEqual(again.read_text(encoding="utf-8"), "<html>first-pass</html>")

    def test_cli_seeds_from_semantic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index-semantic.html").write_text(
                "<html>first-pass</html>", encoding="utf-8"
            )
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "seed_index.py"), str(root)]
            )
            self.assertEqual(rc, 0)
            self.assertEqual(
                (root / "rebuild" / "index.html").read_text(encoding="utf-8"),
                "<html>first-pass</html>",
            )

    def test_missing_semantic_fails_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "seed_index.py"), tmp]
            )
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
