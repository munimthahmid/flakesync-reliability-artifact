#!/usr/bin/env python3
"""Build the five-case manual reliable-repair aggregate.

The inputs are compact, sanitized validation ledgers.  This script verifies
their identities, verdicts, source-ledger provenance, patch hashes, and gate
counts before producing deterministic JSON and CSV results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATIONS = ROOT / "data" / "reliable_repairs" / "validations"
PROTOCOL = ROOT / "contract" / "manual_repair_validation_protocol.json"
SUBJECTS = ROOT / "data" / "subjects.csv"
OUT_JSON = ROOT / "results" / "reliable_repairs.json"
OUT_CSV = ROOT / "results" / "reliable_repairs.csv"

CASE_IDS = ("FS005", "FS014", "FS020", "FS056", "FS059")
SUCCESS_IDS = ("FS005", "FS014", "FS059")
REJECTED_IDS = ("FS020", "FS056")
VERDICTS = {"pass", "fail", "unknown", "not_applicable"}
CHECKS = (
    "patch_apply",
    "compile",
    "ordinary",
    "unpatched_recorded_delay",
    "patched_recorded_delay",
    "missing_completion",
    "interruption",
    "multi_writer",
    "neighboring_tests",
    "same_process",
    "parallel",
    "state_leakage",
)
CSV_FIELDS = (
    "CaseId",
    "Project",
    "SourceRevision",
    "TargetTest",
    "OverallVerdict",
    "CandidateStatus",
    "OrdinaryExecuted",
    "OrdinaryPasses",
    "ControlDelayExecuted",
    "ControlNonpasses",
    "PatchedDelayExecuted",
    "PatchedPasses",
    "PatchedNonpasses",
    "MissingCompletion",
    "Interruption",
    "MultiWriter",
    "NeighboringTests",
    "SameProcess",
    "Parallel",
    "StateLeakage",
    "PatchPath",
    "PatchSha256",
    "ValidationPath",
    "ValidationSha256",
    "SourceLedgerSha256",
    "Blocker",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected JSON object: {rel(path)}")
    return value


def encoded_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def resolve_release_path(value: object, label: str) -> Path:
    require(isinstance(value, str) and value, f"{label}: path is missing")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, f"{label}: unsafe path {value}")
    resolved = (ROOT / path).resolve()
    require(resolved.is_relative_to(ROOT.resolve()), f"{label}: path escapes repository")
    return resolved


def load_subjects() -> dict[str, str]:
    with SUBJECTS.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row["Project"]: row["SourceRevision"] for row in rows}


def validation_path(case_id: str) -> Path:
    return VALIDATIONS / f"{case_id}.json"


def audit_validation(case_id: str, value: dict[str, Any], subjects: dict[str, str]) -> None:
    require(value.get("schema_version") == "reliable-repair-release-validation-v1", f"{case_id}: schema")
    require(value.get("case_id") == case_id, f"{case_id}: identity")
    require(value.get("selection_scope") == "manual_candidate", f"{case_id}: selection scope")
    project = value.get("project")
    require(project in subjects, f"{case_id}: unknown project {project}")
    require(value.get("source_revision") == subjects[project], f"{case_id}: source revision")
    require(value.get("overall_verdict") in VERDICTS, f"{case_id}: overall verdict")
    require(set(value.get("checks", {})) == set(CHECKS), f"{case_id}: check set")
    for check_name in CHECKS:
        require(value["checks"][check_name].get("verdict") in VERDICTS, f"{case_id}.{check_name}: verdict")

    patch = value.get("patch") or {}
    patch_path = resolve_release_path(patch.get("path"), f"{case_id}.patch")
    require(patch_path.is_file(), f"{case_id}: missing patch")
    require(sha256(patch_path) == patch.get("sha256"), f"{case_id}: patch hash")

    source = value.get("source_ledger") or {}
    require(str(source.get("original_path", "")).startswith("<PRIVATE_STUDY_ROOT>/"), f"{case_id}: source path")
    require(isinstance(source.get("original_bytes"), int) and source["original_bytes"] > 0, f"{case_id}: source bytes")
    source_hash = source.get("original_sha256")
    require(isinstance(source_hash, str) and len(source_hash) == 64, f"{case_id}: source hash")
    require(bool(source.get("transformation")), f"{case_id}: sanitization record")

    ordinary = value["checks"]["ordinary"]
    control = value["checks"]["unpatched_recorded_delay"]
    repaired = value["checks"]["patched_recorded_delay"]
    require(control.get("verdict") == "pass", f"{case_id}: causal control gate")
    control_nonpasses = control.get("confirmed_nonpasses", control.get("nonpasses"))
    require(control.get("executed") == 5 and control_nonpasses == 5, f"{case_id}: control counts")
    if case_id in SUCCESS_IDS:
        require(value["overall_verdict"] == "pass", f"{case_id}: expected successful verdict")
        require(patch.get("published_as_success") is True, f"{case_id}: success publication flag")
        require(ordinary.get("verdict") == "pass", f"{case_id}: ordinary verdict")
        require(ordinary.get("executed") == 100 and ordinary.get("passes") == 100, f"{case_id}: ordinary 100/100")
        require(repaired.get("verdict") == "pass", f"{case_id}: repaired causal verdict")
        repaired_passes = repaired.get("confirmed_passes", repaired.get("passes"))
        require(repaired.get("executed") == 5 and repaired_passes == 5, f"{case_id}: repaired causal counts")
    else:
        require(case_id in REJECTED_IDS, f"{case_id}: unexpected case classification")
        require(value["overall_verdict"] == "fail", f"{case_id}: expected rejected verdict")
        require(patch.get("published_as_success") is False, f"{case_id}: rejected publication flag")
        require(repaired.get("verdict") == "fail", f"{case_id}: causal rejection")
        require(bool(value.get("blocker")), f"{case_id}: blocker missing")


def case_result(case_id: str, value: dict[str, Any]) -> dict[str, Any]:
    checks = value["checks"]
    ordinary = checks["ordinary"]
    control = checks["unpatched_recorded_delay"]
    repaired = checks["patched_recorded_delay"]
    validation = validation_path(case_id)
    return {
        "project": value["project"],
        "source_revision": value["source_revision"],
        "target_test": value["target_test"],
        "candidate_status": value["candidate_status"],
        "overall_verdict": value["overall_verdict"],
        "ordinary": {
            "verdict": ordinary["verdict"],
            "executed": ordinary.get("executed", 0),
            "passes": ordinary.get("passes", 0),
        },
        "causal_replay": {
            "unpatched_verdict": control["verdict"],
            "unpatched_executed": control.get("executed", 0),
            "unpatched_nonpasses": control.get("confirmed_nonpasses", control.get("nonpasses", 0)),
            "repaired_verdict": repaired["verdict"],
            "repaired_executed": repaired.get("executed", 0),
            "repaired_passes": repaired.get("confirmed_passes", repaired.get("passes", 0)),
            "repaired_nonpasses": repaired.get("confirmed_nonpasses", repaired.get("nonpasses", 0)),
        },
        "additional_gate_verdicts": {
            name: checks[name]["verdict"]
            for name in (
                "missing_completion",
                "interruption",
                "multi_writer",
                "neighboring_tests",
                "same_process",
                "parallel",
                "state_leakage",
            )
        },
        "patch": value["patch"],
        "validation": {
            "path": rel(validation),
            "sha256": sha256(validation),
            "source_ledger_sha256": value["source_ledger"]["original_sha256"],
        },
        "causal_conclusion": value["causal_conclusion"],
        "claim_boundary": value["claim_boundary"],
        "blocker": value.get("blocker"),
    }


def build_values() -> tuple[dict[str, Any], str]:
    protocol = load_json(PROTOCOL)
    require(protocol["scope"]["case_ids"] == list(CASE_IDS), "protocol case roster")
    subjects = load_subjects()
    validations: dict[str, dict[str, Any]] = {}
    for case_id in CASE_IDS:
        path = validation_path(case_id)
        require(path.is_file(), f"missing validation: {rel(path)}")
        validations[case_id] = load_json(path)
        audit_validation(case_id, validations[case_id], subjects)

    cases = {case_id: case_result(case_id, validations[case_id]) for case_id in CASE_IDS}
    successful = [case_id for case_id in CASE_IDS if cases[case_id]["overall_verdict"] == "pass"]
    rejected = [case_id for case_id in CASE_IDS if cases[case_id]["overall_verdict"] == "fail"]
    require(successful == list(SUCCESS_IDS), "successful case roster")
    require(rejected == list(REJECTED_IDS), "rejected case roster")

    summary = {
        "schema_version": "reliable-repair-release-summary-v1",
        "status": "pass",
        "claim_boundary": protocol["scope"]["claim_boundary"],
        "manual_candidates": {"count": len(CASE_IDS), "case_ids": list(CASE_IDS)},
        "successful_reliable_repairs": {"count": len(successful), "case_ids": successful},
        "rejected_candidates": {"count": len(rejected), "case_ids": rejected},
        "unknown_overall": {"count": 0, "case_ids": []},
        "validation_protocol": {"path": rel(PROTOCOL), "sha256": sha256(PROTOCOL)},
        "cases": cases,
        "boundaries": {
            "selected_case_studies_not_population_estimate": True,
            "unknown_check_is_neither_pass_nor_fail": True,
            "rejected_candidates_stop_before_later_gates": True,
            "successful_repair_does_not_mean_every_possible_schedule_was_tested": True,
        },
    }

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for case_id in CASE_IDS:
        case = cases[case_id]
        causal = case["causal_replay"]
        gates = case["additional_gate_verdicts"]
        writer.writerow(
            {
                "CaseId": case_id,
                "Project": case["project"],
                "SourceRevision": case["source_revision"],
                "TargetTest": case["target_test"],
                "OverallVerdict": case["overall_verdict"],
                "CandidateStatus": case["candidate_status"],
                "OrdinaryExecuted": case["ordinary"]["executed"],
                "OrdinaryPasses": case["ordinary"]["passes"],
                "ControlDelayExecuted": causal["unpatched_executed"],
                "ControlNonpasses": causal["unpatched_nonpasses"],
                "PatchedDelayExecuted": causal["repaired_executed"],
                "PatchedPasses": causal["repaired_passes"],
                "PatchedNonpasses": causal["repaired_nonpasses"],
                "MissingCompletion": gates["missing_completion"],
                "Interruption": gates["interruption"],
                "MultiWriter": gates["multi_writer"],
                "NeighboringTests": gates["neighboring_tests"],
                "SameProcess": gates["same_process"],
                "Parallel": gates["parallel"],
                "StateLeakage": gates["state_leakage"],
                "PatchPath": case["patch"]["path"],
                "PatchSha256": case["patch"]["sha256"],
                "ValidationPath": case["validation"]["path"],
                "ValidationSha256": case["validation"]["sha256"],
                "SourceLedgerSha256": case["validation"]["source_ledger_sha256"],
                "Blocker": case["blocker"] or "",
            }
        )
    return summary, buffer.getvalue()


def expected_outputs() -> dict[Path, bytes]:
    summary, csv_text = build_values()
    return {OUT_JSON: encoded_json(summary), OUT_CSV: csv_text.encode("utf-8")}


def build(write: bool = True) -> dict[str, Any]:
    expected = expected_outputs()
    if write:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        for path, payload in expected.items():
            path.write_bytes(payload)
    for path, payload in expected.items():
        require(path.is_file(), f"missing output: {rel(path)}")
        require(path.read_bytes() == payload, f"stale output: {rel(path)}")
    return json.loads(expected[OUT_JSON])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-only", action="store_true", help="verify deterministic outputs without writing")
    args = parser.parse_args()
    summary = build(write=not args.audit_only)
    print(
        "reliable-repair build: PASS "
        f"candidates={summary['manual_candidates']['count']} "
        f"successful={summary['successful_reliable_repairs']['count']} "
        f"rejected={summary['rejected_candidates']['count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
