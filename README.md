# FlakeSync repair-reliability artifact

My main focus in this study was to answer one question: can a FlakeSync-style repair remain reliable when thread timing changes, completion is missed, interruption occurs, or tests share a process?

This repository is the compact, private evidence package for that study. It contains the frozen inputs, repair patches, sanitized validation ledgers, deterministic analysis scripts, derived results, tests, and licensing notices needed to audit the reported claims.

## What was studied

Keep these four evidence units separate:

| Evidence unit | Exact scope |
|---|---|
| 67 attempted patch generations | The 67 paper-reported success cases on which we attempted the released artifact's patch-generation goal. This is not 67 locally reproduced repairs. |
| 18 usable generated-patch cases | Fourteen cases emitted usable patches in the main artifact-location run, and four more did so in an experimental root-reactor replay. This is not 18 reliable repairs. |
| 6 developer-fix case instances | The comparison set contains six case instances representing three independent repair designs. It is evaluated separately from FlakeSync-generated and manually designed repairs. |
| 5 manual repair candidates | FS005, FS014, FS020, FS056, and FS059 were selected as case studies. Three passed the declared reliability gates; two were rejected at the causal-effectiveness gate. |

The paper's reported 67 repairs among 80 flaky tests is a prior-work result. This study does not re-estimate that result.

## Three reliable repairs

FS005, FS014, and FS059 met the case-specific reliability definition. Each patch applied and compiled, passed 100/100 ordinary runs, recreated the original failure in 5/5 matched unpatched controls, passed 5/5 repaired runs under the same trigger, and passed the additional checks that were applicable and executed.

| Case | Ordinary runs | Matched recorded-delay replay | Additional evidence |
|---|---:|---:|---|
| FS005 | 100/100 pass | unpatched 5/5 non-pass; repaired 5/5 pass | bounded missing-completion behavior, interruption propagation, 24/24 neighboring methods, 10 target runs in one JVM with a peer, and witnessed parallel overlap |
| FS014 | 100/100 pass | unpatched 5/5 non-pass; repaired 5/5 pass | bounded missing-completion behavior, interruption propagation, 5/5 neighbor runs, reused-JVM repetitions, and five witnessed parallel rounds |
| FS059 | 100/100 pass | unpatched 5/5 non-pass; repaired 5/5 pass | bounded missing-publication behavior, interruption propagation, 5/5 neighbor runs, and 10/10 reused-JVM runs; parallel overlap remains `unknown` |

The aggregate result is in [`results/reliable_repairs.json`](results/reliable_repairs.json), with the same five cases in [`results/reliable_repairs.csv`](results/reliable_repairs.csv). The validation rule is frozen in [`contract/manual_repair_validation_protocol.json`](contract/manual_repair_validation_protocol.json).

The other two candidates were not counted as reliable repairs:

| Case | Causal result | Disposition |
|---|---:|---|
| FS020 | repaired candidate failed 5/5 matched runs | Reordering weakened the intended contention and still could not satisfy the unchanged 10-second completion oracle under the 12.8-second injected delay. |
| FS056 | repaired candidate failed the first confirmed matched run | The event-based completion requirement could not fit inside the unchanged 20-second test oracle; the stopping rule rejected the candidate after one confirmed non-pass. |

These are five selected case studies, not an effectiveness estimate for the 67 attempted cases or the 18 generated-patch cases. `unknown` remains distinct from pass and fail. A successful result also does not claim correctness under every possible Java schedule.

## Verify the artifact

Python 3.10 or newer is sufficient. The release analysis uses only the standard library and does not require Maven, Docker, cloned projects, or network access.

```bash
python3 -B scripts/build_analysis.py
python3 -B scripts/build_reliable_repairs.py
python3 -B -m unittest discover -s tests -v
python3 -B scripts/verify_release.py
git diff --exit-code
```

The first two commands deterministically regenerate every checked-in file under [`results/`](results). The release verifier checks file hashes, quantitative invariants, patch and validation provenance, README links, private path and secret patterns, allowed file types, and the absence of caches, binaries, workspace data, and irrelevant Markdown. Continuous integration runs the same sequence.

## Repository map

- [`data/generation/case_outcomes_67.csv`](data/generation/case_outcomes_67.csv): all 67 attempted patch-generation outcomes from the main run.
- [`data/static/generated_patch_summary.json`](data/static/generated_patch_summary.json): the 18 usable generated-patch cases, split into 14 main-run and 4 replay cases.
- [`data/developer/case_matrix.csv`](data/developer/case_matrix.csv): six developer-fix case instances; [`results/developer_designs.csv`](results/developer_designs.csv) groups them into three independent designs.
- [`data/reliable_repairs/validations/`](data/reliable_repairs/validations): sanitized, hash-bound validation ledgers for all five manual candidates.
- [`patches/reliable/`](patches/reliable): the exact five manual candidate patches, including the two rejected candidates for auditability.
- [`results/reliable_repairs.json`](results/reliable_repairs.json) and [`results/reliable_repairs.csv`](results/reliable_repairs.csv): the five-case aggregate and the three successful reliable repairs.
- [`results/summary.json`](results/summary.json): the separate generated/author repair analysis, including the 18 local emissions and two author-submitted repairs. Its combined 20-artifact denominator is not the manual-repair denominator.
- [`contract/reliability_contract.json`](contract/reliability_contract.json): the broader nine-property reliability contract and ten counter-scenarios.
- [`scripts/`](scripts): all scripts required to rebuild and verify the checked-in release results.
- [`data/source_file_manifest.csv`](data/source_file_manifest.csv): original and published hashes for every sanitized frozen source input.

The repository intentionally excludes the multi-gigabyte raw execution archive, cloned project workspaces, build caches, raw logs, compiled probes, containers, and paper or professor writeups. The compact ledgers retain the verdicts, bounds, counted outcomes, causal witnesses, original source hashes, and sanitization records needed to audit the claims; they are not a full VM replay package.

This repository is private and grants no project-level reuse license. Patch excerpts remain subject to their upstream projects' terms; attribution and retained license or notice files are documented in [`THIRD_PARTY.md`](THIRD_PARTY.md).
