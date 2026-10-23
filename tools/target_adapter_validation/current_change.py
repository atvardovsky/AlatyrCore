"""Canonical capability decisions for current-change entry points."""

from __future__ import annotations

from pathlib import Path


def change_packages_enabled(target: Path) -> bool:
    """Resolve package capability through the validator, including legacy profiles."""
    from target_validation_support import parse_manifest
    from validate_target_adapter import AdapterValidatorConfig, Validator

    checked = Validator(
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
        raise ValueError("cannot resolve change-package capability: target manifest is unavailable")
    manifest = parse_manifest(checked.context.text_source(path))
    if manifest.parse_failures:
        raise ValueError("cannot resolve change-package capability: " + "; ".join(manifest.parse_failures))
    enabled = checked.enabled_modules(manifest)
    if checked.unsafe_target_paths:
        raise ValueError("cannot resolve change-package capability: target paths escape the repository")
    return "change-packages" in enabled
