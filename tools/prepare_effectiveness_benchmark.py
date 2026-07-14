#!/usr/bin/env python3
"""Prepare isolated no/minimal/full effectiveness benchmark workspaces."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_TEMPLATE = (
    ROOT / "conformance" / "benchmarks" / "effectiveness-run-report-template.json"
)
MODES = ["none", "minimal", "full"]
ALLOWED_ACTIONS = {
    "read-only",
    "docs-only",
    "adapter-only",
    "code-and-tests",
    "full-with-approval",
}
ALLOWED_ADAPTER_PATTERN_ROOTS = [
    ".ai/",
    ".agents/",
    ".claude/",
    ".cursor/",
    ".devin/",
    ".gemini/",
    ".windsurf/",
    ".github/instructions/",
    ".github/prompts/",
    ".github/skills/",
]
ALLOWED_ADAPTER_PATTERN_FILES = {
    "AGENTS.md",
    "AI_ASSISTANTS.md",
    "CLAUDE.md",
    "CODEOWNERS",
    "GEMINI.md",
    ".cursorrules",
    ".windsurfrules",
    ".github/copilot-instructions.md",
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def source_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def safe_id(value: str) -> str:
    rendered = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-" for char in value
    ).strip("-")
    if not rendered:
        raise ValueError(f"identifier has no safe characters: {value}")
    return rendered


def relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def excluded(relpath: str, patterns: list[str]) -> bool:
    return relpath == ".git" or relpath.startswith(".git/") or any(
        fnmatch.fnmatchcase(relpath, pattern) for pattern in patterns
    )


def adapter_pattern_allowed(pattern: str) -> bool:
    literal_prefix = pattern.split("*", 1)[0]
    prefix_path = Path(literal_prefix)
    if prefix_path.is_absolute() or ".." in prefix_path.parts:
        return False
    return pattern in ALLOWED_ADAPTER_PATTERN_FILES or any(
        literal_prefix.startswith(root) for root in ALLOWED_ADAPTER_PATTERN_ROOTS
    )


def file_entries(root: Path, patterns: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relpath = path.relative_to(root).as_posix()
        if excluded(relpath, patterns):
            continue
        if path.is_symlink():
            raise ValueError(f"benchmark snapshots must not contain symlinks: {path}")
        if path.is_file():
            entries.append((relpath, hashlib.sha256(path.read_bytes()).hexdigest()))
    return entries


def tree_hash(root: Path, patterns: list[str]) -> str:
    digest = hashlib.sha256()
    for relpath, content_hash in file_entries(root, patterns):
        digest.update(relpath.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        expected = "list" if allow_empty else "non-empty list"
        raise ValueError(f"{label} must be a {expected}")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must not contain duplicates")
    return value


def check_mode_contract(
    snapshot: Path,
    mode: str,
    contract: dict[str, Any],
) -> None:
    required = string_list(
        contract.get("required_paths"),
        f"mode_contracts.{mode}.required_paths",
        allow_empty=True,
    )
    forbidden = string_list(
        contract.get("forbidden_paths"),
        f"mode_contracts.{mode}.forbidden_paths",
        allow_empty=True,
    )
    for relpath in required:
        path = Path(relpath)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"{mode} required path is unsafe: {relpath}")
        if not (snapshot / relpath).exists():
            raise ValueError(f"{mode} snapshot missing required path: {relpath}")
    for relpath in forbidden:
        path = Path(relpath)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"{mode} forbidden path is unsafe: {relpath}")
        if (snapshot / relpath).exists():
            raise ValueError(f"{mode} snapshot contains forbidden path: {relpath}")


def copy_snapshot(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git"))


def render_prompt(
    *,
    task: dict[str, Any],
    mode: str,
    run_id: str,
    repetition: int,
    target: Path,
    report: Path,
    benchmark_id: str,
    commit: str,
    baseline_hash: str,
) -> str:
    criteria = "\n".join(
        f"- {criterion}" for criterion in task["acceptance_criteria"]
    )
    return f"""# Alatyr Effectiveness Benchmark Run

This is one isolated run in a paired effectiveness benchmark.

## Identity

- Benchmark: `{benchmark_id}`
- Task id: `{task['id']}`
- Adapter mode: `{mode}`
- Repetition: `{repetition}`
- Run id: `{run_id}`
- Source commit: `{commit}`
- Target baseline hash: `{baseline_hash}`
- Target workspace: `{target}`
- Report path: `{report}`

## Isolation

Work only inside the target workspace. Do not inspect sibling mode or
repetition workspaces. Do not infer another run's output. Use only instructions
available inside this target and the task below.

## Task

{task['request']}

Allowed actions: `{task['allowed_actions']}`
Task profile for comparison: `{task['task_profile']}`

## Acceptance Criteria

{criteria}

## Evidence

After the task, write a JSON report to `{report}` using
`{REPORT_TEMPLATE}`. Record observed or explicitly unknown tokens, monetary
cost, context volume, duration, validation, changed files, consistency
evidence, and run provenance.
Keep `review.status` as `pending`; an independent reviewer evaluates the same
acceptance criteria for every adapter mode. Do not claim that this run proves
Alatyr is cheaper or more effective.
"""


def prepare_benchmark(plan_path: Path, output: Path, *, overwrite: bool) -> Path:
    plan_path = plan_path.resolve()
    output = output.resolve()
    plan = load_json(plan_path)
    if plan.get("schema_version") != 1:
        raise ValueError("benchmark plan schema_version must be 1")
    if plan.get("benchmark_kind") != "alatyr-effectiveness-benchmark-input":
        raise ValueError("benchmark plan has unsupported benchmark_kind")
    benchmark_id = plan.get("benchmark_id")
    if not isinstance(benchmark_id, str) or not benchmark_id or benchmark_id.startswith("{"):
        raise ValueError("benchmark_id must replace its template value")
    repetitions = plan.get("repetitions")
    if not isinstance(repetitions, int) or not 1 <= repetitions <= 20:
        raise ValueError("repetitions must be an integer from 1 to 20")
    patterns = string_list(plan.get("adapter_surface_patterns"), "adapter_surface_patterns")
    invalid_patterns = [pattern for pattern in patterns if not adapter_pattern_allowed(pattern)]
    if invalid_patterns:
        raise ValueError(
            "adapter_surface_patterns may cover only known AI adapter surfaces: "
            + ", ".join(invalid_patterns)
        )
    mode_contracts = plan.get("mode_contracts")
    if not isinstance(mode_contracts, dict) or set(mode_contracts) != set(MODES):
        raise ValueError("mode_contracts must define none, minimal, and full")
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a non-empty list")
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise ValueError(f"benchmark output is not empty: {output}; use --overwrite")
    output.mkdir(parents=True, exist_ok=True)

    commit = source_commit()
    runs: list[dict[str, Any]] = []
    seen_task_ids: set[str] = set()
    prepared_tasks: list[dict[str, Any]] = []
    for task_index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{task_index}] must be an object")
        for field in ["id", "name", "task_profile", "request", "allowed_actions"]:
            if not isinstance(task.get(field), str) or not task[field]:
                raise ValueError(f"tasks[{task_index}].{field} must be non-empty")
        task_id = safe_id(task["id"])
        if task_id != task["id"]:
            raise ValueError(f"task id must already be path-safe: {task['id']}")
        if task_id in seen_task_ids:
            raise ValueError(f"duplicate task id: {task_id}")
        seen_task_ids.add(task_id)
        if task["allowed_actions"] not in ALLOWED_ACTIONS:
            raise ValueError(f"task {task_id} has invalid allowed_actions")
        criteria = string_list(
            task.get("acceptance_criteria"),
            f"tasks[{task_index}].acceptance_criteria",
        )
        sources = task.get("sources")
        if not isinstance(sources, dict) or set(sources) != set(MODES):
            raise ValueError(f"task {task_id} sources must define none, minimal, and full")

        resolved_sources: dict[str, Path] = {}
        project_hashes: dict[str, str] = {}
        snapshot_hashes: dict[str, str] = {}
        for mode in MODES:
            source_value = sources[mode]
            if not isinstance(source_value, str) or not source_value or source_value.startswith("{"):
                raise ValueError(f"task {task_id} source {mode} must replace its template value")
            snapshot = (plan_path.parent / source_value).resolve()
            if not snapshot.is_dir():
                raise ValueError(f"task {task_id} source {mode} is not a directory: {snapshot}")
            if relative_to(output, snapshot):
                raise ValueError("benchmark output must not be inside a source snapshot")
            contract = mode_contracts[mode]
            if not isinstance(contract, dict):
                raise ValueError(f"mode_contracts.{mode} must be an object")
            check_mode_contract(snapshot, mode, contract)
            resolved_sources[mode] = snapshot
            project_hashes[mode] = tree_hash(snapshot, patterns)
            snapshot_hashes[mode] = tree_hash(snapshot, [])
        if len(set(project_hashes.values())) != 1:
            raise ValueError(
                f"task {task_id} project snapshots differ outside adapter surfaces"
            )
        project_hash = project_hashes[MODES[0]]

        prepared_tasks.append(
            {
                "id": task_id,
                "name": task["name"],
                "task_profile": task["task_profile"],
                "allowed_actions": task["allowed_actions"],
                "acceptance_criteria": criteria,
                "project_baseline_hash": project_hash,
                "mode_snapshot_hashes": snapshot_hashes,
            }
        )
        for repetition in range(1, repetitions + 1):
            for mode in MODES:
                run_id = f"{safe_id(benchmark_id)}-{task_id}-{mode}-r{repetition}"
                workspace_rel = Path("runs") / task_id / mode / f"r{repetition}"
                workspace = output / workspace_rel
                target = workspace / "target"
                report = workspace / "report.json"
                workspace.mkdir(parents=True, exist_ok=True)
                if report.exists():
                    report.unlink()
                copy_snapshot(resolved_sources[mode], target)
                prompt = workspace / "prompt.md"
                prompt.write_text(
                    render_prompt(
                        task={**task, "acceptance_criteria": criteria},
                        mode=mode,
                        run_id=run_id,
                        repetition=repetition,
                        target=target,
                        report=report,
                        benchmark_id=benchmark_id,
                        commit=commit,
                        baseline_hash=project_hash,
                    ),
                    encoding="utf-8",
                )
                runs.append(
                    {
                        "run_id": run_id,
                        "task_id": task_id,
                        "adapter_mode": mode,
                        "repetition": repetition,
                        "workspace": workspace_rel.as_posix(),
                        "target": (workspace_rel / "target").as_posix(),
                        "prompt": (workspace_rel / "prompt.md").as_posix(),
                        "report": (workspace_rel / "report.json").as_posix(),
                        "project_baseline_hash": project_hash,
                        "snapshot_hash": snapshot_hashes[mode],
                    }
                )

    manifest = {
        "schema_version": 1,
        "benchmark_kind": "alatyr-effectiveness-benchmark-plan",
        "status": "prepared-not-executed",
        "benchmark_id": benchmark_id,
        "source_commit": commit,
        "input_plan_hash": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "adapter_surface_patterns": patterns,
        "repetitions": repetitions,
        "modes": MODES,
        "tasks": prepared_tasks,
        "expected_report_count": len(runs),
        "execution_claimed": False,
        "runs": runs,
    }
    manifest_path = output / "benchmark.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "# Prepared Effectiveness Benchmark\n\n"
        "Status: `prepared-not-executed`. Run each prompt externally, preserve "
        "isolation, and review acceptance criteria before comparative claims.\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare paired no/minimal/full effectiveness benchmark workspaces."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        manifest = prepare_benchmark(args.plan, args.output, overwrite=args.overwrite)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"OK: prepared effectiveness benchmark at {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
