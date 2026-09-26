#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import library_14_foundations_gate as gate  # noqa: E402

import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    "pipeline_progress", _SCRIPTS / "pipeline-progress.py"
)
pipeline_progress = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(pipeline_progress)


def _official(root: Path) -> None:
    (root / "design-library").mkdir()
    (root / "qa").mkdir()
    (root / "design-library" / "library.json").write_text("{}")
    (root / "qa" / "library-seed-qa.json").write_text(json.dumps({"ok": True}))
    (root / "qa" / "design-library-step.json").write_text(json.dumps({
        "status": "done",
        "writer": "render-library.mjs",
        "kind": "foundations",
        "commands": ["extract-library.mjs", "render-library.mjs"],
    }))
    (root / "qa" / "buttons-components-pull.json").write_text(json.dumps({
        "ok": True,
        "writer": "pull-desktop-specimens.mjs",
        "geometry": {"ok": True},
        "scannedSections": ["01 · hero"],
        "buttons": [],
        "components": [],
    }))
    (root / "qa" / "button-hover.json").write_text(json.dumps({
        "ok": True,
        "writer": "author-button-hover.mjs",
        "applied": [],
        "skipped": [],
    }))


class FoundationsGateTest(unittest.TestCase):
    def test_library_alone_is_a_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "design-library").mkdir()
            (root / "design-library" / "library.json").write_text("{}")
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("design-library-step.json", errors)

    def test_hand_built_receipt_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "design-library").mkdir()
            (root / "qa").mkdir()
            (root / "design-library" / "library.json").write_text("{}")
            (root / "qa" / "library-seed-qa.json").write_text(json.dumps({"ok": True}))
            (root / "qa" / "design-library-step.json").write_text(json.dumps({
                "status": "done",
                "writer": "write_html",
                "kind": "custom",
                "commands": [],
            }))
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("official foundations", errors)
            self.assertFalse(pipeline_progress.artifact_done(root, "1.3"))

    def test_official_receipt_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _official(root)
            self.assertEqual(gate.gate_errors(root), [])
            self.assertTrue(pipeline_progress.artifact_done(root, "1.3"))


if __name__ == "__main__":
    unittest.main()
