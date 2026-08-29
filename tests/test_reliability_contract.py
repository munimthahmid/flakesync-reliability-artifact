import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract" / "reliability_contract.json"


class ReliabilityAwareRepairContractV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_status_does_not_overclaim_implementation(self):
        self.assertEqual(
            self.contract["status"], "specified-not-implemented-or-evaluated"
        )
        self.assertIn("not evidence", self.contract["scope"]["claim_boundary"])

    def test_nine_ordered_unique_properties(self):
        properties = self.contract["properties"]
        self.assertEqual([item["id"] for item in properties], [f"P{i}" for i in range(1, 10)])
        self.assertEqual(len({item["name"] for item in properties}), 9)
        for item in properties:
            self.assertTrue(item["requirement"])
            self.assertTrue(item["static_checks"])
            self.assertTrue(item["dynamic_checks"])
            self.assertTrue(item["failure_oracle"])

    def test_pass_fail_unknown_are_distinct(self):
        lattice = self.contract["verdict_lattice"]
        self.assertIn("positive evidence", lattice["pass"])
        self.assertIn("violation", lattice["fail"])
        self.assertIn("lacks a valid", lattice["unknown"])
        self.assertEqual(set(lattice["overall"]), {"reliable", "unreliable", "unresolved"})

    def test_ten_counter_scenarios_have_witnesses_and_oracles(self):
        scenarios = self.contract["counter_scenarios"]
        self.assertEqual([item["id"] for item in scenarios], [f"C{i}" for i in range(1, 11)])
        for item in scenarios:
            self.assertTrue(item["targets"])
            self.assertTrue(item["intervention"])
            self.assertTrue(item["required_witnesses"])
            self.assertTrue(item["expected_reliable_outcome"])

    def test_generation_can_abstain(self):
        strategies = self.contract["candidate_generation"]["ordered_strategy"]
        self.assertEqual(strategies[-1]["strategy"], "abstain")
        self.assertIn("otherwise abstain", self.contract["candidate_generation"]["timeout_selection_priority"][-1])

    def test_evaluation_is_held_out_and_matched(self):
        evaluation = self.contract["evaluation"]
        self.assertIn("Freeze a separate case roster", evaluation["development_and_test_split"]["held_out_requirement"])
        self.assertIn("unpatched pinned source", evaluation["arms"])
        self.assertIn("raw FlakeSync source repair", evaluation["arms"])
        self.assertIn("reliability-aware candidate or explicit abstention", evaluation["arms"])
        self.assertIn("same critical point", evaluation["controlled_inputs"][2])
        self.assertIn("Do not use independent-case binomial", evaluation["statistics"]["current_cohort"])

    def test_prevention_map_covers_every_observed_issue_family(self):
        expected = {
            "partial_or_malformed_generation",
            "causal_mismatch",
            "unbounded_wait_or_deadlock",
            "missed_publication_or_visibility",
            "non_atomic_counter_update",
            "stale_or_cross_test_state",
            "ignored_interruption",
            "assertion_suppression_or_worker_failure_masking",
            "neighbor_or_parallel_interference",
        }
        prevention = self.contract["expected_prevention_map"]
        self.assertEqual(set(prevention), expected)
        valid_ids = {item["id"] for item in self.contract["properties"]}
        for property_ids in prevention.values():
            self.assertTrue(set(property_ids) <= valid_ids)

    def test_non_guarantees_are_explicit(self):
        rendered = " ".join(self.contract["non_guarantees"])
        self.assertIn("cannot prove correctness under every Java schedule", rendered)
        self.assertIn("cannot repair an incorrect critical/barrier localization", rendered)
        self.assertIn("correct result is then abstention", rendered)


if __name__ == "__main__":
    unittest.main()
