#!/usr/bin/env python3
"""Plan, check, record, or guardedly apply target support generation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from support_generation import (
    INDEX_PATH,
    SupportGenerationError,
    build_generation_index,
    generation_plan,
    load_index,
    load_registry,
    repository_state_digest,
    render_json,
)


def _head(target: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target, check=False, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _apply(target: Path, plan: dict[str, Any], args: argparse.Namespace) -> int:
    if args.authorization != "modify":
        print("FAIL: --apply requires --authorization modify for the current scope", file=sys.stderr)
        return 1
    if args.plan_digest != plan["plan_digest"]:
        print("FAIL: supplied plan digest is stale or incorrect", file=sys.stderr)
        return 1
    approval_record: Path | None = None
    if args.approval_record is not None:
        approval_record = args.approval_record
        if not approval_record.is_absolute():
            approval_record = target / approval_record
        approval_record = approval_record.resolve()
        try:
            approval_record.relative_to(target)
        except ValueError:
            print("FAIL: approval record must be inside the target repository", file=sys.stderr)
            return 1
        if not approval_record.is_file():
            print("FAIL: approval record does not exist", file=sys.stderr)
            return 1
    registry = load_registry(target)
    artifacts = {item["id"]: item for item in registry["artifacts"]}
    base = _head(target)
    stale_ids = [item["id"] for item in plan["actions"] if item["status"] == "stale"]
    for artifact_id in stale_ids:
        artifact = artifacts[artifact_id]
        if artifact["mode"] != "deterministic-derived":
            continue
        if artifact.get("approval_trigger", "none") != "none" and approval_record is None:
            print(f"FAIL: {artifact_id} requires --approval-record", file=sys.stderr)
            return 1
        generator = artifact.get("generator")
        command = generator.get("command") if isinstance(generator, dict) else None
        if (
            not isinstance(generator, dict)
            or generator.get("execution_contract") != "staged-output-only"
            or not isinstance(command, list)
            or not command
            or not all(isinstance(value, str) and value for value in command)
        ):
            print(f"FAIL: {artifact_id} has no safe staged generator", file=sys.stderr)
            return 1
        before_generation = repository_state_digest(target)
        with tempfile.TemporaryDirectory(prefix="alatyr-support-") as directory:
            stage = Path(directory)
            rendered_command = [value.replace("{OUTPUT_DIR}", str(stage)) for value in command]
            result = subprocess.run(rendered_command, cwd=target, check=False)
            if result.returncode != 0:
                print(f"FAIL: generator {artifact_id} exited {result.returncode}", file=sys.stderr)
                return 1
            generated: list[tuple[Path, Path]] = []
            for relpath in artifact["outputs"]:
                staged = stage / relpath
                if not staged.is_file():
                    print(f"FAIL: generator {artifact_id} omitted {relpath}", file=sys.stderr)
                    return 1
                generated.append((staged, target / relpath))
            if _head(target) != base or repository_state_digest(target) != before_generation:
                print("FAIL: repository state changed while generation was running", file=sys.stderr)
                return 1
            backups: list[tuple[Path, bytes | None]] = []
            try:
                for staged, destination in generated:
                    backups.append((destination, destination.read_bytes() if destination.is_file() else None))
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(staged, destination)
            except OSError as exc:
                for destination, content in reversed(backups):
                    if content is None:
                        destination.unlink(missing_ok=True)
                    else:
                        destination.write_bytes(content)
                print(f"FAIL: generation apply rolled back: {exc}", file=sys.stderr)
                return 1
    index = build_generation_index(target, registry)
    (target / INDEX_PATH).write_bytes(render_json(index).encode("utf-8"))
    print(f"Applied {len(stale_ids)} support-generation action(s) at {base}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--record", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plan-digest")
    parser.add_argument("--authorization")
    parser.add_argument("--approval-record", type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        if args.record:
            index = build_generation_index(target)
            output = target / INDEX_PATH
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(render_json(index).encode("utf-8"))
            print(f"Wrote {INDEX_PATH} with {len(index['artifacts'])} artifacts")
            return 0
        if args.check:
            current = build_generation_index(target)
            recorded = load_index(target)
            if current != recorded:
                print("FAIL: support-generation index is stale", file=sys.stderr)
                return 1
            print(f"OK: support-generation index covers {len(current['artifacts'])} artifacts")
            return 0
        plan = generation_plan(target)
    except SupportGenerationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.apply:
        return _apply(target, plan, args)
    rendered = render_json(plan)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered.encode("utf-8"))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
