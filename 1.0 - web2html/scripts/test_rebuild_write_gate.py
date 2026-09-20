#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import rebuild_write_gate as gate  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "pipeline_progress", _SCRIPTS / "pipeline-progress.py"
)
pipeline_progress = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(pipeline_progress)


def _done_through(root: Path, last: str) -> None:
    data = pipeline_progress.empty_progress(root.name)
    for sid in pipeline_progress.STEP_IDS:
        data["steps"][sid]["status"] = "done"
        if sid == last:
            break
    pipeline_progress.save_progress(root, data, force=True)


class RebuildWriteGateTest(unittest.TestCase):
    def test_no_board_is_a_fail_even_without_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("pipeline-progress.json", errors)

    def test_index_without_board_is_unauthorized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html><h1>Hi</h1></html>")
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("without a board", errors)

    def test_design_system_allow_ok_after_14(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "1.4")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "design-system.html").write_text("<html></html>")
            self.assertEqual(gate.gate_errors(root, allow=gate.ALLOW_DESIGN_SYSTEM), [])

    def test_design_system_html_is_kept_at_22(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "1.4")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "design-system.html").write_text("<html></html>")
            self.assertEqual(gate.gate_errors(root, allow=gate.ALLOW_INDEX), [])

    def test_index_is_unauthorized_at_21(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "1.4")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_DESIGN_SYSTEM))
            self.assertIn("index.html", errors)

    def test_semantic_is_unauthorized_at_21(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "1.4")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index-semantic.html").write_text("<html></html>")
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_DESIGN_SYSTEM))
            self.assertIn("index-semantic.html", errors)

    def test_index_without_allow_is_unauthorized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "1.4")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("index.html", errors)

    def test_index_ok_after_14(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "1.4")
            self.assertEqual(gate.gate_errors(root, allow=gate.ALLOW_INDEX), [])

    def test_tailwind_cdn_is_freehand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "2.1")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(
                '<html><script src="https://cdn.tailwindcss.com"></script></html>'
            )
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_INDEX))
            self.assertIn("cdn.tailwindcss.com", errors)

    def test_paper_index_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "2.1")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(
                "<html><body><main><section><h1>Home</h1><p>Copy from Paper.</p></section></main></body></html>"
            )
            self.assertEqual(gate.gate_errors(root, allow=gate.ALLOW_INDEX), [])

    def test_raw_get_jsx_fixture_is_not_a_ship_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "2.1")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(
                '<html><body data-pc="pc-01-0">'
                '<section data-export="get_jsx-inline-styles"><p><div>Soup</div></p></section>'
                '</body></html>'
            )
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_INDEX))
            self.assertIn("raw Paper get_jsx export metadata", errors)
            self.assertIn("invalid HTML nesting", errors)

    def test_semantic_dump_is_not_a_ship_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "2.1")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index-semantic.html").write_text(
                '<html><body data-pc="pc-01-0">'
                '<section data-export="get_jsx-inline-styles"><p><div>Soup</div></p></section>'
                '</body></html>'
            )
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_INDEX))
            self.assertIn("raw Paper get_jsx export metadata", errors)
            self.assertIn("invalid HTML nesting", errors)

    def test_index_raw_dump_is_allowed_with_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "2.1")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(
                "<html><body><main><section><h1>Home</h1></section></main></body></html>"
            )
            (root / "rebuild" / "index-raw.html").write_text(
                '<html data-export="get_jsx-inline-styles"><body><div>dump</div></body></html>'
            )
            self.assertEqual(gate.gate_errors(root, allow=gate.ALLOW_INDEX), [])

    def test_polish_is_unauthorized_before_24(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "2.3")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index-polish.html").write_text("<html></html>")
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_POLISH))
            self.assertIn("2.4", errors)

    def test_polish_ok_after_24(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "2.4")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html><body><main><section><h1>Home</h1></section></main></body></html>")
            (root / "rebuild" / "index-polish.html").write_text(
                "<html><body><main><section><h1>Home</h1></section></main></body></html>"
            )
            (root / "rebuild" / "polish-report.html").write_text("<html></html>")
            self.assertEqual(gate.gate_errors(root, allow=gate.ALLOW_POLISH), [])

    def test_polish_is_unauthorized_under_index_allow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "1.4")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            (root / "rebuild" / "index-polish.html").write_text("<html></html>")
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_INDEX))
            self.assertIn("index-polish.html", errors)

    def test_quarantine_moves_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            src = root / "rebuild" / "index.html"
            src.write_text("<html>freehand</html>")
            moved = gate.quarantine_unauthorized_ship(root)
            self.assertEqual(len(moved), 1)
            self.assertFalse(src.is_file())
            self.assertTrue(moved[0].is_file())
            self.assertIn("quarantine", moved[0].as_posix())


class PipelineBypassLockTest(unittest.TestCase):
    def test_mark_cannot_jump_to_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"))
            self.assertEqual(pipeline_progress.cmd_mark(root, "2.1", "active", None), 2)
            self.assertEqual(pipeline_progress.cmd_mark(root, "2.3", "active", None), 2)
            self.assertEqual(
                pipeline_progress.load_progress(root)["steps"]["2.1"]["status"],
                "pending",
            )

    def test_mark_12_active_does_not_require_11(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"))
            self.assertEqual(pipeline_progress.cmd_mark(root, "1.2", "active", None), 0)

    def test_mark_13_active_requires_12_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"))
            self.assertEqual(pipeline_progress.cmd_mark(root, "1.3", "active", None), 2)

    def test_mark_14_done_needs_the_review_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "1.3")
            (root / "qa").mkdir(parents=True, exist_ok=True)
            self.assertEqual(pipeline_progress.cmd_mark(root, "1.4", "done", None), 2)
            (root / "qa" / "paper-human-review.md").write_text("# signed\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "1.4", "done", None), 0)

    def test_sync_does_not_complete_21_from_tokens_before_14(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = pipeline_progress.empty_progress("demo")
            for sid in ("1.1", "1.2", "1.3"):
                data["steps"][sid]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            css = root / "rebuild" / "css"
            css.mkdir(parents=True)
            (css / "tokens.css").write_text(":root{}\n")
            self.assertEqual(pipeline_progress.cmd_sync(root), 0)
            after = pipeline_progress.load_progress(root)
            self.assertEqual(after["steps"]["2.1"]["status"], "pending")
            self.assertEqual(after["steps"]["1.4"]["status"], "pending")

    def test_start_quarantines_freehand_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html>nope</html>")
            original = pipeline_progress.open_live_board
            pipeline_progress.open_live_board = lambda dest: True
            try:
                code = pipeline_progress.cmd_start(root)
            finally:
                pipeline_progress.open_live_board = original
            self.assertEqual(code, 2)
            self.assertFalse((root / "rebuild" / "index.html").is_file())
            quarantined = list((root / "qa" / "quarantine").rglob("index.html"))
            self.assertEqual(len(quarantined), 1)
            self.assertTrue((root / "qa" / "pipeline-progress.json").is_file())

    def test_interior_html_illegal_before_phase5(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "3.4")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "about.html").write_text("<html></html>")
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_PAGES))
            self.assertIn("phase-5-opted", errors)

    def test_interior_html_allowed_after_44_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _done_through(root, "4.4")
            (root / "qa").mkdir(exist_ok=True)
            (root / "qa" / "phase-5-opted.json").write_text("{}\n")
            (root / "qa" / "phase-4-pages.json").write_text(
                '{"pages": [{"slug": "about"}]}\n'
            )
            (root / "rebuild").mkdir()
            for name in (
                "index.html",
                "index-semantic.html",
                "design-system.html",
                "index-raw.html",
                "index-polish.html",
                "about-raw.html",
            ):
                (root / "rebuild" / name).write_text("<html></html>")
            self.assertEqual(gate.gate_errors(root, allow=gate.ALLOW_PAGES), [])
            # Interiors are astro/src/pages/{slug}.astro — a rebuild/{slug}.html is a leak.
            (root / "rebuild" / "about.html").write_text("<html></html>")
            errors = " ".join(gate.gate_errors(root, allow=gate.ALLOW_PAGES))
            self.assertIn("rebuild/about.html", errors)


if __name__ == "__main__":
    unittest.main()
