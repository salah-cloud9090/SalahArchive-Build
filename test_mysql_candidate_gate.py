import unittest
from mysql_candidate_gate import inspect_candidate

class CandidateGateTests(unittest.TestCase):
    def test_candidate_static_gate_passes_without_claiming_live_readiness(self):
        report = inspect_candidate()
        self.assertEqual(report["status"], "PASS_STATIC_CANDIDATE", report)
        self.assertTrue(all(report["checks"].values()))
        self.assertTrue(any("No MySQL server connection" in item for item in report["limitations"]))

if __name__ == "__main__": unittest.main(verbosity=2)
