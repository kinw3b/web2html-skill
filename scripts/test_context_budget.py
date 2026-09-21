from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import context_budget


def transcript_line(kind: str, usage: dict | None = None) -> str:
    row = {"type": kind, "message": {"role": kind}}
    if usage is not None:
        row["message"]["usage"] = usage
    return json.dumps(row)


class ContextBudgetTests(unittest.TestCase):
    def test_window_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "settings.json"
            self.assertEqual(context_budget.resolve_window({"WEB2HTML_CONTEXT_WINDOW": "123456"}, settings), (123456, "env WEB2HTML_CONTEXT_WINDOW"))
            self.assertEqual(context_budget.resolve_window({}, settings)[0], context_budget.DEFAULT_WINDOW)
            settings.write_text(json.dumps({"model": "claude-fable-5-1[1m]"}))
            self.assertEqual(context_budget.resolve_window({}, settings)[0], context_budget.BIG_WINDOW)
            settings.write_text("not json")
            self.assertEqual(context_budget.resolve_window({}, settings)[0], context_budget.DEFAULT_WINDOW)

    def test_transcript_tail_uses_the_last_assistant_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            sid = "abc-123"
            path = cfg / "projects" / "-Users-x-proj" / f"{sid}.jsonl"
            path.parent.mkdir(parents=True)
            lines = [
                transcript_line("user"),
                transcript_line("assistant", {"input_tokens": 5, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 100}),
                "not json at all",
                transcript_line("assistant", {"input_tokens": 2, "cache_read_input_tokens": 139383, "cache_creation_input_tokens": 24682, "output_tokens": 2148}),
                transcript_line("user"),
                json.dumps({"type": "progress", "usage": "decoy"}),
            ]
            path.write_text("\n".join(lines) + "\n")
            env = {"CLAUDE_CODE_SESSION_ID": sid, "CLAUDE_CONFIG_DIR": str(cfg)}
            self.assertEqual(context_budget.transcript_tokens(env), 2 + 139383 + 24682)
            self.assertIsNone(context_budget.transcript_tokens({"CLAUDE_CODE_SESSION_ID": "missing", "CLAUDE_CONFIG_DIR": str(cfg)}))
            self.assertIsNone(context_budget.transcript_tokens({}))
            report = context_budget.budget(None, env | {"WEB2HTML_CONTEXT_WINDOW": "200000"})
            self.assertEqual(report["source"], "transcript")
            self.assertEqual(report["usedPct"], 82.0)
            self.assertEqual(report["state"], "force")
            report = context_budget.budget(None, env | {"WEB2HTML_CONTEXT_WINDOW": "1000000"})
            self.assertEqual((report["usedPct"], report["state"]), (16.4, "ok"))

    def test_sidecar_accepts_percent_or_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            side = Path(tmp) / "ctx.json"
            side.write_text(json.dumps({"context_window": {"used_percentage": 55}}))
            env = {"WEB2HTML_CONTEXT_SIDECAR": str(side), "WEB2HTML_CONTEXT_WINDOW": "200000", "CLAUDE_CONFIG_DIR": tmp}
            report = context_budget.budget(None, env)
            self.assertEqual((report["source"], report["usedTokens"], report["state"]), ("sidecar", 110000, "armed"))
            side.write_text(json.dumps({"used_tokens": 20000}))
            self.assertEqual(context_budget.budget(None, env)["usedPct"], 10.0)

    def test_estimator_ledger_is_per_owner_and_never_bumps_the_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa").mkdir()
            progress = {"revision": 7, "controller": {"owner": "session-2", "status": "active"}, "steps": {}}
            (root / "qa" / "pipeline-progress.json").write_text(json.dumps(progress))
            env = {"WEB2HTML_CONTEXT_WINDOW": "100000", "CLAUDE_CONFIG_DIR": tmp}
            self.assertEqual(context_budget.budget(root, env)["usedTokens"], context_budget.BASE_TOKENS)
            self.assertEqual(context_budget.add_spend(root, "shoot"), context_budget.SPEND["shoot"])
            self.assertEqual(context_budget.add_spend(root, "reference", nbytes=4000), context_budget.SPEND["shoot"] + 1000)
            data = json.loads((root / "qa" / "pipeline-progress.json").read_text())
            self.assertEqual(data["revision"], 7)
            self.assertEqual(data["budget"]["owner"], "session-2")
            self.assertEqual(data["budget"]["events"], 2)
            report = context_budget.budget(root, env)
            self.assertEqual(report["source"], "estimator")
            self.assertEqual(report["usedTokens"], context_budget.BASE_TOKENS + context_budget.SPEND["shoot"] + 1000)
            # A new owner starts a fresh ledger.
            data["controller"]["owner"] = "session-2b"
            (root / "qa" / "pipeline-progress.json").write_text(json.dumps(data))
            self.assertEqual(context_budget.add_spend(root, "record"), context_budget.SPEND["record"])
            # No run here → nothing to add, nothing raised.
            self.assertIsNone(context_budget.add_spend(root / "nope", "shoot"))

    def test_thresholds_from_env_and_unknown_state(self):
        self.assertEqual(context_budget.thresholds({}), (50, 75))
        self.assertEqual(context_budget.thresholds({"WEB2HTML_RELAY_ARM": "60", "WEB2HTML_RELAY_FORCE": "40"}), (60, 60))
        self.assertEqual(context_budget.thresholds({"WEB2HTML_RELAY_ARM": "junk"}), (50, 75))
        with tempfile.TemporaryDirectory() as tmp:
            report = context_budget.budget(None, {"CLAUDE_CONFIG_DIR": tmp})
            self.assertEqual((report["source"], report["state"], report["usedPct"]), ("none", "unknown", None))
            self.assertIn("unknown", context_budget.one_line(report))


if __name__ == "__main__":
    unittest.main()
