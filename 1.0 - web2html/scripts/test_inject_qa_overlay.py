#!/usr/bin/env python3
"""QA overlay must land in rebuild/css + rebuild/js, never beside the project."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent

SHIP = """<!doctype html><html><head><title>Test</title></head><body>
<main id="main"><section><h1>Hero</h1></section></main>
</body></html>
"""


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPTS / "inject-qa-overlay.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class InjectQaOverlayTest(unittest.TestCase):
    def test_project_root_writes_rebuild_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            templates = Path(tmp)
            project = templates / "kp-demo"
            (project / "rebuild").mkdir(parents=True)
            (project / "rebuild" / "index.html").write_text(SHIP, encoding="utf-8")
            proc = _run(templates, str(project))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((project / "rebuild" / "css" / "qa-overlay.css").is_file())
            self.assertTrue((project / "rebuild" / "js" / "qa-overlay.js").is_file())
            self.assertFalse((templates / "css").exists())
            self.assertFalse((templates / "js").exists())
            self.assertFalse((project / "css").exists())
            html = (project / "rebuild" / "index.html").read_text(encoding="utf-8")
            self.assertIn("css/qa-overlay.css", html)
            self.assertIn('data-qa-outlines="tags"', html)

    def test_rebuild_index_same(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(SHIP, encoding="utf-8")
            proc = _run(root, "rebuild/index.html")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((root / "rebuild" / "css" / "qa-overlay.css").is_file())
            self.assertFalse((root / "css").exists())

    def test_dot_outside_project_does_not_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            templates = Path(tmp)
            (templates / "kp-demo" / "rebuild").mkdir(parents=True)
            (templates / "kp-demo" / "rebuild" / "index.html").write_text(
                SHIP, encoding="utf-8"
            )
            proc = _run(templates, ".")
            self.assertEqual(proc.returncode, 2)
            self.assertIn("Pitfall #197", proc.stderr)
            self.assertFalse((templates / "css").exists())
            self.assertFalse((templates / "js").exists())

    def test_assets_dir_outside_rebuild_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(SHIP, encoding="utf-8")
            proc = _run(root, "rebuild/index.html", "--assets-dir", str(root))
            self.assertEqual(proc.returncode, 2)
            self.assertFalse((root / "css").exists())


if __name__ == "__main__":
    unittest.main()
