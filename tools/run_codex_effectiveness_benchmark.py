#!/usr/bin/env python3
"""Execute a prepared effectiveness benchmark with isolated Codex processes."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COUNT_FIELDS = [
    "context_files_loaded",
    "approximate_context_volume",
    "context_expansions",
    "clarifications",
    "approvals_requested",
    "missed_companion_updates",
    "rework_count",
    "changed_fact_count",
    "relationships_reviewed",
    "companion_surfaces_checked",
    "unresolved_consistency_gaps",
    "protected_changes_blocked",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def parse_events(text: str) -> tuple[str, dict[str, int]]:
    thread_id = "unknown"
    usage: dict[str, int] = {}
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            value = event.get("thread_id")
            if isinstance(value, str) and value:
                thread_id = value
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = {
                key: value
                for key, value in event["usage"].items()
                if isinstance(key, str) and isinstance(value, int)
            }
    return thread_id, usage


def update_report(
    path: Path,
    *,
    manifest: dict[str, Any],
    run: dict[str, Any],
    task: dict[str, Any],
    thread_id: str,
    usage: dict[str, int],
    started_at: str,
    completed_at: str,
    duration_seconds: float,
) -> None:
    report = load_object(path)
    report.update(
        {
            "schema_version": 1,
            "report_kind": "effectiveness-benchmark-result",
            "benchmark_id": manifest["benchmark_id"],
            "task": task["name"],
            "task_id": run["task_id"],
            "task_profile": task["task_profile"],
            "adapter_mode": run["adapter_mode"],
            "operation_id": run["run_id"],
            "repetition": run["repetition"],
            "source_commit": manifest["source_commit"],
            "target_baseline_hash": run["project_baseline_hash"],
        }
    )
    provenance = report.get("run_provenance")
    if not isinstance(provenance, dict):
        provenance = {}
        report["run_provenance"] = provenance
    provenance.update(
        {
            "provider": "OpenAI",
            "product": "Codex",
            "model": "unknown",
            "version_or_date": "2026-07-14",
            "execution_mode": "isolated Codex CLI benchmark",
            "started_at": started_at,
            "completed_at": completed_at,
            "operator": f"Codex CLI process {thread_id}",
            "report_origin": "assistant-reported with executor-observed usage",
        }
    )
    report["context_measurement_kind"] = (
        "Codex CLI completion-event tokens with assistant-reported file context"
    )
    report["input_tokens"] = usage.get("input_tokens", "unknown")
    report["output_tokens"] = usage.get("output_tokens", "unknown")
    report["estimated_cost"] = "unknown"
    report["cost_currency"] = "unknown"
    report["cost_evidence"] = "unavailable; no comparable billing export"
    report["duration_seconds"] = round(duration_seconds)
    for field in COUNT_FIELDS:
        value = report.get(field)
        if value != "unknown" and (not isinstance(value, int) or value < 0):
            report[field] = "unknown"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def run_benchmark(args: argparse.Namespace) -> int:
    executable = shutil.which(args.codex_command)
    if not executable:
        raise ValueError(f"Codex executable not found: {args.codex_command}")
    manifest_path = args.benchmark.resolve()
    manifest = load_object(manifest_path)
    if manifest.get("benchmark_kind") != "alatyr-effectiveness-benchmark-plan":
        raise ValueError("benchmark manifest kind is invalid")
    if manifest.get("status") != "prepared-not-executed":
        raise ValueError("benchmark manifest must remain prepared-not-executed")
    base = manifest_path.parent
    logs = base / "execution-logs"
    logs.mkdir(parents=True, exist_ok=True)
    executions: list[dict[str, Any]] = []
    tasks = {
        task["id"]: task
        for task in manifest.get("tasks", [])
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    failed = False

    for run in manifest.get("runs", []):
        if not isinstance(run, dict):
            raise ValueError("benchmark run entries must be objects")
        run_id = str(run.get("run_id"))
        workspace = base / str(run.get("workspace"))
        target = base / str(run.get("target"))
        prompt = (base / str(run.get("prompt"))).read_text(encoding="utf-8")
        report_path = base / str(run.get("report"))
        task = tasks.get(run.get("task_id"))
        if task is None:
            raise ValueError(f"benchmark run has unknown task: {run.get('task_id')}")
        command = [
            executable,
            "exec",
            "--ignore-user-config",
            "-C",
            str(target),
            "--add-dir",
            str(workspace),
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
            "--ephemeral",
            "--json",
            "-",
        ]
        print(f"RUN: {run_id}", flush=True)
        started_at = utc_now()
        started = time.monotonic()
        result = subprocess.run(
            command,
            input=prompt,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout_seconds,
        )
        duration = time.monotonic() - started
        completed_at = utc_now()
        stdout_path = logs / f"{run_id}.jsonl"
        stderr_path = logs / f"{run_id}.stderr.txt"
        stdout_path.write_text(result.stdout, encoding="utf-8")
        stderr_path.write_text(result.stderr, encoding="utf-8")
        thread_id, usage = parse_events(result.stdout)
        report_exists = report_path.is_file()
        if result.returncode == 0 and report_exists:
            update_report(
                report_path,
                manifest=manifest,
                run=run,
                task=task,
                thread_id=thread_id,
                usage=usage,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )
            print(f"OK: {run_id} completed in {duration:.3f}s", flush=True)
        else:
            failed = True
            print(
                f"FAIL: {run_id} exit={result.returncode} report={report_exists}",
                file=sys.stderr,
            )
        executions.append(
            {
                "run_id": run_id,
                "task_id": run.get("task_id"),
                "adapter_mode": run.get("adapter_mode"),
                "repetition": run.get("repetition"),
                "thread_id": thread_id,
                "started_at": started_at,
                "completed_at": completed_at,
                "duration_seconds": round(duration, 3),
                "exit_code": result.returncode,
                "report_exists": report_exists,
                "usage": usage,
            }
        )

    totals: dict[str, int] = {}
    for execution in executions:
        for key, value in execution["usage"].items():
            totals[key] = totals.get(key, 0) + value
    summary = {
        "schema_version": 1,
        "run_kind": "codex-effectiveness-benchmark-execution",
        "benchmark_id": manifest.get("benchmark_id"),
        "source_commit": manifest.get("source_commit"),
        "codex_version": subprocess.run(
            [executable, "--version"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip(),
        "isolation": {
            "fresh_process_per_run": True,
            "ephemeral_session": True,
            "user_config_loaded": False,
            "working_root": "mode target",
        },
        "executions": executions,
        "total_usage": totals,
    }
    (base / "execution-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    checker = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "check_effectiveness_benchmark.py"),
            "--benchmark",
            str(manifest_path),
            "--require-reports",
        ],
        cwd=ROOT,
        check=False,
    )
    return 1 if failed or checker.returncode != 0 else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a prepared paired effectiveness benchmark with Codex CLI."
    )
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--codex-command", default="codex")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    try:
        return run_benchmark(args)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
