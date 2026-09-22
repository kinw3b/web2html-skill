"""run_config.py — the three intake questions and the gates that read them (2.24.0)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

import run_config
import section_22_gate as gate

os.environ.setdefault("WEB2HTML_NO_PROBE", "1")

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pipeline_progress", HERE / "pipeline-progress.py")
pipeline_progress = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pipeline_progress)

WEBFLOW_INDEX = """<!DOCTYPE html><html data-wf-page="abc" data-wf-site="def"><body>
<header class="w-nav"><nav>Home</nav></header>
<main><section class="hero w-section"><h1>Hi</h1></section><section>Two</section></main>
<footer>f</footer></body></html>"""

NEXT_INDEX = """<!DOCTYPE html><html><body><div id="__next"></div>
<script id="__NEXT_DATA__" type="application/json">{}</script></body></html>"""


class ClassifySource(unittest.TestCase):
    def test_webflow_export_is_clean_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "export"
            src.mkdir()
            (src / "index.html").write_text(WEBFLOW_INDEX, encoding="utf-8")
            meta = run_config.classify_source(src)
            self.assertEqual(meta["kind"], "clean-html")
            self.assertTrue(meta["webflow"])
            self.assertEqual(meta["indexHtml"], "index.html")

    def test_next_dump_is_framework(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "out"
            (src / "_next").mkdir(parents=True)
            (src / "index.html").write_text(NEXT_INDEX, encoding="utf-8")
            meta = run_config.classify_source(src)
            self.assertEqual(meta["kind"], "framework-dump")
            self.assertTrue(any(m.startswith("dir:_next") for m in meta["markers"]))

    def test_empty_folder_is_framework_dump_with_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = run_config.classify_source(Path(tmp))
            self.assertEqual(meta["kind"], "framework-dump")
            self.assertIn("no readable index.html", meta["reason"])


class Intake(unittest.TestCase):
    def test_defaults_when_nothing_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(run_config.exists(root))
            self.assertEqual(run_config.widths(root), (1600, 768, 390))
            self.assertFalse(run_config.is_fast(root))
            self.assertFalse(run_config.checkpoints_auto(root))
            self.assertTrue(run_config.design_library_enabled(root))

    def test_full_human_records_three_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = run_config.intake(root, source="none", checkpoints="human", speed="full")
            self.assertTrue(run_config.exists(root))
            self.assertEqual(cfg["humanStops"], ["1.4", "2.4", "3.4"])
            self.assertEqual(cfg["widths"], [1600, 768, 390])
            self.assertFalse((root / run_config.DESIGN_LIBRARY_SKIPPED).exists())

    def test_fast_forces_auto_and_drops_tablet_and_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = run_config.intake(root, source="none", checkpoints="human", speed="fast")
            self.assertEqual(cfg["checkpoints"], "auto")
            self.assertEqual(cfg["widths"], [1600, 390])
            self.assertEqual(cfg["humanStops"], ["3.4"])
            self.assertFalse(cfg["designLibrary"])
            self.assertFalse(cfg["designSystem"])
            self.assertFalse(cfg["rawDump"])
            self.assertTrue((root / run_config.DESIGN_LIBRARY_SKIPPED).is_file())
            self.assertTrue((root / run_config.DESIGN_SYSTEM_SKIPPED).is_file())
            self.assertEqual(run_config.widths(root), (1600, 390))

    def test_source_folder_is_copied_and_classified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            src = Path(tmp) / "webflow-export"
            src.mkdir()
            (src / "index.html").write_text(WEBFLOW_INDEX, encoding="utf-8")
            (src / "node_modules").mkdir()
            (src / "node_modules" / "junk.js").write_text("x")
            cfg = run_config.intake(root, source=str(src), checkpoints="human", speed="full")
            self.assertEqual(cfg["source"]["kind"], "clean-html")
            self.assertEqual(cfg["source"]["indexHtml"], "source-html/index.html")
            self.assertTrue((root / "source-html" / "index.html").is_file())
            self.assertFalse((root / "source-html" / "node_modules").exists())
            self.assertTrue(run_config.port_mode(root))

    def test_source_inside_project_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inner = root / "rebuild"
            inner.mkdir()
            with self.assertRaises(ValueError):
                run_config.intake(root, source=str(inner), checkpoints="human", speed="full")

    def test_missing_source_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                run_config.intake(Path(tmp), source="/nope/never/here", checkpoints="human", speed="full")

    def test_cli_intake_and_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = run_config.main(["intake", tmp, "--source", "none", "--checkpoints", "auto", "--speed", "full"])
            self.assertEqual(code, 0)
            self.assertIn("checkpoints=auto", out.getvalue())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(run_config.main(["show", tmp]), 0)
            self.assertIn("human stops: 3.4", out.getvalue())


class ThreeFourNeverAuto(unittest.TestCase):
    def test_auto_accepts_only_14_and_24(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="auto", speed="fast")
            self.assertTrue(run_config.auto_accepts(root, "1.4"))
            self.assertTrue(run_config.auto_accepts(root, "2.4"))
            self.assertFalse(run_config.auto_accepts(root, "3.4"))
            self.assertFalse(run_config.auto_accepts(root, "4.4"))

    def test_human_mode_never_auto_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            for step in ("1.4", "2.4", "3.4"):
                self.assertFalse(run_config.auto_accepts(root, step))

    def test_hand_edited_config_cannot_add_34(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="auto", speed="full")
            path = run_config.config_path(root)
            data = json.loads(path.read_text())
            data["humanStops"] = []
            data["autoAccept"] = ["3.4"]
            path.write_text(json.dumps(data))
            self.assertFalse(run_config.auto_accepts(root, "3.4"))


class FastGates(unittest.TestCase):
    def test_13_and_21_artifact_done_on_fast_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="auto", speed="fast")
            self.assertTrue(pipeline_progress.artifact_done(root, "1.3"))
            self.assertFalse(pipeline_progress.artifact_done(root, "2.1"))  # fonts still required
            (root / "rebuild" / "css").mkdir(parents=True)
            (root / "rebuild" / "css" / "fonts.css").write_text("/* fonts */")
            self.assertTrue(pipeline_progress.artifact_done(root, "2.1"))

    def test_13_not_done_on_full_run_without_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            self.assertFalse(pipeline_progress.artifact_done(root, "1.3"))

    def test_design_system_bound_skipped_on_fast(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="auto", speed="fast")
            self.assertTrue(pipeline_progress.design_system_bound(root))

    def test_section_22_gate_widths_follow_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(gate.run_widths(root), (1600, 768, 390))
            run_config.intake(root, source="none", checkpoints="auto", speed="fast")
            self.assertEqual(gate.run_widths(root), (1600, 390))
            self.assertEqual(gate.run_width_keys(root), ("1600", "390"))
            self.assertEqual(
                [p.as_posix() for p in gate.run_source_dirs(root)],
                ["capture/home-desktop/source-sections", "capture/home-390/source-sections"],
            )
            self.assertFalse(gate.raw_required(root))

    def test_fast_gate_does_not_demand_768_or_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="auto", speed="fast")
            gate.install_passing_artifacts(root)
            # strip the tablet artifacts and the raw dump — a fast run never made them
            import shutil

            shutil.rmtree(root / "capture" / "home-768", ignore_errors=True)
            (root / gate.RAW).unlink(missing_ok=True)
            receipt_path = root / gate.RECEIPT
            payload = json.loads(receipt_path.read_text())
            payload["widths"] = [1600, 390]
            for row in payload["sections"]:
                row.pop("768", None)
            receipt_path.write_text(json.dumps(payload))
            errors = gate.gate_errors(root)
            self.assertFalse([e for e in errors if "768" in e or "index-raw" in e], errors)

    def test_full_gate_still_demands_768(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            import shutil

            shutil.rmtree(root / "capture" / "home-768")
            errors = gate.gate_errors(root)
            self.assertTrue(any("home-768" in e for e in errors), errors)


class AutoAccept(unittest.TestCase):
    def test_14_auto_writes_receipt_without_paper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="auto", speed="full")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                pipeline_progress.write_auto_accept_14(root)
            note = (root / "qa" / "paper-human-review.md").read_text()
            self.assertIn("AUTO-ACCEPTED", note)
            self.assertIn("no Paper / browser opened", out.getvalue())
            self.assertTrue(pipeline_progress.artifact_done(root, "1.4"))

    def test_24_auto_refuses_while_23_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="auto", speed="full")
            with self.assertRaises(SystemExit):
                pipeline_progress.write_auto_accept_24(root)
            self.assertFalse((root / "qa" / "build-checkpoint.md").exists())

    def test_24_auto_accepts_when_23_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="auto", speed="full")
            gate.install_passing_artifacts(root)
            self.assertEqual(gate.gate_errors(root), [])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                pipeline_progress.write_auto_accept_24(root)
            self.assertTrue((root / "qa" / "build-checkpoint.md").is_file())
            self.assertTrue(pipeline_progress.artifact_done(root, "2.4"))

    def test_24_human_mode_still_needs_opened_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            (root / "qa").mkdir(exist_ok=True)
            (root / "qa" / "build-checkpoint.md").write_text("# signed")
            self.assertFalse(pipeline_progress.artifact_done(root, "2.4"))


class LiveBoardMode(unittest.TestCase):
    """The board reflects the intake: title icon/badge + which rows are stops."""

    def _board(self, checkpoints: str, speed: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa").mkdir()
            run_config.intake(root, source="none", checkpoints=checkpoints, speed=speed)
            template = pipeline_progress.live_template().read_text()
            return pipeline_progress.stamp_run_mode(template, root)

    @staticmethod
    def _markup(html: str) -> str:
        return html.split("<body", 1)[1]

    def test_full_run_has_no_mode_no_badge_no_row_flags(self):
        html = self._board("human", "full")
        body = self._markup(html)
        self.assertNotIn("data-mode=", body.split(">", 1)[0])
        self.assertNotIn('class="run-mode ', body)
        self.assertNotIn("data-run-step=", body)

    def test_auto_run_hides_1_4_and_2_4_only(self):
        html = self._board("auto", "full")
        self.assertIn('<body data-mode="auto"', html)
        self.assertIn(">Auto Run<", html)
        self.assertRegex(html, r'data-step="1\.4"[^>]*data-run-step="auto"')
        self.assertRegex(html, r'data-step="2\.4"[^>]*data-run-step="auto"')
        self.assertRegex(html, r'data-progress-step="1\.4"[^>]*data-run-step="auto"')
        self.assertNotRegex(html, r'data-step="3\.4"[^>]*data-run-step=')
        self.assertNotIn('data-run-step="skipped"', self._markup(html))

    def test_fast_run_strikes_1_3_and_2_1_and_hides_checkpoints(self):
        html = self._board("auto", "fast")
        self.assertIn('<body data-mode="fast"', html)
        self.assertIn(">Fast Run<", html)
        self.assertIn("1600/390", html)
        self.assertRegex(html, r'data-step="1\.3"[^>]*data-run-step="skipped"')
        self.assertRegex(html, r'data-step="2\.1"[^>]*data-run-step="skipped"')
        self.assertRegex(html, r'data-step="1\.4"[^>]*data-run-step="auto"')
        self.assertNotRegex(html, r'data-step="3\.4"[^>]*data-run-step=')

    def test_restamp_is_idempotent(self):
        html = self._board("auto", "fast")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa").mkdir()
            run_config.intake(root, source="none", checkpoints="auto", speed="fast")
            again = pipeline_progress.stamp_run_mode(html, root)
        self.assertEqual(html, again)

    def test_template_carries_one_icon_per_mode(self):
        template = pipeline_progress.live_template().read_text()
        for cls in ("run-gear", "run-orbit", "run-turbo"):
            self.assertEqual(template.count(f'class="run-icon {cls}"'), 1, cls)


if __name__ == "__main__":
    unittest.main()
