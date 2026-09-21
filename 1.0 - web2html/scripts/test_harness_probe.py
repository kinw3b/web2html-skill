from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import harness_probe


def fake_runner(responses: dict[str, tuple[int, object]]):
    """Key on the first three argv words after the executable, e.g. 'status', 'terminal show'."""
    calls: list[list[str]] = []

    def run(argv):
        calls.append(argv)
        key = " ".join(argv[1:3]) if argv[1] in {"terminal", "worktree", "orchestration"} else argv[1]
        code, body = responses.get(key, (1, {}))
        return code, json.dumps(body) if not isinstance(body, str) else body

    run.calls = calls  # type: ignore[attr-defined]
    return run


REACHABLE = {"result": {"runtime": {"reachable": True, "appVersion": "1.4.206", "capabilities": ["orchestration.federation.v1"]}}}
UNREACHABLE = {"result": {"runtime": {"reachable": False}}}
TERM_CLAUDE = {"result": {"terminal": {"agentIdentity": "claude", "worktreeId": "repo::/wt"}}}
TERM_CODEX = {"result": {"terminal": {"agentIdentity": "codex", "worktreeId": "repo::/wt"}}}
NO_RUN = {"result": {"run": None}}


class HarnessProbeTests(unittest.TestCase):
    def test_detects_claude_code_and_ignores_orca_exported_opencode_vars(self):
        self.assertEqual(harness_probe.detect_harness({"CLAUDECODE": "1", "OPENCODE_CONFIG_DIR": "/x", "ORCA_OPENCODE_CONFIG_DIR": "/x"}), "claude-code")
        self.assertEqual(harness_probe.detect_harness({"OPENCODE_CONFIG_DIR": "/x", "ORCA_OPENCODE_CONFIG_DIR": "/x"}), "generic")
        self.assertEqual(harness_probe.detect_harness({"OPENCODE_CONFIG_DIR": "/x"}), "opencode")
        self.assertEqual(harness_probe.detect_harness({"CODEX_SANDBOX": "1"}), "codex")
        self.assertEqual(harness_probe.detect_harness({"HERMES_HOME": "/h"}), "hermes")
        self.assertEqual(harness_probe.detect_harness({}), "generic")

    def test_orca_cli_resolution_prefers_the_exported_command_and_never_bare_orca_on_linux(self):
        self.assertEqual(harness_probe.resolve_orca_cli({"ORCA_CLI_COMMAND": "/usr/local/bin/orca"}, "Darwin"), "/usr/local/bin/orca")
        # Outside an Orca terminal on Linux, bare `orca` is the GNOME screen reader.
        self.assertNotEqual(harness_probe.resolve_orca_cli({}, "Linux"), "orca")

    def test_absent_orca_degrades_without_error(self):
        env = {"CLAUDECODE": "1", "PATH": ""}
        run = fake_runner({})
        report = harness_probe.probe(env, run, None)
        self.assertFalse(report["orca"]["present"])
        self.assertEqual(report["adapters"], {"waves": "subagent", "relay": "print-prompt"})
        report = harness_probe.probe({"PATH": ""}, run, None)
        self.assertEqual(report["harness"], "generic")
        self.assertEqual(report["adapters"], {"waves": "serial", "relay": "print-prompt"})
        self.assertEqual(run.calls, [])

    def test_unreachable_runtime_is_present_but_off(self):
        env = {"CLAUDECODE": "1", "ORCA_CLI_COMMAND": "/bin/orca", "ORCA_TERMINAL_HANDLE": "term_1", "ORCA_WORKTREE_ID": "repo::/wt"}
        report = harness_probe.probe(env, fake_runner({"status": (0, UNREACHABLE)}), None)
        self.assertTrue(report["orca"]["present"])
        self.assertFalse(report["orca"]["reachable"])
        self.assertEqual(report["adapters"], {"waves": "subagent", "relay": "print-prompt"})

    def test_reachable_orca_uses_its_own_agent_identity_for_the_same_source_rule(self):
        env = {"CLAUDECODE": "1", "ORCA_CLI_COMMAND": "/bin/orca", "ORCA_TERMINAL_HANDLE": "term_1", "ORCA_WORKTREE_ID": "repo::/wt"}
        run = fake_runner({"status": (0, REACHABLE), "terminal show": (0, TERM_CODEX), "orchestration run-current": (0, NO_RUN)})
        report = harness_probe.probe(env, run, None)
        # Orca knows what launched this terminal; an inherited CLAUDECODE var does not override it.
        self.assertEqual(report["agent"], "codex")
        self.assertEqual(report["agentCommand"], "codex")
        self.assertIn("agentIdentity", report["agentSource"])
        self.assertEqual(report["adapters"], {"waves": "orca", "relay": "orca-terminal"})
        self.assertEqual(report["orca"]["version"], "1.4.206")
        self.assertIsNone(report["orca"]["run"])

    def test_unknown_agent_turns_orca_rungs_off(self):
        env = {"HERMES_HOME": "/h", "ORCA_CLI_COMMAND": "/bin/orca", "ORCA_TERMINAL_HANDLE": "term_1", "ORCA_WORKTREE_ID": "repo::/wt"}
        run = fake_runner({"status": (0, REACHABLE), "terminal show": (0, {"result": {"terminal": {}}}), "orchestration run-current": (0, NO_RUN)})
        report = harness_probe.probe(env, run, None)
        self.assertTrue(report["orca"]["reachable"])
        self.assertIsNone(report["agent"])
        self.assertEqual(report["adapters"], {"waves": "serial", "relay": "print-prompt"})
        # The operator may name the agent explicitly.
        report = harness_probe.probe(env | {"WEB2HTML_ORCA_AGENT": "codex"}, run, None)
        self.assertEqual(report["agent"], "codex")
        self.assertEqual(report["adapters"]["waves"], "orca")

    def test_relay_command_override_and_claude_default(self):
        env = {"CLAUDECODE": "1", "ORCA_CLI_COMMAND": "/bin/orca", "ORCA_TERMINAL_HANDLE": "term_1", "ORCA_WORKTREE_ID": "repo::/wt"}
        run = fake_runner({"status": (0, REACHABLE), "terminal show": (0, TERM_CLAUDE), "orchestration run-current": (0, NO_RUN)})
        self.assertEqual(harness_probe.probe(env, run, None)["agentCommand"], "claude")
        self.assertEqual(harness_probe.probe(env | {"WEB2HTML_RELAY_COMMAND": "claude --model opus"}, run, None)["agentCommand"], "claude --model opus")

    def test_report_round_trips_through_qa(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(harness_probe.write_report(root, {"x": 1}))  # no qa/ yet
            (root / "qa").mkdir()
            report = harness_probe.probe({"PATH": ""}, fake_runner({}), root)
            dest = harness_probe.write_report(root, report)
            self.assertEqual(dest, (root / "qa" / "harness-probe.json").resolve())
            self.assertEqual(harness_probe.load_report(root)["adapters"]["waves"], "serial")
            self.assertIn("orca absent", harness_probe.brief(report))

    def test_main_never_fails(self):
        old = dict(os.environ)
        try:
            os.environ.clear()
            os.environ["PATH"] = ""
            self.assertEqual(harness_probe.main(["--brief"]), 0)
        finally:
            os.environ.clear()
            os.environ.update(old)


if __name__ == "__main__":
    unittest.main()
