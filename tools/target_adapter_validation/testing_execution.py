"""Integrate policy-aware testing records through the registered TDD validator."""

from __future__ import annotations

from typing import Any

from path_spec import select_paths
from repository_inventory import RepositoryInventory, RepositoryInventoryError
from test_execution_contract import SURFACES, TestExecutionContract, has_placeholders, surface_binding_failures, policy_projection_failures
from target_adapter_validation.capability import CapabilityValidationContext
from target_adapter_validation.context import TargetFileState


def validate_testing_execution(context: CapabilityValidationContext, policy: dict[str, Any], manifest=None) -> None:
    source = ".ai/project/testing/test-first-policy.json"
    if "execution_contract" not in policy:
        version = manifest.scalars.get(("schema_version",)) if manifest is not None else None
        current = version is not None and isinstance(version.value, str) and version.value.isdigit() and int(version.value) >= 74
        finding = context.error if current else context.warn
        finding("TDD_EXECUTION_CONTRACT_MISSING", "policy has no execution contract; reconcile canonical owners, timing, command effects and evidence before claiming execution readiness", source)
        return
    try:
        contract = TestExecutionContract()
    except (OSError, ValueError) as exc:
        context.error("TDD_EXECUTION_SCHEMA", str(exc), source)
        return
    failures = contract.policy_failures(policy, placeholders=context.allow_placeholders)
    for failure in failures:
        context.error("TDD_EXECUTION_CONTRACT", failure, source)
    if failures or (context.allow_placeholders and has_placeholders(policy)):
        return
    template = ".ai/assistant/templates/test-execution-evidence.json"
    if not context.is_target_file(template):
        context.error("TDD_EXECUTION_TEMPLATE_MISSING", "execution contract requires its evidence template", template)
    execution = policy["execution_contract"]
    owner_path = execution["canonical_policy"]
    if not context.is_target_file(owner_path):
        context.error("TDD_CANONICAL_POLICY_MISSING", "canonical testing policy is missing or outside the target", owner_path)
        return
    canonical = context.load_json_object(context.target_path(owner_path), "TDD_CANONICAL_POLICY")
    if canonical is not None:
        for failure in policy_projection_failures(policy, canonical):
            context.error("TDD_POLICY_PROJECTION_DRIFT", failure, source)
    matrix = execution["canonical_coverage_matrix"]
    if matrix is not None and not context.is_target_file(matrix):
        context.error("TDD_COVERAGE_OWNER_MISSING", "canonical coverage matrix does not exist", matrix)
    for path in (*SURFACES, *execution.get("additional_evidence_templates", [])):
        if not context.is_target_file(path):
            context.error("TDD_SURFACE_POLICY_BINDING", "declared test surface is missing or outside the target", path)
            continue
        content = context.filesystem.read_bytes_result(context.target_path(path), max_bytes=128 * 1024)
        if content.value is None:
            context.error("TDD_SURFACE_POLICY_BINDING", "test surface exceeds 128 KiB or is unreadable", path)
            continue
        try:
            text = content.value.decode("utf-8")
        except UnicodeError:
            context.error("TDD_SURFACE_POLICY_BINDING", "test surface must be UTF-8 Markdown", path)
            continue
        for failure in surface_binding_failures(text):
            context.error("TDD_SURFACE_POLICY_BINDING", failure, path)
    commands = {command["id"]: command for command in policy["commands"]}
    for command in commands.values():
        for path in command["execution"]["configuration_paths"]:
            if not context.is_target_file(path):
                context.error("TDD_COMMAND_CONFIGURATION_MISSING", "declared test command configuration is missing", path)
    inventory = None
    evidence_paths = set(execution["evidence_records"])
    review = policy.get("repair_review")
    if isinstance(review, dict) and review.get("state") == "enabled":
        evidence_paths.update(item["path"] for item in review["records"])
        repair_template = ".ai/assistant/templates/repair-qualification.json" if review["schema_version"] == 2 else ".ai/assistant/templates/repair-review.json"
        if review["schema_version"] == 2 and not context.is_target_file(".ai/framework/repair-qualification.md"):
            context.error("TDD_EXECUTION_CONTRACT", "adopted schema-2 repair qualification requires its conditional framework guidance", ".ai/framework/repair-qualification.md")
        if not context.is_target_file(repair_template):
            context.error("TDD_EXECUTION_TEMPLATE_MISSING", "enabled repair review requires its current authoring template", repair_template)
        else:
            value = context.load_json_object(context.target_path(repair_template), "TDD_EXECUTION_TEMPLATE_MISSING")
            if value is not None:
                for failure in contract.shape(value, "repair_evidence", placeholders=True):
                    context.error("TDD_EXECUTION_TEMPLATE_MISSING", failure, repair_template)
    for path in execution["evidence_records"]:
        if not context.is_target_file(path):
            context.error("TDD_EXECUTION_EVIDENCE_MISSING", "selected current test evidence is missing or outside the target", path)
            continue
        record = context.load_json_object(context.target_path(path), "TDD_EXECUTION_EVIDENCE")
        if record is None:
            continue
        shape = contract.shape(record, "evidence")
        if shape:
            for failure in shape:
                context.error("TDD_EXECUTION_EVIDENCE", failure, path)
            continue
        command = commands.get(record["command_id"])
        if command is None:
            context.error("TDD_EXECUTION_EVIDENCE", "record references an unknown command", path)
            continue
        failures = contract.evidence_failures(record, command, execution)
        for failure in failures:
            context.error("TDD_EXECUTION_EVIDENCE", failure, path)
        if failures:
            continue
        if record["claim"] in {"suite", "full"}:
            try:
                if inventory is None:
                    inventory = RepositoryInventory.load(context.target)
                universe = set(select_paths(inventory.paths, command["execution"]["suite_patterns"]))
                if universe != set(record["files"]["universe"]):
                    context.error("TDD_SUITE_SELECTION_DRIFT", "suite universe differs from current target-owned patterns; reconcile additions and exclusions", path)
            except RepositoryInventoryError as exc:
                context.error("TDD_SUITE_SELECTION_DRIFT", str(exc), path)
        if record["policy_sha256"] != context.content_digest(context.target_path(owner_path)):
            context.error("TDD_EXECUTION_EVIDENCE_STALE", "record policy hash differs from the canonical owner", path)
        inputs = list(record["input_sha256"].items())
        if record["result_artifact"] is not None:
            artifact = record["result_artifact"]
            inputs.append((artifact["path"], artifact["sha256"]))
        revision = record["repository_revision"]
        changed = context.git.changed_files(revision)
        bound_paths = set(record["input_sha256"]) | evidence_paths | {owner_path}
        if record["result_artifact"] is not None:
            bound_paths.add(record["result_artifact"]["path"])
        if context.git.is_ancestor(revision, context.git.head_revision()) is not True or changed is None or set(changed) - bound_paths:
            context.error("TDD_EXECUTION_EVIDENCE_STALE", "revision is unavailable or committed/staged/unstaged/untracked non-evidence changes lack current input hashes", path)
        for input_path, digest in inputs:
            target_path = context.target_path(input_path)
            if digest is None:
                matches = context.status(target_path).state == TargetFileState.MISSING
            else:
                matches = context.content_digest(target_path) == digest
            if not matches:
                context.error("TDD_EXECUTION_EVIDENCE_STALE", f"missing, escaped or changed evidence input: {input_path}", path)
    if contract.view.finalize():
        context.error("TDD_EXECUTION_SCHEMA", "testing schema changed during validation; rerun", source)
