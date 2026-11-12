#!/usr/bin/env python3
"""astro_build.build() installs only when node_modules is missing or package.json/lockfile changed."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import astro_build


class _Done:
    returncode = 0
    stdout = ""
    stderr = ""


class InstallStampTest(unittest.TestCase):
    def _run_build(self, root: Path) -> list[list[str]]:
        calls: list[list[str]] = []

        def fake_run(cmd, **_kw):
            calls.append(list(cmd))
            if cmd[0] == "npm":
                (root / "astro" / "node_modules").mkdir(exist_ok=True)
            return _Done()

        with mock.patch.object(subprocess, "run", fake_run), \
             mock.patch.object(astro_build, "stamp_components"), \
             mock.patch.object(astro_build, "relativize_dist", return_value=[]), \
             mock.patch.object(astro_build, "inject_review_overlay"):
            result = astro_build.build(root)
        self.assertTrue(result["built"])
        return calls

    def test_install_skipped_when_stamp_matches_and_rerun_on_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            astro = root / "astro"
            astro.mkdir()
            (astro / "package.json").write_text('{"name":"a"}')
            first = self._run_build(root)
            self.assertEqual([c[0] for c in first], ["npm", "npx"])
            second = self._run_build(root)
            self.assertEqual([c[0] for c in second], ["npx"])  # no install
            (astro / "package-lock.json").write_text("{}")
            third = self._run_build(root)
            self.assertEqual([c[0] for c in third], ["npm", "npx"])
            (astro / "package.json").write_text('{"name":"b"}')
            self.assertEqual([c[0] for c in self._run_build(root)], ["npm", "npx"])

    def test_missing_node_modules_reinstalls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "astro").mkdir()
            (root / "astro" / "package.json").write_text("{}")
            self._run_build(root)
            import shutil
            shutil.rmtree(root / "astro" / "node_modules")
            self.assertEqual([c[0] for c in self._run_build(root)], ["npm", "npx"])

    def test_failed_install_leaves_no_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "astro").mkdir()
            (root / "astro" / "package.json").write_text("{}")
            fail = mock.Mock(returncode=1, stdout="", stderr="boom")

            def fake_run(cmd, **_kw):
                (root / "astro" / "node_modules").mkdir(exist_ok=True)
                return fail

            with mock.patch.object(subprocess, "run", fake_run), mock.patch.object(astro_build, "stamp_components"):
                result = astro_build.build(root)
            self.assertFalse(result["built"])
            self.assertEqual(result["errors"], ["npm install failed"])
            self.assertFalse(astro_build.deps_current(root / "astro"))


if __name__ == "__main__":
    unittest.main()
