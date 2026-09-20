#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "apply_hover_css", _SCRIPTS / "apply-hover-css.py"
)
apply_mod = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(apply_mod)


def _project(tmp: str) -> Path:
    root = Path(tmp)
    (root / "qa").mkdir()
    (root / "rebuild" / "css").mkdir(parents=True)
    (root / "rebuild" / "css" / "tokens.css").write_text(
        ":root { --color-ink: #111111; --color-text-inverse-2: #ffffff; }\n",
        encoding="utf-8",
    )
    (root / "rebuild" / "index-polish.html").write_text(
        "<html><head><link rel=\"stylesheet\" href=\"css/tokens.css\" /></head>"
        "<body><a href=\"#go\">Get Started Now</a></body></html>\n",
        encoding="utf-8",
    )
    return root


class ApplyHoverCssTest(unittest.TestCase):
    def test_writes_and_links_hover_from_1_3_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "qa" / "button-hover.json").write_text(
                json.dumps({
                    "ok": True,
                    "writer": "author-button-hover.mjs",
                    "applied": [{
                        "label": "Primary - Get Started Now",
                        "sectionId": "01",
                        "sectionName": "hero",
                        "className": "btn-primary",
                        "sourceSelector": ".btn-primary:hover",
                        "declarations": {
                            "background-color": "#111111",
                            "color": "#ffffff",
                        },
                    }],
                    "skipped": [],
                }),
                encoding="utf-8",
            )
            receipt = apply_mod.apply_hover_css(root)
            self.assertTrue(apply_mod.hover_receipt_ok(receipt))
            self.assertEqual(len(receipt["applied"]), 1)
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertIn("css/hover.css", html)
            self.assertIn("btn-primary", html)
            css = (root / "rebuild" / "css" / "hover.css").read_text(encoding="utf-8")
            self.assertIn(".btn-primary:hover", css)
            self.assertIn("var(--color-ink)", css)

    def test_skip_when_1_3_found_no_hover(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "qa" / "button-hover.json").write_text(
                json.dumps({
                    "ok": True,
                    "writer": "author-button-hover.mjs",
                    "applied": [],
                    "skipped": [{"label": "X", "reason": "no source CSS :hover paint"}],
                }),
                encoding="utf-8",
            )
            receipt = apply_mod.apply_hover_css(root)
            self.assertTrue(receipt["ok"])
            self.assertEqual(receipt["applied"], [])
            html = (root / "rebuild" / "index-polish.html").read_text(encoding="utf-8")
            self.assertNotIn("css/hover.css", html)

    def test_preserves_faq_block_already_in_hover_css(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _project(tmp)
            (root / "rebuild" / "css" / "hover.css").write_text(
                "/* Detected FAQ */\n[data-action=\"toggle-faq\"] { width: 100%; }\n",
                encoding="utf-8",
            )
            (root / "qa" / "button-hover.json").write_text(
                json.dumps({
                    "ok": True,
                    "writer": "author-button-hover.mjs",
                    "applied": [{
                        "label": "Get Started Now",
                        "className": "btn-primary",
                        "declarations": {"background-color": "#000"},
                    }],
                    "skipped": [],
                }),
                encoding="utf-8",
            )
            apply_mod.apply_hover_css(root)
            css = (root / "rebuild" / "css" / "hover.css").read_text(encoding="utf-8")
            self.assertIn(".btn-primary:hover", css)
            self.assertIn("Detected FAQ", css)


if __name__ == "__main__":
    unittest.main()
