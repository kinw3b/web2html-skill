from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import agent_loop  # noqa: E402
import run_component_qa_wave as component_wave  # noqa: E402
import run_responsive_review_wave as responsive_wave  # noqa: E402


class ReviewerWaveTests(unittest.TestCase):
    def test_component_wave_prepares_only_the_two_sanctioned_reviewers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifests = root / "source-site" / "components" / "home" / "buttons"
            manifests.mkdir(parents=True)
            (manifests / "manifest.json").write_text("{}", encoding="utf-8")
            qa = root / "qa"
            qa.mkdir()
            (qa / "component-state-coverage.json").write_text("{}", encoding="utf-8")
            (qa / "component-paper-qa.json").write_text("{}", encoding="utf-8")

            wave = component_wave.prepare(root, "run-01")

            self.assertEqual(wave["reviewers"], ["component-coverage", "paper-geometry"])
            self.assertTrue((root / "qa" / "agent-runs" / "run-01" / "a7" / "snapshot.json").is_file())
            self.assertEqual([path.name for path in agent_loop.active_reviewer_leases(root)], ["component-coverage.json", "paper-geometry.json"])

    def test_responsive_wave_requires_one_current_report_per_viewport(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rebuild" / "css").mkdir(parents=True)
            (root / "rebuild" / "index.html").write_text("<main></main>", encoding="utf-8")
            (root / "rebuild" / "css" / "sections.css").write_text(".hero{}", encoding="utf-8")
            for width in (768, 390):
                frame = root / "capture" / f"home-{width}"
                frame.mkdir(parents=True)
                (frame / "fullpage.png").write_bytes(b"png")
            (root / "qa").mkdir()
            (root / "qa" / "responsive-pc-join.json").write_text("{}", encoding="utf-8")

            wave = responsive_wave.prepare(root, "run-01")
            snapshot = wave["snapshot"]
            self.assertEqual(wave["reviewers"], ["tablet-768", "phone-390"])
            self.assertFalse(responsive_wave.ready_for_controller(root, "run-01", snapshot))

            for agent, width in (("tablet-768", 768), ("phone-390", 390)):
                agent_loop.submit_finding(
                    root,
                    "run-01",
                    snapshot,
                    {
                        "generatedFrom": agent_loop.FINDINGS_GENERATED_FROM,
                        "phase": "2.2.d",
                        "agent": agent,
                        "inputSha256": snapshot["sha256"],
                        "findings": [],
                        "viewport": width,
                    },
                )
                agent_loop.release_reviewer(root, agent, snapshot["sha256"])

            self.assertTrue(responsive_wave.ready_for_controller(root, "run-01", snapshot))


if __name__ == "__main__":
    unittest.main()
