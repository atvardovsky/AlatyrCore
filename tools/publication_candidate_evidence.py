"""Read selected, candidate-bound catalog and canonical testing evidence."""

from __future__ import annotations

from pathlib import Path


def _failure(path: str, reason: str) -> dict[str, str]:
    return {"path": path, "reason": reason}


def _tracked_regular(entries, paths) -> list[dict[str, str]]:
    selected = sorted(set(paths))
    committed = entries(selected) if selected else {}
    return [_failure(path, "selected input is not a regular file in the candidate commit")
            for path in selected if committed.get(path, ("", "", ""))[0] not in {"100644", "100755"}]


def _passing_command(record: dict, kind: str) -> bool:
    counts = record["counts"]
    if (record["state"] != "passed" or counts["executed"] <= 0 or counts["failed"]
            or counts["skipped"] or counts.get("not_run", 0) or record["result_artifact"] is None
            or record["filter"] is not None):
        return False
    if kind == "automated-test":
        return record["claim"] in {"suite", "full"} and not record["files"]["excluded"]
    return kind in {"static-analysis", "metadata-check"} and record["claim"] == "static"


def context_failures(target: Path, index: str, paths: list[str], entries) -> list[dict[str, str]]:
    from context_catalog import (
        ContextProjectionDrift, catalog_content_stats, discover_context_catalog,
    )
    from context_input_snapshot import ContextInputSnapshot

    root = target / index
    failures = _tracked_regular(entries, [index, *paths])
    if failures:
        return failures
    try:
        with ContextInputSnapshot(target, regular_files_only=True, max_input_bytes=1024 * 1024,
                                  max_inputs=256) as snapshot:
            if root.resolve() != root:
                return [_failure(index, "context index must not traverse symlinks")]
            catalog = discover_context_catalog(root, reject_aliases=True)
            prefix = root.parent.relative_to(target)
            failures.extend(_tracked_regular(entries, [(prefix / path).as_posix() for path in catalog.indexes]))
            by_path = {(prefix / item.path).as_posix(): item for item in catalog.items}
            for path in paths:
                item = by_path.get(path)
                if item is None:
                    failures.append(_failure(path, f"not indexed by {index}"))
                    continue
                snapshot.read(target / path)
                stats = catalog_content_stats(target / path)
                if stats.digest != item.content_digest or stats.words != item.estimated_words:
                    owner = (prefix / item.index_chain[-1]).as_posix()
                    failures.append(_failure(path, f"stale catalog projection in {owner}; regenerate its ancestor chain"))
    except ContextProjectionDrift as exc:
        failures.append(_failure(index, str(exc)))
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        failures.append(_failure(index, f"context projection unavailable: {exc}"))
    return failures


def test_evidence_failures(target: Path, revision: str, commands: list[str], entries) -> list[dict[str, str]]:
    from target_adapter_validation.testing_execution import validate_testing_execution
    from validate_target_adapter import AdapterValidatorConfig, Validator

    path = ".ai/project/testing/test-first-policy.json"
    failures = _tracked_regular(entries, [path])
    if failures:
        return failures
    validator = Validator(
        target, framework_source=None, diff_ref=None, approval_records=[],
        enforce_approval_scope=False, change_packages=[], enforce_change_package=False,
        migration_diff=None, allow_placeholders=False, allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )
    context = validator.capability_validation_context()
    if context.git.head_revision() != revision:
        return [_failure(path, "canonical testing evidence reader does not observe the exact candidate HEAD")]
    policy = context.load_json_object(context.target_path(path), "TDD_EXECUTION_CONTRACT")
    if policy is not None and (policy.get("state") != "enabled" or "execution_contract" not in policy):
        return [_failure(path, "enabled canonical testing execution contract is required")]
    if policy is not None:
        validate_testing_execution(context, policy)
    failures = [_failure(item.path or path, f"{item.code}: {item.message}")
                for item in validator.findings if item.level == "error"]
    if failures or policy is None:
        return failures or [_failure(path, "canonical testing policy could not be read")]
    execution = policy["execution_contract"]
    failures.extend(_tracked_regular(entries, [execution["canonical_policy"]]))
    configured = {row["id"]: row["execution"]["kind"] for row in policy["commands"]}
    matched = set()
    for record_path in execution["evidence_records"]:
        record = context.load_json_object(context.target_path(record_path), "TDD_EXECUTION_EVIDENCE")
        if record is None or record["command_id"] not in commands or record["repository_revision"] != revision:
            continue
        if not _passing_command(record, configured[record["command_id"]]):
            failures.append(_failure(record_path, "selected command lacks an unskipped, unfiltered passing execution of its configured scope on the exact candidate"))
            continue
        failures.extend(_tracked_regular(entries, [p for p, digest in record["input_sha256"].items() if digest is not None]))
        matched.add(record["command_id"])
    for command in commands:
        if command not in configured:
            failures.append(_failure(path, f"unknown canonical test command: {command}"))
        elif command not in matched:
            failures.append(_failure(path, f"no passing exact-candidate record for {command}"))
    if context.filesystem.finalize() or not context.git.finalize():
        failures.append(_failure(path, "test evidence or Git state changed during the observation; retry"))
    return failures
