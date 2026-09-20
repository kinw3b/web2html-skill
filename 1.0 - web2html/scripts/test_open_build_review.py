#!/usr/bin/env python3
"""Build-review opener gates the 2.4 TAGS checkpoint."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

from author_21_gate import install_passing_artifacts as install_21
from section_22_gate import install_passing_artifacts as install_22

_SHIP = """<!doctype html><html><head><title>Test</title></head><body>
<header><nav aria-label="Primary"><a href="#main">Home</a></nav></header>
<main id="main">
<section class="hero"><h1>Hero</h1></section>
</main>
</body></html>
"""


def _run(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPTS / "open-build-review.py"), str(root), "--no-open", *extra],
        capture_output=True,
        text=True,
    )


class OpenBuildReviewTest(unittest.TestCase):
    def test_refuses_before_section_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild" / "js").mkdir(parents=True)
            (root / "rebuild" / "index.html").write_text(_SHIP, encoding="utf-8")
            (root / "rebuild" / "js" / "qa-overlay.js").write_text("/* overlay */\n", encoding="utf-8")
            proc = _run(root)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("2.3", proc.stderr)
            self.assertNotIn("qa-outlines=tags", proc.stdout)

    def test_checkpoint_opens_tags_after_22(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_21(root)
            (root / "rebuild" / "js").mkdir(parents=True, exist_ok=True)
            (root / "rebuild" / "js" / "qa-overlay.js").write_text("/* overlay */\n", encoding="utf-8")
            (root / "rebuild" / "index.html").write_text(_SHIP, encoding="utf-8")
            install_22(root)  # VALIDATE fingerprints the final ship; overlay injection is ignored
            proc = _run(root, "--stage", "2.4")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("2.4 TAGS checkpoint", proc.stdout)
            self.assertIn("qa-outlines=tags", proc.stdout)
            self.assertTrue((root / "qa" / "build-checkpoint-opened.json").is_file())

    def test_missing_overlay_injects_into_rebuild_not_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            templates = Path(tmp)
            root = templates / "kp-demo"
            install_21(root)
            (root / "rebuild").mkdir(parents=True, exist_ok=True)
            (root / "rebuild" / "index.html").write_text(_SHIP, encoding="utf-8")
            install_22(root)  # VALIDATE fingerprints the final ship; overlay injection is ignored
            proc = _run(root, "--stage", "2.4")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((root / "rebuild" / "js" / "qa-overlay.js").is_file())
            self.assertTrue((root / "rebuild" / "css" / "qa-overlay.css").is_file())
            self.assertFalse((templates / "css").exists())
            self.assertFalse((templates / "js").exists())

    def test_unknown_stage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(_SHIP, encoding="utf-8")
            proc = _run(root, "--stage", "2.2.b")
            self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
