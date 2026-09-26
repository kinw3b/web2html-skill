import contextlib
import importlib.util
import io
import json
import os
import re
import tempfile
import unittest
from html import escape as html_escape
from pathlib import Path

import run_config


os.environ.setdefault("WEB2HTML_NO_PROBE", "1")  # keep start/resume hermetic: no live Orca probe in tests

MODULE_PATH = Path(__file__).with_name("pipeline-progress.py")
SPEC = importlib.util.spec_from_file_location("pipeline_progress", MODULE_PATH)
pipeline_progress = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(pipeline_progress)


class PipelineProgressTests(unittest.TestCase):
    def test_public_landing_page_uses_unique_phase_labels(self):
        landing = MODULE_PATH.parents[2] / "index.html"
        html = landing.read_text()
        steps = re.findall(
            r'<article class="step">\s*<div class="dot">([^<]+)</div>\s*<div>\s*<h2>([^<]+)</h2>',
            html,
        )
        labels = [label for label, _ in steps if label != "✓"]

        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels[:4], ["1.1", "1.2", "1.3", "1.4"])
        self.assertIn(("1.3", "Mine tokens, then pull buttons and components"), steps)
        self.assertIn(("1.4", "Sign off in Paper"), steps)
        articles = re.findall(r'<article class="step(?: is-end)?">(.*?)</article>', html, re.DOTALL)
        summaries = [re.search(r'<p>(.*?)</p>', article, re.DOTALL).group(1) for article in articles]
        summary_words = [re.sub(r'<[^>]+>', '', summary).split() for summary in summaries]
        self.assertTrue(all(len(words) <= 24 for words in summary_words))
        self.assertNotIn('<ul class="step-list">', html)
        dg_css = re.search(r'  \.dg \{(.*?)\n  \}', html, re.DOTALL).group(1)
        self.assertNotIn('border-top', dg_css)
        self.assertNotIn('padding:', dg_css)
        step_css = re.search(r'  \.step \{(.*?)\n  \}', html, re.DOTALL).group(1)
        self.assertIn('padding: 56px 0;', step_css)
        self.assertIn('padding: 40px 0;', html)
        self.assertNotRegex(html, r'(?i)tailwind')

    def test_qa_is_a_three_point_zero_phase(self):
        self.assertEqual(
            pipeline_progress.REQUIRED_STEPS[-4:],
            ["3.1", "3.2", "3.3", "3.4"],
        )
        self.assertEqual(
            pipeline_progress.STEPS[-10:],
            [
                ("4.1", "Sitemap"),
                ("4.2", "Capture pages"),
                ("4.3", "Seed tokens"),
                ("4.4", "Human review"),
                ("5.1", "Scaffold Astro"),
                ("5.2", "Author pages"),
                ("5.3", "Desktop QA"),
                ("5.4", "Responsive"),
                ("5.5", "Wire routes + SEO"),
                ("5.6", "Human checkpoint"),
            ],
        )
        self.assertEqual(
            pipeline_progress.HUMAN_CHECKPOINTS,
            frozenset({"1.4", "2.4", "3.4", "4.4", "5.6"}),
        )
        # Design system moved ahead of the optional Capture Tool: tokens are
        # mined straight off the 1.2 Paper frames.
        self.assertIn(("1.2", "Breakpoints + Navigation"), pipeline_progress.STEPS)
        self.assertIn(("1.3", "Design Library + Tokens"), pipeline_progress.STEPS)
        # 1.4 is the single human checkpoint: optional Capture Tool + Paper sign-off.
        self.assertIn(("1.4", "Human checkpoint"), pipeline_progress.STEPS)
        self.assertIn(("2.1", "Design System"), pipeline_progress.STEPS)
        self.assertIn(("2.2", "Author the homepage"), pipeline_progress.STEPS)
        self.assertIn(("2.3", "Validate vs Paper"), pipeline_progress.STEPS)
        self.assertIn(("2.4", "Sign-off → 3.0 polish"), pipeline_progress.STEPS)
        self.assertEqual(
            [sid for sid in pipeline_progress.STEP_IDS if sid.startswith("2.")],
            ["2.1", "2.2", "2.3", "2.4"],
        )
        self.assertNotIn("2.2.a", pipeline_progress.STEP_IDS)
        self.assertNotIn("2.2.e", pipeline_progress.STEP_IDS)
        self.assertEqual(
            pipeline_progress.SPINE_GROUPS["static"],
            ("2.1", "2.2", "2.3", "2.4"),
        )
        template = pipeline_progress.live_template().read_text()
        self.assertEqual(
            re.findall(r'data-step="([^"]+)"', template),
            pipeline_progress.STEP_IDS,
        )
        cards = re.findall(r'<section class="card[^"]*">(.*?)</section>', template, re.DOTALL)
        self.assertEqual(len(cards), 5)
        self.assertEqual(
            [re.search(r'<h3>([^<]+)</h3>', card).group(1) for card in cards],
            ["Capture", "Build", "QA", "Pages", "Site"],
        )
        self.assertEqual(
            [re.findall(r'data-step="([^"]+)"', card) for card in cards],
            [
                ["1.1", "1.2", "1.3", "1.4"],
                ["2.1", "2.2", "2.3", "2.4"],
                ["3.1", "3.2", "3.3", "3.4"],
                ["4.1", "4.2", "4.3", "4.4"],
                ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6"],
            ],
        )
        self.assertIn("0 / 12", template)
        self.assertNotIn("Capture, Build, QA", template)
        self.assertNotIn("The run", template)
        self.assertIn("is-optional", template)
        self.assertEqual(
            re.findall(
                r'<article class="row check"[^>]*>.*?<h4>([^<]+)</h4>',
                template,
                re.DOTALL,
            ),
            [
                "Human checkpoint",
                "Sign-off → 3.0 polish",
                "Human checkpoint",
                "Human review",
                "Human checkpoint",
            ],
        )
        self.assertIn("Take it wherever you build", template)
        self.assertIn("optional 4.0", template)
        self.assertIn("This board stays next to <code>rebuild/</code>.", template)
        self.assertNotIn("data-pipeline-here-next", template)
        self.assertIn("data-pipeline-capture", template)
        self.assertIn("data-pipeline-capture-copy", template)
        self.assertIn('target="_blank"', template)
        self.assertIn('data-state="waiting"', template)
        self.assertIn("data-finish", template)
        self.assertIn("Astro", template)
        self.assertIn('<h1 class="run-title">', template)
        self.assertIn("Web2Html", template)
        self.assertIn('class="run-icon run-gear"', template)
        self.assertIn("<span>Run</span></h1>", template)
        self.assertNotIn("Five files control the package", template)
        self.assertNotIn("Eight rules prevent almost every failed run", template)
        self.assertEqual(len(re.findall(r'class="timeline-item"', template)), 22)
        self.assertEqual(len(re.findall(r'class="dg"', template)), 22)
        self.assertIn("optional 5.0", template)
        self.assertNotIn("optional 6.0", template)
        self.assertIn("review, then tidy", template)
        self.assertIn('.timeline-item[data-status="done"] .timeline-status::after { content: "COMPLETE"; }', template)
        self.assertIn('.timeline-item[data-status="done"] .timeline-head h3 { color: var(--ink); }', template)
        self.assertIn('.timeline-item[data-status="done"]::before { background: var(--accent); }', template)
        self.assertIn('.timeline-item[data-status="pending"],', template)
        self.assertIn('.timeline-item[data-status="up-next"] {', template)
        self.assertIn('.timeline-item[data-status="up-next"] .timeline-status::before { content: "UP NEXT"; }', template)
        self.assertNotIn('.timeline-item[data-status="done"] .timeline-head h3 { color: var(--muted); }', template)
        self.assertEqual(
            re.findall(r'data-spine="([^"]+)"', template),
            list(pipeline_progress.SPINE_GROUPS),
        )
        self.assertIn('.spine li[data-status="active"], .spine li[data-status="done"]', template)
        self.assertIn('.spine li:not(:last-child)::after', template)
        self.assertNotIn('.spine li + li::before', template)
        self.assertIn('background: var(--accent);', template)

    def test_dependency_spine_tracks_overlapping_run_milestones(self):
        data = pipeline_progress.empty_progress("demo")
        data["steps"]["1.1"]["status"] = "done"
        data["steps"]["1.2"]["status"] = "active"

        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)

        states = dict(re.findall(r'data-spine="([^"]+)" data-status="([^"]+)"', html))
        self.assertEqual(states, {
            "url": "done",
            "evidence": "active",
            "paper": "active",
            "static": "pending",
            "qa": "pending",
        })

        for sid in pipeline_progress.STEP_IDS:
            data["steps"][sid]["status"] = "done"
        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)
        states = dict(re.findall(r'data-spine="([^"]+)" data-status="([^"]+)"', html))
        self.assertTrue(all(status == "done" for status in states.values()))

    def test_timeline_tracks_the_same_live_step_states(self):
        data = pipeline_progress.empty_progress("demo")
        data["steps"]["1.1"]["status"] = "done"
        data["steps"]["1.2"]["status"] = "active"

        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)
        timeline_states = re.findall(
            r'data-progress-step="([^"]+)" data-status="([^"]+)"',
            html,
        )

        self.assertEqual(timeline_states[0], ("1.1", "done"))
        self.assertEqual(timeline_states[1], ("1.2", "active"))
        self.assertEqual(timeline_states[2], ("1.3", "up-next"))
        self.assertIn(("3.4", "pending"), timeline_states)
        self.assertIn('data-progress-step="1.3" data-status="up-next" aria-disabled="true"', html)
        self.assertIn('data-progress-step="3.4" data-status="pending" aria-disabled="true"', html)
        self.assertNotIn('data-progress-step="1.2" data-status="active" aria-disabled', html)
        self.assertIn(
            'class="row" data-step="1.2" data-status="active"',
            html,
        )

    def test_capture_url_lands_under_the_bar_once_paper_exists(self):
        data = pipeline_progress.empty_progress("demo")
        waiting = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)
        self.assertIn('data-pipeline-capture data-state="waiting"', waiting)
        self.assertIn('data-pipeline-capture-url href=""', waiting)
        self.assertIn("data-pipeline-capture-copy disabled", waiting)
        self.assertIn("data-pipeline-capture-open disabled", waiting)
        # the address is a data carrier for the buttons, never painted
        self.assertIn(
            'class="capture-url" data-pipeline-capture-url href="" target="_blank" rel="noopener noreferrer" hidden',
            waiting,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "example-site"
            qa = root / "qa"
            qa.mkdir(parents=True)
            (qa / "paper-file.json").write_text(json.dumps({
                "fileId": "FILE123",
                "sourceUrl": "https://example.com/",
            }))
            html = pipeline_progress.stamp_html(
                pipeline_progress.live_template().read_text(), data, root
            )
            url = html_escape(pipeline_progress.build_capture_tool_page_url(root), quote=True)
            # URL is stored as soon as Paper exists, but Copy / Open stay hidden
            # until step 1.4 is the active step.
            self.assertIn('data-pipeline-capture data-state="held"', html)
            self.assertIn(f'href="{url}"', html)
            self.assertIn('target="_blank"', html)
            self.assertIn(f">{url}</a>", html)
            self.assertIn("data-pipeline-capture-copy disabled", html)
            self.assertIn("data-pipeline-capture-open disabled", html)
            self.assertLess(
                html.index("data-pipeline-capture"),
                html.index('class="spine"'),
            )

            data["steps"]["1.4"]["status"] = "active"
            shown = pipeline_progress.stamp_html(
                pipeline_progress.live_template().read_text(), data, root
            )
            self.assertIn('data-pipeline-capture data-state="ready"', shown)
            self.assertIn('data-pipeline-capture-copy>', shown)
            self.assertIn('data-pipeline-capture-open>', shown)
            self.assertNotIn("data-pipeline-capture-copy disabled", shown)
            self.assertNotIn("data-pipeline-capture-open disabled", shown)

            data["steps"]["1.4"]["status"] = "done"
            data["steps"]["2.1"]["status"] = "active"
            later = pipeline_progress.stamp_html(
                pipeline_progress.live_template().read_text(), data, root
            )
            self.assertIn('data-pipeline-capture data-state="held"', later)
            self.assertIn("data-pipeline-capture-copy disabled", later)
            self.assertIn("data-pipeline-capture-open disabled", later)

    def test_finished_run_drops_refresh_and_marks_the_board_done(self):
        data = pipeline_progress.empty_progress("demo")
        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)
        self.assertIn('http-equiv="refresh" content="15"', html)
        self.assertNotRegex(html, r'<body[^>]*data-run="done"')

        for sid in pipeline_progress.STEP_IDS:
            data["steps"][sid]["status"] = "done"
        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)
        self.assertNotIn('http-equiv="refresh"', html)
        self.assertRegex(html, r'<body[^>]*data-run="done"')
        self.assertIn("22 / 22", html)
        self.assertIn("Take it wherever you build", html)

    def test_board_after_24_points_at_31_polish(self):
        data = pipeline_progress.empty_progress("demo")
        for sid in ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4"):
            data["steps"][sid]["status"] = "done"
        html = pipeline_progress.stamp_html(
            pipeline_progress.live_template().read_text(), data
        )
        self.assertIn("NEXT  3.1", html)
        self.assertIn("Session 3 polish", html)
        self.assertRegex(html, r'<body[^>]*data-run="yield"')
        self.assertIn(
            'data-progress-step="3.1" data-status="up-next"',
            html,
        )
        self.assertNotIn(">Ready<", html)

        data["steps"]["2.4"]["status"] = "active"
        html = pipeline_progress.stamp_html(
            pipeline_progress.live_template().read_text(), data
        )
        self.assertIn("▶ 2.4  Sign-off → 3.0 polish", html)

    def test_start_and_write_live_do_not_ship_next_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "NEXT.html").write_text("stale")
            (root / "rebuild").mkdir()
            (root / "rebuild" / "NEXT.html").write_text("stale")
            data = pipeline_progress.empty_progress("demo")
            pipeline_progress.write_live(root, data)
            self.assertFalse((root / "NEXT.html").exists())
            self.assertFalse((root / "rebuild" / "NEXT.html").exists())
            self.assertTrue((root / "pipeline.html").is_file())

    def _finished_progress(self, root: Path) -> dict:
        data = pipeline_progress.empty_progress("demo")
        for sid in pipeline_progress.REQUIRED_STEPS:
            data["steps"][sid]["status"] = "done"
        (root / "qa").mkdir(parents=True, exist_ok=True)
        (root / "qa" / "phase-4-skipped.json").write_text("{}\n")
        pipeline_progress.save_progress(root, data, force=True)
        (root / "pipeline.html").write_text(
            pipeline_progress.stamp_html(
                pipeline_progress.live_template().read_text(),
                data,
                root,
            )
        )
        return data

    def test_finish_strips_qa_shots_and_run_trees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            (root / "rebuild" / "NEXT.html").write_text("stale")
            (root / "NEXT.html").write_text("stale")
            (root / "rebuild" / "polish-report.html").write_text("qa")
            (root / "qa" / "states").mkdir(parents=True)
            (root / "qa" / "states" / "nav.png").write_bytes(b"x")
            (root / "capture" / "home-desktop").mkdir(parents=True)
            (root / "capture" / "home-desktop" / "fullpage.png").write_bytes(b"x")
            (root / "rebuild" / "diff-heatmap.png").write_bytes(b"x")
            (root / "rebuild" / "images").mkdir()
            (root / "rebuild" / "images" / "hero.png").write_bytes(b"x")
            (root / "source-site").mkdir()
            (root / "v4-build.png").write_bytes(b"x")
            (root / "scratch").mkdir()
            data = self._finished_progress(root)
            self.assertTrue(pipeline_progress.run_is_complete(data, root))
            self.assertTrue(pipeline_progress.run_may_tidy(root))

            removed = pipeline_progress.tidy_completed_run(root)
            self.assertIn("qa", removed)
            self.assertIn("capture", removed)
            self.assertIn("source-site", removed)
            self.assertNotIn("pipeline.html", removed)
            self.assertIn("rebuild/polish-report.html", removed)
            self.assertFalse((root / "qa").exists())
            self.assertFalse((root / "capture").exists())
            self.assertIn("v4-build.png", removed)
            self.assertIn("scratch", removed)
            self.assertIn("rebuild/diff-heatmap.png", removed)
            self.assertTrue((root / "rebuild" / "index.html").is_file())
            self.assertTrue((root / "pipeline.html").is_file())
            self.assertIn('data-run="done"', (root / "pipeline.html").read_text())
            self.assertFalse((root / "NEXT.html").exists())
            self.assertFalse((root / "rebuild" / "NEXT.html").exists())
            self.assertFalse((root / "rebuild" / "polish-report.html").exists())
            # Real site assets survive the sweep.
            self.assertTrue((root / "rebuild" / "images" / "hero.png").is_file())
            self.assertEqual(
                sorted(p.name for p in root.iterdir()),
                ["pipeline.html", "rebuild"],
            )
            self.assertTrue(pipeline_progress.run_may_tidy(root))
            self.assertEqual(pipeline_progress.cmd_finish(root), 0)

    def test_finish_refuses_a_partial_run_without_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            (root / "capture").mkdir()
            (root / "pipeline.html").write_text("<html></html>")
            self.assertFalse(pipeline_progress.run_may_tidy(root))
            self.assertEqual(pipeline_progress.cmd_finish(root), 2)
            self.assertTrue((root / "capture").is_dir())
            with self.assertRaises(SystemExit):
                pipeline_progress.tidy_completed_run(root)

    def test_finish_refuses_an_open_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            data = pipeline_progress.empty_progress("demo")
            data["steps"]["1.1"]["status"] = "done"
            (qa / "pipeline-progress.json").write_text(
                __import__("json").dumps(data),
            )
            self.assertEqual(pipeline_progress.cmd_finish(root), 2)
            self.assertTrue(qa.is_dir())

    def test_capture_requires_geometry_postflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "capture" / "home-desktop").mkdir(parents=True)
            self.assertFalse(pipeline_progress.artifact_done(root, "1.2"))
            (root / "qa").mkdir()
            (root / "qa" / "stretch-root-evidence.md").write_text("Result: PASS\n")
            (root / "source-site" / "components").mkdir(parents=True)
            self.assertFalse(pipeline_progress.artifact_done(root, "1.2"))
            shots = root / "capture" / "home-desktop" / "source-sections"
            shots.mkdir(parents=True)
            (shots / "01-hero.png").write_bytes(b"x")
            self.assertFalse(pipeline_progress.artifact_done(root, "1.2"))
            for folder in ("home-768", "home-390"):
                band = root / "capture" / folder / "source-sections"
                band.mkdir(parents=True)
                (band / "01-hero.png").write_bytes(b"x")
            self.assertFalse(pipeline_progress.artifact_done(root, "1.2"))
            (root / "qa" / "breakpoint-shot-qa.json").write_text(json.dumps({
                "ok": True,
                "missingFrames": [],
                "frames": [{"name": "home-768"}, {"name": "home-390"}],
            }))
            self.assertTrue(pipeline_progress.artifact_done(root, "1.2"))

            # 1.3 is now the Design Library, mined straight off the 1.2 frames.
            (root / "design-library").mkdir()
            (root / "design-library" / "library.json").write_text("{}")
            self.assertFalse(pipeline_progress.artifact_done(root, "1.3"))
            (root / "qa" / "library-seed-qa.json").write_text(json.dumps({"ok": False, "failures": [{}]}))
            self.assertFalse(pipeline_progress.artifact_done(root, "1.3"))
            (root / "qa" / "library-seed-qa.json").write_text(json.dumps({"ok": True, "failures": []}))
            self.assertFalse(pipeline_progress.artifact_done(root, "1.3"))
            (root / "qa" / "design-library-step.json").write_text(json.dumps({
                "status": "done",
                "writer": "render-library.mjs",
                "kind": "foundations",
                "commands": ["extract-library.mjs", "render-library.mjs"],
            }))
            self.assertFalse(pipeline_progress.artifact_done(root, "1.3"))
            (root / "qa" / "buttons-components-pull.json").write_text(json.dumps({
                "ok": True,
                "writer": "pull-desktop-specimens.mjs",
                "geometry": {"ok": True},
                "scannedSections": ["01 · hero"],
                "buttons": [],
                "components": [],
            }))
            self.assertFalse(pipeline_progress.artifact_done(root, "1.3"))
            (root / "qa" / "button-hover.json").write_text(json.dumps({
                "ok": True,
                "writer": "author-button-hover.mjs",
                "applied": [],
                "skipped": [],
            }))
            self.assertTrue(pipeline_progress.artifact_done(root, "1.3"))

            # 1.4 is the Paper checkpoint. Capture Tool is optional leftover.
            self.assertFalse(pipeline_progress.artifact_done(root, "1.4"))
            (root / "qa" / "paper-human-review.md").write_text("# signed\n")
            self.assertTrue(pipeline_progress.artifact_done(root, "1.4"))

            (root / "qa" / "stretch-root-evidence.md").write_text("Result: FAIL\n")
            self.assertFalse(pipeline_progress.artifact_done(root, "1.2"))

    def test_21_requires_design_system_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(pipeline_progress.artifact_done(root, "2.1"))
            from design_system_21_gate import install_passing_artifacts as install_ds

            install_ds(root)
            self.assertTrue(pipeline_progress.artifact_done(root, "2.1"))
            self.assertFalse(pipeline_progress.artifact_done(root, "2.2"))

    def test_22_authors_from_21_tokens_without_invented_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from author_21_gate import install_passing_artifacts

            install_passing_artifacts(root)
            self.assertTrue(pipeline_progress.artifact_done(root, "2.1"))
            self.assertTrue(pipeline_progress.artifact_done(root, "2.2"))
            (root / "rebuild" / "css" / "page.css").write_text(
                ":root { --color-hotpink: #ff2bd6; }\n"
            )
            self.assertFalse(pipeline_progress.artifact_done(root, "2.2"))
            (root / "rebuild" / "css" / "page.css").write_text(
                "h1 { color: #111; font-size: 48px; }\n"
            )
            self.assertTrue(pipeline_progress.artifact_done(root, "2.2"))
            utilities = root / "rebuild" / "css" / "token-utilities.css"
            utilities.write_text(".ink { color: var(--color-ink); }\n")
            self.assertFalse(pipeline_progress.artifact_done(root, "2.2"))
            html = (root / "rebuild" / "index-semantic.html").read_text()
            (root / "rebuild" / "index-semantic.html").write_text(
                html.replace(
                    'href="css/tokens.css">',
                    'href="css/tokens.css">'
                    '<link rel="stylesheet" href="css/token-utilities.css">',
                )
            )
            self.assertTrue(pipeline_progress.artifact_done(root, "2.2"))

    def test_22_done_seeds_index_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from author_21_gate import install_passing_artifacts

            install_passing_artifacts(root)
            data = pipeline_progress.empty_progress("demo")
            for sid in ("1.1", "1.2", "1.3", "1.4", "2.1"):
                data["steps"][sid]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            self.assertFalse((root / "rebuild" / "index.html").is_file())
            self.assertEqual(pipeline_progress.cmd_mark(root, "2.2", "done", None), 0)
            self.assertTrue((root / "rebuild" / "index.html").is_file())
            self.assertEqual(
                (root / "rebuild" / "index.html").read_text(encoding="utf-8"),
                (root / "rebuild" / "index-semantic.html").read_text(encoding="utf-8"),
            )

    def test_22_requires_every_section_signed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from author_21_gate import install_passing_artifacts as install_21
            from section_22_gate import install_passing_artifacts as install_22

            install_21(root)
            self.assertFalse(pipeline_progress.artifact_done(root, "2.3"))
            install_22(root)
            self.assertTrue(pipeline_progress.artifact_done(root, "2.3"))

    def test_23_requires_overlay_and_human_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            (root / "rebuild" / "js").mkdir(parents=True)
            (root / "rebuild" / "js" / "qa-overlay.js").write_text(
                'function mode() { return localStorage.getItem(KEY) || "tags"; }\n'
            )
            self.assertFalse(pipeline_progress.artifact_done(root, "2.4"))
            (qa / "build-checkpoint-opened.json").write_text(
                json.dumps(
                    {
                        "generatedFrom": "web2html/open-build-review",
                        "stage": "2.4",
                    }
                )
            )
            self.assertFalse(pipeline_progress.artifact_done(root, "2.4"))
            (qa / "build-checkpoint.md").write_text("# approved\n")
            self.assertTrue(pipeline_progress.artifact_done(root, "2.4"))

    def test_nav_drawer_done_rejects_capture_tool_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            self.assertFalse(pipeline_progress.nav_drawer_done(root))
            (qa / "nav-drawer.json").write_text(json.dumps({
                "ok": True,
                "writer": "author-nav-drawer.py",
                "applied": [],
                "skipped": [{
                    "finding": "burger open drawer",
                    "reason": "No Capture Tool open-nav pair. Inventing a sheet is new chrome.",
                }],
            }))
            self.assertFalse(pipeline_progress.nav_drawer_done(root))
            (qa / "nav-drawer.json").write_text(json.dumps({
                "ok": True,
                "writer": "author-nav-drawer.py",
                "applied": [{"finding": "burger open drawer", "fix": "stacked desktop links"}],
                "skipped": [],
            }))
            self.assertTrue(pipeline_progress.nav_drawer_done(root))

    def test_faq_done_rejects_empty_bodies_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            self.assertFalse(pipeline_progress.faq_done(root))
            (qa / "faq.json").write_text(json.dumps({
                "ok": True,
                "writer": "author-faq.py",
                "painted": True,
                "applied": [],
                "skipped": [{
                    "finding": "FAQ accordion",
                    "reason": "2.3 dump/Paper signed empty bodies. Do not invent copy.",
                }],
            }))
            self.assertFalse(pipeline_progress.faq_done(root))
            (qa / "faq.json").write_text(json.dumps({
                "ok": True,
                "writer": "author-faq.py",
                "painted": True,
                "applied": [{"finding": "FAQ accordion", "fix": "wired toggle"}],
                "skipped": [],
            }))
            self.assertTrue(pipeline_progress.faq_done(root))

    def test_nav_dropdown_done_rejects_capture_tool_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            self.assertFalse(pipeline_progress.nav_dropdown_done(root))
            (qa / "nav-dropdown.json").write_text(json.dumps({
                "ok": True,
                "writer": "author-nav-dropdown.py",
                "applied": [],
                "skipped": [{
                    "finding": "nav dropdown",
                    "reason": "Capture Tool did not run. --allow-dropdown was not passed. Do not hunt.",
                }],
            }))
            self.assertFalse(pipeline_progress.nav_dropdown_done(root))
            (qa / "nav-dropdown.json").write_text(json.dumps({
                "ok": True,
                "writer": "author-nav-dropdown.py",
                "applied": [{"finding": "nav dropdown", "fix": "wired panel"}],
                "skipped": [],
            }))
            self.assertTrue(pipeline_progress.nav_dropdown_done(root))

    def test_mark_refuses_retired_22_letters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            self.assertEqual(pipeline_progress.cmd_mark(root, "2.2.a", "done", None), 2)
            self.assertEqual(pipeline_progress.cmd_mark(root, "2.2.e", "active", None), 2)

    def test_old_22_letters_migrate_to_21_22_23(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            progress = {
                "project": "legacy-22",
                "current": "2.2.d",
                "steps": {
                    "1.1": {"title": "Contract", "status": "done"},
                    "1.2": {"title": "Capture", "status": "done"},
                    "1.3": {"title": "Hover", "status": "done"},
                    "1.4": {"title": "Library", "status": "done"},
                    "1.5": {"title": "Review", "status": "done"},
                    "2.1": {"title": "Gallery", "status": "done"},
                    "2.2.a": {"title": "Dump", "status": "done"},
                    "2.2.b": {"title": "Inline", "status": "done"},
                    "2.2.c": {"title": "Hover", "status": "done"},
                    "2.2.d": {"title": "Responsive", "status": "active"},
                    "2.2.e": {"title": "Review", "status": "pending"},
                    "3.1": {"title": "QA1", "status": "pending"},
                    "3.2": {"title": "QA2", "status": "pending"},
                    "3.3": {"title": "Polish", "status": "pending"},
                    "3.4": {"title": "Review", "status": "pending"},
                },
            }
            (qa / "pipeline-progress.json").write_text(json.dumps(progress))
            migrated = pipeline_progress.load_progress(root)
            self.assertNotIn("2.2.a", migrated["steps"])
            self.assertEqual("done", migrated["steps"]["2.1"]["status"])
            self.assertEqual("active", migrated["steps"]["2.3"]["status"])
            self.assertEqual("pending", migrated["steps"]["2.4"]["status"])
            self.assertEqual("2.3", migrated["current"])
            self.assertEqual(
                "Validate vs Paper",
                migrated["steps"]["2.3"]["title"],
            )
            self.assertEqual("pending", migrated["steps"]["2.2"]["status"])
            self.assertEqual("Author the homepage", migrated["steps"]["2.2"]["title"])

    def test_21ds_migrates_to_sequential_22(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            progress = {
                "project": "legacy-ds",
                "current": "2.1.ds",
                "steps": {
                    "1.1": {"title": "Contract", "status": "done"},
                    "1.2": {"title": "Capture", "status": "done"},
                    "1.3": {"title": "Library", "status": "done"},
                    "1.4": {"title": "Review", "status": "done"},
                    "2.1": {"title": "Author", "status": "done"},
                    "2.1.ds": {"title": "Design System", "status": "active"},
                    "2.2": {"title": "Validate", "status": "pending"},
                    "2.3": {"title": "Human checkpoint", "status": "pending"},
                    "3.1": {"title": "QA1", "status": "pending"},
                    "3.2": {"title": "QA2", "status": "pending"},
                    "3.3": {"title": "Polish", "status": "pending"},
                    "3.4": {"title": "Review", "status": "pending"},
                },
            }
            (qa / "pipeline-progress.json").write_text(json.dumps(progress))
            migrated = pipeline_progress.load_progress(root)
            self.assertNotIn("2.1.ds", migrated["steps"])
            self.assertEqual("2.2", migrated["current"])
            self.assertEqual("active", migrated["steps"]["2.2"]["status"])
            self.assertEqual("Author the homepage", migrated["steps"]["2.2"]["title"])
            self.assertEqual("pending", migrated["steps"]["2.3"]["status"])
            self.assertEqual("Validate vs Paper", migrated["steps"]["2.3"]["title"])
            self.assertEqual("pending", migrated["steps"]["2.4"]["status"])
            self.assertEqual("Sign-off → 3.0 polish", migrated["steps"]["2.4"]["title"])

    def test_live_24_is_not_migrated_to_old_qa(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = pipeline_progress.empty_progress("demo")
            data["steps"]["2.4"]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            migrated = pipeline_progress.load_progress(root)
            self.assertEqual("done", migrated["steps"]["2.4"]["status"])
            self.assertEqual("Sign-off → 3.0 polish", migrated["steps"]["2.4"]["title"])
            self.assertEqual("pending", migrated["steps"]["3.4"]["status"])

    def test_controller_lease_is_exclusive_and_releasable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"))

            self.assertEqual(pipeline_progress.claim_controller(root, "controller-a", 1), 0)
            data = pipeline_progress.load_progress(root)
            self.assertEqual(data["controller"]["owner"], "controller-a")
            self.assertEqual(data["revision"], 2)
            self.assertEqual(pipeline_progress.claim_controller(root, "controller-b", 2), 2)
            self.assertEqual(pipeline_progress.release_controller(root, "controller-a", 2), 0)
            self.assertEqual(pipeline_progress.claim_controller(root, "controller-b", 3), 0)

    def test_mark_rejects_a_stale_expected_revision_without_mutating_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"))
            run_config.intake(root, source="none", checkpoints="human", speed="full")

            self.assertEqual(pipeline_progress.cmd_mark(root, "1.1", "active", None, 1), 0)
            before = pipeline_progress.progress_path(root).read_text()
            self.assertEqual(pipeline_progress.cmd_mark(root, "1.1", "done", None, 1), 2)
            self.assertEqual(pipeline_progress.progress_path(root).read_text(), before)

    def test_mark_11_active_refuses_without_run_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(pipeline_progress.cmd_mark(root, "1.1", "active", None, 1), 2)
            self.assertIn("run_config.py intake", err.getvalue())
            self.assertEqual(pipeline_progress.load_progress(root)["steps"]["1.1"]["status"], "pending")

    def test_sync_ignores_noncanonical_agent_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = pipeline_progress.empty_progress("demo")
            for sid in pipeline_progress.STEP_IDS[:8]:
                data["steps"][sid]["status"] = "done"
            pipeline_progress.save_progress(root, data)
            findings = root / "qa" / "agent-findings" / "run-01" / "3.1"
            findings.mkdir(parents=True)
            (findings / "c3-3.1-impeccable.json").write_text("{}")
            (findings / "c3-3.2-design-taste-frontend.json").write_text("{}")
            (findings.parent / "3.3").mkdir()
            (findings.parent / "3.3" / "semantics-pass-qa.json").write_text("{}")

            self.assertEqual(pipeline_progress.cmd_sync(root), 0)
            after = pipeline_progress.load_progress(root)
            self.assertEqual(after["steps"]["3.1"]["status"], "pending")
            self.assertEqual(after["steps"]["3.2"]["status"], "pending")
            self.assertEqual(after["steps"]["3.3"]["status"], "pending")

    def test_sync_refuses_to_change_progress_while_a_reviewer_is_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"))
            lease = root / "qa" / "agent-runs" / "leases" / "tablet-768.json"
            lease.parent.mkdir(parents=True)
            lease.write_text(json.dumps({"role": "reviewer", "status": "active"}))

            self.assertEqual(pipeline_progress.cmd_sync(root), 2)
            self.assertEqual(pipeline_progress.load_progress(root)["revision"], 1)

    def test_34_done_and_finish_refuse_while_a_reviewer_lease_is_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            data = pipeline_progress.empty_progress("demo")
            for sid in pipeline_progress.REQUIRED_STEPS:
                if sid != "3.4":
                    data["steps"][sid]["status"] = "done"
            data["steps"]["3.4"]["status"] = "active"
            data["current"] = "3.4"
            pipeline_progress.save_progress(root, data)
            (root / "qa" / "phase-4-skipped.json").write_text("{}\n")
            lease = root / "qa" / "agent-runs" / "leases" / "mobile-390.json"
            lease.parent.mkdir(parents=True)
            lease.write_text(json.dumps({"role": "reviewer", "status": "active"}))

            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 2)
            self.assertEqual(pipeline_progress.cmd_finish(root), 2)
            self.assertTrue((root / "qa").is_dir())
            self.assertEqual(pipeline_progress.load_progress(root)["steps"]["3.4"]["status"], "active")

    def test_34_done_refuses_without_index_polish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text("<html></html>")
            data = pipeline_progress.empty_progress("demo")
            for sid in pipeline_progress.REQUIRED_STEPS:
                if sid != "3.4":
                    data["steps"][sid]["status"] = "done"
            data["steps"]["3.4"]["status"] = "active"
            data["current"] = "3.4"
            pipeline_progress.save_progress(root, data)
            (root / "qa" / "phase-4-skipped.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 2)
            self.assertEqual(pipeline_progress.load_progress(root)["steps"]["3.4"]["status"], "active")

    def test_old_design_steps_migrate_without_losing_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            progress = {
                "project": "legacy",
                "current": "1.4",
                "steps": {
                    "1.1": {"title": "Contract", "status": "done"},
                    "1.2": {"title": "Capture", "status": "done"},
                    "1.3": {"title": "Geometry", "status": "done"},
                    "1.4": {"title": "Hover", "status": "active"},
                    "1.5": {"title": "Library", "status": "pending"},
                    "1.6": {"title": "Review", "status": "pending"},
                },
            }
            (qa / "pipeline-progress.json").write_text(json.dumps(progress))

            migrated = pipeline_progress.load_progress(root)

            self.assertNotIn("1.6", migrated["steps"])
            self.assertEqual("1.3", migrated["current"])
            self.assertEqual("done", migrated["steps"]["1.2"]["status"])
            self.assertEqual("active", migrated["steps"]["1.3"]["status"])
            self.assertEqual(
                "Design Library + Tokens",
                migrated["steps"]["1.3"]["title"],
            )

    def test_old_qa_steps_migrate_without_losing_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            qa.mkdir()
            progress = {
                "project": "legacy-qa",
                "current": "2.3.b",
                "steps": {
                    **{
                        sid: {"title": title, "status": "done"}
                        for sid, title in pipeline_progress.STEPS
                        if sid.startswith("1.") or sid.startswith("2.1") or sid.startswith("2.3")
                    },
                    "2.3.a": {"title": "Impeccable", "status": "done"},
                    "2.3.b": {"title": "Taste", "status": "active"},
                    "2.3.c": {"title": "Emil", "status": "pending"},
                    "2.3.d": {"title": "Guidelines", "status": "pending"},
                    "2.3.e": {"title": "Semantics", "status": "pending"},
                    "2.4": {"title": "Review", "status": "pending"},
                },
            }
            (qa / "pipeline-progress.json").write_text(json.dumps(progress))

            migrated = pipeline_progress.load_progress(root)

            self.assertEqual("3.1", migrated["current"])
            self.assertEqual("active", migrated["steps"]["3.1"]["status"])
            self.assertEqual("pending", migrated["steps"]["3.2"]["status"])
            self.assertEqual("pending", migrated["steps"]["3.3"]["status"])
            self.assertEqual("pending", migrated["steps"]["3.4"]["status"])
            self.assertNotIn("2.3.a", migrated["steps"])
            self.assertEqual("pending", migrated["steps"]["2.4"]["status"])
            self.assertEqual("Sign-off → 3.0 polish", migrated["steps"]["2.4"]["title"])

    def test_write_capture_tool_session_reads_paper_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "capture-home"
            root = Path(tmp) / "example-site"
            qa = root / "qa"
            qa.mkdir(parents=True)
            (qa / "paper-file.json").write_text(json.dumps({
                "fileId": "FILE123",
                "url": "https://example.com/",
            }))
            old = os.environ.get("PAPER_CAPTURE_HOME")
            os.environ["PAPER_CAPTURE_HOME"] = str(home)
            try:
                dest = pipeline_progress.write_capture_tool_session(root)
            finally:
                if old is None:
                    os.environ.pop("PAPER_CAPTURE_HOME", None)
                else:
                    os.environ["PAPER_CAPTURE_HOME"] = old
            data = json.loads(dest.read_text())
            self.assertEqual("FILE123", data["paperFileId"])
            self.assertEqual(str(root.resolve()), data["projectRoot"])
            self.assertTrue((qa / "capture-tool-session.json").is_file())

    def test_build_capture_tool_page_url_stamps_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "kp-frilly"
            qa = root / "qa"
            qa.mkdir(parents=True)
            (qa / "paper-file.json").write_text(json.dumps({
                "fileId": "01M0GPEFVQ1A4G5E078T82CNDW",
                "url": "https://kp-frilly.framer.website/",
            }))
            uri = pipeline_progress.build_capture_tool_page_url(root)
            from urllib.parse import unquote
            self.assertTrue(uri.startswith("https://kp-frilly.framer.website/"))
            self.assertIn("paperFileId=01M0GPEFVQ1A4G5E078T82CNDW", uri)
            self.assertIn("projectRoot=", uri)
            self.assertIn(str(root.resolve()), unquote(uri))

    def test_print_14_hard_stop_includes_copyable_urls_and_comment_prompt(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            qa = root / "qa"
            qa.mkdir(parents=True)
            (qa / "paper-file.json").write_text(json.dumps({
                "fileId": "01M0GPEFVQ1A4G5E078T82CNDW",
                "url": "https://example.com/",
            }))
            buf = io.StringIO()
            with redirect_stdout(buf):
                pipeline_progress.print_14_hard_stop(root, paper_opened=False)
            out = buf.getvalue()
            self.assertIn("Paper file", out)
            self.assertIn("https://app.paper.design/file/01M0GPEFVQ1A4G5E078T82CNDW", out)
            self.assertIn("Pin comments", out)
            self.assertIn("FRAME Buttons", out)
            self.assertIn("FRAME Components", out)
            self.assertIn("Done & continue to next step", out)
            self.assertIn("Provide hand-off prompt to start fresh session", out)
            self.assertIn("Paper did not open", out)
            self.assertIn("open-capture", out)

    def test_handoff_draft_while_14_is_open(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            data["steps"]["1.4"]["status"] = "active"
            pipeline_progress.save_progress(root, data, force=True)
            qa = root / "qa"
            qa.mkdir(parents=True, exist_ok=True)
            (qa / "paper-file.json").write_text(json.dumps({
                "fileId": "01M0GPEFVQ1A4G5E078T82CNDW",
                "url": "https://example.com/",
            }))
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(pipeline_progress.cmd_handoff(root), 0)
            out = buf.getvalue()
            self.assertIn("DRAFT", out)
            self.assertIn("SESSION 2", out)
            self.assertIn("01M0GPEFVQ1A4G5E078T82CNDW", out)
            self.assertTrue((root / "qa" / "handoff-2.0.md").is_file())

    def test_mark_14_active_opens_paper_and_forces_capture_browser(self):
        """1.4 active opens Paper AND the browser on the stamped source URL (Pitfall #217)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            data["steps"]["1.1"]["status"] = "done"
            data["steps"]["1.2"]["status"] = "done"
            data["steps"]["1.3"]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            self.assertEqual(pipeline_progress.cmd_mark(root, "1.4", "active", None), 2)
            self.assertEqual(pipeline_progress.load_progress(root)["steps"]["1.4"]["status"], "pending")

            qa = root / "qa"
            qa.mkdir(parents=True, exist_ok=True)
            (qa / "paper-file.json").write_text(json.dumps({
                "fileId": "01M0GPEFVQ1A4G5E078T82CNDW",
                "url": "https://example.com/",
            }))
            browser_calls = []
            original_open = pipeline_progress._open_in_browser
            original_run = pipeline_progress.subprocess.run
            original_doctor = pipeline_progress.capture_doctor

            def fake_open(uri):
                browser_calls.append(uri)
                return True

            class _R:
                returncode = 0

            pipeline_progress._open_in_browser = fake_open
            pipeline_progress.subprocess.run = lambda *a, **k: _R()
            pipeline_progress.capture_doctor = lambda root=None: {"ok": True, "problems": [], "fixes": [], "notes": []}
            try:
                self.assertEqual(pipeline_progress.cmd_mark(root, "1.4", "active", None), 0)
            finally:
                pipeline_progress._open_in_browser = original_open
                pipeline_progress.subprocess.run = original_run
                pipeline_progress.capture_doctor = original_doctor
            self.assertEqual(len(browser_calls), 1)
            self.assertIn("paperFileId=01M0GPEFVQ1A4G5E078T82CNDW", browser_calls[0])
            self.assertIn("projectRoot=", browser_calls[0])
            self.assertTrue(browser_calls[0].startswith("https://example.com/"))
            self.assertTrue((qa / "capture-tool-opened.json").is_file())
            self.assertEqual(pipeline_progress.load_progress(root)["steps"]["1.4"]["status"], "active")

    def test_mark_14_active_survives_browser_failure(self):
        """The browser open is forced but non-fatal: 1.4 still goes active, URL is printed."""
        import io
        from contextlib import redirect_stdout, redirect_stderr

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            for sid in ("1.1", "1.2", "1.3"):
                data["steps"][sid]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            qa = root / "qa"
            qa.mkdir(parents=True, exist_ok=True)
            (qa / "paper-file.json").write_text(json.dumps({
                "fileId": "01M0GPEFVQ1A4G5E078T82CNDW",
                "url": "https://example.com/",
            }))
            original_open = pipeline_progress._open_in_browser
            original_run = pipeline_progress.subprocess.run
            original_doctor = pipeline_progress.capture_doctor

            class _R:
                returncode = 0

            pipeline_progress._open_in_browser = lambda uri: False
            pipeline_progress.subprocess.run = lambda *a, **k: _R()
            pipeline_progress.capture_doctor = lambda root=None: {"ok": False, "problems": ["Google Chrome: native host manifest missing (x)"], "fixes": ["sh install --quiet"], "notes": []}
            out, err = io.StringIO(), io.StringIO()
            try:
                with redirect_stdout(out), redirect_stderr(err):
                    rc = pipeline_progress.cmd_mark(root, "1.4", "active", None)
            finally:
                pipeline_progress._open_in_browser = original_open
                pipeline_progress.subprocess.run = original_run
                pipeline_progress.capture_doctor = original_doctor
            self.assertEqual(rc, 0)
            self.assertEqual(pipeline_progress.load_progress(root)["steps"]["1.4"]["status"], "active")
            self.assertIn("OFFLINE", err.getvalue())
            self.assertIn("native host manifest missing", err.getvalue())
            self.assertIn("Capture Tool URL", out.getvalue())
            self.assertIn("https://example.com/?paperFileId=", out.getvalue())
            self.assertFalse((qa / "capture-tool-opened.json").is_file())

    def test_paper_source_url_prefers_live_site_over_paper_app(self):
        """create-paper-file writes url=app.paper.design; the Capture Tool needs the site."""
        self.assertEqual(
            pipeline_progress.paper_source_url({
                "url": "https://app.paper.design/file/01M0GPEFVQ1A4G5E078T82CNDW",
                "sourceUrl": "https://example.com/",
            }),
            "https://example.com/",
        )
        self.assertEqual(pipeline_progress.paper_source_url({"url": "https://example.com/"}), "https://example.com/")
        self.assertEqual(pipeline_progress.paper_source_url({"sourceUrl": "https://example.com/"}), "https://example.com/")
        self.assertEqual(pipeline_progress.paper_source_url({"url": "https://app.paper.design/file/x"}), "")
        stamped = pipeline_progress.build_capture_tool_page_url(Path("/tmp/demo"), {
            "fileId": "F1",
            "url": "https://app.paper.design/file/F1",
            "sourceUrl": "https://example.com/",
        })
        self.assertTrue(stamped.startswith("https://example.com/?"))

    def test_write_capture_tool_session_skips_global_file_for_temp_roots(self):
        """Test fixtures under the OS temp dir must not clobber the extension's active-session.json."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True)
            (root / "qa" / "paper-file.json").write_text(json.dumps({"fileId": "F", "url": "https://example.com/"}))
            old = os.environ.pop("PAPER_CAPTURE_HOME", None)
            try:
                dest = pipeline_progress.write_capture_tool_session(root)
            finally:
                if old is not None:
                    os.environ["PAPER_CAPTURE_HOME"] = old
            self.assertIsNone(dest)
            self.assertTrue((root / "qa" / "capture-tool-session.json").is_file())

    def test_capture_doctor_reports_missing_bridge(self):
        """Missing manifest / launcher / host → FAIL with the installer as the fix."""
        if pipeline_progress.sys.platform != "darwin":
            self.skipTest("bridge checks are macOS-only")
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "capture-home"
            old_home = os.environ.get("PAPER_CAPTURE_HOME")
            os.environ["PAPER_CAPTURE_HOME"] = str(home)
            original_apps = pipeline_progress._installed_browser_apps
            pipeline_progress._installed_browser_apps = lambda: [("Google Chrome", "Google Chrome", Path(tmp) / "nm")]
            try:
                report = pipeline_progress.capture_doctor(None)
            finally:
                pipeline_progress._installed_browser_apps = original_apps
                if old_home is None:
                    os.environ.pop("PAPER_CAPTURE_HOME", None)
                else:
                    os.environ["PAPER_CAPTURE_HOME"] = old_home
            self.assertFalse(report["ok"])
            joined = "\n".join(report["problems"])
            self.assertIn("native host manifest missing", joined)
            self.assertIn("bridge launcher missing", joined)
            self.assertIn("bridge host.mjs missing", joined)
            self.assertTrue(any("install-native-host.command" in f for f in report["fixes"]))

    def test_capture_doctor_passes_on_complete_install(self):
        if pipeline_progress.sys.platform != "darwin":
            self.skipTest("bridge checks are macOS-only")
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "capture-home"
            home.mkdir()
            repo_host = pipeline_progress.capture_extension_dir() / "bridge" / "host.mjs"
            (home / "host.mjs").write_text(repo_host.read_text())
            node = Path(tmp) / "node"
            node.write_text("#!/bin/sh\n")
            node.chmod(0o700)
            launcher = home / "run-paper-capture-host"
            launcher.write_text(f'#!/bin/sh\nexec "{node}" "{home / "host.mjs"}"\n')
            launcher.chmod(0o700)
            nm = Path(tmp) / "nm"
            nm.mkdir()
            (nm / f"{pipeline_progress.CAPTURE_HOST_NAME}.json").write_text(json.dumps({
                "name": pipeline_progress.CAPTURE_HOST_NAME,
                "path": str(launcher),
                "type": "stdio",
                "allowed_origins": [f"chrome-extension://{pipeline_progress.CAPTURE_EXTENSION_ID}/"],
            }))
            old_home = os.environ.get("PAPER_CAPTURE_HOME")
            os.environ["PAPER_CAPTURE_HOME"] = str(home)
            original_apps = pipeline_progress._installed_browser_apps
            pipeline_progress._installed_browser_apps = lambda: [("Google Chrome", "Google Chrome", nm)]
            try:
                report = pipeline_progress.capture_doctor(None)
            finally:
                pipeline_progress._installed_browser_apps = original_apps
                if old_home is None:
                    os.environ.pop("PAPER_CAPTURE_HOME", None)
                else:
                    os.environ["PAPER_CAPTURE_HOME"] = old_home
            self.assertTrue(report["ok"], report["problems"])

    def test_installer_writes_manifest_per_browser_and_finds_node_off_path(self):
        """Regression for Finder's bare PATH: node discovery must not rely on `command -v` alone."""
        installer = pipeline_progress.capture_host_installer()
        text = installer.read_text()
        self.assertIn("--quiet", text)
        for cand in ("/opt/homebrew/bin/node", "/usr/local/bin/node", ".nvm/versions/node"):
            self.assertIn(cand, text)
        for rel in ("BraveSoftware/Brave-Browser/NativeMessagingHosts", "Chromium/NativeMessagingHosts", "Microsoft Edge/NativeMessagingHosts", "Arc/User Data/NativeMessagingHosts"):
            self.assertIn(rel, text)
        self.assertIn("PING", text)
        install_skills = MODULE_PATH.parents[2] / "scripts" / "install-skills.sh"
        self.assertIn("install-native-host.command", install_skills.read_text())

    def test_capture_tool_is_not_required_for_14_done(self):
        """1.4 done is the Paper review file. Capture Tool skip is not a gate."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True, exist_ok=True)
            self.assertFalse(pipeline_progress.artifact_done(root, "1.4"))
            (root / "qa" / "paper-human-review.md").write_text("# signed\n")
            self.assertTrue(pipeline_progress.artifact_done(root, "1.4"))

    def test_resume_does_not_reset_progress(self):
        """start force-writes empty progress; resume must never do that."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            for sid in ("1.1", "1.2", "1.3", "1.4"):
                data["steps"][sid]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)

            opened = []
            original = pipeline_progress.open_live_board
            pipeline_progress.open_live_board = lambda dest: opened.append(dest) or True
            try:
                self.assertEqual(pipeline_progress.cmd_resume(root, "2.1", "session-2"), 0)
            finally:
                pipeline_progress.open_live_board = original

            self.assertEqual(opened, [], "resume must not reopen pipeline.html")
            after = pipeline_progress.load_progress(root)
            self.assertEqual(after["steps"]["1.4"]["status"], "done")
            self.assertEqual(after["controller"]["owner"], "session-2")

    def test_resume_refuses_unfinished_predecessors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            data["steps"]["1.1"]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            self.assertEqual(pipeline_progress.cmd_resume(root, "2.1", "session-2"), 2)

    def test_resume_refuses_when_there_is_no_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                pipeline_progress.cmd_resume(Path(tmp) / "demo", "2.1", "session-2"), 2
            )

    def test_handoff_prompt_is_emitted_at_the_checkpoints(self):
        """1.4 and 2.4 done must produce a copy-ready prompt and free the lease."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True, exist_ok=True)
            (root / "qa" / "paper-file.json").write_text(json.dumps({
                "fileId": "01M0GPEFVQ1A4G5E078T82CNDW",
                "url": "https://example.com/",
            }))
            data = pipeline_progress.empty_progress("demo")
            data["controller"] = {"owner": "session-1", "status": "active"}
            pipeline_progress.emit_handoff(root, data, "1.4")

            body = (root / "qa" / "handoff-2.0.md").read_text()
            self.assertIn("SESSION 2 of 3", body)
            self.assertIn("resume .", body)
            self.assertNotIn("pipeline-progress.py start", body)
            self.assertIn("01M0GPEFVQ1A4G5E078T82CNDW", body)
            self.assertIn("The only stop is 2.4", body)
            self.assertNotIn("controller", data)

            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(
                "<html><body><main><section id='hero'><h1>Home</h1></section></main></body></html>",
                encoding="utf-8",
            )
            pipeline_progress.emit_handoff(root, data, "2.4")
            body3 = (root / "qa" / "handoff-3.0.md").read_text()
            self.assertIn("SESSION 3 of 3", body3)
            self.assertIn("YOU ARE HERE", body3)
            self.assertIn("NEXT", body3)
            self.assertIn("NOT YET", body3)
            self.assertIn("3.1", body3)
            self.assertIn("fidelity freeze", body3)
            self.assertIn("font-size", body3)
            self.assertIn("index-polish.html", body3)
            self.assertIn("mandatory GSAP", body3)
            self.assertIn("inject-gsap-reveal.py", body3)
            self.assertIn("apply-hover-css.py", body3)
            self.assertIn("author-nav-drawer.py", body3)
            self.assertIn("author-faq.py", body3)
            self.assertIn("author-nav-dropdown.py", body3)
            self.assertFalse((root / "rebuild" / "index-polish.html").is_file())
            self.assertTrue((root / "qa" / "fidelity-freeze-24.json").is_file())

    def test_31_active_seeds_unpolished_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True, exist_ok=True)
            (root / "rebuild").mkdir()
            (root / "rebuild" / "index.html").write_text(
                "<html><body><main><section id='hero'><h1>Home</h1></section></main></body></html>",
                encoding="utf-8",
            )
            data = pipeline_progress.empty_progress("demo")
            for sid in ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4"):
                data["steps"][sid]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            self.assertFalse((root / "rebuild" / "index-polish.html").is_file())
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.1", "active", None), 0)
            polish = root / "rebuild" / "index-polish.html"
            self.assertTrue(polish.is_file())
            self.assertEqual(
                polish.read_text(encoding="utf-8"),
                (root / "rebuild" / "index.html").read_text(encoding="utf-8"),
            )
            board = (root / "pipeline.html").read_text(encoding="utf-8")
            self.assertIn("▶ 3.1", board)
            self.assertNotIn("NEXT  3.1", board)

    def test_32_active_writes_hover_css(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True, exist_ok=True)
            (root / "rebuild" / "css").mkdir(parents=True)
            (root / "rebuild" / "index.html").write_text(
                "<html><head><link rel=\"stylesheet\" href=\"css/tokens.css\" /></head>"
                "<body><main><section id='hero'><a href='#go'>Get Started Now</a>"
                "</section></main></body></html>",
                encoding="utf-8",
            )
            (root / "rebuild" / "css" / "tokens.css").write_text(
                ":root { --color-ink: #111111; }\n",
                encoding="utf-8",
            )
            (root / "qa" / "button-hover.json").write_text(
                json.dumps({
                    "ok": True,
                    "writer": "author-button-hover.mjs",
                    "applied": [{
                        "label": "Get Started Now",
                        "className": "btn-primary",
                        "declarations": {"background-color": "#111111"},
                    }],
                    "skipped": [],
                }),
                encoding="utf-8",
            )
            data = pipeline_progress.empty_progress("demo")
            for sid in ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4", "3.1"):
                data["steps"][sid]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.2", "active", None), 0)
            receipt = json.loads(
                (root / "qa" / "button-hover-css.json").read_text(encoding="utf-8")
            )
            self.assertTrue(pipeline_progress.button_hover_css_done(root))
            self.assertEqual(receipt["writer"], "apply-hover-css.py")
            polish = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertIn("css/hover.css", polish)
            css = (root / "rebuild" / "css" / "hover.css").read_text(encoding="utf-8")
            self.assertIn(".btn-primary:hover", css)
            self.assertTrue((root / "qa" / "nav-drawer.json").is_file())
            self.assertTrue(pipeline_progress.nav_drawer_done(root))
            self.assertTrue((root / "qa" / "faq.json").is_file())
            self.assertTrue(pipeline_progress.faq_done(root))
            self.assertTrue((root / "qa" / "nav-dropdown.json").is_file())
            self.assertTrue(pipeline_progress.nav_dropdown_done(root))

    def test_no_handoff_on_ordinary_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True, exist_ok=True)
            self.assertIsNone(
                pipeline_progress.emit_handoff(root, pipeline_progress.empty_progress("demo"), "2.3")
            )

    def _homepage_ready(self, root: Path) -> dict:
        data = pipeline_progress.empty_progress("demo")
        for sid in pipeline_progress.REQUIRED_STEPS:
            if sid != "3.4":
                data["steps"][sid]["status"] = "done"
        data["steps"]["3.4"]["status"] = "active"
        data["current"] = "3.4"
        (root / "rebuild").mkdir(exist_ok=True)
        (root / "rebuild" / "index-polish.html").write_text("<html></html>")
        (root / "qa").mkdir(exist_ok=True)
        pipeline_progress.save_progress(root, data, force=True)
        return data

    def test_34_done_requires_phase4_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._homepage_ready(root)
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 2)
            (root / "qa" / "phase-4-skipped.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 0)
            self.assertIn('data-run="done"', (root / "pipeline.html").read_text())
            self.assertFalse((root / "qa").exists())

    def test_adopt_34_requires_phase4_and_does_not_ask(self):
        import source_fidelity

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            src = Path(tmp) / "export"
            src.mkdir()
            (src / "index.html").write_text(
                '<!DOCTYPE html><html data-wf-site="x"><body><section class="w-section">Hi</section></body></html>',
                encoding="utf-8",
            )
            run_config.intake(root, source=str(src), checkpoints="human", speed="fast")
            self.assertEqual(run_config.load(root)["humanStops"], ["4.4"])
            self._homepage_ready(root)
            (root / "rebuild" / "index-polish.html").unlink()
            source_fidelity.snapshot(root)
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 0)
            self.assertTrue((root / "qa" / "phase-4-opted.json").is_file())
            self.assertTrue((root / "qa").is_dir())
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.1", "active", None), 0)
            self.assertEqual(pipeline_progress.main(["skip", str(root), "--step", "4.2", "--reason", "no"]), 2)

    def test_adopt_34_refuses_a_skip_receipt(self):
        import source_fidelity

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            src = Path(tmp) / "export"
            src.mkdir()
            (src / "index.html").write_text(
                '<!DOCTYPE html><html data-wf-site="x"><body><section class="w-section">Hi</section></body></html>',
                encoding="utf-8",
            )
            run_config.intake(root, source=str(src), checkpoints="human", speed="full")
            self._homepage_ready(root)
            (root / "rebuild" / "index-polish.html").unlink()
            source_fidelity.snapshot(root)
            (root / "qa" / "phase-4-skipped.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 2)

    def test_34_opted_does_not_tidy_and_opens_41(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._homepage_ready(root)
            (root / "qa" / "phase-4-opted.json").write_text("{}\n")
            (root / "source-site").mkdir()
            (root / "qa" / "phase-4-sitemap.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 0)
            self.assertTrue((root / "qa").is_dir())
            self.assertTrue((root / "source-site").is_dir())
            self.assertFalse(pipeline_progress.run_is_complete(pipeline_progress.load_progress(root), root))
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.1", "active", None), 0)

    def test_4x_cannot_activate_before_34_or_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = pipeline_progress.empty_progress("demo")
            pipeline_progress.save_progress(root, data, force=True)
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.1", "active", None), 2)
            self._homepage_ready(root)
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.1", "active", None), 2)
            (root / "qa" / "phase-4-opted.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 0)
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.1", "active", None), 0)

    def test_skip_allowed_only_on_phase4(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"), force=True)
            self.assertEqual(pipeline_progress.main(["skip", str(root), "--step", "1.2"]), 2)
            self._homepage_ready(root)
            (root / "qa" / "phase-4-opted.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 0)
            self.assertEqual(pipeline_progress.main(["skip", str(root), "--step", "4.1", "--reason", "empty sitemap"]), 0)
            self.assertEqual(pipeline_progress.load_progress(root)["steps"]["4.1"]["status"], "skipped")

    def _phase4_ready(self, root: Path) -> dict:
        self._homepage_ready(root)
        (root / "qa" / "phase-4-opted.json").write_text("{}\n")
        self.assertEqual(pipeline_progress.cmd_mark(root, "3.4", "done", None), 0)
        data = pipeline_progress.load_progress(root)
        for sid in ("4.1", "4.2", "4.3"):
            data["steps"][sid]["status"] = "done"
        data["steps"]["4.4"]["status"] = "active"
        data["current"] = "4.4"
        (root / "qa" / "phase-4-review.md").write_text("reviewed\n")
        pipeline_progress.save_progress(root, data, force=True)
        return data

    def test_44_done_requires_phase5_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._phase4_ready(root)
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.4", "done", None), 2)
            (root / "qa" / "phase-5-skipped.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.4", "done", None), 0)
            self.assertIn('data-run="done"', (root / "pipeline.html").read_text())
            self.assertFalse((root / "qa").exists())

    def test_44_opted_does_not_tidy_and_opens_51(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._phase4_ready(root)
            (root / "qa" / "phase-5-opted.json").write_text("{}\n")
            (root / "source-site").mkdir(exist_ok=True)
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.4", "done", None), 0)
            self.assertTrue((root / "qa").is_dir())
            self.assertTrue((root / "source-site").is_dir())
            self.assertFalse(pipeline_progress.run_is_complete(pipeline_progress.load_progress(root), root))
            self.assertTrue((root / "qa" / "handoff-5.0.md").is_file())
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.1", "active", None), 0)
            self.assertIn("16 / 22", (root / "pipeline.html").read_text())

    def test_5x_cannot_activate_before_44_or_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = pipeline_progress.empty_progress("demo")
            pipeline_progress.save_progress(root, data, force=True)
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.1", "active", None), 2)
            self._phase4_ready(root)
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.1", "active", None), 2)
            (root / "qa" / "phase-5-opted.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.4", "done", None), 0)
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.1", "active", None), 0)

    def test_skip_allowed_on_phase5_after_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._phase4_ready(root)
            (root / "qa" / "phase-5-opted.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.4", "done", None), 0)
            self.assertEqual(
                pipeline_progress.main(["skip", str(root), "--step", "5.1", "--reason", "one page"]),
                0,
            )
            self.assertEqual(pipeline_progress.load_progress(root)["steps"]["5.1"]["status"], "skipped")

    def _phase5_ready(self, root: Path) -> dict:
        self._phase4_ready(root)
        (root / "qa" / "phase-5-opted.json").write_text("{}\n")
        self.assertEqual(pipeline_progress.cmd_mark(root, "4.4", "done", None), 0)
        data = pipeline_progress.load_progress(root)
        for sid in ("5.1", "5.2", "5.3", "5.4", "5.5"):
            data["steps"][sid]["status"] = "done"
        data["steps"]["5.6"]["status"] = "active"
        data["current"] = "5.6"
        pipeline_progress.save_progress(root, data, force=True)
        return data

    def test_56_done_requires_review_then_tidies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._phase5_ready(root)
            (root / "astro").mkdir(exist_ok=True)
            (root / "astro" / "package.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.6", "done", None), 2)
            (root / "qa" / "phase-5-review.md").write_text("reviewed\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.6", "done", None), 0)
            self.assertIn('data-run="done"', (root / "pipeline.html").read_text())
            self.assertFalse((root / "qa").exists())
            self.assertTrue((root / "astro" / "package.json").is_file())
            self.assertFalse((root / "qa" / "handoff-6.0.md").exists())

    def test_51_done_needs_all_three_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._phase4_ready(root)
            (root / "qa" / "phase-5-opted.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "4.4", "done", None), 0)
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.1", "active", None), 0)
            (root / "qa" / "phase-5-scaffold.json").write_text("{}\n")
            (root / "qa" / "phase-5-components.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.1", "done", None), 2)
            (root / "qa" / "phase-5-home.json").write_text("{}\n")
            self.assertEqual(pipeline_progress.cmd_mark(root, "5.1", "done", None), 0)
            self.assertNotIn("6.1", pipeline_progress.STEP_IDS)
            self.assertEqual(pipeline_progress.SESSION_OF["5.6"], 5)
            self.assertNotIn("5.6", pipeline_progress.HANDOFF_AT)

    def test_32_done_requires_companion_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qa = root / "qa"
            (qa / "polish-passes").mkdir(parents=True)
            (qa / "polish-passes" / "c3-3.3-emil-design-eng.json").write_text("{}")
            (qa / "gsap-reveal-qa.json").write_text(json.dumps({"ok": True}))
            for name, writer in (
                ("button-hover-css.json", "apply-hover-css.py"),
                ("nav-drawer.json", "author-nav-drawer.py"),
                ("faq.json", "author-faq.py"),
                ("nav-dropdown.json", "author-nav-dropdown.py"),
            ):
                (qa / name).write_text(
                    json.dumps({"ok": True, "writer": writer, "applied": [], "skipped": []})
                )
            self.assertFalse(pipeline_progress.companion_receipts_done(root))
            self.assertFalse(pipeline_progress.artifact_done(root, "3.2"))
            (qa / "web-design-guidelines.md").write_text("- applied: focus ring\n")
            (qa / "find-animation-opportunities.md").write_text("- skipped: hero parallax — not recorded\n")
            (qa / "apple-design.md").write_text("   \n")
            self.assertFalse(pipeline_progress.artifact_done(root, "3.2"))
            (qa / "apple-design.md").write_text("- n-a: springs Paper never had\n")
            self.assertTrue(pipeline_progress.companion_receipts_done(root))
            self.assertTrue(pipeline_progress.artifact_done(root, "3.2"))


if __name__ == "__main__":
    unittest.main()


class RelayTests(unittest.TestCase):
    """A relay is a change of agent at a receipt boundary — never a human stop (Pitfall #218 #219 #220)."""

    def _run(self, tmp: str, current: str = "2.3", owner: str = "session-2") -> Path:
        root = Path(tmp) / "demo"
        data = pipeline_progress.empty_progress("demo")
        for sid in ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2"):
            data["steps"][sid]["status"] = "done"
            data["steps"][sid]["ended"] = "2026-09-20T10:00:00-06:00"
        data["steps"][current]["status"] = "active"
        data["steps"][current]["started"] = "2026-09-20T10:05:00-06:00"
        data["current"] = current
        data["controller"] = {"owner": owner, "status": "active", "claimedAt": "2026-09-20T09:00:00-06:00"}
        pipeline_progress.save_progress(root, data, force=True)
        (root / "qa" / "paper-file.json").write_text(json.dumps({"fileId": "paper-1", "url": "https://example.com"}))
        return root

    def _patch(self, probe: dict, orca_script: dict):
        calls: list[list[str]] = []

        def run(argv, timeout_s=60):
            calls.append(argv)
            key = " ".join(argv[1:3])
            code, body = orca_script.get(key, (1, {}))
            return code, json.dumps(body)

        originals = (pipeline_progress._probe_report, pipeline_progress._orca_run, pipeline_progress._budget_snapshot)
        pipeline_progress._probe_report = lambda root, fresh=False: probe
        pipeline_progress._orca_run = run
        pipeline_progress._budget_snapshot = lambda root: {"usedPct": 52.0, "window": 200000, "source": "transcript", "state": "armed"}
        self.addCleanup(lambda: setattr(pipeline_progress, "_probe_report", originals[0]))
        self.addCleanup(lambda: setattr(pipeline_progress, "_orca_run", originals[1]))
        self.addCleanup(lambda: setattr(pipeline_progress, "_budget_snapshot", originals[2]))
        return calls

    ORCA_PROBE = {"harness": "codex", "agent": "codex", "agentCommand": "codex",
                  "orca": {"cli": "/bin/orca", "reachable": True, "worktree": "repo::/wt"},
                  "adapters": {"waves": "orca", "relay": "orca-terminal"}}
    NO_ORCA = {"harness": "generic", "agent": None, "agentCommand": None, "orca": {"present": False},
               "adapters": {"waves": "serial", "relay": "print-prompt"}}

    def test_relay_without_orca_prints_the_prompt_and_frees_the_lease_for_the_successor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._run(tmp)
            calls = self._patch(self.NO_ORCA, {})
            self.assertEqual(pipeline_progress.cmd_relay(root, "session-2"), 0)
            self.assertEqual(calls, [])
            prompt = (root / "qa" / "handoff-2.3.relay1.md").read_text()
            for needle in ("RELAY", "NOT A HUMAN CHECKPOINT", "--at 2.3 --owner session-2b", "resume", "52.0%", "paper-1", "Do not fire a CTA"):
                self.assertIn(needle, prompt)
            self.assertNotIn("`start`\n", prompt)
            after = pipeline_progress.load_progress(root)
            self.assertNotIn("controller", after)
            self.assertFalse(pipeline_progress.controller_lease_path(root).is_file())
            self.assertEqual(after["relays"][0]["to"], "session-2b")
            self.assertEqual(after["relays"][0]["adapter"], "print-prompt")
            self.assertEqual(after["steps"]["2.3"]["status"], "active", "the step stays active; the successor continues it")
            # The successor claims the lease with resume, at the same step.
            self.assertEqual(pipeline_progress.cmd_resume(root, "2.3", "session-2b"), 0)
            self.assertEqual(pipeline_progress.load_progress(root)["controller"]["owner"], "session-2b")

    def test_relay_via_orca_opens_a_terminal_for_the_same_agent_and_ends_the_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._run(tmp)
            calls = self._patch(self.ORCA_PROBE, {
                "terminal create": (0, {"result": {"terminal": {"handle": "term_new"}}}),
                "terminal wait": (0, {"result": {"wait": {"satisfied": True}}}),
                "terminal send": (0, {"result": {"accepted": True, "stages": ["input_accepted", "turn_started"]}}),
            })
            self.assertEqual(pipeline_progress.cmd_relay(root, "session-2"), 0)
            create = [c for c in calls if c[1:3] == ["terminal", "create"]][0]
            self.assertEqual(create[create.index("--command") + 1], "codex", "same source as the orchestrator, never a hardcoded claude")
            self.assertEqual(create[create.index("--worktree") + 1], "id:repo::/wt")
            send = [c for c in calls if c[1:3] == ["terminal", "send"]][0]
            self.assertIn("--owner session-2b", send[send.index("--text") + 1])
            self.assertIn("--enter", send)
            after = pipeline_progress.load_progress(root)
            self.assertNotIn("controller", after)
            self.assertEqual(after["relays"][0]["terminal"], "term_new")
            self.assertTrue(after["relays"][0]["started"])

    def test_relay_takes_the_lease_back_when_the_terminal_never_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._run(tmp)
            self._patch(self.ORCA_PROBE, {
                "terminal create": (0, {"result": {"terminal": {"handle": "term_new"}}}),
                "terminal wait": (0, {"result": {"wait": {"satisfied": False}}}),
            })
            self.assertEqual(pipeline_progress.cmd_relay(root, "session-2"), 3)
            after = pipeline_progress.load_progress(root)
            self.assertEqual(after["controller"]["owner"], "session-2", "a run is never left ownerless")
            self.assertTrue(pipeline_progress.controller_lease_path(root).is_file())
            self.assertFalse(after["relays"][0]["started"])
            self.assertTrue((root / "qa" / "handoff-2.3.relay1.md").is_file())

    def test_relay_refuses_a_foreign_owner_a_human_checkpoint_and_a_wave_in_flight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._run(tmp)
            self._patch(self.NO_ORCA, {})
            self.assertEqual(pipeline_progress.cmd_relay(root, "session-3"), 2)
            wave_dir = root / "qa" / "agent-runs" / "r1" / "2.3"
            wave_dir.mkdir(parents=True)
            (wave_dir / "wave.json").write_text(json.dumps({"runId": "r1", "tasks": [{"id": "band-hero", "status": "running"}]}))
            self.assertEqual(pipeline_progress.cmd_relay(root, "session-2"), 2)
            self.assertEqual(pipeline_progress.cmd_relay(root, "session-2", force=True), 0)
        with tempfile.TemporaryDirectory() as tmp:
            root = self._run(tmp, current="2.4")
            self._patch(self.NO_ORCA, {})
            self.assertEqual(pipeline_progress.cmd_relay(root, "session-2"), 2, "2.4 yields to the human, it is not relayed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            self.assertEqual(pipeline_progress.cmd_relay(root, "session-2"), 2)

    def test_relay_owners_chain(self):
        self.assertEqual(pipeline_progress.next_relay_owner("session-2"), "session-2b")
        self.assertEqual(pipeline_progress.next_relay_owner("session-2b"), "session-2c")
        self.assertEqual(pipeline_progress.next_relay_owner("session-2z"), "session-2z-r1")
        self.assertEqual(pipeline_progress.next_relay_owner("session-2z-r1"), "session-2z-r2")

    def test_mark_prints_the_budget_line_and_keeps_a_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._run(tmp, current="2.1")
            self._patch(self.NO_ORCA, {})
            data = pipeline_progress.load_progress(root)
            data["steps"]["2.1"]["status"] = "pending"
            data["current"] = None
            pipeline_progress.save_progress(root, data)
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = pipeline_progress.cmd_mark(root, "2.1", "active", None, None, "session-2")
            self.assertEqual(code, 0)
            after = pipeline_progress.load_progress(root)
            self.assertEqual(after["budget"]["owner"], "session-2")
            self.assertGreater(after["budget"]["spendTokens"], 0)
            self.assertIn("budget:", buf.getvalue())



class TimingTests(unittest.TestCase):
    """Per-step durations + a run total that is the SUM of steps, never wall clock."""

    T = "2026-09-26T01:{:02d}:{:02d}-06:00".format

    def _timed(self, sid: str, start: tuple[int, int], end: tuple[int, int], data: dict, status: str = "done") -> None:
        data["steps"][sid].update(status=status, started=self.T(*start), ended=self.T(*end))

    def test_refresh_timing_sums_steps_not_wall_clock(self):
        data = pipeline_progress.empty_progress("demo")
        data["started"] = self.T(0, 0)
        self._timed("1.1", (0, 53), (0, 57), data)          # 4s
        self._timed("1.2", (1, 5), (4, 2), data)            # 2m 57s
        self._timed("1.3", (4, 10), (9, 10), data)          # 5m
        self._timed("1.4", (9, 20), (15, 20), data)         # 6m human
        # a long pause between sessions, then 2.1 — must not count
        data["steps"]["2.1"].update(status="done", started="2026-09-26T09:00:00-06:00", ended="2026-09-26T09:01:00-06:00")
        data["steps"]["2.2"].update(status="done", ended="2026-09-26T09:05:00-06:00")  # no started → untimed
        data["steps"]["2.3"].update(status="active", started="2026-09-26T09:05:10-06:00")

        timing = pipeline_progress.refresh_timing(data)

        self.assertEqual(data["steps"]["1.2"]["durationSeconds"], 177)
        self.assertNotIn("durationSeconds", data["steps"]["2.2"])
        self.assertEqual(timing["totalSeconds"], 4 + 177 + 300 + 360 + 60)
        self.assertEqual(timing["humanSeconds"], 360)
        self.assertEqual(timing["agentSeconds"], timing["totalSeconds"] - 360)
        self.assertEqual(timing["timedSteps"], 5)
        self.assertEqual(timing["untimedSteps"], 1)
        self.assertEqual(timing["phases"], {"1": 4 + 177 + 300 + 360, "2": 60})
        self.assertEqual(timing["lastEndedStep"], "2.2")
        self.assertEqual(timing["activeStep"], "2.3")
        self.assertEqual(timing["activeSince"], "2026-09-26T09:05:10-06:00")

    def test_fmt_duration_scales(self):
        f = pipeline_progress.fmt_duration
        self.assertEqual(f(None), "—")
        self.assertEqual(f(0), "0s")
        self.assertEqual(f(42), "42s")
        self.assertEqual(f(252), "4m 12s")
        self.assertEqual(f(3600 + 12 * 60 + 5), "1h 12m")

    def test_mark_done_backfills_started_from_the_tightest_lower_bound(self):
        """A step closed without `mark active` still lands in the total — flagged."""
        data = pipeline_progress.empty_progress("demo")
        data["started"] = self.T(0, 0)
        data["controller"] = {"owner": "s1", "status": "active", "claimedAt": self.T(0, 30)}
        self._timed("1.1", (0, 53), (0, 57), data)
        data["sessions"] = [{"kind": "start", "owner": "session-1", "at": "1.1", "startedAt": self.T(0, 0)}]

        pipeline_progress.close_step_timing(data, "1.2")
        row = data["steps"]["1.2"]

        self.assertEqual(row["started"], self.T(0, 57), "previous step's end is the tightest bound")
        self.assertTrue(row["startedInferred"])
        self.assertIsNotNone(pipeline_progress.parse_iso(row["ended"]))

        # a later session claim beats an older step end
        data["controller"]["claimedAt"] = "2026-09-26T09:00:00-06:00"
        pipeline_progress.close_step_timing(data, "1.3")
        self.assertEqual(data["steps"]["1.3"]["started"], "2026-09-26T09:00:00-06:00")

        # skipped is not work: no inference
        pipeline_progress.close_step_timing(data, "4.1", infer=False)
        self.assertNotIn("started", data["steps"]["4.1"])

    def test_mark_writes_duration_and_prints_the_timing_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"))
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            (root / "source-site").mkdir()

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_mark(root, "1.1", "active", None), 0)
            self.assertRegex(out.getvalue(), r"1\.1 started \d\d:\d\d:\d\d")

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_mark(root, "1.1", "done", None), 0)
            text = out.getvalue()
            self.assertRegex(text, r"1\.1 finished \d\d \w{3} \d\d:\d\d   took \d+s")
            self.assertIn("run total", text)
            self.assertIn("1 step timed", text)

            data = pipeline_progress.load_progress(root)
            row = data["steps"]["1.1"]
            self.assertIn("started", row)
            self.assertIn("ended", row)
            self.assertIsInstance(row["durationSeconds"], int)
            self.assertNotIn("startedInferred", row)
            self.assertEqual(data["timing"]["timedSteps"], 1)
            self.assertEqual(data["timing"]["totalSeconds"], row["durationSeconds"])
            self.assertEqual(data["timing"]["lastEndedStep"], "1.1")

    def test_mark_done_without_active_is_inferred_and_flagged_in_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = pipeline_progress.empty_progress("demo")
            data["started"] = self.T(0, 0)
            data["steps"]["1.1"].update(status="done", started=self.T(0, 53), ended=self.T(0, 57))
            pipeline_progress.save_progress(root, data)
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            original = pipeline_progress.artifact_done
            pipeline_progress.artifact_done = lambda r, sid: True
            self.addCleanup(lambda: setattr(pipeline_progress, "artifact_done", original))

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_mark(root, "1.2", "done", None), 0)
            self.assertIn("start inferred", out.getvalue())
            row = pipeline_progress.load_progress(root)["steps"]["1.2"]
            self.assertEqual(row["started"], self.T(0, 57))
            self.assertTrue(row["startedInferred"])
            self.assertIn("durationSeconds", row)

    def test_board_shows_finished_stamp_duration_phase_sum_and_run_total(self):
        data = pipeline_progress.empty_progress("demo")
        data["started"] = self.T(0, 0)
        self._timed("1.1", (0, 53), (0, 57), data)
        self._timed("1.2", (1, 5), (4, 2), data)
        data["steps"]["1.3"].update(status="active", started=self.T(4, 10))

        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)

        self.assertIn('<span class="row-time" data-step-time="1.1">4s</span>', html)
        self.assertIn('<span class="row-time" data-step-time="1.2">2m 57s</span>', html)
        self.assertIn('<span class="row-time" data-step-time="1.3">running</span>', html)
        self.assertIn('<span class="row-time" data-step-time="1.4"></span>', html)
        self.assertIn('data-step-time="1.2">Finished 26 Sep 01:04 · took 2m 57s</span>', html)
        self.assertIn('data-step-time="1.3">Started 26 Sep 01:04 · running</span>', html)
        self.assertIn('<span class="card-time" data-phase-time="1">3m 01s</span>', html)
        self.assertIn('<span class="card-time" data-phase-time="2"></span>', html)
        self.assertRegex(html, r'data-pipeline-duration[^>]*>total 3m 01s</span>')

        # inferred starts are marked so the board never over-claims
        data["steps"]["1.3"].update(status="done", ended=self.T(9, 10), startedInferred=True)
        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)
        self.assertIn('data-step-time="1.3">5m 00s*</span>', html)
        self.assertIn("took 5m 00s (start inferred)", html)

    def test_board_hides_timing_on_a_fresh_run(self):
        data = pipeline_progress.empty_progress("demo")
        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)
        self.assertRegex(html, r'data-pipeline-duration[^>]*></span>')
        self.assertEqual(len(re.findall(r'data-step-time="[^"]+">[^<]', html)), 0)
        template = pipeline_progress.live_template().read_text()
        self.assertEqual(len(re.findall(r'data-step-time="', template)), 2 * len(pipeline_progress.STEP_IDS))
        self.assertEqual(re.findall(r'data-phase-time="(\d)"', template), ["1", "2", "3", "4", "5"])
        self.assertIn(".row-time:empty { display: none; }", template)

    def test_start_and_resume_log_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            original = pipeline_progress.open_live_board
            pipeline_progress.open_live_board = lambda dest: True
            try:
                self.assertEqual(pipeline_progress.cmd_start(root), 0)
            finally:
                pipeline_progress.open_live_board = original
            data = pipeline_progress.load_progress(root)
            self.assertEqual([s["kind"] for s in data["sessions"]], ["start"])
            self.assertEqual(data["sessions"][0]["owner"], "session-1")
            self.assertEqual(data["timing"]["totalSeconds"], 0)

            for sid in ("1.1", "1.2", "1.3", "1.4"):
                data["steps"][sid].update(status="done", started=self.T(0, 0), ended=self.T(1, 0))
            pipeline_progress.save_progress(root, data)

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_resume(root, "2.1", "session-2"), 0)
            data = pipeline_progress.load_progress(root)
            self.assertEqual([s["kind"] for s in data["sessions"]], ["start", "resume"])
            self.assertEqual(data["sessions"][1]["owner"], "session-2")
            self.assertEqual(data["sessions"][1]["at"], "2.1")
            self.assertIn("run total 4m 00s", out.getvalue())
            self.assertIn("mark --step 2.1 --status active before working", out.getvalue())

    def test_resume_detects_the_step_when_at_is_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            for sid in ("1.1", "1.2", "1.3", "1.4"):
                data["steps"][sid].update(status="done", started=self.T(0, 0), ended=self.T(1, 0))
            pipeline_progress.save_progress(root, data, force=True)

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_resume(root, None, "session-2"), 0)
            text = out.getvalue()
            self.assertIn("detected 2.1 Design System", text)
            self.assertIn("next 2.1", text)
            self.assertEqual(pipeline_progress.load_progress(root)["sessions"][-1]["at"], "2.1")

            # an active step wins over the first pending one, and its clock keeps running
            data = pipeline_progress.load_progress(root)
            data["steps"]["2.1"].update(status="active", started=self.T(5, 0))
            data["current"] = "2.1"
            pipeline_progress.save_progress(root, data)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_resume(root, None, "session-2"), 0)
            self.assertIn("detected 2.1", out.getvalue())
            self.assertIn("2.1 is still active since 26 Sep 01:05", out.getvalue())

    def test_resume_refuses_when_nothing_is_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            for sid in pipeline_progress.REQUIRED_STEPS:
                data["steps"][sid]["status"] = "done"
            pipeline_progress.save_progress(root, data, force=True)
            (root / "qa" / "phase-4-skipped.json").write_text("{}")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(pipeline_progress.cmd_resume(root, None, "session-3"), 2)
            self.assertIn("nothing left to resume", err.getvalue())

    def test_timing_command_prints_table_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            self._timed("1.1", (0, 53), (0, 57), data)
            self._timed("1.2", (1, 5), (4, 2), data)
            data["steps"]["1.3"].update(status="done", ended=self.T(9, 0), started=self.T(4, 2), startedInferred=True)
            data["sessions"] = [{"kind": "start", "owner": "session-1", "at": "1.1", "startedAt": self.T(0, 0)}]
            pipeline_progress.save_progress(root, data, force=True)

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_timing(root), 0)
            text = out.getvalue()
            self.assertRegex(text, r"1\.2\s+done\s+26 Sep 01:01\s+26 Sep 01:04\s+2m 57s")
            self.assertRegex(text, r"1\.3\s+done.*4m 58s\*")
            self.assertIn("1.4   pending", text)
            self.assertIn("phase 1   7m 59s", text)
            self.assertIn("run total 7m 59s", text)
            self.assertIn("* start inferred", text)
            self.assertIn("sessions", text)
            self.assertIn("session-1 at 1.1", text)

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_timing(root, as_json=True), 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["timing"]["totalSeconds"], 4 + 177 + 298)
            self.assertEqual(payload["steps"][1]["durationSeconds"], 177)
            self.assertTrue(payload["steps"][2]["startedInferred"])
            self.assertEqual(len(payload["sessions"]), 1)

    def test_timing_command_refuses_without_a_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(pipeline_progress.cmd_timing(Path(tmp) / "demo"), 2)
            self.assertIn("no run here", err.getvalue())

    def test_sync_closes_steps_with_inferred_starts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True)
            data = pipeline_progress.empty_progress("demo")
            data["started"] = self.T(0, 0)
            pipeline_progress.save_progress(root, data, force=True)
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            (root / "source-site").mkdir()
            self.assertTrue(pipeline_progress.artifact_done(root, "1.1"))

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_sync(root), 0)
            row = pipeline_progress.load_progress(root)["steps"]["1.1"]
            self.assertEqual(row["status"], "done")
            self.assertTrue(row.get("startedInferred"))
            self.assertIn("durationSeconds", row)

    def test_new_session_can_resume_after_a_checkpoint_releases_the_lease(self):
        """1.4 done releases the lease ON DISK; session 2 resumes without --at and inherits the run total."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True)
            data = pipeline_progress.empty_progress("demo")
            data["started"] = self.T(0, 0)
            for sid in ("1.1", "1.2", "1.3"):
                data["steps"][sid].update(status="done", started=self.T(0, 0), ended=self.T(5, 0))
            data["steps"]["1.4"].update(status="active", started=self.T(6, 0))
            data["controller"] = {"owner": "session-1", "status": "active", "claimedAt": self.T(0, 0)}
            pipeline_progress.save_progress(root, data, force=True)
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            (root / "qa" / "paper-human-review.md").write_text("# signed\n")
            (root / "qa" / "paper-file.json").write_text(json.dumps({"fileId": "F1", "url": "https://example.com/"}))

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pipeline_progress.cmd_mark(root, "1.4", "done", None, None, "session-1"), 0)
            after = pipeline_progress.load_progress(root)
            self.assertNotIn("controller", after, "lease release must be persisted, not just in memory")
            self.assertFalse(pipeline_progress.controller_lease_path(root).exists())
            self.assertEqual(after["timing"]["timedSteps"], 4)
            self.assertGreaterEqual(after["steps"]["1.4"]["durationSeconds"], 0)

            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(pipeline_progress.cmd_resume(root, None, "session-2"), 0, err.getvalue())
            text = out.getvalue()
            self.assertIn("detected 2.1", text)
            self.assertIn("run total", text)
            self.assertIn("last finished 1.4", text)
            resumed = pipeline_progress.load_progress(root)
            self.assertEqual(resumed["controller"]["owner"], "session-2")
            self.assertEqual(resumed["sessions"][-1], {**resumed["sessions"][-1], "kind": "resume", "owner": "session-2", "at": "2.1"})
            self.assertEqual(resumed["timing"]["totalSeconds"], after["timing"]["totalSeconds"], "resume adds no time — only marks do")


class AgentTrackingTests(unittest.TestCase):
    """Every session records its agent + model, and each step carries the one that ran it."""

    T = "2026-09-26T01:{:02d}:{:02d}-06:00".format

    def test_resume_records_agent_and_model_on_the_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"), force=True)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    pipeline_progress.cmd_resume(
                        root, "1.1", "session-1", "opencode", "deepseek-v4.1-flash"
                    ),
                    0,
                )
            entry = pipeline_progress.load_progress(root)["sessions"][-1]
            self.assertEqual(entry["agent"], "opencode")
            self.assertEqual(entry["model"], "deepseek-v4.1-flash")

    def test_mark_stamps_the_step_with_the_agent_that_ran_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"), force=True)
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    pipeline_progress.cmd_mark(
                        root, "1.1", "active", None, None, "session-1", "claude-code", "claude-fable-5.1"
                    ),
                    0,
                )
            row = pipeline_progress.load_progress(root)["steps"]["1.1"]
            self.assertEqual(row["agent"], "claude-code")
            self.assertEqual(row["model"], "claude-fable-5.1")

    def test_mark_inherits_the_session_agent_when_no_flag_is_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            (root / "qa").mkdir(parents=True)
            pipeline_progress.save_progress(root, pipeline_progress.empty_progress("demo"), force=True)
            run_config.intake(root, source="none", checkpoints="human", speed="full")
            with contextlib.redirect_stdout(io.StringIO()):
                pipeline_progress.cmd_resume(root, "1.1", "session-1", "opencode", "gpt-5.9")
                self.assertEqual(pipeline_progress.cmd_mark(root, "1.1", "active", None, None, "session-1"), 0)
            row = pipeline_progress.load_progress(root)["steps"]["1.1"]
            self.assertEqual(row["agent"], "opencode")
            self.assertEqual(row["model"], "gpt-5.9")

    def test_a_done_mark_never_overwrites_the_active_attribution(self):
        data = pipeline_progress.empty_progress("demo")
        row = data["steps"]["1.1"]
        pipeline_progress.stamp_step_who(row, "opencode", "m1", overwrite=True)
        pipeline_progress.stamp_step_who(row, "claude-code", "m2", overwrite=False)
        self.assertEqual((row["agent"], row["model"]), ("opencode", "m1"))

    def test_phase_agent_copy_reads_uniform_and_mixed(self):
        f = pipeline_progress.phase_agent_copy
        self.assertEqual(f(None, None), "")
        self.assertEqual(f(None, 300), "5m 00s")
        self.assertEqual(
            f([{"agent": "opencode", "model": "m1", "seconds": 300}], 300),
            "5m 00s · opencode · m1",
        )
        self.assertEqual(
            f([{"agent": None, "model": None, "seconds": 60}], 60),
            "1m 00s",
        )
        self.assertEqual(
            f(
                [
                    {"agent": "claude-code", "model": None, "seconds": 3600},
                    {"agent": "opencode", "model": None, "seconds": 300},
                ],
                3900,
            ),
            "1h 05m · claude-code (1h 00m) + opencode (5m 00s)",
        )

    def test_phase_agents_group_steps_by_who_ran_them(self):
        data = pipeline_progress.empty_progress("demo")
        data["steps"]["2.1"].update(
            status="done", started=self.T(0, 0), ended=self.T(0, 30),
            agent="opencode", model="m1",
        )
        data["steps"]["2.2"].update(
            status="done", started=self.T(1, 0), ended=self.T(3, 0),
            agent="claude-code", model="m2",
        )
        data["steps"]["2.3"].update(
            status="done", started=self.T(3, 0), ended=self.T(3, 30),
            agent="opencode", model="m1",
        )
        timing = pipeline_progress.refresh_timing(data)
        phase = timing["phaseAgents"]["2"]
        self.assertEqual(len(phase), 2)
        self.assertEqual(phase[0]["agent"], "claude-code")   # longest first
        self.assertEqual(phase[0]["seconds"], 120)
        self.assertEqual(sorted(phase[1]["steps"]), ["2.1", "2.3"])
        self.assertEqual(phase[1]["seconds"], 60)

    def test_board_renders_hud_agent_and_phase_agent_labels(self):
        data = pipeline_progress.empty_progress("demo")
        data["started"] = self.T(0, 0)
        data["sessions"] = [{
            "kind": "resume", "owner": "session-2", "at": "2.1", "startedAt": self.T(5, 0),
            "agent": "opencode", "model": "deepseek-v4.1-flash",
        }]
        data["steps"]["1.1"].update(
            status="done", started=self.T(0, 53), ended=self.T(0, 57),
            agent="claude-code", model="claude-fable-5.1",
        )
        html = pipeline_progress.stamp_html(pipeline_progress.live_template().read_text(), data)
        self.assertIn(
            '<span class="hud-agent" data-pipeline-agent title="Agent + model recorded for the current session">'
            'opencode · deepseek-v4.1-flash</span>',
            html,
        )
        self.assertIn('<p class="card-agents" data-phase-agents="1">4s · claude-code · claude-fable-5.1</p>', html)
        self.assertIn('<p class="card-agents" data-phase-agents="2"></p>', html)

    def test_timing_table_names_the_agent_per_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo"
            data = pipeline_progress.empty_progress("demo")
            data["steps"]["1.1"].update(
                status="done", started=self.T(0, 0), ended=self.T(1, 0),
                agent="opencode", model="deepseek-v4.1-flash",
            )
            pipeline_progress.save_progress(root, data, force=True)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(pipeline_progress.cmd_timing(root), 0)
            text = out.getvalue()
            self.assertIn("opencode · deepseek-v4.1-flash", text)
            self.assertIn("phase 1   1m 00s · opencode · deepseek-v4.1-flash", text)
