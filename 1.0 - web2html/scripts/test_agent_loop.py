from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import agent_loop  # noqa: E402


class AgentLoopTests(unittest.TestCase):
    def test_snapshot_hash_rejects_a_stale_reviewer_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ship = root / "rebuild" / "index.html"
            ship.parent.mkdir()
            ship.write_text("<main>first</main>", encoding="utf-8")
            snapshot = agent_loop.create_snapshot(root, "2.2.d", ["rebuild/index.html"])
            ship.write_text("<main>second</main>", encoding="utf-8")

            errors = agent_loop.validate_finding(
                root,
                snapshot,
                {
                    "generatedFrom": agent_loop.FINDINGS_GENERATED_FROM,
                    "phase": "2.2.d",
                    "agent": "tablet-768",
                    "inputSha256": snapshot["sha256"],
                    "findings": [],
                },
            )
            self.assertTrue(any("stale" in error for error in errors))

    def test_submit_finding_uses_the_noncanonical_agent_findings_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ship = root / "rebuild" / "index.html"
            ship.parent.mkdir()
            ship.write_text("<main></main>", encoding="utf-8")
            snapshot = agent_loop.create_snapshot(root, "a7", ["rebuild/index.html"])
            finding = {
                "generatedFrom": agent_loop.FINDINGS_GENERATED_FROM,
                "phase": "a7",
                "agent": "component-coverage",
                "inputSha256": snapshot["sha256"],
                "findings": [
                    {
                        "key": "pc-01-0|coverage",
                        "severity": "high",
                        "source": "source-site/components/home/buttons/manifest.json",
                        "evidence": "button state missing",
                        "suggestion": "recapture the named control",
                    }
                ],
            }

            dest = agent_loop.submit_finding(root, "run-01", snapshot, finding)

            self.assertEqual(
                dest,
                (root / "qa" / "agent-findings" / "run-01" / "a7" / "component-coverage.json").resolve(),
            )
            self.assertTrue(dest.is_file())
            self.assertFalse((root / "qa" / "component-state-coverage.json").exists())
            self.assertEqual(json.loads(dest.read_text())["agent"], "component-coverage")

    def test_reviewer_leases_block_until_each_named_reviewer_releases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = {"sha256": "abc", "phase": "2.2.d"}
            first = agent_loop.claim_reviewer(root, "tablet-768", snapshot)
            second = agent_loop.claim_reviewer(root, "phone-390", snapshot)

            self.assertTrue(first.is_file())
            self.assertTrue(second.is_file())
            self.assertEqual([p.name for p in agent_loop.active_reviewer_leases(root)], ["phone-390.json", "tablet-768.json"])
            agent_loop.release_reviewer(root, "tablet-768", "abc")
            self.assertEqual([p.name for p in agent_loop.active_reviewer_leases(root)], ["phone-390.json"])
            agent_loop.release_reviewer(root, "phone-390", "abc")
            self.assertEqual(agent_loop.active_reviewer_leases(root), [])


if __name__ == "__main__":
    unittest.main()
