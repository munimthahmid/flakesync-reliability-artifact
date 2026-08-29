import csv
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_analysis.py"
OUT = ROOT / "results"


def load_builder():
    spec = importlib.util.spec_from_file_location("rq_v3_builder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResearchQuestionsAnalysisV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.summary = cls.builder.build()

    def test_provenance_and_units_are_not_conflated(self):
        units = self.summary["units"]
        self.assertEqual(units["local_source_patch_cohort"]["cases"], 18)
        self.assertEqual(
            units["b2_patch_goal"]["genuine_blank_threshold_cases"], ["FS015"]
        )
        self.assertEqual(units["combined_artifact_cohort"]["cases"], 20)
        self.assertEqual(units["combined_artifact_cohort"]["local_emissions"], 18)
        self.assertEqual(units["combined_artifact_cohort"]["author_submissions"], 2)
        self.assertEqual(units["combined_artifact_cohort"]["projects"], 13)
        self.assertTrue(
            self.summary["claim_boundary"][
                "official_runtime_confirmation_separate_from_source_patch_reliability"
            ]
        )

    def test_official_exact_and_linked_counts(self):
        official = self.summary["official_runtime_reproduction"]
        self.assertEqual(
            official["completed_speed_confirmation_cohort"]["confirmed_100_of_100"],
            ["FS055", "FS057"],
        )
        self.assertEqual(
            official["unfinished_full_confirmation_roster"],
            {
                "declared_cases": 21,
                "status": "waiting_for_official_20",
                "terminal_case_dispositions": 0,
            },
        )
        self.assertEqual(
            official["exact_runtime_to_source_linkage"]["cases"], ["FS057"]
        )
        self.assertEqual(
            official["exact_runtime_to_source_linkage"]["checks_passed"], 61
        )
        self.assertEqual(
            official["exact_runtime_to_source_linkage"]["checks_total"], 61
        )

    def test_headline_metrics(self):
        self.assertEqual(
            self.summary["headline_20_artifact_metrics"],
            {
                "applied": "20/20",
                "compiled": "16/20",
                "ordinary_pass": "14/20",
                "matched_delay_evaluable": "12/20",
                "causal_effective": "2/12",
                "causal_ineffective": "10/12",
                "signal_loss_hang": "8/13",
                "fault_specific_signal_loss_hang": "5/10",
                "interruption_failure": "7/7",
                "neighbor_regression": "1/14 reached; 1/20 cohort-wide",
                "complete_operational_contract": "0/20",
            },
        )

    def test_primary_local_metrics_are_separate_from_author_extension(self):
        self.assertEqual(
            self.summary["headline_18_local_metrics"],
            {
                "applied": "18/18",
                "compiled": "14/18",
                "ordinary_pass": "12/18",
                "matched_delay_evaluable": "11/18",
                "causal_effective": "1/11",
                "causal_ineffective": "10/11",
                "signal_loss_hang": "7/11",
                "fault_specific_signal_loss_hang": "5/9",
                "interruption_failure": "6/6",
                "neighbor_regression": "1/12 reached; 1/18 cohort-wide",
                "complete_operational_contract": "0/18",
            },
        )

    def test_every_gate_partition_is_complete_and_disjoint(self):
        for gate, partition in self.summary["gate_coverage"].items():
            seen = set()
            total = 0
            for status, payload in partition.items():
                if status == "denominator":
                    continue
                members = set(payload["case_ids"])
                self.assertEqual(payload["count"], len(members), (gate, status))
                self.assertFalse(seen & members, (gate, status))
                seen |= members
                total += payload["count"]
            self.assertEqual(total, partition["denominator"], gate)
            self.assertEqual(partition["denominator"], 20, gate)

    def test_unknown_is_not_silently_counted_as_pass_or_failure(self):
        parallel = self.summary["gate_coverage"]["parallel"]
        self.assertEqual(parallel["pass_"]["count"], 1)
        self.assertEqual(
            parallel["inconclusive_execution_not_confirmed"]["count"], 8
        )
        self.assertEqual(parallel["unavailable_no_peer"]["count"], 5)
        self.assertEqual(parallel["not_reached"]["count"], 6)
        self.assertTrue(self.summary["claim_boundary"]["unknown_is_not_failure_and_not_pass"])

    def test_project_and_design_clustering(self):
        clustering = self.summary["clustering"]
        self.assertEqual(clustering["twenty_projects"], 13)
        self.assertEqual(clustering["largest_project"], "Alluxio/alluxio")
        self.assertEqual(clustering["largest_project_cases"], 6)
        self.assertEqual(clustering["local_generated_templates"], 1)
        self.assertEqual(clustering["developer_independent_designs"], 3)
        designs = {
            row["DesignId"]: row
            for row in self.summary["developer_comparison"]["designs"]
        }
        httpcore = designs["httpcore_66d43a02_ordered_bounded_join"]
        self.assertEqual(httpcore["ExactOriginalInstances"], 1)

    def test_nine_property_contract(self):
        properties = self.summary["reliability_contract"]["properties"]
        self.assertEqual(len(properties), 9)
        self.assertIn("causal_effectiveness", properties)
        self.assertIn("bounded_progress", properties)
        self.assertIn("cancellation_interruption_and_cleanup", properties)
        self.assertIn(
            "repeatability_under_declared_positive_and_counter_scenarios", properties
        )

    def test_protocol_forbids_independent_case_confidence_intervals(self):
        self.assertTrue(
            self.summary["claim_boundary"]["no_independent_case_confidence_intervals"]
        )
        rendered = json.dumps(self.summary, sort_keys=True)
        self.assertNotIn("wilson", rendered.lower())

    def test_csv_outputs_have_expected_rows(self):
        expectations = {
            "cohort_flow.csv": 8,
            "gate_coverage.csv": 35,
            "case_reliability_matrix.csv": 20,
            "project_clusters.csv": 13,
            "problem_categories.csv": 6,
            "developer_designs.csv": 3,
        }
        for name, expected in expectations.items():
            with (OUT / name).open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), expected, name)

    def test_every_bound_input_still_matches_its_hash(self):
        for record in self.summary["inputs"].values():
            path = Path(record["path"])
            if not path.is_absolute():
                path = ROOT / path
            self.assertTrue(path.is_file(), path)
            self.assertEqual(path.stat().st_size, record["bytes"], path)
            self.assertEqual(digest(path), record["sha256"], path)

    def test_builder_is_deterministic(self):
        summary_path = OUT / "summary.json"
        before = digest(summary_path)
        self.builder.build()
        after = digest(summary_path)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
