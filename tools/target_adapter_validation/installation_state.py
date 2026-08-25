"""Installation-state transition evidence validation."""

from __future__ import annotations

from typing import Any

from scaffold_state import validate_installation_state_record
from target_adapter_validation.capability import CapabilityValidationContext
from target_validation_support import is_target_relative_path, is_unresolved_value


def validate_installation_state(
    context: CapabilityValidationContext,
    manifest: Any,
) -> None:
    """Bind the manifest state to a continuous machine-readable transition chain."""

    if manifest is None:
        return
    state_scalar = manifest.scalars.get(("installation", "state"))
    record_scalar = manifest.scalars.get(("installation", "state_record"))
    if state_scalar is None or record_scalar is None:
        return
    state = state_scalar.value
    relpath = record_scalar.value
    if is_unresolved_value(state) or is_unresolved_value(relpath):
        return
    if not is_target_relative_path(relpath):
        context.error(
            "INSTALLATION_STATE_RECORD_PATH",
            "installation.state_record must be a target-relative path",
            ".ai/alatyr.yaml",
        )
        return
    path = context.target_path(relpath)
    if not path.is_file():
        context.error(
            "INSTALLATION_STATE_RECORD_MISSING",
            "installation.state_record does not exist",
            relpath,
        )
        return
    record = context.load_json_object(path, "INSTALLATION_STATE")
    if record is None:
        return
    for failure in validate_installation_state_record(record, manifest_state=state):
        context.error("INSTALLATION_STATE_TRANSITION", failure, relpath)
