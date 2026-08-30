#!/usr/bin/env python3
"""Build the release quantitative analysis for the FlakeSync reliability study.

This is an offline, fail-closed synthesis.  It does not execute Maven, Docker,
or network requests.  It keeps official runtime confirmation, locally emitted
source patches, author-submitted repairs, and independent developer repairs in
separate evidence groups.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"


INPUTS = {
    "b2_generator_outcomes": ROOT / "data/generation/case_outcomes_67.csv",
    "artifact_location_audit": ROOT / "data/corpus/artifact_locations_audit.json",
    "static_18_summary": ROOT / "data/static/generated_patch_summary.json",
    "repair_20_summary": ROOT / "data/reliability/repair_cohort_summary.json",
    "repair_20_cases": ROOT / "data/reliability/repair_case_findings.csv",
    "counter_race_summary": ROOT / "data/races/counter_race_summary.json",
    "counter_race_cases": ROOT / "data/races/counter_race_case_findings.csv",
    "developer_summary": ROOT / "data/developer/comparison_summary.json",
    "developer_cases": ROOT / "data/developer/case_matrix.csv",
    "developer_coverage_67": ROOT / "data/developer/coverage_67.json",
    "developer_screening": ROOT / "data/developer/screening_decisions.json",
    "fs059_frequency": ROOT / "data/special/fs059_neighbor_frequency.json",
    "fs059_crossover": ROOT / "data/special/fs059_worker_crossover.json",
    "fs057_linkage": ROOT / "data/linkage/fs057_runtime_source.json",
    "reliability_aware_contract": ROOT / "contract/reliability_contract.json",
    "exact_confirmation_3": ROOT / "data/official/exact_confirmation_3.json",
    "full_confirmation_cohort_21": ROOT / "data/official/full_confirmation_cohort_21.json",
    "full_confirmation_progress": ROOT / "data/official/full_confirmation_progress.json",
    "wasp_replicates": ROOT / "data/official/wasp_replicates.json",
    "wasp_confirmation": ROOT / "data/official/wasp_confirmation_100.json",
    "fs011_confirmation": ROOT / "data/official/fs011_confirmation_100.json",
    "fs012_confirmation": ROOT / "data/official/fs012_confirmation_100.json",
}

EXPECTED_20 = {
    "FS001",
    "FS002",
    "FS003",
    "FS004",
    "FS005",
    "FS006",
    "FS007",
    "FS014",
    "FS016",
    "FS018",
    "FS019",
    "FS020",
    "FS021",
    "FS051",
    "FS053",
    "FS054",
    "FS056",
    "FS057",
    "FS058",
    "FS059",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def ids(rows: Iterable[dict[str, str]]) -> list[str]:
    return sorted(row["CaseId"] for row in rows)


def metric_ids(summary: dict[str, Any], key: str) -> set[str]:
    metric = summary["metrics"][key]
    case_ids = set(metric["case_ids"])
    require(metric["count"] == len(case_ids), f"metric {key}: count/id mismatch")
    return case_ids


def status_partition(
    universe: set[str], **groups: set[str]
) -> dict[str, Any]:
    observed: set[str] = set()
    result: dict[str, Any] = {}
    for label, members in groups.items():
        require(not (observed & members), f"status groups overlap at {label}")
        require(members <= universe, f"status group {label} leaves universe")
        observed |= members
        result[label] = {"count": len(members), "case_ids": sorted(members)}
    require(observed == universe, f"status partition missing {sorted(universe-observed)}")
    result["denominator"] = len(universe)
    return result


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def build() -> dict[str, Any]:
    for label, path in INPUTS.items():
        require(path.is_file(), f"missing input {label}: {path}")

    b2_rows = load_csv(INPUTS["b2_generator_outcomes"])
    artifact_location_audit = load_json(INPUTS["artifact_location_audit"])
    static18 = load_json(INPUTS["static_18_summary"])
    summary20 = load_json(INPUTS["repair_20_summary"])
    rows20 = load_csv(INPUTS["repair_20_cases"])
    counter_summary = load_json(INPUTS["counter_race_summary"])
    counter_rows = load_csv(INPUTS["counter_race_cases"])
    developer_summary = load_json(INPUTS["developer_summary"])
    developer_rows = load_csv(INPUTS["developer_cases"])
    coverage67 = load_json(INPUTS["developer_coverage_67"])
    screening = load_json(INPUTS["developer_screening"])
    exact3 = load_json(INPUTS["exact_confirmation_3"])
    full_confirmation_cohort = load_json(INPUTS["full_confirmation_cohort_21"])
    full_confirmation_progress = load_json(INPUTS["full_confirmation_progress"])
    wasp = load_json(INPUTS["wasp_replicates"])
    wasp_confirmation = load_json(INPUTS["wasp_confirmation"])
    fs011_confirmation = load_json(INPUTS["fs011_confirmation"])
    fs012_confirmation = load_json(INPUTS["fs012_confirmation"])
    linkage = load_json(INPUTS["fs057_linkage"])
    repair_contract = load_json(INPUTS["reliability_aware_contract"])

    require(len(b2_rows) == 67, "B2 roster is not 67 rows")
    require(
        artifact_location_audit["row_count"] == 67
        and artifact_location_audit["genuine_archive_blanks"]["Threshold"] == ["FS015"],
        "archived-location blank-threshold accounting changed",
    )
    require(len(rows20) == 20, "repair cohort is not 20 rows")
    by_case = {row["CaseId"]: row for row in rows20}
    require(set(by_case) == EXPECTED_20, "unexpected 20-artifact membership")
    require(summary20["checks"]["failed"] == 0, "20-artifact overlay failed")
    require(static18["cohort"]["cases"] == 18, "static cohort is not 18")
    require(counter_summary["complete_cases"] == 2, "counter-race cohort changed")
    require(len(developer_rows) == 6, "developer comparator is not six rows")
    require(exact3["verification_status"] == "pass", "exact confirmation failed audit")
    require(
        full_confirmation_cohort["case_count"] == 21
        and len(full_confirmation_cohort["cases"]) == 21,
        "full confirmation roster is not 21 cases",
    )
    require(
        full_confirmation_progress["full_confirmation_case_count"] == 21
        and full_confirmation_progress["status"] == "waiting_for_official_20"
        and full_confirmation_progress["cases"] == [],
        "unfinished full confirmation roster status changed",
    )
    require(linkage["status"] == "linked_exact_tuple_to_emitted_source_patch", "FS057 linkage invalid")
    require(
        repair_contract["status"] == "specified-not-implemented-or-evaluated",
        "repair contract status changed",
    )
    require(
        [item["id"] for item in repair_contract["properties"]]
        == [f"P{index}" for index in range(1, 10)],
        "repair contract must contain P1-P9 in order",
    )
    require(
        [item["id"] for item in repair_contract["counter_scenarios"]]
        == [f"C{index}" for index in range(1, 11)],
        "repair contract must contain C1-C10 in order",
    )

    universe = set(by_case)
    local = metric_ids(summary20, "locally_emitted_patch_cases")
    submitted = metric_ids(summary20, "author_submitted_pinned_repairs")
    require(local | submitted == universe and not local & submitted, "provenance partition invalid")

    applied = metric_ids(summary20, "patch_applied")
    compiled = metric_ids(summary20, "compiled")
    ordinary = metric_ids(summary20, "ordinary_gate_passed")
    matched = metric_ids(summary20, "matched_recorded_delay_evaluable")
    effective = metric_ids(summary20, "causal_effective")
    ineffective = metric_ids(summary20, "causal_ineffective")
    signal_eligible = metric_ids(summary20, "signal_loss_probe_eligible")
    signal_hangs = metric_ids(summary20, "signal_loss_hangs")
    fault_eligible = metric_ids(summary20, "signal_loss_causally_eligible")
    fault_hangs = metric_ids(summary20, "fault_specific_signal_loss_hangs")
    cancel_eligible = metric_ids(summary20, "cancellation_probe_eligible")
    cancel_failures = metric_ids(summary20, "confirmed_interruption_failures")
    neighbor_regressions = metric_ids(summary20, "counted_neighbor_regressions")
    complete = metric_ids(summary20, "complete_operational_reliable")

    require(applied == universe, "not all artifacts apply")
    require(effective | ineffective == matched, "causal partition invalid")
    require(signal_hangs <= signal_eligible, "signal hang outside eligibility")
    require(fault_hangs <= fault_eligible, "fault-specific hang outside eligibility")
    require(cancel_failures == cancel_eligible, "cancellation result changed")
    require(not complete, "unexpected completely reliable repair")

    compile_not_pass = universe - compiled
    ordinary_attempted_fail = compiled - ordinary
    ordinary_not_reached = universe - compiled
    matched_not_reached = (universe - compiled) | (compiled - ordinary)
    matched_inconclusive = universe - matched - matched_not_reached

    neighbor_pass = {
        case_id for case_id, row in by_case.items() if row["NeighborComparison"] == "patched-pass"
    }
    neighbor_not_reached = universe - neighbor_pass - neighbor_regressions

    reused_pass = {
        case_id
        for case_id, row in by_case.items()
        if row["CrossTestReusedJvmComparison"] == "patched-pass"
    }
    reused_no_peer = {
        case_id
        for case_id, row in by_case.items()
        if row["CrossTestReusedJvmComparison"] == "unavailable-no-peer"
    }
    reused_not_reached = universe - reused_pass - reused_no_peer

    parallel_pass = {
        case_id
        for case_id, row in by_case.items()
        if row["CrossTestParallelComparison"] == "patched-pass"
    }
    parallel_inconclusive = {
        case_id
        for case_id, row in by_case.items()
        if row["CrossTestParallelComparison"] == "inconclusive-control-not-confirmed-executed"
    }
    parallel_no_peer = {
        case_id
        for case_id, row in by_case.items()
        if row["CrossTestParallelComparison"] == "unavailable-no-peer"
    }
    parallel_not_reached = universe - parallel_pass - parallel_inconclusive - parallel_no_peer

    counter_by_case = {row["CaseId"]: row for row in counter_rows}
    counter_eligible = set(counter_by_case)
    counter_lost = {
        case_id
        for case_id, row in counter_by_case.items()
        if row["NonAtomicLostUpdateWitness"] == "1"
    }
    counter_inconclusive = counter_eligible - counter_lost

    gate_coverage = {
        "apply": status_partition(universe, pass_=applied, fail=universe - applied),
        "compile": status_partition(universe, pass_=compiled, fail=compile_not_pass),
        "ordinary": status_partition(
            universe,
            pass_=ordinary,
            fail=ordinary_attempted_fail,
            not_reached=ordinary_not_reached,
        ),
        "matched_recorded_delay": status_partition(
            universe,
            pass_causal=effective,
            fail_causal=ineffective,
            inconclusive=matched_inconclusive,
            not_reached=matched_not_reached,
        ),
        "signal_loss": status_partition(
            universe,
            fail_hang=signal_hangs,
            pass_bounded=signal_eligible - signal_hangs,
            not_evaluable=universe - signal_eligible,
        ),
        "fault_specific_signal_loss": status_partition(
            universe,
            fail_hang=fault_hangs,
            pass_bounded=fault_eligible - fault_hangs,
            not_evaluable=universe - fault_eligible,
        ),
        "cancellation": status_partition(
            universe,
            fail_ignored_interrupt=cancel_failures,
            pass_bounded=cancel_eligible - cancel_failures,
            not_evaluable=universe - cancel_eligible,
        ),
        "neighbor": status_partition(
            universe,
            fail_regression=neighbor_regressions,
            pass_=neighbor_pass,
            not_reached=neighbor_not_reached,
        ),
        "reused_jvm": status_partition(
            universe,
            pass_=reused_pass,
            unavailable_no_peer=reused_no_peer,
            not_reached=reused_not_reached,
        ),
        "parallel": status_partition(
            universe,
            pass_=parallel_pass,
            inconclusive_execution_not_confirmed=parallel_inconclusive,
            unavailable_no_peer=parallel_no_peer,
            not_reached=parallel_not_reached,
        ),
        "two_writer_counter": status_partition(
            universe,
            fail_lost_update=counter_lost,
            inconclusive_no_pair=counter_inconclusive,
            not_applicable_or_not_probed=universe - counter_eligible,
        ),
        "complete_operational_contract": status_partition(
            universe, pass_=complete, fail=universe - complete
        ),
    }

    # Project clustering is descriptive.  The generated cases share one
    # template, and six of the twenty rows come from one Alluxio revision.
    project_cases: dict[str, list[str]] = defaultdict(list)
    for case_id, row in by_case.items():
        project_cases[row["LedgerCaseSlug"]].append(case_id)

    project_rows: list[dict[str, Any]] = []
    for project, case_ids in sorted(project_cases.items()):
        members = set(case_ids)
        project_rows.append(
            {
                "Project": project,
                "Cases": len(members),
                "CaseIds": ";".join(sorted(members)),
                "LocallyEmitted": len(members & local),
                "AuthorSubmitted": len(members & submitted),
                "Compiled": len(members & compiled),
                "OrdinaryPassed": len(members & ordinary),
                "MatchedDelayEvaluable": len(members & matched),
                "CausalEffective": len(members & effective),
                "CausalIneffective": len(members & ineffective),
                "SignalLossHangs": len(members & signal_hangs),
                "InterruptionFailures": len(members & cancel_failures),
                "NeighborRegressions": len(members & neighbor_regressions),
            }
        )

    def causal_label(case_id: str) -> str:
        if case_id in effective:
            return "effective"
        if case_id in ineffective:
            return "ineffective"
        if case_id in matched_inconclusive:
            return "inconclusive"
        return "not_reached"

    def signal_label(case_id: str) -> str:
        if case_id in signal_hangs:
            return "hang"
        if case_id in signal_eligible:
            return "bounded"
        return "not_evaluable"

    def cancellation_label(case_id: str) -> str:
        if case_id in cancel_failures:
            return "ignored_interrupt_and_hung"
        if case_id in cancel_eligible:
            return "bounded"
        return "not_evaluable"

    case_rows: list[dict[str, Any]] = []
    for case_id in sorted(universe):
        row = by_case[case_id]
        if case_id in neighbor_regressions:
            neighbor = "regression"
        elif case_id in neighbor_pass:
            neighbor = "pass"
        else:
            neighbor = "not_reached"
        if case_id in counter_lost:
            counter = "lost_update"
        elif case_id in counter_inconclusive:
            counter = "inconclusive_no_pair"
        else:
            counter = "not_applicable_or_not_probed"
        case_rows.append(
            {
                "CaseId": case_id,
                "Project": row["LedgerCaseSlug"],
                "Provenance": row["ArtifactProvenance"],
                "Applied": "pass" if case_id in applied else "fail",
                "Compiled": "pass" if case_id in compiled else "fail",
                "Ordinary": (
                    "pass"
                    if case_id in ordinary
                    else "fail"
                    if case_id in ordinary_attempted_fail
                    else "not_reached"
                ),
                "CausalReplay": causal_label(case_id),
                "SignalLoss": signal_label(case_id),
                "Cancellation": cancellation_label(case_id),
                "Neighbor": neighbor,
                "CounterRace": counter,
                "Overall": "unreliable",
                "KnownFailures": row["OperationalFailureReasonsV2"],
                "Unknowns": row["OperationalUnknownReasonsV2"],
            }
        )

    # Group strict developer comparator rows by independent design, rather than
    # pretending four applications of the Alluxio design are four designs.
    developer_designs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in developer_rows:
        developer_designs[row["DesignId"]].append(row)
    require(len(developer_designs) == 3, "developer design count changed")
    developer_design_rows: list[dict[str, Any]] = []
    for design_id, rows in sorted(developer_designs.items()):
        case_ids = sorted(row["CaseId"] for row in rows)
        projects = sorted({row["ProjectSlug"] for row in rows})
        require(len(projects) == 1, f"design {design_id} spans unexpected projects")
        developer_design_rows.append(
            {
                "DesignId": design_id,
                "Project": projects[0],
                "CaseInstances": len(rows),
                "CaseIds": ";".join(case_ids),
                "AllApplied": all(row["PatchApplied"] == "1" for row in rows),
                "AllCompiled": all(row["Compiled"] == "1" for row in rows),
                "AllOrdinary10Of10": all(row["OrdinaryPassed"] == "10" for row in rows),
                "CausalEffectiveCases": sum(
                    row["CausalEffectivenessEstablished"] == "1" for row in rows
                ),
                "CausalIneffectiveCases": sum(
                    row["CausalIneffectivenessWitness"] == "1" for row in rows
                ),
                "ExactOriginalInstances": sum(
                    row["ExactOriginalPatch"].lower() == "true" for row in rows
                ),
                "Relations": ";".join(sorted({row["Relation"] for row in rows})),
            }
        )

    b2_outcomes = Counter(row["Outcome"] for row in b2_rows)
    require(
        b2_outcomes
        == {
            "usable-patch-emitted": 14,
            "no-usable-patch-emitted": 43,
            "patch-goal-nonzero": 8,
            "no-usable-patch-with-workspace-restoration-defect": 2,
        },
        f"B2 outcomes changed: {b2_outcomes}",
    )
    b2_emitted_projects = {
        row["Slug"] for row in b2_rows if row["Outcome"] == "usable-patch-emitted"
    }
    require(len(b2_emitted_projects) == 9, "B2 emitted-project count changed")

    exact_cases = {row["case_id"]: row for row in exact3["cases"]}
    require(set(exact_cases) == {"FS014", "FS055", "FS057"}, "exact cohort changed")
    require(exact_cases["FS055"]["paper_success_confirmed"], "FS055 no longer exact")
    require(exact_cases["FS057"]["paper_success_confirmed"], "FS057 no longer exact")
    require(not exact_cases["FS014"]["paper_success_confirmed"], "FS014 unexpectedly exact")
    require(wasp["completed_replicates"] == 10 and wasp["exact_replicates"] == 0, "Wasp changed")
    require(wasp_confirmation["passing_runs"] == 100, "Wasp confirmation changed")
    require(fs011_confirmation["passing_runs"] == 0, "FS011 confirmation changed")
    require(
        fs012_confirmation["passing_runs"] == 20
        and fs012_confirmation["first_failure_run"] == 21,
        "FS012 confirmation changed",
    )

    flow_rows = [
        {
            "EvidenceLayer": "paper",
            "Stage": "reported asynchronous tests",
            "Count": 80,
            "Denominator": 80,
            "Meaning": "published population; not re-estimated here",
        },
        {
            "EvidenceLayer": "paper",
            "Stage": "reported repaired tests",
            "Count": 67,
            "Denominator": 80,
            "Meaning": "published 67/80 result",
        },
        {
            "EvidenceLayer": "B2 patch-goal census",
            "Stage": "quota-consistent repaired identities attempted",
            "Count": 67,
            "Denominator": 67,
            "Meaning": "archived locations; not end-to-end search reproduction",
        },
        {
            "EvidenceLayer": "B2 patch-goal census",
            "Stage": "usable patch pairs emitted",
            "Count": 14,
            "Denominator": 67,
            "Meaning": "14 cases across nine projects",
        },
        {
            "EvidenceLayer": "local source-patch exposure cohort",
            "Stage": "locally emitted cases after root-reactor extension",
            "Count": 18,
            "Denominator": 67,
            "Meaning": "two acquisition tracks; descriptive exposure count",
        },
        {
            "EvidenceLayer": "provenance-separated artifact cohort",
            "Stage": "local emissions plus author submissions evaluated",
            "Count": 20,
            "Denominator": 20,
            "Meaning": "18 local plus two author-submitted repairs",
        },
        {
            "EvidenceLayer": "exact official runtime cohort",
            "Stage": "exact tuples confirmed 100/100",
            "Count": 2,
            "Denominator": 3,
            "Meaning": "FS055 and FS057; FS014 failed on run 2",
        },
        {
            "EvidenceLayer": "strict developer comparison",
            "Stage": "case instances dynamically evaluated",
            "Count": 6,
            "Denominator": 6,
            "Meaning": "three independent designs; five backports and one exact diff",
        },
    ]

    gate_rows: list[dict[str, Any]] = []
    for gate, partition in gate_coverage.items():
        denominator = partition["denominator"]
        for status, payload in partition.items():
            if status == "denominator":
                continue
            gate_rows.append(
                {
                    "Gate": gate,
                    "Status": status.removesuffix("_"),
                    "Count": payload["count"],
                    "Denominator": denominator,
                    "CaseIds": ";".join(payload["case_ids"]),
                }
            )

    # These categories deliberately keep structural exposure and dynamic
    # confirmation in separate columns.
    problem_rows = [
        {
            "Category": "generation_safety",
            "StructuralExposure": "18/18 generated diffs have absolute headers; 2/18 have unbraced insertion capture",
            "DynamicOrBuildWitness": "4/20 did not compile",
            "Cases": ";".join(sorted(compile_not_pass)),
            "ClaimScope": "generator and emitted-artifact defect",
        },
        {
            "Category": "causal_mismatch",
            "StructuralExposure": "entry reset can erase an early signal in 18/18 generated cases",
            "DynamicOrBuildWitness": "10/12 evaluable artifacts ineffective; 2/12 effective",
            "Cases": ";".join(sorted(ineffective)),
            "ClaimScope": "matched recorded-delay replay",
        },
        {
            "Category": "negative_progress",
            "StructuralExposure": "unbounded busy-yield wait in 20/20 artifacts",
            "DynamicOrBuildWitness": "8/13 eligible signal-loss probes hung; 5/10 fault-specific",
            "Cases": ";".join(sorted(signal_hangs)),
            "ClaimScope": "bounded, witnessed signal-suppression scenarios",
        },
        {
            "Category": "cancellation_failure",
            "StructuralExposure": "missing interruption path in 20/20 artifacts",
            "DynamicOrBuildWitness": "7/7 eligible interruption probes hung",
            "Cases": ";".join(sorted(cancel_failures)),
            "ClaimScope": "suppression and direct interrupt both witnessed",
        },
        {
            "Category": "memory_and_multiwriter_safety",
            "StructuralExposure": "non-atomic volatile++ in 18/18 generated cases; one non-volatile submitted flag",
            "DynamicOrBuildWitness": "1 lost update in 1 confirmed two-writer rendezvous; second eligible case inconclusive",
            "Cases": ";".join(sorted(counter_lost)),
            "ClaimScope": "threshold>1 generated cases only",
        },
        {
            "Category": "state_lifecycle_and_interference",
            "StructuralExposure": "shared static state and missing robust invocation lifecycle in 20/20 artifacts",
            "DynamicOrBuildWitness": "1/14 reached neighbor probes regressed; FS059 hung in 8/10 fresh patched class runs",
            "Cases": ";".join(sorted(neighbor_regressions)),
            "ClaimScope": "case-specific differential regression, not cohort prevalence",
        },
    ]

    input_manifest = {
        label: {
            "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for label, path in INPUTS.items()
    }

    result: dict[str, Any] = {
        "schema_version": "flakesync-research-questions-analysis-v3",
        "status": "pass",
        "claim_boundary": {
            "paper_67_of_80_not_reestimated": True,
            "official_runtime_confirmation_separate_from_source_patch_reliability": True,
            "twenty_artifacts_are_eighteen_local_plus_two_author_submissions": True,
            "case_counts_are_descriptive_and_clustered": True,
            "no_independent_case_confidence_intervals": True,
            "unknown_is_not_failure_and_not_pass": True,
            "developer_case_instances_are_not_independent_designs": True,
        },
        "units": {
            "paper_population": {"tests": 80, "reported_repairs": 67},
            "b2_patch_goal": {
                "attempted_cases": 67,
                "usable_patch_cases": 14,
                "usable_patch_projects": 9,
                "genuine_blank_threshold_cases": ["FS015"],
                "outcomes": dict(sorted(b2_outcomes.items())),
            },
            "local_source_patch_cohort": {
                "cases": len(local),
                "projects": len({by_case[c]["LedgerCaseSlug"] for c in local}),
                "normalized_generator_templates": 1,
                "case_ids": sorted(local),
            },
            "combined_artifact_cohort": {
                "cases": len(universe),
                "projects": len(project_cases),
                "local_emissions": len(local),
                "author_submissions": len(submitted),
                "case_ids": sorted(universe),
            },
            "developer_comparison": {
                "case_instances": len(developer_rows),
                "independent_designs": len(developer_designs),
                "projects": len({row["ProjectSlug"] for row in developer_rows}),
                "case_ids": sorted(row["CaseId"] for row in developer_rows),
            },
        },
        "official_runtime_reproduction": {
            "completed_speed_confirmation_cohort": {
                "cases": 3,
                "confirmed_100_of_100": ["FS055", "FS057"],
                "failed_before_100": {"FS014": "1/2; assertion failure on run 2"},
            },
            "unfinished_full_confirmation_roster": {
                "declared_cases": 21,
                "status": "waiting_for_official_20",
                "terminal_case_dispositions": 0,
            },
            "alternative_tuples": {
                "WASP_FS016": "100/100; alternative tuple; archive tuple 0/10",
                "FS011": "0/1; alternative tuple",
                "FS012": "20/21; alternative tuple; failure on run 21",
            },
            "exact_runtime_to_source_linkage": {
                "cases": ["FS057"],
                "checks_passed": sum(bool(value) for value in linkage["checks"].values()),
                "checks_total": len(linkage["checks"]),
            },
        },
        "headline_20_artifact_metrics": {
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
        "headline_18_local_metrics": {
            "applied": f"{len(applied & local)}/18",
            "compiled": f"{len(compiled & local)}/18",
            "ordinary_pass": f"{len(ordinary & local)}/18",
            "matched_delay_evaluable": f"{len(matched & local)}/18",
            "causal_effective": f"{len(effective & local)}/{len(matched & local)}",
            "causal_ineffective": f"{len(ineffective & local)}/{len(matched & local)}",
            "signal_loss_hang": f"{len(signal_hangs & local)}/{len(signal_eligible & local)}",
            "fault_specific_signal_loss_hang": f"{len(fault_hangs & local)}/{len(fault_eligible & local)}",
            "interruption_failure": f"{len(cancel_failures & local)}/{len(cancel_eligible & local)}",
            "neighbor_regression": (
                f"{len(neighbor_regressions & local)}/"
                f"{len((neighbor_pass | neighbor_regressions) & local)} reached; "
                f"{len(neighbor_regressions & local)}/18 cohort-wide"
            ),
            "complete_operational_contract": f"{len(complete & local)}/18",
        },
        "gate_coverage": gate_coverage,
        "static_patterns": {
            "generated_cases": static18["case_detector_counts"],
            "harmonized_twenty": summary20["harmonized_static_patterns"],
            "author_submitted": summary20["static"]["author_submitted_repair"],
        },
        "counter_race": {
            "eligible_cases": sorted(counter_eligible),
            "two_writer_pairs_confirmed": counter_summary["two_writer_pairs_confirmed"],
            "lost_update_witnesses": counter_summary["non_atomic_lost_update_witnesses"],
            "classifications": counter_summary["classifications"],
        },
        "developer_comparison": {
            "coverage_67_status": coverage67["status"],
            "strict_case_instances": 6,
            "strict_independent_designs": 3,
            "all_applied_compiled_ordinary_10_of_10": True,
            "causal_effective_cases": 3,
            "causal_ineffective_cases": 3,
            "template_detector_positives": 0,
            "designs": developer_design_rows,
            "screened_context_cases": [
                {
                    "case_id": decision["case_id"],
                    "classification": decision["classification"],
                    "strict_comparator_admitted": decision["strict_comparator_admitted"],
                    "reason": decision["reason"],
                }
                for decision in screening["decisions"]
            ],
        },
        "specificity_analysis": {
            "released_generator_template": {
                "evidence": (
                    "18/18 locally emitted cases instantiate shared static mutable "
                    "counters, non-atomic volatile increments, unbounded Thread.yield "
                    "waits, no interruption path, entry-only reset, and production "
                    "test hooks; the six strict developer-fix case instances, "
                    "representing three independent designs, trigger none of these "
                    "normalized template detectors"
                ),
                "classification": "FlakeSync released-template problem",
                "claim": (
                    "The repeated counter/yield/lifecycle hazards are attributable to "
                    "the observed FlakeSync template, not evidence that every async-test "
                    "repair must have those structures."
                ),
            },
            "flakesync_author_family_extension": {
                "evidence": (
                    "Both author-submitted pinned repairs replace the integer counter "
                    "with a shared static boolean but retain an unbounded yield wait, "
                    "missing interruption, and missing per-invocation lifecycle; FS054 "
                    "dynamically hung under witnessed signal suppression and interruption."
                ),
                "classification": "FlakeSync-family design problem beyond one counter syntax",
                "claim": (
                    "The liveness and lifecycle problem is not confined to volatile++ "
                    "within the FlakeSync repair family."
                ),
            },
            "broader_repair_validation": {
                "evidence": (
                    "10/12 evaluable FlakeSync-generated or author artifacts and 3/6 "
                    "strict developer-fix instances were ineffective under matched "
                    "recorded-delay controls; all six developer instances nevertheless "
                    "applied, compiled, and passed 10/10 ordinary executions."
                ),
                "classification": "general validation and schedule-overfitting problem",
                "claim": (
                    "Ordinary passing behavior is insufficient evidence of causal repair "
                    "for either generated or developer-written fixes."
                ),
            },
            "inference_limit": (
                "The developer evidence represents six case instances but only three "
                "independent designs in three projects. It supports a cross-provenance "
                "mechanism observation, not a prevalence estimate for developer fixes, "
                "all async repairs, or all automated program repair systems."
            ),
        },
        "reliability_contract": {
            "source_status": repair_contract["status"],
            "implemented_or_evaluated": False,
            "verdict_logic": {
                "pass": "all applicable properties pass under declared checks",
                "fail": "at least one direct contract violation or witnessed failure",
                "unknown": "no established failure but one or more required checks lack valid evidence",
            },
            "properties": [
                "artifact_integrity_and_buildability",
                "ordinary_behavior_preservation",
                "causal_effectiveness",
                "bounded_progress",
                "memory_and_multiwriter_safety",
                "invocation_isolation_and_noninterference",
                "cancellation_interruption_and_cleanup",
                "behavioral_fidelity_and_oracle_preservation",
                "repeatability_under_declared_positive_and_counter_scenarios",
            ],
            "property_definitions": [
                {"id": item["id"], "name": item["name"]}
                for item in repair_contract["properties"]
            ],
            "counter_scenarios": [
                {"id": item["id"], "name": item["name"]}
                for item in repair_contract["counter_scenarios"]
            ],
            "candidate_strategy_order": [
                item["strategy"]
                for item in repair_contract["candidate_generation"]["ordered_strategy"]
            ],
            "held_out_required": True,
            "non_guarantees": repair_contract["non_guarantees"],
        },
        "clustering": {
            "twenty_projects": len(project_cases),
            "largest_project": "Alluxio/alluxio",
            "largest_project_cases": len(project_cases["Alluxio/alluxio"]),
            "local_generated_templates": 1,
            "developer_independent_designs": 3,
            "inference_rule": "report case, project, and design units; do not treat rows as independent Bernoulli trials",
        },
        "inputs": input_manifest,
        "outputs": {
            "summary": "results/summary.json",
            "cohort_flow": "results/cohort_flow.csv",
            "gate_coverage": "results/gate_coverage.csv",
            "case_matrix": "results/case_reliability_matrix.csv",
            "project_clusters": "results/project_clusters.csv",
            "problem_categories": "results/problem_categories.csv",
            "developer_designs": "results/developer_designs.csv",
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUT / "cohort_flow.csv",
        flow_rows,
        ["EvidenceLayer", "Stage", "Count", "Denominator", "Meaning"],
    )
    write_csv(
        OUT / "gate_coverage.csv",
        gate_rows,
        ["Gate", "Status", "Count", "Denominator", "CaseIds"],
    )
    write_csv(
        OUT / "case_reliability_matrix.csv",
        case_rows,
        [
            "CaseId",
            "Project",
            "Provenance",
            "Applied",
            "Compiled",
            "Ordinary",
            "CausalReplay",
            "SignalLoss",
            "Cancellation",
            "Neighbor",
            "CounterRace",
            "Overall",
            "KnownFailures",
            "Unknowns",
        ],
    )
    write_csv(
        OUT / "project_clusters.csv",
        project_rows,
        [
            "Project",
            "Cases",
            "CaseIds",
            "LocallyEmitted",
            "AuthorSubmitted",
            "Compiled",
            "OrdinaryPassed",
            "MatchedDelayEvaluable",
            "CausalEffective",
            "CausalIneffective",
            "SignalLossHangs",
            "InterruptionFailures",
            "NeighborRegressions",
        ],
    )
    write_csv(
        OUT / "problem_categories.csv",
        problem_rows,
        ["Category", "StructuralExposure", "DynamicOrBuildWitness", "Cases", "ClaimScope"],
    )
    write_csv(
        OUT / "developer_designs.csv",
        developer_design_rows,
        [
            "DesignId",
            "Project",
            "CaseInstances",
            "CaseIds",
            "AllApplied",
            "AllCompiled",
            "AllOrdinary10Of10",
            "CausalEffectiveCases",
            "CausalIneffectiveCases",
            "ExactOriginalInstances",
            "Relations",
        ],
    )

    summary_path = OUT / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


if __name__ == "__main__":
    built = build()
    print(
        json.dumps(
            {
                "status": built["status"],
                "output": str(OUT / "summary.json"),
                "cases": built["units"]["combined_artifact_cohort"]["cases"],
                "projects": built["units"]["combined_artifact_cohort"]["projects"],
            },
            sort_keys=True,
        )
    )
