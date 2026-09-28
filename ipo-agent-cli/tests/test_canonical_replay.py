"""Regression test for the offline canonical evidence replay."""

from __future__ import annotations

import unittest

from ipo_agent.replay import verify_canonical_replay


class CanonicalReplayTests(unittest.TestCase):
    def test_example_batch_evidence_replay_passes(self) -> None:
        result = verify_canonical_replay()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["case_id"], "example-batch-evidence-v1")
        self.assertEqual(result["mismatches"], {})


if __name__ == "__main__":
    unittest.main()
