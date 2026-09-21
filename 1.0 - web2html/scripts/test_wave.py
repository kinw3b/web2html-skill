from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import agent_loop
import wave


def fake_orca(script: dict[str, list[tuple[int, object]]]):
    """Responses keyed by the orchestration verb; each verb pops its next scripted reply."""
    calls: list[list[str]] = []

    def run(argv, timeout_s=0):
        calls.append(argv)
        verb = argv[2] if len(argv) > 2 else argv[1]
        queue = script.get(verb) or [(0, {})]
        code, body = queue.pop(0) if len(queue) > 1 else queue[0]
        return code, json.dumps(body)

    run.calls = calls  # type: ignore[attr-defined]
    return run


ORCA_PROBE = {
    "harness": "claude-code", "agent": "claude",
    "orca": {"cli": "/bin/orca", "reachable": True, "worktree": "repo::/wt"},
    "adapters": {"waves": "orca", "relay": "orca-terminal"},
}
SERIAL_PROBE = {"harness": "generic", "agent": None, "orca": {}, "adapters": {"waves": "serial", "relay": "print-prompt"}}


def finding_for(wave_doc: dict, task: dict, **extra) -> dict:
    row = {
        "generatedFrom": agent_loop.FINDINGS_GENERATED_FROM,
        "phase": wave_doc["phase"],
        "agent": task["id"],
        "inputSha256": wave_doc["inputSha256"],
        "findings": [],
    }
    row.update(extra)
    return row


class WaveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "qa").mkdir()
        (self.root / "rebuild" / "css").mkdir(parents=True)
        (self.root / "rebuild" / "index.html").write_text("<main><section id='hero'></section><footer id='footer'></footer></main>")
        (self.root / "rebuild" / "css" / "tokens.css").write_text(":root{}")
        self._open_bands = wave._open_bands
        self._probe = wave._probe
        wave._open_bands = lambda root: [{"id": "hero", "state": "open", "rounds": 0}, {"id": "footer", "state": "open", "rounds": 1}]

    def tearDown(self):
        wave._open_bands = self._open_bands
        wave._probe = self._probe
        self._tmp.cleanup()

    def test_prepare_plans_one_read_only_task_per_open_band_with_a_lease(self):
        doc = wave.prepare(self.root, "r1", "2.3")
        self.assertEqual([t["id"] for t in doc["tasks"]], ["band-hero", "band-footer"])
        self.assertEqual(doc["maxWorkers"], 4)
        self.assertEqual(len(agent_loop.active_reviewer_leases(self.root)), 2)
        spec = doc["tasks"][0]["spec"]
        for needle in ("Read-only", "verdict", "inputSha256", "wave.py", "check", "--agent band-hero", "worker_done"):
            self.assertIn(needle, spec)
        self.assertTrue((self.root / "qa" / "agent-runs" / "r1" / "2.3" / "wave.json").is_file())
        self.assertTrue(agent_loop.snapshot_path(self.root, "r1", "2.3").is_file())

    def test_orca_adapter_launches_up_to_max_workers_with_the_same_agent_and_never_relaunches(self):
        wave._probe = lambda root: ORCA_PROBE
        wave.prepare(self.root, "r1", "2.3", max_workers=1)
        run = fake_orca({
            "run-create": [(0, {"result": {"run": {"id": "run_1"}}})],
            "worker-start": [(0, {"result": {"task": {"id": "task_1"}, "dispatch": {"id": "disp_1"}, "handle": "term_a"}})],
        })
        doc = wave.start(self.root, "r1", "2.3", "auto", run)
        self.assertEqual(doc["adapter"], "orca")
        self.assertEqual(doc["orca"]["runId"], "run_1")
        starts = [c for c in run.calls if c[2] == "worker-start"]
        self.assertEqual(len(starts), 1)
        self.assertIn("--agent", starts[0])
        self.assertEqual(starts[0][starts[0].index("--agent") + 1], "claude")
        self.assertEqual(starts[0][starts[0].index("--worktree") + 1], "id:repo::/wt")
        self.assertNotIn("--model", starts[0])
        self.assertEqual([t["status"] for t in doc["tasks"]], ["running", "planned"])
        # The first worker settles; the next launch fails → the rest drop a rung; nothing is relaunched.
        doc["tasks"][0]["status"] = "done"
        wave.save_wave(self.root, doc)
        run2 = fake_orca({"worker-start": [(1, {"failedStage": "terminal_ready", "residualResources": []})]})
        doc = wave.start(self.root, "r1", "2.3", "orca", run2)
        self.assertEqual(doc["tasks"][1]["status"], "dispatch")
        self.assertEqual(doc["tasks"][1]["orca"]["failedStage"], "terminal_ready")
        self.assertEqual(len([c for c in run2.calls if c[2] == "worker-start"]), 1)

    def test_wave_model_is_only_passed_when_the_operator_sets_it(self):
        wave._probe = lambda root: ORCA_PROBE
        wave.prepare(self.root, "r1", "2.3")
        run = fake_orca({"run-create": [(0, {"result": {"id": "run_1"}})],
                         "worker-start": [(0, {"result": {"dispatch_id": "d1"}})]})
        wave.start(self.root, "r1", "2.3", "auto", run, env={"WEB2HTML_WAVE_MODEL": "opus"})
        start = [c for c in run.calls if c[2] == "worker-start"][0]
        self.assertEqual(start[start.index("--model") + 1], "opus")

    def test_wait_validates_worker_done_releases_and_acks_then_apply_prints_record(self):
        wave._probe = lambda root: ORCA_PROBE
        doc = wave.prepare(self.root, "r1", "2.3")
        run = fake_orca({
            "run-create": [(0, {"result": {"id": "run_1"}})],
            "worker-start": [(0, {"result": {"dispatch": {"id": "disp_hero"}}}), (0, {"result": {"dispatch": {"id": "disp_footer"}}})],
        })
        doc = wave.start(self.root, "r1", "2.3", "auto", run)
        self.assertEqual([t["orca"]["dispatchId"] for t in doc["tasks"]], ["disp_hero", "disp_footer"])
        hero = doc["tasks"][0]
        finding = finding_for(doc, hero, band="hero",
                              verdict={"1600": "match", "768": "miss", "390": "match"},
                              seen="cards stack one column at 768 while Paper paints two columns; 1600 and 390 match the clip exactly",
                              misses=[{"width": 768, "what": "cards 1-col", "fix": "#hero .grid: repeat(2, 1fr) at 768"}],
                              patch="#hero .grid { grid-template-columns: repeat(2, 1fr); }",
                              findings=[{"key": "768", "severity": "medium", "source": "side.png", "evidence": "1-col", "suggestion": "2-col"}])
        path = self.root / hero["findings"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(finding))
        delivery = {"result": {"delivery": {"id": "dl_1"}, "messages": [
            {"id": "m1", "type": "worker_done", "payload": {"dispatch_id": "disp_hero", "outcome": "succeeded", "report_path": hero["findings"]}},
        ]}}
        run_wait = fake_orca({"check": [(0, delivery)], "worker-release": [(0, {"result": {"status": "released"}})]})
        summary, code = wave.wait(self.root, "r1", "2.3", 1000, None, run_wait)
        self.assertEqual(code, 0)
        self.assertEqual(summary["settled"], ["band-hero"])
        self.assertTrue(summary["acked"])
        self.assertIn(["--dispatch", "disp_hero"], [c[3:5] for c in run_wait.calls if c[2] == "worker-release"])
        self.assertEqual(len(agent_loop.active_reviewer_leases(self.root)), 1)
        ok, problems = wave.ready(self.root, "r1", "2.3")
        self.assertFalse(ok)
        self.assertIn("band-footer: no finding yet", problems)
        # Empty wait is a checkpoint, not a failure.
        summary, code = wave.wait(self.root, "r1", "2.3", 1000, None, fake_orca({"check": [(0, {"result": {"messages": []}})]}))
        self.assertEqual((code, summary["empty"]), (0, True))
        footer = doc["tasks"][1]
        (self.root / footer["findings"]).write_text(json.dumps(finding_for(
            doc, footer, band="footer", verdict={"1600": "match", "768": "match", "390": "match"},
            seen="footer columns, logo row, and legal line match the 1.2 clip at every width with no drift", misses=[], patch="")))
        self.assertTrue(wave.ready(self.root, "r1", "2.3")[0])
        out = wave.apply(self.root, "r1", "2.3")
        self.assertEqual([a["band"] for a in out["actions"]], ["hero", "footer"])
        record = out["actions"][0]["record"]
        self.assertIn("--verdict 1600=match,768=miss,390=match", record)
        self.assertIn("--patched", record)
        self.assertIn("768|cards 1-col|#hero .grid: repeat(2, 1fr) at 768", record)
        self.assertNotIn("--patched", out["actions"][1]["record"])
        self.assertEqual(agent_loop.active_reviewer_leases(self.root), [])

    def test_stale_or_thin_findings_are_rejected(self):
        doc = wave.prepare(self.root, "r1", "2.3")
        hero = doc["tasks"][0]
        path = self.root / hero["findings"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(finding_for(doc, hero, verdict={"1600": "match"}, seen="too short")))
        errors = wave.check_one(self.root, "r1", "2.3", "band-hero")
        self.assertTrue(any("verdict" in e for e in errors))
        self.assertTrue(any("12 words" in e for e in errors))
        # The controller patched the ship after the snapshot → every finding is stale.
        (self.root / "rebuild" / "css" / "tokens.css").write_text(":root{--x:1}")
        errors = wave.check_one(self.root, "r1", "2.3", "band-hero")
        self.assertTrue(any("stale" in e for e in errors))

    def test_question_blocks_ack_and_returns_4(self):
        wave._probe = lambda root: ORCA_PROBE
        wave.prepare(self.root, "r1", "2.3")
        run = fake_orca({"run-create": [(0, {"result": {"id": "run_1"}})], "worker-start": [(0, {"result": {"dispatch_id": "d1"}}), (0, {"result": {"dispatch_id": "d2"}})]})
        wave.start(self.root, "r1", "2.3", "auto", run)
        delivery = {"result": {"delivery_id": "dl_9", "messages": [{"id": "q1", "type": "question", "subject": "Which clip?", "payload": {"dispatch_id": "d1"}}]}}
        run_wait = fake_orca({"check": [(0, delivery)]})
        summary, code = wave.wait(self.root, "r1", "2.3", 1000, None, run_wait)
        self.assertEqual(code, 4)
        self.assertEqual(summary["needsReply"][0]["task"], "band-hero")
        self.assertNotIn("acked", summary)
        self.assertFalse([c for c in run_wait.calls if "--ack" in c])

    def test_serial_rung_prints_specs_and_apply_promotes_companion_reports(self):
        wave._probe = lambda root: SERIAL_PROBE
        (self.root / "rebuild" / "index-polish.html").write_text("<main></main>")
        doc = wave.prepare(self.root, "r1", "3.2")
        self.assertEqual([t["id"] for t in doc["tasks"]], ["web-design-guidelines", "find-animation-opportunities", "apple-design"])
        doc = wave.start(self.root, "r1", "3.2", "auto", fake_orca({}))
        self.assertEqual(doc["adapter"], "serial")
        self.assertTrue(all(t["status"] == "dispatch" for t in doc["tasks"]))
        # An operator may pick a lower rung, never a higher one than the probe allows.
        self.assertEqual(wave._resolve_adapter("orca", SERIAL_PROBE)[0], "serial")
        self.assertEqual(wave._resolve_adapter("serial", ORCA_PROBE)[0], "serial")
        for task in doc["tasks"]:
            (self.root / task["findings"]).parent.mkdir(parents=True, exist_ok=True)
            (self.root / task["report"]).write_text(f"# {task['skill']}\n\n| row | applied |\n")
            (self.root / task["findings"]).write_text(json.dumps(finding_for(doc, task, report=task["report"])))
        self.assertTrue(wave.ready(self.root, "r1", "3.2")[0])
        out = wave.apply(self.root, "r1", "3.2")
        self.assertEqual(out["promoted"], ["qa/web-design-guidelines.md", "qa/find-animation-opportunities.md", "qa/apple-design.md"])
        self.assertIn("apple-design", (self.root / "qa" / "apple-design.md").read_text())

    def test_prepare_refuses_without_the_step_inputs(self):
        with self.assertRaises(FileNotFoundError):
            wave.prepare(self.root, "r1", "3.2")
        with self.assertRaises(FileNotFoundError):
            wave.prepare(self.root, "r1", "5.2")

    def test_52_plans_one_writer_per_interior_page(self):
        (self.root / "qa" / "phase-4-pages.json").write_text(json.dumps({"pages": [{"slug": "about"}, {"slug": "home"}, {"slug": "pricing"}]}))
        doc = wave.prepare(self.root, "r1", "5.2")
        self.assertEqual([t["slug"] for t in doc["tasks"]], ["about", "pricing"])
        self.assertEqual(doc["maxWorkers"], 2)
        self.assertEqual(doc["tasks"][0]["writes"], ["astro/src/pages/about.astro"])
        self.assertIn("<main>", doc["tasks"][0]["spec"])


if __name__ == "__main__":
    unittest.main()
