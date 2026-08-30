#!/usr/bin/env python3
"""Fail-closed integrity, completeness, link, and privacy checks."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {
    ".a", ".bin", ".class", ".dll", ".dylib", ".exe", ".gz", ".idx",
    ".jar", ".jks", ".key", ".o", ".p12", ".pack", ".pem", ".pyc",
    ".pyo", ".so", ".tar", ".war", ".wasm", ".zip",
}
FORBIDDEN_PARTS = {
    ".agents", ".codex", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".venv", "__pycache__", "build_cache", "logs", "node_modules", "target",
    "workspaces",
}
FORBIDDEN_NAMES = {".DS_Store", "AGENTS.md", "SKILL.md"}
ALLOWED_MARKDOWN = {Path("README.md"), Path("THIRD_PARTY.md")}
SECRET_PATTERNS = {
    "GitHub token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Slack token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}"),
}
PRIVATE_PATH_PATTERNS = (
    b"/" + b"home" + b"/",
    b"/" + b"Users" + b"/",
    b"C:" + b"\\" + b"Users" + b"\\",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def public_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            raise AssertionError(f"symlink is not allowed: {relative}")
        if path.is_file():
            files.append(path)
    return sorted(files)


def verify_file_policy() -> None:
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts:
            continue
        require(not path.is_symlink(), f"symlink is not allowed: {relative}")
        require(not (set(relative.parts) & FORBIDDEN_PARTS), f"forbidden artifact directory: {relative}")
        require(path.name not in FORBIDDEN_NAMES, f"forbidden artifact file: {relative}")
    for path in public_files():
        relative = path.relative_to(ROOT)
        if path.suffix.lower() in {".md", ".markdown"}:
            require(relative in ALLOWED_MARKDOWN, f"irrelevant Markdown file: {relative}")
        require(path.stat().st_size <= 5_000_000, f"unexpected large file: {relative}")
        require(path.suffix.lower() not in FORBIDDEN_SUFFIXES, f"forbidden file type: {relative}")
        payload = path.read_bytes()
        require(b"\0" not in payload, f"binary NUL byte in {relative}")
        try:
            payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AssertionError(f"non-UTF-8 file in text-only release: {relative}") from exc
        for marker in PRIVATE_PATH_PATTERNS:
            require(marker not in payload, f"absolute private path in {relative}: {marker!r}")
        for label, pattern in SECRET_PATTERNS.items():
            require(pattern.search(payload) is None, f"possible {label} in {relative}")


def verify_source_manifest() -> None:
    rows = csv_rows(ROOT / "data/source_file_manifest.csv")
    require(len(rows) == 29, f"expected 29 frozen source files, found {len(rows)}")
    for row in rows:
        path = ROOT / row["published_path"]
        require(path.is_file(), f"missing frozen source: {row['published_path']}")
        require(path.stat().st_size == int(row["published_bytes"]), f"size mismatch: {path}")
        require(sha256(path) == row["published_sha256"], f"hash mismatch: {path}")


def verify_patch_manifests() -> None:
    generated = csv_rows(ROOT / "patches/generated_manifest.csv")
    comparators = csv_rows(ROOT / "patches/comparator_manifest.csv")
    require(len(generated) == 36, f"expected 36 generated patch files, found {len(generated)}")
    require(len({row["CaseId"] for row in generated}) == 18, "generated patches must cover 18 cases")
    require(len(comparators) == 8, f"expected eight comparator patch files, found {len(comparators)}")
    require(sum(row["Provenance"].startswith("author") for row in comparators) == 2, "author repair count changed")
    require(sum(row["Provenance"].startswith("developer") for row in comparators) == 6, "developer comparator count changed")
    for row in generated + comparators:
        path = ROOT / row["PublishedPatch"]
        require(path.is_file(), f"missing patch: {row['PublishedPatch']}")
        require(path.stat().st_size == int(row["PublishedBytes"]), f"patch size mismatch: {path}")
        require(sha256(path) == row["PublishedSha256"], f"patch hash mismatch: {path}")


def verify_reliable_repairs() -> None:
    result = json.loads((ROOT / "results/reliable_repairs.json").read_text(encoding="utf-8"))
    require(result["status"] == "pass", "reliable-repair result is not pass")
    require(
        result["manual_candidates"]
        == {"count": 5, "case_ids": ["FS005", "FS014", "FS020", "FS056", "FS059"]},
        "manual repair candidate roster changed",
    )
    require(
        result["successful_reliable_repairs"]
        == {"count": 3, "case_ids": ["FS005", "FS014", "FS059"]},
        "successful reliable-repair roster changed",
    )
    require(
        result["rejected_candidates"]
        == {"count": 2, "case_ids": ["FS020", "FS056"]},
        "rejected reliable-repair roster changed",
    )
    for case_id, case in result["cases"].items():
        patch = ROOT / case["patch"]["path"]
        validation = ROOT / case["validation"]["path"]
        require(patch.is_file(), f"{case_id}: missing reliable-repair patch")
        require(validation.is_file(), f"{case_id}: missing reliable-repair validation")
        require(sha256(patch) == case["patch"]["sha256"], f"{case_id}: reliable patch hash")
        require(sha256(validation) == case["validation"]["sha256"], f"{case_id}: validation hash")
    rows = csv_rows(ROOT / "results/reliable_repairs.csv")
    require([row["CaseId"] for row in rows] == ["FS005", "FS014", "FS020", "FS056", "FS059"], "reliable CSV roster")
    require(sum(row["OverallVerdict"] == "pass" for row in rows) == 3, "reliable CSV success count")


def verify_readme_links() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    require(bool(targets), "README has no links")
    for target in targets:
        if target.startswith(("https://", "http://", "mailto:", "#")):
            continue
        local = target.split("#", 1)[0]
        require(local, f"empty README link target: {target}")
        path = Path(local)
        require(not path.is_absolute() and ".." not in path.parts, f"unsafe README link: {target}")
        resolved = (ROOT / path).resolve()
        require(resolved.is_relative_to(ROOT.resolve()), f"README link escapes repository: {target}")
        require(resolved.exists(), f"broken README link: {target}")


def verify_scientific_counts() -> None:
    require(len(csv_rows(ROOT / "data/generation/case_outcomes_67.csv")) == 67, "generation roster changed")
    require(len(csv_rows(ROOT / "data/corpus/paper_success_cases_67.csv")) == 67, "paper-success roster changed")
    require(len(csv_rows(ROOT / "data/reliability/repair_case_findings.csv")) == 20, "repair cohort changed")
    require(len(csv_rows(ROOT / "data/developer/case_matrix.csv")) == 6, "developer case matrix changed")

    summary = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
    require(summary["status"] == "pass", "analysis status is not pass")
    require(summary["units"]["local_source_patch_cohort"]["cases"] == 18, "local patch count changed")
    require(summary["units"]["combined_artifact_cohort"]["cases"] == 20, "combined cohort changed")
    require(summary["units"]["combined_artifact_cohort"]["projects"] == 13, "project count changed")
    require(summary["headline_20_artifact_metrics"]["causal_effective"] == "2/12", "causal result changed")
    require(summary["headline_20_artifact_metrics"]["complete_operational_contract"] == "0/20", "contract result changed")
    reliable = json.loads((ROOT / "results/reliable_repairs.json").read_text(encoding="utf-8"))
    require(reliable["manual_candidates"]["count"] == 5, "manual candidate count changed")
    require(reliable["successful_reliable_repairs"]["count"] == 3, "reliable repair count changed")


def verify_deterministic_results() -> None:
    result_paths = sorted((ROOT / "results").glob("*"))
    before = {path.name: sha256(path) for path in result_paths if path.is_file()}
    subprocess.run([sys.executable, str(ROOT / "scripts/build_analysis.py")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(ROOT / "scripts/build_reliable_repairs.py")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    result_paths = sorted((ROOT / "results").glob("*"))
    after = {path.name: sha256(path) for path in result_paths if path.is_file()}
    require(before == after, "derived results are not deterministic")


def verify() -> None:
    verify_file_policy()
    verify_readme_links()
    verify_source_manifest()
    verify_patch_manifests()
    verify_reliable_repairs()
    verify_scientific_counts()
    verify_deterministic_results()


if __name__ == "__main__":
    verify()
    print("release verification: PASS")
