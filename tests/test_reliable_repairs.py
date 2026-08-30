import csv
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_reliable_repairs.py"
OUT_JSON = ROOT / "results" / "reliable_repairs.json"
OUT_CSV = ROOT / "results" / "reliable_repairs.csv"


def load_builder():
    spec = importlib.util.spec_from_file_location("reliable_repair_builder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReliableRepairReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.summary = cls.builder.build()

    def test_exact_manual_candidate_outcomes(self):
        self.assertEqual(
            self.summary["manual_candidates"],
            {"count": 5, "case_ids": ["FS005", "FS014", "FS020", "FS056", "FS059"]},
        )
        self.assertEqual(
            self.summary["successful_reliable_repairs"],
            {"count": 3, "case_ids": ["FS005", "FS014", "FS059"]},
        )
        self.assertEqual(
            self.summary["rejected_candidates"],
            {"count": 2, "case_ids": ["FS020", "FS056"]},
        )

    def test_successful_repairs_pass_required_primary_gates(self):
        for case_id in ("FS005", "FS014", "FS059"):
            case = self.summary["cases"][case_id]
            self.assertEqual(case["ordinary"], {"verdict": "pass", "executed": 100, "passes": 100})
            self.assertEqual(case["causal_replay"]["unpatched_executed"], 5)
            self.assertEqual(case["causal_replay"]["unpatched_nonpasses"], 5)
            self.assertEqual(case["causal_replay"]["repaired_executed"], 5)
            self.assertEqual(case["causal_replay"]["repaired_passes"], 5)
            self.assertTrue(case["patch"]["published_as_success"])

    def test_rejected_candidates_preserve_stopping_rule(self):
        fs020 = self.summary["cases"]["FS020"]
        fs056 = self.summary["cases"]["FS056"]
        self.assertEqual(fs020["causal_replay"]["repaired_nonpasses"], 5)
        self.assertEqual(fs056["causal_replay"]["repaired_nonpasses"], 1)
        for case in (fs020, fs056):
            self.assertEqual(case["overall_verdict"], "fail")
            self.assertFalse(case["patch"]["published_as_success"])
            self.assertTrue(case["blocker"])

    def test_unknown_checks_remain_explicit(self):
        self.assertEqual(
            self.summary["cases"]["FS059"]["additional_gate_verdicts"]["parallel"],
            "unknown",
        )
        self.assertTrue(self.summary["boundaries"]["unknown_check_is_neither_pass_nor_fail"])

    def test_csv_has_one_row_per_candidate(self):
        with OUT_CSV.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["CaseId"] for row in rows], ["FS005", "FS014", "FS020", "FS056", "FS059"])
        self.assertEqual(sum(row["OverallVerdict"] == "pass" for row in rows), 3)

    def test_validation_and_patch_hashes_are_bound(self):
        for case in self.summary["cases"].values():
            patch = ROOT / case["patch"]["path"]
            validation = ROOT / case["validation"]["path"]
            self.assertEqual(digest(patch), case["patch"]["sha256"])
            self.assertEqual(digest(validation), case["validation"]["sha256"])

    def test_builder_is_deterministic(self):
        before = {OUT_JSON.name: digest(OUT_JSON), OUT_CSV.name: digest(OUT_CSV)}
        self.builder.build()
        after = {OUT_JSON.name: digest(OUT_JSON), OUT_CSV.name: digest(OUT_CSV)}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
