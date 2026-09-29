"""Validate target-local checker coverage and canonical-result boundaries."""

from __future__ import annotations

import json
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
        if coverage == "canonical-delegate" and "validate_target_adapter" not in command:
            sink.error(
                "VALIDATION_CONTRACT_FALSE_CANONICAL_CLAIM",
                f"{operation} claims canonical delegation without naming the canonical validator",
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
    sink.info(
        "VALIDATION_CONTRACT_CHECKED",
        "target-local validation coverage is explicit; local success is not canonical success",
        CONTRACT_PATH,
    )


__all__ = ["validate_validation_contract"]
