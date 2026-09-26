from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("WEB2HTML_NO_PROBE", "1")

import run_report


def write_board(root: Path, steps: dict, sessions: list | None = None) -> None:
    qa = root / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    board = {
        "project": root.name,
        "started": "2026-09-26T09:00:00+00:00",
        "revision": 1,
        "steps": steps,
        "sessions": sessions or [],
    }
    (qa / "pipeline-progress.json").write_text(json.dumps(board))


class RunReportTests(unittest.TestCase):
    def test_build_writes_report_with_timing_agents_and_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            root.mkdir()
            write_board(
                root,
                {
                    "1.1": {
                        "status": "done",
                        "started": "2026-09-26T09:00:00+00:00",
                        "ended": "2026-09-26T09:10:00+00:00",
                        "agent": "opencode",
                        "model": "claude-fable-5.1",
                    },
                    "1.4": {
                        "status": "done",
                        "started": "2026-09-26T10:00:00+00:00",
                        "ended": "2026-09-26T10:20:00+00:00",
                        "agent": "opencode",
                        "model": "claude-fable-5.1",
                    },
                },
                sessions=[
                    {
                        "kind": "start",
                        "owner": "session-1",
                        "at": "1.1",
                        "agent": "opencode",
                        "model": "claude-fable-5.1",
                        "startedAt": "2026-09-26T09:00:00+00:00",
                    }
                ],
            )
            dest = run_report.build(root)
            self.assertEqual(dest, (root / "run-report.md").resolve())
            text = dest.read_text()
            self.assertIn("# Run report — proj", text)
            self.assertIn("claude-fable-5.1", text)
            self.assertIn("opencode", text)
            self.assertIn("10m", text)  # 1.1 duration
            self.assertIn("### 1.4 — Human checkpoint", text)
            self.assertIn("## Notes & additional requests", text)
            # No tool names leak into the portable document.
            self.assertNotIn("pipeline-progress", text)
            self.assertNotIn(".mjs", text)
            self.assertNotIn(".py", text)

    def test_notes_are_logged_and_rendered_under_their_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            root.mkdir()
            write_board(root, {"2.4": {"status": "done"}})
            run_report.add_note(root, "2.4", "Hero CTA should be pill shaped", author="human")
            text = run_report.build(root).read_text()
            self.assertIn("Hero CTA should be pill shaped", text)
            self.assertIn("human", text)
            notes = json.loads((root / "qa" / "run-report-notes.json").read_text())
            self.assertEqual(len(notes), 1)
            self.assertEqual(notes[0]["step"], "2.4")

    def test_paper_comments_merge_across_snapshots_and_mark_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            (root / "qa").mkdir(parents=True)
            log = root / "qa" / "paper-comments-log.jsonl"
            log.write_text(
                json.dumps(
                    {
                        "generatedAt": "2026-09-26T11:00:00Z",
                        "openCount": 2,
                        "threads": [
                            {"id": "c-nav", "status": "open", "text": "Fix the navbar"},
                            {"id": "c-hero", "status": "open", "text": "Hero too tall"},
                        ],
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "generatedAt": "2026-09-26T11:30:00Z",
                        "openCount": 1,
                        "threads": [{"id": "c-hero", "status": "open", "text": "Hero too tall"}],
                    }
                )
                + "\n"
            )
            comments = run_report.collect_paper_comments(root)
            self.assertEqual([c["id"] for c in comments], ["c-nav", "c-hero"])
            self.assertEqual(comments[0]["status"], "resolved")
            self.assertEqual(comments[0]["text"], "Fix the navbar")
            self.assertEqual(comments[1]["status"], "open")
            write_board(root, {"1.4": {"status": "done"}})
            text = run_report.build(root).read_text()
            self.assertIn("[resolved] “Fix the navbar”", text)
            self.assertIn("[open] “Hero too tall”", text)

    def test_report_survives_tidy_keep_list(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pipeline_progress", Path(__file__).with_name("pipeline-progress.py")
        )
        pp = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(pp)
        self.assertIn("run-report.md", pp.KEEP_ROOT)


if __name__ == "__main__":
    unittest.main()
