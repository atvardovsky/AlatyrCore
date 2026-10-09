"""Validate target-local checker coverage and canonical-result boundaries."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any, Protocol

import jsonschema

from target_validation_support import is_placeholder


CONTRACT_PATH = ".ai/assistant/validation-contract.json"
VALIDATION_CONTRACT_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "schemas/alatyr-validation-contract.schema.json"
)
ENTRYPOINTS = ("adapter-health", "current-change", "archive-audit")
DELEGATE_PATH = ".ai/assistant/tools/alatyr_delegate.py"
EXPECTED_DELEGATES = {
    "adapter-health": {
        "operation": "status",
        "validation_phase": "not-applicable",
        "validation_scope": "not-applicable",
        "approval_archive_mode": "not-applicable",
        "requires_diff_ref": False,
        "requires_approval_records": False,
        "requires_change_packages": False,
    },
    "current-change": {
        "operation": "validate-adapter",
        "validation_phase": "acceptance",
        "validation_scope": "full",
        "approval_archive_mode": "full",
        "requires_diff_ref": True,
        "requires_approval_records": True,
        "requires_change_packages": True,
    },
    "archive-audit": {
        "operation": "validate-adapter",
        "validation_phase": "acceptance",
        "validation_scope": "full",
        "approval_archive_mode": "full",
        "requires_diff_ref": False,
        "requires_approval_records": False,
        "requires_change_packages": False,
    },
}


class FindingSink(Protocol):
    allow_placeholders: bool

    def target_path(self, relpath: str) -> Path: ...
    def load_json_object(self, path: Path, code_prefix: str) -> dict[str, Any] | None: ...
    def error(self, code: str, message: str, path: str | None = None) -> None: ...
    def warn(self, code: str, message: str, path: str | None = None) -> None: ...
    def info(self, code: str, message: str, path: str | None = None) -> None: ...


def validate_validation_contract(sink: FindingSink, manifest: Any) -> None:
    if manifest is not None:
        pointer = manifest.scalars.get(("validation", "contract"))
        if pointer is not None and pointer.value != CONTRACT_PATH:
            sink.error(
                "VALIDATION_CONTRACT_POINTER",
                f"manifest validation.contract must be {CONTRACT_PATH}",
                ".ai/alatyr.yaml",
            )
    contract = sink.load_json_object(
        sink.target_path(CONTRACT_PATH), "VALIDATION_CONTRACT"
    )
    if contract is None:
        return
    try:
        schema = json.loads(VALIDATION_CONTRACT_SCHEMA.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        sink.error(
            "VALIDATION_CONTRACT_SCHEMA",
            str(exc),
            str(VALIDATION_CONTRACT_SCHEMA),
        )
        return
    try:
        jsonschema.validate(contract, schema)
    except jsonschema.ValidationError as exc:
        sink.error(
            "VALIDATION_CONTRACT_SCHEMA",
            exc.message,
            CONTRACT_PATH,
        )
        return

    schema_version = contract["schema_version"]
    entrypoints = contract["entrypoints"]
    structural_only: list[str] = []
    for operation in ENTRYPOINTS:
        entry = entrypoints[operation]
        command = entry["command"]
        coverage = entry["coverage"]
        if is_placeholder(command):
            report = sink.warn if sink.allow_placeholders else sink.error
            report(
                "VALIDATION_CONTRACT_COMMAND_UNRESOLVED",
                f"{operation} command is unresolved",
                CONTRACT_PATH,
            )
        try:
            command_tokens = shlex.split(command)
        except ValueError:
            command_tokens = []
        absolute_tokens = [
            token
            for token in command_tokens
            if token.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", token)
        ]
        if absolute_tokens:
            sink.error(
                "VALIDATION_CONTRACT_ABSOLUTE_PATH",
                f"{operation} command contains machine-local absolute paths",
                CONTRACT_PATH,
            )
        if schema_version == 1:
            if coverage == "canonical-delegate" and "validate_target_adapter" not in command:
                sink.error(
                    "VALIDATION_CONTRACT_FALSE_CANONICAL_CLAIM",
                    f"{operation} claims canonical delegation without naming the canonical validator",
                    CONTRACT_PATH,
                )
        else:
            delegate = entry.get("canonical_delegate")
            if coverage == "canonical-delegate":
                if DELEGATE_PATH not in command_tokens:
                    sink.error(
                        "VALIDATION_CONTRACT_DELEGATE_COMMAND",
                        f"{operation} canonical command must invoke {DELEGATE_PATH}",
                        CONTRACT_PATH,
                    )
                if not isinstance(delegate, dict):
                    sink.error(
                        "VALIDATION_CONTRACT_DELEGATE_MISSING",
                        f"{operation} canonical delegation requires structured delegate metadata",
                        CONTRACT_PATH,
                    )
                else:
                    expected = EXPECTED_DELEGATES[operation]
                    drift = sorted(
                        key for key, value in expected.items() if delegate.get(key) != value
                    )
                    if drift:
                        sink.error(
                            "VALIDATION_CONTRACT_DELEGATE_DRIFT",
                            f"{operation} canonical delegate differs for: {', '.join(drift)}",
                            CONTRACT_PATH,
                        )
            elif delegate is not None:
                sink.error(
                    "VALIDATION_CONTRACT_DELEGATE_UNCLAIMED",
                    f"{operation} has canonical delegate metadata without canonical-delegate coverage",
                    CONTRACT_PATH,
                )
        if coverage in {"structural-only", "manual"}:
            structural_only.append(operation)
        if entry["final_evidence_eligible"] and coverage not in {
            "canonical-delegate",
            "target-equivalent",
        }:
            sink.error(
                "VALIDATION_CONTRACT_FINAL_EVIDENCE",
                f"{operation} cannot be final-evidence eligible with {coverage} coverage",
                CONTRACT_PATH,
            )

    if structural_only:
        sink.warn(
            "VALIDATION_CONTRACT_LIMITED",
            "target-local validation is not canonical for: "
            + ", ".join(structural_only),
            CONTRACT_PATH,
        )
    if schema_version == 1:
        sink.warn(
            "VALIDATION_CONTRACT_LEGACY",
            "schema version 1 cannot prove canonical delegation structurally; migrate to version 2",
            CONTRACT_PATH,
        )
    sink.info(
        "VALIDATION_CONTRACT_CHECKED",
        "target-local validation coverage is explicit; local success is not canonical success",
        CONTRACT_PATH,
    )


__all__ = ["validate_validation_contract"]
