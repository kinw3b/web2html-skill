#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import design_system_21_gate as gate


class DesignSystem21GateTest(unittest.TestCase):
    def test_rejects_font_style_byte_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            with patch.object(gate, "font_face_errors", return_value=["Inter 400 normal: font bytes do not match source style/weight"]):
                self.assertIn("font bytes do not match", " ".join(gate.gate_errors(root)))

    def test_missing_library_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("library.json", errors)
            self.assertFalse(gate.ready(root))

    def test_passing_artifacts_are_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            self.assertEqual(gate.gate_errors(root), [])
            self.assertTrue(gate.ready(root))

    def test_freehand_receipt_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / gate.RECEIPT).write_text("{}\n", encoding="utf-8")
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("emit-design-system", errors)

    def test_invented_color_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / "rebuild" / "css" / "page.css").write_text(
                ":root { --color-hotpink: #ff2bd6; }\n",
                encoding="utf-8",
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("invented", errors)

    def test_hardcoded_chrome_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate.install_passing_artifacts(root)
            (root / gate.PAGE).write_text(
                '<html><head><link rel="stylesheet" href="css/tokens.css"></head>'
                '<body data-page="design-system"><p>DESIGN SYSTEM</p></body></html>\n',
                encoding="utf-8",
            )
            errors = " ".join(gate.gate_errors(root))
            self.assertIn("var(--color-", errors)


if __name__ == "__main__":
    unittest.main()
