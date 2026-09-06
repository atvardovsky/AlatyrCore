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
    safe_destination,
)
from target_validation_support import is_placeholder, scope_entries_cover


def _head(target: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target, check=False, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _load_approval(path: Path, plan: dict[str, Any], base: str, outputs: list[str]) -> str | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"approval record is invalid: {exc}"
    if not isinstance(value, dict) or value.get("schema_version") != 2 or value.get("record_kind") != "alatyr-approval-record":
        return "approval record identity is invalid"
    plan_record = value.get("plan")
    diff = value.get("diff")
    scope = value.get("scope")
    approval = value.get("approval")
    if not all(isinstance(item, dict) for item in [plan_record, diff, scope, approval]):
        return "approval record contract is incomplete"
    if plan_record.get("sha256") != plan["plan_digest"]:
        return "approval record is not bound to the current generation plan"
    if diff.get("repository_revision_at_approval") != base:
        return "approval record is not bound to the current base revision"
    allowed = scope.get("allowed_files_or_surfaces")
    excluded = scope.get("excluded_files_or_surfaces")
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        return "approval record has no valid allowed output scope"
    if not isinstance(excluded, list) or not all(isinstance(item, str) for item in excluded):
        return "approval record has no valid excluded output scope"
    if any(not scope_entries_cover(output, allowed) for output in outputs):
        return "approval record does not cover every protected output"
    if any(scope_entries_cover(output, excluded) for output in outputs):
        return "approval record excludes a protected output"
    if scope.get("allowed_actions_mode") != "full-with-approval":
        return "approval record does not allow protected modification"
    for field in ["approved_by", "approved_at", "source_or_message"]:
        if not isinstance(approval.get(field), str) or is_placeholder(approval[field]):
            return f"approval record {field} is unresolved"
    return None


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
    deterministic_ids = [item for item in stale_ids if artifacts[item]["mode"] == "deterministic-derived"]
    protected_outputs = [
        output
        for artifact_id in deterministic_ids
        if artifacts[artifact_id].get("approval_trigger", "none") != "none"
        for output in artifacts[artifact_id]["outputs"]
    ]
    if protected_outputs:
        if approval_record is None:
            print("FAIL: protected support generation requires --approval-record", file=sys.stderr)
            return 1
        approval_error = _load_approval(approval_record, plan, base, protected_outputs)
        if approval_error:
            print(f"FAIL: {approval_error}", file=sys.stderr)
            return 1
    before_generation = repository_state_digest(target)
    with tempfile.TemporaryDirectory(prefix="alatyr-support-") as directory:
        stage_root = Path(directory)
        generated: list[tuple[Path, Path]] = []
        for artifact_id in deterministic_ids:
            artifact = artifacts[artifact_id]
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
            stage = stage_root / artifact_id
            stage.mkdir()
            rendered_command = [value.replace("{OUTPUT_DIR}", str(stage)) for value in command]
            result = subprocess.run(rendered_command, cwd=target, check=False)
            if result.returncode != 0:
                print(f"FAIL: generator {artifact_id} exited {result.returncode}", file=sys.stderr)
                return 1
            for relpath in artifact["outputs"]:
                staged = stage / relpath
                if staged.is_symlink() or not staged.is_file():
                    print(f"FAIL: generator {artifact_id} omitted {relpath}", file=sys.stderr)
                    return 1
                try:
                    staged.resolve().relative_to(stage.resolve())
                    destination = safe_destination(target, relpath)
                except (ValueError, SupportGenerationError) as exc:
                    print(f"FAIL: unsafe generated output {relpath}: {exc}", file=sys.stderr)
                    return 1
                generated.append((staged, destination))
            for validation in artifact["validation"]:
                if validation.get("kind") != "command" or validation.get("required") is not True:
                    continue
                validation_command = [
                    value.replace("{OUTPUT_DIR}", str(stage)).replace("{TARGET}", str(target))
                    for value in validation["command"]
                ]
                validation_result = subprocess.run(validation_command, cwd=target, check=False)
                if validation_result.returncode != 0:
                    print(
                        f"FAIL: validation for {artifact_id} exited {validation_result.returncode}",
                        file=sys.stderr,
                    )
                    return 1
            if _head(target) != base or repository_state_digest(target) != before_generation:
                print("FAIL: repository state changed while generation was running", file=sys.stderr)
                return 1
        backup_root = stage_root / ".backups"
        backup_root.mkdir()
        backups: list[tuple[Path, Path | None]] = []
        index_path = target / INDEX_PATH
        try:
            for position, (staged, destination) in enumerate(generated):
                destination = safe_destination(target, destination.relative_to(target).as_posix())
                backup = backup_root / f"output-{position}"
                if destination.is_file():
                    os.replace(destination, backup)
                else:
                    backup = None
                backups.append((destination, backup))
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, destination)
            index = build_generation_index(target, registry)
            index_backup = backup_root / "index"
            if index_path.is_file():
                os.replace(index_path, index_backup)
            else:
                index_backup = None
            backups.append((index_path, index_backup))
            index_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_index = stage_root / "support-generation-index.json"
            temporary_index.write_bytes(render_json(index).encode("utf-8"))
            os.replace(temporary_index, index_path)
        except (OSError, SupportGenerationError) as exc:
            rollback_errors: list[str] = []
            for destination, backup in reversed(backups):
                try:
                    destination.unlink(missing_ok=True)
                    if backup is not None:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(backup, destination)
                except OSError as rollback_exc:
                    rollback_errors.append(str(rollback_exc))
            detail = (
                f"; rollback also failed: {'; '.join(rollback_errors)}"
                if rollback_errors
                else ""
            )
            print(f"FAIL: generation apply rolled back: {exc}{detail}", file=sys.stderr)
            return 1
    print(f"Applied {len(deterministic_ids)} support-generation action(s) at {base}")
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
