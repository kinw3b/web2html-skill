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

    def test_stale_check_exits_3_so_workers_stop_instead_of_looping(self):
        doc = wave.prepare(self.root, "r1", "2.3")
        hero = doc["tasks"][0]
        path = self.root / hero["findings"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "match", "768": "match", "390": "match"},
            seen="hero headline, CTA pair, and photo frame match the clip at every width with no drift", misses=[], patch="")))
        argv = ["check", str(self.root), "--phase", "2.3", "--run-id", "r1", "--agent", "band-hero"]
        self.assertEqual(wave.main(argv), 0)
        (self.root / "rebuild" / "css" / "tokens.css").write_text(":root{--x:2}")
        self.assertEqual(wave.main(argv), 3)
        self.assertIn("STOP RULES", hero["spec"])
        self.assertIn("never Read that file whole", hero["spec"])

    def test_new_wave_supersedes_an_abandoned_waves_leases(self):
        wave.prepare(self.root, "r1", "2.3")
        (self.root / "rebuild" / "css" / "tokens.css").write_text(":root{--x:3}")
        doc = wave.prepare(self.root, "r2", "2.3")
        self.assertEqual(len(agent_loop.active_reviewer_leases(self.root)), 2)
        self.assertEqual(doc["runId"], "r2")

    def test_prepare_refuses_an_open_band_that_was_not_reshot(self):
        wave._open_bands = self._open_bands
        import section_22_gate as gate
        import paper_23_validate as validate

        root = self.root / "proj"
        root.mkdir()
        gate.install_passing_artifacts(root)
        receipt = gate.validate_receipt_path(root, "hero")
        payload = json.loads(receipt.read_text())
        payload["status"] = "open"
        receipt.write_text(json.dumps(payload))
        with self.assertRaises(FileNotFoundError) as ctx:
            wave.prepare(root, "r1", "2.3")
        self.assertIn("--shoot-open", str(ctx.exception))
        self.assertTrue(validate.round_recorded(validate.last_round(payload)))

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
        (self.root / "rebuild" / "index.html").unlink()
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


class CompareWaveTests(unittest.TestCase):
    """/compare rides wave.py: one read-only task per band in the side-by-side report."""

    REPORT = {
        "generatedFrom": "web2html/section-23-side-by-side",
        "ok": True,
        "widths": [1600, 390],
        "stops": [
            {"id": "hero", "nn": "01", "width": 1600, "side": "qa/side-by-side/1600/01-hero-1600-side.png", "diffPct": 22.6},
            {"id": "hero", "nn": "01", "width": 390, "side": "qa/side-by-side/390/01-hero-390-side.png", "diffPct": 34.7},
            {"id": "pricing", "nn": "06", "width": 1600, "side": "qa/side-by-side/1600/06-pricing-1600-side.png", "diffPct": 1.2},
            {"id": "pricing", "nn": "06", "width": 390, "side": "qa/side-by-side/390/06-pricing-390-side.png", "diffPct": 2.4},
        ],
    }

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "rebuild").mkdir(parents=True)
        (self.root / "rebuild" / "index.html").write_text("<main><section id='hero'></section><section id='pricing'></section></main>")
        pairs = self.root / "qa" / "side-by-side"
        pairs.mkdir(parents=True)
        (pairs / "report.json").write_text(json.dumps(self.REPORT))

    def tearDown(self):
        self._tmp.cleanup()

    def test_prepare_plans_one_task_per_report_band_with_pair_paths_in_the_spec(self):
        doc = wave.prepare(self.root, "c1", "compare")
        self.assertEqual([t["id"] for t in doc["tasks"]], ["band-hero", "band-pricing"])
        self.assertEqual(doc["maxWorkers"], 4)
        spec = doc["tasks"][0]["spec"]
        for needle in ("qa/side-by-side/1600/01-hero-1600-side.png",
                       "qa/side-by-side/390/01-hero-390-side.png",
                       "Read-only", '"1600":"match|miss"', '"390":"match|miss"',
                       "--agent band-hero", "diffPct"):
            self.assertIn(needle, spec)
        # The pricing spec must not list hero's pairs.
        self.assertNotIn("01-hero", doc["tasks"][1]["spec"])

    def test_prepare_refuses_without_a_shot_report(self):
        (self.root / "qa" / "side-by-side" / "report.json").unlink()
        with self.assertRaises(FileNotFoundError) as ctx:
            wave.prepare(self.root, "c1", "compare")
        self.assertIn("paper_23_side_by_side.py", str(ctx.exception))

    def test_orca_start_launches_read_only_band_workers(self):
        saved = wave._probe
        wave._probe = lambda root: ORCA_PROBE
        try:
            doc = wave.prepare(self.root, "c1", "compare")
            run = fake_orca({
                "run-create": [(0, {"result": {"run": {"id": "run_c"}}})],
                "worker-start": [(0, {"result": {"dispatch": {"id": "d_hero"}}}), (0, {"result": {"dispatch": {"id": "d_pricing"}}})],
            })
            doc = wave.start(self.root, "c1", "compare", "auto", run)
            self.assertEqual(doc["adapter"], "orca")
            self.assertEqual([t["status"] for t in doc["tasks"]], ["running", "running"])
            starts = [c for c in run.calls if c[2] == "worker-start"]
            self.assertEqual(starts[0][starts[0].index("--agent") + 1], "claude")
        finally:
            wave._probe = saved

    def test_finding_validation_needs_a_scoped_patch_and_confirm_apply_caps_rounds(self):
        doc = wave.prepare(self.root, "c1", "compare")
        hero = doc["tasks"][0]
        path = self.root / hero["findings"]
        path.parent.mkdir(parents=True, exist_ok=True)
        # misses without a patch → invalid; an unscoped patch → invalid.
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "miss", "390": "match"},
            seen="hero headline wraps to three lines at 390 while the source crop wraps to two",
            misses=[{"width": 1600, "what": "columns stacked", "fix": "2-col grid"}], patch="")))
        errors = wave.check_one(self.root, "c1", "compare", "band-hero")
        self.assertTrue(any("scoped patch" in e for e in errors))
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "miss", "390": "match"},
            seen="hero headline wraps to three lines at 390 while the source crop wraps to two",
            misses=[{"width": 1600, "what": "columns stacked", "fix": "2-col grid"}],
            patch="body .grid { grid-template-columns: repeat(2, 1fr); }")))
        errors = wave.check_one(self.root, "c1", "compare", "band-hero")
        self.assertTrue(any("scoped to #<band>" in e for e in errors))
        # A properly scoped finding passes; apply prints patch + re-shoot + the 2-round cap.
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "miss", "390": "match"},
            seen="hero headline wraps to three lines at 390 while the source crop wraps to two",
            misses=[{"width": 1600, "what": "columns stacked", "fix": "#hero .grid: repeat(2, 1fr)"}],
            patch="#hero .grid { grid-template-columns: repeat(2, 1fr); }",
            nav=[],
            findings=[{"key": "1600", "severity": "medium", "source": self.REPORT["stops"][0]["side"],
                       "evidence": "stacked", "suggestion": "2-col"}])))
        (self.root / doc["tasks"][1]["findings"]).write_text(json.dumps(finding_for(
            doc, doc["tasks"][1], band="pricing", verdict={"1600": "match", "390": "match"},
            seen="pricing cards, gaps, and radii match the source crop at both widths", misses=[], patch="", nav=[])))
        self.assertTrue(wave.ready(self.root, "c1", "compare")[0])
        out = wave.apply(self.root, "c1", "compare")
        self.assertEqual([a["band"] for a in out["actions"]], ["hero", "pricing"])
        self.assertIn("#hero .grid", out["actions"][0]["patch"])
        self.assertIn("--id hero", out["actions"][0]["note"])
        self.assertIn("2 rounds", out["actions"][0]["note"])
        self.assertEqual(out["actions"][1]["patch"], "")
        self.assertEqual(agent_loop.active_reviewer_leases(self.root), [])

    def test_a_patch_to_the_ship_stales_compare_findings(self):
        doc = wave.prepare(self.root, "c1", "compare")
        hero = doc["tasks"][0]
        path = self.root / hero["findings"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "match", "390": "match"},
            seen="hero headline, CTA pair, and photo frame match the crop at both widths", misses=[], patch="", nav=[])))
        self.assertEqual(wave.check_one(self.root, "c1", "compare", "band-hero"), [])
        (self.root / "rebuild" / "index.html").write_text("<main><section id='hero'>patched</section></main>")
        errors = wave.check_one(self.root, "c1", "compare", "band-hero")
        self.assertTrue(any("stale" in e for e in errors))
        argv = ["check", str(self.root), "--phase", "compare", "--run-id", "c1", "--agent", "band-hero"]
        self.assertEqual(wave.main(argv), 3)

    def test_nav_inventory_is_mandatory_and_a_missing_item_forces_a_miss(self):
        doc = wave.prepare(self.root, "c1", "compare")
        hero = doc["tasks"][0]
        path = self.root / hero["findings"]
        path.parent.mkdir(parents=True, exist_ok=True)
        # No nav list at all → invalid (Pitfall #247).
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "match", "390": "match"},
            seen="hero headline, CTA pair, and photo frame match the crop at both widths", misses=[], patch="")))
        errors = wave.check_one(self.root, "c1", "compare", "band-hero")
        self.assertTrue(any("nav must be a list" in e for e in errors))
        # A missing dropdown with a match verdict → invalid.
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "match", "390": "match"},
            seen="hero headline, CTA pair, and photo frame match the crop at both widths", misses=[], patch="",
            nav=[{"trigger": "Products", "kind": "dropdown", "state": "missing",
                  "evidence": "source paints a chevron + panel; rebuild paints a flat link"}])))
        errors = wave.check_one(self.root, "c1", "compare", "band-hero")
        self.assertTrue(any("Products" in e and "verdict must be miss" in e for e in errors))
        # A missing dropdown with a miss verdict but no patch → invalid.
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "miss", "390": "match"},
            seen="source paints a Products chevron with an open panel; rebuild paints a flat link",
            misses=[], patch="",
            nav=[{"trigger": "Products", "kind": "dropdown", "state": "missing",
                  "evidence": "source paints a chevron + panel; rebuild paints a flat link"}])))
        errors = wave.check_one(self.root, "c1", "compare", "band-hero")
        self.assertTrue(any("Products" in e and "patch proposal" in e for e in errors))
        # Miss verdict + scoped patch → valid; apply prints the nav-dropdown wiring note.
        path.write_text(json.dumps(finding_for(
            doc, hero, band="hero", verdict={"1600": "miss", "390": "match"},
            seen="source paints a Products chevron with an open panel; rebuild paints a flat link",
            misses=[{"width": 1600, "what": "Products dropdown missing",
                     "fix": "#hero header: stamp data-nav-dropdown-trigger + panel"}],
            patch="#hero header [data-nav-dropdown-trigger] Products: insert [data-nav-dropdown-panel] from scrape submenu",
            nav=[{"trigger": "Products", "kind": "dropdown", "state": "missing",
                  "evidence": "source paints a chevron + panel; rebuild paints a flat link"}])))
        self.assertEqual(wave.check_one(self.root, "c1", "compare", "band-hero"), [])
        (self.root / doc["tasks"][1]["findings"]).write_text(json.dumps(finding_for(
            doc, doc["tasks"][1], band="pricing", verdict={"1600": "match", "390": "match"},
            seen="pricing cards, gaps, and radii match the source crop at both widths", misses=[], patch="", nav=[])))
        out = wave.apply(self.root, "c1", "compare")
        nav_notes = [a for a in out["actions"] if a.get("nav")]
        self.assertTrue(nav_notes)
        self.assertTrue(any("nav-dropdown.md" in a["note"] and "Pitfall #241" in a["note"] for a in nav_notes))

    def test_interior_page_compare_wave_reads_the_per_slug_report(self):
        interior = {
            "generatedFrom": "web2html/section-23-side-by-side",
            "ok": True,
            "page": "about",
            "widths": [1600, 390],
            "rebuild": "astro/dist/about/index.html",
            "stops": [
                {"id": "about-hero", "nn": "01", "width": 1600,
                 "side": "qa/side-by-side/about/1600/01-about-hero-1600-side.png"},
                {"id": "about-hero", "nn": "01", "width": 390,
                 "side": "qa/side-by-side/about/390/01-about-hero-390-side.png"},
            ],
        }
        pairs = self.root / "qa" / "side-by-side" / "about"
        pairs.mkdir(parents=True)
        (pairs / "report.json").write_text(json.dumps(interior))
        dist = self.root / "astro" / "dist" / "about"
        dist.mkdir(parents=True)
        (dist / "index.html").write_text("<main><section id='about-hero'></section></main>")
        (self.root / "astro" / "src").mkdir(parents=True)
        doc = wave.prepare(self.root, "c1", "compare", page="about")
        self.assertEqual(doc["page"], "about")
        self.assertEqual([t["id"] for t in doc["tasks"]], ["about--band-about-hero"])
        self.assertEqual(doc["tasks"][0]["page"], "about")
        spec = doc["tasks"][0]["spec"]
        self.assertIn("qa/side-by-side/about/1600/01-about-hero-1600-side.png", spec)
        self.assertIn("PHASE-5 interior pass", spec)
        self.assertIn("--page about", spec)
        self.assertIn("astro/dist/about", " ".join(doc["inputs"]))
        # Without the built page the wave refuses.
        (dist / "index.html").unlink()
        dist.rmdir()
        with self.assertRaises(FileNotFoundError) as ctx:
            wave.prepare(self.root, "c2", "compare", page="about")
        self.assertIn("build-astro-dist.py", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
