"""Canonical capability decisions for current-change entry points."""

from __future__ import annotations

from pathlib import Path


from target_adapter_validation.package_applicability import package_requirement


def required_package_for_finalization(target: Path, task_id: str | None,
                                      task_class: str | None = None, *, require_task_acceptance: bool = False,
                                      explicit: bool = False) -> dict:
    from validate_target_adapter import AdapterValidatorConfig, Validator
    validator = Validator(target, framework_source=None, diff_ref=None, approval_records=[],
        enforce_approval_scope=False, change_packages=[], enforce_change_package=False,
        migration_diff=None, allow_placeholders=False, allow_local_paths=[],
        current_task_id=task_id, current_task_class=task_class,
        require_task_acceptance=require_task_acceptance, config=AdapterValidatorConfig())
    result = package_requirement(validator, module_enabled="change-packages" in enabled_capabilities(target, validator=validator),
                                 automatic=True, explicit=explicit)
    result["failures"].extend(item.message for item in validator.findings if item.level == "error")
    validator.finalize_inputs()
    result["failures"].extend(item.message for item in validator.findings if item.level == "error"
                              and item.message not in result["failures"])
    if result["failures"]:
        raise ValueError("invalid package applicability: " + "; ".join(result["failures"][:4]))
    return result


def enabled_capabilities(target: Path, *, validator=None) -> set[str]:
    """Resolve installed capabilities through their canonical profile policy."""
    from target_validation_support import parse_manifest
    from validate_target_adapter import AdapterValidatorConfig, Validator

    checked = validator if validator is not None else Validator(
        target,
        framework_source=None,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=False,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
    )
    path = checked.target_path(".ai/alatyr.yaml")
    if not checked.is_target_file(path):
        raise ValueError("cannot resolve target capabilities: target manifest is unavailable")
    manifest = parse_manifest(checked.context.text_source(path))
    if manifest.parse_failures:
        raise ValueError("cannot resolve target capabilities: " + "; ".join(manifest.parse_failures))
    enabled = checked.enabled_modules(manifest)
    if checked.unsafe_target_paths:
        raise ValueError("cannot resolve target capabilities: target paths escape the repository")
    return enabled


def change_packages_enabled(target: Path) -> bool:
    """Resolve package capability through the validator, including legacy profiles."""
    return "change-packages" in enabled_capabilities(target)
