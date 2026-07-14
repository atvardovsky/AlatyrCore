#!/usr/bin/env python3
"""Execute fresh Codex CLI processes against staged conformance fixtures."""

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

from materialize_conformance_fixtures import fixture_dirs
from prepare_conformance_run import default_source_commit, prepare_run


ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_events(path: Path) -> tuple[str, dict[str, int]]:
    thread_id = "unknown"
    usage: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
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


def codex_version(executable: str) -> str:
    result = subprocess.run(
        [executable, "--version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout.strip() or "unknown"


def execute(args: argparse.Namespace) -> int:
    executable = shutil.which(args.codex_command)
    if not executable:
        print(f"FAIL: Codex executable not found: {args.codex_command}", file=sys.stderr)
        return 1

    output = args.output.resolve()
    source_commit = args.source_commit or default_source_commit()
    selected = [path.name for path in fixture_dirs(args.fixture)]
    prepare_args = argparse.Namespace(
        output=output,
        assistant_surface="codex",
        allow_custom_surface=False,
        run_id=args.run_id or f"codex-isolated-{source_commit[:7]}",
        source_commit=source_commit,
        fixture=args.fixture,
        overwrite=args.overwrite,
        staged_adapter_profile=args.staged_adapter_profile,
    )
    failures = prepare_run(prepare_args)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    logs = output / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    executions: list[dict[str, Any]] = []
    overall_failure = False
    for fixture in selected:
        target = output / "targets" / fixture
        prompt = (output / "prompts" / f"{fixture}.md").read_text(encoding="utf-8")
        stdout_path = logs / f"{fixture}.jsonl"
        stderr_path = logs / f"{fixture}.stderr.txt"
        command = [
            executable,
            "exec",
            "--ignore-user-config",
            "-C",
            str(target),
            "--add-dir",
            str(output / "reports"),
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
            "--ephemeral",
            "--json",
            "-",
        ]
        print(f"RUN: Codex fixture {fixture}", flush=True)
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
        duration = round(time.monotonic() - started, 3)
        stdout_path.write_text(result.stdout, encoding="utf-8")
        stderr_path.write_text(result.stderr, encoding="utf-8")
        thread_id, usage = parse_events(stdout_path)
        report_exists = (output / "reports" / f"{fixture}.json").is_file()
        executions.append(
            {
                "fixture": fixture,
                "started_at": started_at,
                "completed_at": utc_now(),
                "duration_seconds": duration,
                "exit_code": result.returncode,
                "thread_id": thread_id,
                "usage": usage,
                "report_exists": report_exists,
                "stdout_log": f"logs/{fixture}.jsonl",
                "stderr_log": f"logs/{fixture}.stderr.txt",
            }
        )
        if result.returncode != 0 or not report_exists:
            overall_failure = True
            print(
                f"FAIL: {fixture} exit={result.returncode} report={report_exists}",
                file=sys.stderr,
            )
        else:
            print(f"OK: Codex fixture {fixture} completed in {duration}s", flush=True)

    totals: dict[str, int] = {}
    for execution in executions:
        for key, value in execution["usage"].items():
            totals[key] = totals.get(key, 0) + value
    summary = {
        "schema_version": 1,
        "run_kind": "codex-conformance-execution",
        "run_id": prepare_args.run_id,
        "source_commit": source_commit,
        "assistant_surface": "codex",
        "codex_version": codex_version(executable),
        "isolation": {
            "fresh_process_per_fixture": True,
            "ephemeral_session": True,
            "user_config_loaded": False,
            "working_root": "fixture target",
            "staged_adapter_profile": args.staged_adapter_profile,
        },
        "executions": executions,
        "total_usage": totals,
    }
    (output / "execution-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    checker = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "check_conformance_reports.py"),
            "--actual-dir",
            str(output / "reports"),
            "--require-actual-reports",
            "--require-all-fixtures",
        ],
        cwd=ROOT,
        check=False,
    )
    return 1 if overall_failure or checker.returncode != 0 else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run isolated Codex conformance against staged target adapters."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--source-commit")
    parser.add_argument("--fixture", action="append", default=[])
    parser.add_argument(
        "--staged-adapter-profile",
        choices=["core", "standard", "full"],
        default="core",
    )
    parser.add_argument("--codex-command", default="codex")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        return execute(args)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
