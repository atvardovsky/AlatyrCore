"""Selected canonical authoring checks; never full acceptance or authorization."""

from __future__ import annotations

from pathlib import Path


def inspect_finalization(target: Path, *, task_id=None, task_class=None,
                         require_task_acceptance=False, diff_ref=None,
                         approval_records=(), problem_models=(), migration_staging=False):
    from validate_target_adapter import Validator, load_validator_config
    from target_adapter_validation.active_tasks import validate_active_tasks

    config, findings = load_validator_config(target, None)
    validator = Validator(target, framework_source=None, diff_ref=diff_ref,
        approval_records=list(approval_records), enforce_approval_scope=False,
        change_packages=[], enforce_change_package=False, migration_diff=None,
        allow_placeholders=migration_staging, allow_local_paths=[],
        config=config, initial_findings=findings, current_task_id=task_id,
        current_task_class=task_class, require_task_acceptance=require_task_acceptance,
        problem_models=list(problem_models), approval_archive_mode="none")
    # Select explicit approvals only: generated archive drift is repaired later.
    if validator.approval_records:
        validator.check_approval_record_shape(validator.approval_records)
        validator.check_approval_hash_evidence(validator.approval_records)
    if task_id is not None:
        validate_active_tasks(validator, selected_only=True, authoring_only=True)
    validator.finalize_inputs()
    return validator


def preflight_report(validator) -> dict:
    findings = [{"level": item.level, "code": item.code, "message": item.message,
                 "path": item.path} for item in validator.findings]
    return {"schema_version": 1, "report_kind": "alatyr-finalization-preflight",
            "state": "blocked" if any(item["level"] == "error" for item in findings) else "ready-for-finalization",
            "findings": findings, "input_sha256": validator.context.content_bindings(),
            "authorization_granted": False, "acceptance_eligible": False,
            "limitation": "Selected authoring checks only. Current scope, generated outputs, full archive and final acceptance still require canonical validation. Human authorization remains primary-owned."}
