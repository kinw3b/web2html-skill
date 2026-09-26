from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import orca_workspace


def _fake_orca_bin(directory: Path) -> Path:
    bin_dir = directory / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    cli = bin_dir / "orca"
    cli.write_text("#!/bin/sh\nexit 0\n")
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
    return bin_dir


def _reachable_runner(calls: list):
    def run(argv):
        calls.append(argv)
        if argv[1:3] == ["status", "--json"] or argv[1:2] == ["status"]:
            return 0, json.dumps({"result": {"runtime": {"reachable": True, "appVersion": "test"}}})
        if argv[1:3] == ["repo", "add"]:
            return 0, json.dumps({"result": {"repo": {"id": "repo-42"}}})
        if argv[1:3] == ["worktree", "current"]:
            return 0, json.dumps({"result": {}})
        if argv[1:3] == ["orchestration", "run-current"]:
            return 1, ""
        return 0, "{}"

    return run


class OrcaWorkspaceTests(unittest.TestCase):
    def _env(self, tmp: Path, orca: bool) -> dict:
        env = {"WEB2HTML_HOME": str(tmp / "web2html-home")}
        if orca:
            env["PATH"] = str(_fake_orca_bin(tmp))
        else:
            env["PATH"] = str(tmp / "empty-bin")
        return env

    def test_ensure_without_orca_creates_a_plain_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = self._env(root, orca=False)
            record = orca_workspace.ensure("demo run", base=root / "ws", env=env, run=_reachable_runner([]))
            self.assertFalse(record["orca"])
            self.assertIsNone(record["repoId"])
            self.assertTrue((root / "ws" / "demo-run" / "qa" / "orca-workspace.json").is_file())

    def test_ensure_with_orca_registers_one_folder_context_and_reuses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = self._env(root, orca=True)
            calls: list = []
            first = orca_workspace.ensure("demo", base=root / "ws", env=env, run=_reachable_runner(calls))
            self.assertTrue(first["orca"])
            self.assertEqual(first["repoId"], "repo-42")
            adds = [c for c in calls if c[1:3] == ["repo", "add"]]
            self.assertEqual(len(adds), 1)

            calls.clear()
            second = orca_workspace.ensure("demo", base=root / "ws", env=env, run=_reachable_runner(calls))
            self.assertEqual(second["path"], first["path"])
            self.assertEqual([c for c in calls if c[1:3] == ["repo", "add"]], [])
            self.assertTrue((root / "ws" / "demo").is_dir())
            # the index remembers the single primary workspace for continued sessions
            self.assertEqual(orca_workspace.load_index(env)["demo"]["path"], first["path"])

    def test_show_prints_the_recorded_root_and_fails_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = self._env(root, orca=False)
            record = orca_workspace.ensure("demo", base=root / "ws", env=env, run=_reachable_runner([]))
            self.assertEqual(orca_workspace.show("demo", env=env), 0)
            self.assertEqual(orca_workspace.show("nope", env=env), 2)
            self.assertTrue(Path(record["path"]).is_dir())

    def test_orca_registration_failure_still_leaves_a_plain_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = self._env(root, orca=True)

            def run(argv):
                if argv[1:3] == ["repo", "add"]:
                    return 1, "boom"
                return _reachable_runner([])(argv)

            record = orca_workspace.ensure("demo", base=root / "ws", env=env, run=run)
            self.assertTrue(record["orca"])
            self.assertIsNone(record["repoId"])
            self.assertTrue((root / "ws" / "demo").is_dir())


if __name__ == "__main__":
    unittest.main()
