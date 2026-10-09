"""Target-validator scenarios for local and canonical validation boundaries."""

from __future__ import annotations

import copy
from pathlib import Path
import json

from .common import parse_manifest, validator, write_json
from target_adapter_validation.validation_contract import (
    DELEGATE_PATH,
    validate_validation_contract,
)


def run(target: Path, failures: list[str]) -> None:
    contract_target = target / "validation-contract"
    manifest_path = contract_target / ".ai/alatyr.yaml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        "validation:\n  contract: .ai/assistant/validation-contract.json\n",
        encoding="utf-8",
    )
    contract_path = contract_target / ".ai/assistant/validation-contract.json"
    contract = {
        "schema_version": 1,
        "contract_kind": "target-validation-contract",
        "entrypoints": {
            operation: {
                "command": "bash scripts/check-alatyr.sh",
                "coverage": "structural-only",
                "final_evidence_eligible": False,
            }
            for operation in ["adapter-health", "current-change", "archive-audit"]
        },
        "parity": {
            "local_pass_is_canonical": False,
            "comparison": "canonical-result-required",
            "result_evidence": "unavailable",
        },
    }
    write_json(contract_path, contract)
    manifest = parse_manifest(manifest_path)
    limited = validator(contract_target)
    validate_validation_contract(limited, manifest)
    if "VALIDATION_CONTRACT_LIMITED" not in {
        finding.code for finding in limited.findings
    }:
        failures.append("structural-only local validation must report limited coverage")

    contract["entrypoints"]["adapter-health"] = {
        "command": "bash scripts/check-alatyr.sh",
        "coverage": "canonical-delegate",
        "final_evidence_eligible": True,
    }
    write_json(contract_path, contract)
    false_claim = validator(contract_target)
    validate_validation_contract(false_claim, manifest)
    if "VALIDATION_CONTRACT_FALSE_CANONICAL_CLAIM" not in {
        finding.code for finding in false_claim.findings
    }:
        failures.append("canonical delegation claims must name the canonical validator")

    version2 = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "templates/target/.ai/assistant/validation-contract.json"
        ).read_text(encoding="utf-8")
    )
    source_delegate = (
        Path(__file__).resolve().parents[3]
        / "templates/target"
        / DELEGATE_PATH
    )
    installed_delegate = contract_target / DELEGATE_PATH
    installed_delegate.parent.mkdir(parents=True, exist_ok=True)
    installed_delegate.write_text(
        source_delegate.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    write_json(contract_path, version2)
    valid = validator(contract_target)
    validate_validation_contract(valid, manifest)
    if any(finding.level == "error" for finding in valid.findings):
        failures.append("structured canonical delegate contract must validate")

    spoofed_contract = copy.deepcopy(version2)
    spoofed_contract["entrypoints"]["current-change"]["command"] = (
        "python3 .ai/assistant/tools/alatyr_delegate.py-invalid validate-current"
    )
    write_json(contract_path, spoofed_contract)
    spoofed = validator(contract_target)
    validate_validation_contract(spoofed, manifest)
    if "VALIDATION_CONTRACT_DELEGATE_COMMAND" not in {
        finding.code for finding in spoofed.findings
    }:
        failures.append("near-match delegate paths must not prove canonical delegation")

    mutation_cases = [
        (
            "python3 .ai/assistant/tools/alatyr_delegate.py status --target .",
            "VALIDATION_CONTRACT_DELEGATE_OPERATION",
            "wrong delegate operations must not prove canonical delegation",
        ),
        (
            "echo .ai/assistant/tools/alatyr_delegate.py",
            "VALIDATION_CONTRACT_DELEGATE_COMMAND",
            "mentioning the delegate path must not prove invocation",
        ),
        (
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --help yes",
            "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
            "unsupported delegate arguments must not prove canonical execution",
        ),
        (
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --diff-ref -h --approval-record approval.json --change-package package.json",
            "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
            "delegate-parser argument rejection must prevent canonical delegation",
        ),
        (
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . --diff-ref HEAD --diff-r OTHER --approval-record approval.json --change-package package.json",
            "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
            "abbreviated duplicate options must not replace canonical bindings",
        ),
        (
            "python3 .ai/assistant/tools/alatyr_delegate.py validate-current --target . && echo done",
            "VALIDATION_CONTRACT_DELEGATE_ARGUMENTS",
            "shell-composed commands must not prove canonical execution",
        ),
    ]
    for command, expected_code, message in mutation_cases:
        mutated_contract = copy.deepcopy(version2)
        mutated_contract["entrypoints"]["current-change"]["command"] = command
        write_json(contract_path, mutated_contract)
        mutated = validator(contract_target)
        validate_validation_contract(mutated, manifest)
        if expected_code not in {finding.code for finding in mutated.findings}:
            failures.append(message)

    drifted_contract = copy.deepcopy(version2)
    drifted_contract["entrypoints"]["current-change"]["canonical_delegate"][
        "requires_diff_ref"
    ] = False
    write_json(contract_path, drifted_contract)
    drifted = validator(contract_target)
    validate_validation_contract(drifted, manifest)
    if "VALIDATION_CONTRACT_DELEGATE_DRIFT" not in {
        finding.code for finding in drifted.findings
    }:
        failures.append("structured current-change enforcement drift must fail")

    write_json(contract_path, version2)
    installed_delegate.write_text(
        source_delegate.read_text(encoding="utf-8")
        + "\nCANONICAL_OPERATION_DISABLED = True\n",
        encoding="utf-8",
    )
    content_drift = validator(contract_target)
    validate_validation_contract(content_drift, manifest)
    if "VALIDATION_CONTRACT_DELEGATE_CONTENT" not in {
        finding.code for finding in content_drift.findings
    }:
        failures.append("modified delegate semantics must not prove canonical delegation")
