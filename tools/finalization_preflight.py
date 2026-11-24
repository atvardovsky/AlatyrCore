"""Selected canonical authoring checks; never full acceptance or authorization."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path


def inspect_finalization(target: Path, *, task_id=None, task_class=None,
                         require_task_acceptance=False, diff_ref=None,
                         approval_records=(), problem_models=(), migration_staging=False,
                         change_packages=(), enforce_approval_scope=False,
                         historical_evidence_index=None, inspect_archive=False):
    from validate_target_adapter import Validator, load_validator_config
    from target_adapter_validation.active_tasks import validate_active_tasks

    config, findings = load_validator_config(target, None)
    validator = Validator(target, framework_source=None, diff_ref=diff_ref,
        approval_records=list(approval_records), enforce_approval_scope=enforce_approval_scope,
        change_packages=list(change_packages), enforce_change_package=False, migration_diff=None,
        allow_placeholders=migration_staging, allow_local_paths=[],
        config=config, initial_findings=findings, current_task_id=task_id,
        current_task_class=task_class, require_task_acceptance=require_task_acceptance,
        problem_models=list(problem_models), approval_archive_mode="full" if inspect_archive else "none",
        historical_evidence_index=historical_evidence_index)
    selected = validator.resolve_approval_records()
    if validator.approval_records or enforce_approval_scope:
        validator.check_current_approval_scope(selected)
    if task_id is not None:
        validate_active_tasks(validator, selected_only=True, authoring_only=True)
    from target_adapter_validation.preflight_packages import validate_package_prerequisites
    validate_package_prerequisites(validator)
    if inspect_archive:
        # Archive shape and evidence can be checked before its generated index is repaired.
        validator.check_approval_archive(selected, check_index=False)
    validator.finalize_inputs()
    return validator


def preview_generated_scope(validator, step_ids) -> dict:
    from support_write_transaction import read_output
    from target_support_outputs import step_outputs

    paths, diagnostics = set(), []
    # This is an isolated first-pass preview, not a simulation of dependent postimages.
    for step_id in step_ids:
        if step_id in {"canonical-validation", "bootstrap-pass-2", "context-pass-2", "support-state"}:
            continue
        try:
            for path, output in step_outputs(step_id, validator.target).items():
                if read_output(validator.target, path) != output:
                    paths.add(validator.rel(path))
        except (OSError, ValueError, RecursionError) as exc:
            diagnostics.append({"step": step_id, "message": str(exc)})
    scope_findings = []
    if paths and validator.enforce_approval_scope:
        scopes = [scope for record in validator.resolve_approval_records()
                  if (scope := validator.load_approval_scope(record)) is not None]
        start = len(validator.findings)
        validator.check_approval_path_coverage(sorted(paths), scopes)
        scope_findings = [replace(item, evidence_scope="generated-preview").to_json()
                          for item in validator.findings[start:]]
        del validator.findings[start:]
    return {"state": "partial" if diagnostics else "previewed", "changed_candidates": sorted(paths),
            "scope_findings": scope_findings, "diagnostics": diagnostics,
            "limitation": "Advisory first-pass renderer comparison; dependent postimages and support-state are not predicted. Exact final diff enforcement still applies."}


def preflight_report(validator, *, generated_scope=None) -> dict:
    findings = [{"level": item.level, "code": item.code, "message": item.message,
                 "path": item.path, **({"evidence_scope": item.evidence_scope} if item.evidence_scope else {})}
                for item in validator.findings]
    return {"schema_version": 1, "report_kind": "alatyr-finalization-preflight",
            "state": "blocked" if any(item["level"] == "error" for item in findings) else "ready-for-finalization",
            "findings": findings, "input_sha256": validator.context.content_bindings(),
            "approval_archive": validator.approval_archive_summary,
            "generated_scope": generated_scope,
            "authorization_granted": False, "acceptance_eligible": False,
            "limitation": "Selected authoring checks only. Current scope, generated outputs, full archive and final acceptance still require canonical validation. Human authorization remains primary-owned."}
