# FlakeSync repair-reliability artifact

This is the compact evidence package for our FlakeSync repair-reliability study. It contains the frozen data, repair patches, reliability contract, final analysis script, and tests. It intentionally excludes the 6.6 GB raw execution archive, cloned projects, build caches, logs, containers, and paper/professor writeups.

## Keep these evidence units separate

| Evidence unit | What it means |
|---|---|
| 67 cases | Paper-reported success cases on which we attempted the released artifact's patch-generation goal. This is not 67 locally reproduced repairs. |
| 18 cases | Cases for which our local runs emitted FlakeSync source patches. This is not 18 exact end-to-end reproductions of the paper workflow. |
| 20 cases | The reliability cohort: 18 local emissions plus 2 author-submitted FlakeSync repairs. |
| 6 case instances / 3 designs | Independently developer-written comparators evaluated separately from FlakeSync repairs. |
| Exact runtime confirmations | FS055 and FS057 passed 100/100; FS014 failed one of two runs. Only FS057 currently has the audited runtime-to-emitted-source bridge (61/61 checks). |

The paper's reported 67/80 result is prior work and is not re-estimated here.

## Result snapshot

The 20-artifact reliability cohort produced these gate-specific results:

| Check | Result |
|---|---:|
| Patch applied | 20/20 |
| Compiled | 16/20 |
| Passed ordinary runs | 14/20 |
| Evaluable under matched recorded-delay replay | 12/20 |
| Causally effective in that replay | 2/12 |
| Hung under signal loss | 8/13 eligible |
| Failed interruption handling | 7/7 eligible |
| Satisfied the complete operational contract | 0/20 |

The denominators change because a check is counted only when its prerequisite gate and intervention witness were established. Unknown, not-reached, and unavailable outcomes remain explicit in the data.

## Verify the artifact

Python 3.10 or newer is sufficient; the analysis uses only the standard library.

```bash
python3 scripts/build_analysis.py
python3 -m unittest discover -s tests -v
python3 scripts/verify_release.py
git diff --exit-code
```

The first command deterministically regenerates the seven files in [`results/`](results). Continuous integration runs the same checks on every push and pull request.

## Repository map

- [`data/generation/case_outcomes_67.csv`](data/generation/case_outcomes_67.csv): all 67 patch-generation outcomes.
- [`data/reliability/repair_case_findings.csv`](data/reliability/repair_case_findings.csv): the 20-case reliability matrix used by the analysis.
- [`data/official/`](data/official): frozen official-workflow confirmation summaries.
- [`patches/`](patches): 36 locally emitted source-file patches, 2 author-submitted repairs, and 6 developer-comparator instances, with raw and published hashes.
- [`contract/reliability_contract.json`](contract/reliability_contract.json): nine reliability properties and ten counter-scenarios.
- [`results/summary.json`](results/summary.json): machine-readable synthesis and explicit claim boundaries.
- [`results/problem_categories.csv`](results/problem_categories.csv): observed reliability-problem categories and evidence scope.
- [`scripts/build_analysis.py`](scripts/build_analysis.py): deterministic synthesis.

This is an analysis capsule, not a full VM or container replay package. Frozen summaries are hash-bound in [`data/source_file_manifest.csv`](data/source_file_manifest.csv). Private filesystem roots were replaced with stable placeholders. Generated patch headers retain their original absolute-path shape with only the private root redacted; patch hunks are unchanged, and both original and published hashes are recorded.

This repository is currently private and grants no project-level reuse license. Patch excerpts remain subject to their upstream projects' terms; attribution and copied license/notice files are in [`THIRD_PARTY.md`](THIRD_PARTY.md).
