#!/usr/bin/env python3
"""Render machine-readable real-run and effectiveness evidence coverage."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from evidence_contract import (
    contract_digest_at,
    current_contract_digest,
    valid_source_commit,
)


ROOT = Path(__file__).resolve().parents[1]
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
RUNS = ROOT / "conformance" / "runs" / "assistant-results" / "index.json"
SUITE = ROOT / "conformance" / "benchmarks" / "benchmark-task-suite.json"
RESULTS = ROOT / "conformance" / "benchmarks" / "results"
OUTPUT = ROOT / "conformance" / "evidence-status.json"


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def source_version(commit: str) -> str:
    if not valid_source_commit(commit):
        return "unavailable"
    result = subprocess.run(
        ["git", "show", f"{commit}:VERSION"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def evidence_state(
    source_version_value: str,
    source_digest: str | None,
    current_version: str,
    current_digest: str,
) -> str:
    if source_digest is None:
        return "unavailable"
    if source_digest == current_digest:
        return "current-contract"
    if source_version_value == current_version:
        return "same-version-stale-contract"
    return "historical"


def captured_benchmarks(
    current_version: str,
    current_digest: str,
) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []
    if not RESULTS.is_dir():
        return captured
    for path in sorted(RESULTS.glob("*/result.json")):
        result = load_object(path)
        task = result.get("task") if isinstance(result.get("task"), dict) else {}
        claims = result.get("claims") if isinstance(result.get("claims"), dict) else {}
        commit = str(result.get("source_commit", ""))
        version = source_version(commit)
        source_digest = contract_digest_at(commit)
        captured.append(
            {
                "benchmark_id": result.get("benchmark_id"),
                "task_id": task.get("id"),
                "task_class_id": task.get("class_id"),
                "task_profile": task.get("task_profile"),
                "repetition": task.get("repetition"),
                "source_commit": commit,
                "source_version": version,
                "source_contract_digest": source_digest,
                "evidence_state": evidence_state(
                    version,
                    source_digest,
                    current_version,
                    current_digest,
                ),
                "all_modes_accepted": claims.get("all_modes_accepted", False),
                "aggregate_coverage_eligible": claims.get(
                    "aggregate_coverage_eligible", False
                ),
                "broad_cost_claim_supported": claims.get(
                    "broad_cost_claim_supported", False
                ),
            }
        )
    return captured


def benchmark_coverage(
    task_classes: list[str],
    minimum_repetitions: Any,
    current_digest: str,
    benchmarks: list[dict[str, Any]],
) -> tuple[dict[str, int], bool]:
    repetitions = {
        task_class: len(
            {
                item.get("repetition")
                for item in benchmarks
                if item.get("task_class_id") == task_class
                and item.get("source_contract_digest") == current_digest
                and item.get("all_modes_accepted") is True
                and item.get("aggregate_coverage_eligible") is True
            }
        )
        for task_class in task_classes
    }
    complete = (
        bool(task_classes)
        and isinstance(minimum_repetitions, int)
        and not isinstance(minimum_repetitions, bool)
        and minimum_repetitions > 0
        and all(count >= minimum_repetitions for count in repetitions.values())
    )
    return repetitions, complete


def build() -> dict[str, Any]:
    current_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    current_digest = current_contract_digest()
    surface_data = load_object(SURFACES)
    run_data = load_object(RUNS)
    suite = load_object(SUITE)
    declared_surfaces = [
        item["id"]
        for item in surface_data.get("surfaces", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    captured_runs: list[dict[str, Any]] = []
    for run in run_data.get("runs", []):
        if not isinstance(run, dict):
            continue
        commit = str(run.get("source_commit", ""))
        version = source_version(commit)
        source_digest = contract_digest_at(commit)
        captured_runs.append(
            {
                "id": run.get("id"),
                "assistant_surface": run.get("assistant_surface"),
                "source_commit": commit,
                "source_version": version,
                "source_contract_digest": source_digest,
                "evidence_state": evidence_state(
                    version,
                    source_digest,
                    current_version,
                    current_digest,
                ),
                "complete_fixture_set": run.get("complete_fixture_set") is True,
            }
        )
    captured_surfaces = sorted(
        {
            str(run["assistant_surface"])
            for run in captured_runs
            if run.get("assistant_surface")
        }
    )
    current_surfaces = sorted(
        {
            str(run["assistant_surface"])
            for run in captured_runs
            if run.get("source_contract_digest") == current_digest
            and run.get("complete_fixture_set") is True
        }
    )
    task_classes = [
        item["id"]
        for item in suite.get("task_classes", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    minimum_repetitions = suite.get("recommended_minimum_repetitions")
    benchmarks = captured_benchmarks(current_version, current_digest)
    current_accepted_repetitions, coverage_complete = benchmark_coverage(
        task_classes,
        minimum_repetitions,
        current_digest,
        benchmarks,
    )
    return {
        "schema_version": 1,
        "evidence_kind": "alatyr-source-evidence-coverage",
        "current_framework_version": current_version,
        "current_contract_digest": current_digest,
        "assistant_conformance": {
            "declared_surfaces": declared_surfaces,
            "captured_surfaces": captured_surfaces,
            "current_contract_complete_surfaces": current_surfaces,
            "captured_runs": captured_runs,
            "broad_cross_assistant_claim_supported": bool(declared_surfaces)
            and set(current_surfaces) == set(declared_surfaces),
        },
        "effectiveness": {
            "suite_status": suite.get("status"),
            "required_task_classes": task_classes,
            "recommended_minimum_repetitions": minimum_repetitions,
            "captured_benchmarks": benchmarks,
            "current_contract_accepted_repetitions_by_task_class": current_accepted_repetitions,
            "required_coverage_complete": coverage_complete,
            "broad_cost_or_quality_claim_supported": coverage_complete
            and suite.get("status") == "executed",
        },
        "interpretation": {
            "static_conformance_is_not_real_run_evidence": True,
            "same_version_runs_with_stale_contracts_are_historical": True,
            "historical_runs_do_not_prove_current_contract_behavior": True,
            "missing_evidence_is_not_treated_as_failure_of_project_semantics": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        rendered = json.dumps(build(), indent=2, sort_keys=True) + "\n"
        if args.check:
            if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
                raise ValueError(f"stale generated evidence status: {OUTPUT.relative_to(ROOT)}")
            print(f"OK: checked {OUTPUT.relative_to(ROOT)}")
        else:
            OUTPUT.write_text(rendered, encoding="utf-8")
            print(f"Rendered {OUTPUT.relative_to(ROOT)}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
