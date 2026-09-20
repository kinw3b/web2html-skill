#!/usr/bin/env python3
"""2.20.1 — polish report, verify gate, and 3.2 companion receipts (Pitfall #215)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent

SHIP = (
    "<!doctype html><html><head><title>Test</title></head><body>"
    "<header><nav aria-label='Primary'><a href='#main-content'>Home</a></nav></header>"
    "<main id='main-content'>"
    "<section class='hero' aria-labelledby='hero-title'><h1 id='hero-title'>Hero</h1></section>"
    "<section id='features' aria-labelledby='features-title'>"
    "<h2 id='features-title'>Features</h2>"
    "<article class='card'><h3>One</h3><p>Card one body.</p></article>"
    "<article class='card'><h3>Two</h3><p>Card two body.</p></article>"
    "</section></main>"
    "<footer><a href='#features'>Features</a></footer>"
    "</body></html>"
)


def _receipt(pass_id: str, skill: str) -> dict:
    return {
        "pass": pass_id,
        "skill": skill,
        "status": "applied",
        "ended_at": "2026-08-16T02:00:00Z",
        "applied": [
            {
                "file": "rebuild/index-polish.html",
                "finding": f"{skill} contrast fix",
                "why": f"{skill} raised muted text to --text",
            }
        ],
        "skipped": [{"finding": "fidelity lock", "reason": "Paper geometry"}],
        "files_changed": [{"path": "rebuild/index-polish.html", "kind": "modified"}],
        "notes": "test",
    }


def _project(root: Path) -> None:
    (root / "rebuild").mkdir()
    (root / "qa" / "polish-passes").mkdir(parents=True)
    (root / "rebuild" / "index.html").write_text(SHIP, encoding="utf-8")
    subprocess.check_call(
        [sys.executable, str(_SCRIPTS / "seed_index_polish.py"), str(root)]
    )
    for pid, skill, name in (
        ("3.1", "impeccable", "c3-3.1-impeccable.json"),
        ("3.2", "design-taste-frontend", "c3-3.2-design-taste-frontend.json"),
        ("3.3", "emil-design-eng", "c3-3.3-emil-design-eng.json"),
    ):
        (root / "qa" / "polish-passes" / name).write_text(
            json.dumps(_receipt(pid, skill)), encoding="utf-8"
        )
    (root / "qa" / "button-hover.json").write_text(
        json.dumps({
            "ok": True,
            "writer": "author-button-hover.mjs",
            "applied": [],
            "skipped": [{"label": "X", "reason": "no source CSS :hover paint"}],
        }),
        encoding="utf-8",
    )
    (root / "qa" / "button-hover-css.json").write_text(
        json.dumps({
            "ok": True,
            "writer": "apply-hover-css.py",
            "applied": [{"className": "btn-primary", "label": "Primary CTA"}],
            "skipped": [{"finding": "button hover", "reason": "1.3 found no source CSS :hover paint on pulled buttons"}],
            "files": ["rebuild/css/hover.css", "rebuild/index-polish.html"],
            "linked": True,
        }),
        encoding="utf-8",
    )
    (root / "qa" / "nav-drawer.json").write_text(
        json.dumps({
            "ok": True,
            "writer": "author-nav-drawer.py",
            "applied": [],
            "skipped": [{
                "finding": "burger open drawer",
                "reason": "no hamburger painted on index-polish.html",
            }],
            "painted": False,
        }),
        encoding="utf-8",
    )
    (root / "qa" / "faq.json").write_text(
        json.dumps({
            "ok": True,
            "writer": "author-faq.py",
            "applied": [],
            "skipped": [{
                "finding": "FAQ accordion",
                "reason": "No painted FAQ rows on index-polish.html. Do not invent a FAQ section.",
            }],
            "painted": False,
        }),
        encoding="utf-8",
    )
    (root / "qa" / "nav-dropdown.json").write_text(
        json.dumps({
            "ok": True,
            "writer": "author-nav-dropdown.py",
            "applied": [],
            "skipped": [{
                "finding": "nav dropdown",
                "reason": "No painted dropdown trigger and no scrape submenu matching a polish nav label. Do not invent a menu.",
            }],
            "painted": False,
        }),
        encoding="utf-8",
    )
    for name in ("web-design-guidelines", "find-animation-opportunities", "apple-design"):
        (root / "qa" / f"{name}.md").write_text(
            f"# {name} — 3.2 receipt\n\n"
            "- applied: :focus-visible on existing controls\n"
            "- skipped: new drawer — fidelity lock (Pitfall #196)\n"
            "- n-a: virtualization\n",
            encoding="utf-8",
        )


def _run(script: str, *args: str) -> int:
    return subprocess.call([sys.executable, str(_SCRIPTS / script), *args])


class PolishReviewTest(unittest.TestCase):
    def test_report_puts_hover_on_emil_and_names_companions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _project(root)
            self.assertEqual(_run("inject-gsap-reveal.py", str(root / "rebuild" / "index-polish.html")), 0)
            self.assertEqual(_run("render-polish-report.py", str(root)), 0)
            ship = (root / "rebuild" / "polish-report.html").read_text(encoding="utf-8")
            emil_at = ship.index("emil-design-eng")
            # hover / drawer rows belong to Emil (C/3.3), not the taste card before it
            self.assertNotIn("apply-hover-css.py", ship[:emil_at])
            self.assertNotIn("author-nav-drawer.py", ship[:emil_at])
            self.assertIn("apply-hover-css.py", ship[emil_at:])
            self.assertNotIn("Semantics and SEO", ship)
            self.assertIn("emil-design-eng · board 3.2", ship)
            self.assertIn("design-taste-frontend · board 3.1", ship)
            self.assertIn("semantics_pass.py · board 3.3", ship)
            for name in ("web-design-guidelines", "find-animation-opportunities", "apple-design"):
                self.assertIn(name, ship)
                self.assertIn(f'href="../qa/{name}.md"', ship)
            self.assertIn("companions 3 / 3", ship)
            self.assertNotIn("NO RECEIPT", ship)
            qa = (root / "qa" / "polish-report.html").read_text(encoding="utf-8")
            self.assertIn('href="web-design-guidelines.md"', qa)
            (root / "qa" / "apple-design.md").unlink()
            self.assertEqual(_run("render-polish-report.py", str(root)), 0)
            ship = (root / "rebuild" / "polish-report.html").read_text(encoding="utf-8")
            self.assertIn("NO RECEIPT", ship)
            self.assertIn("companions 2 / 3", ship)

    def test_verify_fails_without_companion_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _project(root)
            self.assertEqual(_run("inject-gsap-reveal.py", str(root / "rebuild" / "index-polish.html")), 0)
            self.assertEqual(_run("render-polish-report.py", str(root)), 0)
            self.assertEqual(_run("verify-polish-passes.py", str(root)), 0)
            (root / "qa" / "apple-design.md").write_text("   \n", encoding="utf-8")
            self.assertEqual(_run("verify-polish-passes.py", str(root)), 2)
            (root / "qa" / "apple-design.md").unlink()
            self.assertEqual(_run("verify-polish-passes.py", str(root)), 2)

    def test_record_pass_points_companions_at_markdown_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _project(root)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(_SCRIPTS / "record-polish-pass.py"),
                    str(root),
                    "--id", "3.3",
                    "--skill", "apple-design",
                    "--phase", "start",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("qa/apple-design.md", proc.stderr)
            self.assertIn("#215", proc.stderr)
            self.assertFalse((root / "qa" / "polish-passes" / ".snap-3.3.json").exists())

    def test_render_writes_rebuild_copy_and_polish_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _project(root)
            rc = subprocess.call(
                [
                    sys.executable,
                    str(_SCRIPTS / "inject-gsap-reveal.py"),
                    str(root / "rebuild" / "index-polish.html"),
                ]
            )
            self.assertEqual(rc, 0)
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "render-polish-report.py"), str(root)]
            )
            self.assertEqual(rc, 0)
            ship = (root / "rebuild" / "polish-report.html").read_text(encoding="utf-8")
            self.assertIn("3.1", ship)
            self.assertIn("impeccable", ship)
            self.assertIn('href="index.html"', ship)
            self.assertIn('href="index-polish.html"', ship)
            self.assertIn("apply-hover-css.py", ship)
            self.assertIn("Btn-primary:hover", ship)
            self.assertIn("author-nav-drawer.py", ship)
            self.assertIn("Identified &amp; applied", ship)
            self.assertIn("Files touched", ship)
            self.assertIn('details class="files"', ship)
            self.assertNotIn("None recorded", ship)
            self.assertIn("#c7ff52", ship)
            self.assertIn("#0b0d0a", ship)
            lock = (root / "rebuild" / "index.html").read_text(encoding="utf-8")
            polish = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertNotIn("polish-report.html", lock)
            self.assertIn("polish-report.html", polish)
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "verify-polish-passes.py"), str(root)]
            )
            self.assertEqual(rc, 0)

    def test_verify_fails_capture_tool_guidelines_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _project(root)
            subprocess.check_call(
                [
                    sys.executable,
                    str(_SCRIPTS / "inject-gsap-reveal.py"),
                    str(root / "rebuild" / "index-polish.html"),
                ]
            )
            (root / "qa" / "web-design-guidelines.md").write_text(
                "rebuild/index-polish.html:25 - burger opens no drawer — "
                "skipped; Capture Tool did not park an open nav; "
                "inventing a sheet would be new chrome\n",
                encoding="utf-8",
            )
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "verify-polish-passes.py"), str(root)]
            )
            self.assertEqual(rc, 2)

    def test_verify_fails_without_gsap_inject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _project(root)
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "render-polish-report.py"), str(root)]
            )
            self.assertEqual(rc, 0)
            rc = subprocess.call(
                [sys.executable, str(_SCRIPTS / "verify-polish-passes.py"), str(root)]
            )
            self.assertEqual(rc, 2)
            rc = subprocess.call(
                [
                    sys.executable,
                    str(_SCRIPTS / "open-human-review.py"),
                    str(root),
                    "--no-open",
                ]
            )
            self.assertEqual(rc, 2)
            lock = (root / "rebuild" / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("polish-report.html", lock)

    def test_open_human_review_fails_without_polish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _project(root)
            (root / "rebuild" / "index-polish.html").unlink()
            rc = subprocess.call(
                [
                    sys.executable,
                    str(_SCRIPTS / "open-human-review.py"),
                    str(root),
                    "--no-open",
                ]
            )
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
