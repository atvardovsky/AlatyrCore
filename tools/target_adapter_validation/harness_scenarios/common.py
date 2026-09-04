"""Shared fixtures and helpers for target-validator scenarios."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from framework_packaging import FRAMEWORK_ROOT, projected_framework_contents
from validate_target_adapter import (
    AdapterValidatorConfig,
    Finding,
    Validator,
    approval_enforcement_enabled,
    extract_list_field,
    findings_payload,
    git_changed_files,
    parse_manifest,
    parse_registry_fact_entries,
    result_code,
    scope_entries_cover,
)
from target_adapter_validation.context_catalogs import (
    validate_context_catalog_contract,
)
from target_adapter_validation.assistant_capabilities import (
    CAPABILITY_INDEX_KIND,
    CAPABILITY_INDEX_SCHEMA_VERSION,
    STATE_EVIDENCE_TEXT,
    SURFACE_CAPABILITY_KIND,
    SURFACE_CAPABILITY_SCHEMA_VERSION,
    capability_record_path,
)

ROOT = Path(__file__).resolve().parents[3]
DELEGATION_FIXTURE_PATHS = (
    ".ai/framework/task-decomposition.md",
    ".ai/framework/subagent-delegation.md",
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/delegation-policy.json",
    ".ai/assistant/context/task-scales/delegated-execution.json",
    ".ai/assistant/flows/subagent-delegation.flow.md",
    ".ai/assistant/prompts/worker-orchestration.md",
    ".ai/assistant/templates/subagent-task-packet.md",
    ".ai/assistant/templates/native-worker-binding.md",
    ".ai/assistant/templates/worker-execution-plan.md",
    ".ai/assistant/templates/worker-result.md",
    ".ai/assistant/workers/role-catalog.json",
    ".ai/assistant/workers/roles/explorer.md",
    ".ai/assistant/workers/roles/implementer.md",
    ".ai/assistant/workers/roles/test-runner.md",
    ".ai/assistant/workers/roles/documentation-worker.md",
    ".ai/assistant/workers/roles/reviewer.md",
    ".ai/assistant/workers/roles/fast-focused-worker.md",
    ".ai/assistant/assistant-capabilities.json",
    ".ai/assistant/bridge-capability-matrix.md",
)


def validator(
    target: Path,
    framework_source: Path | None = None,
    *,
    validation_phase: str = "migration-staging",
) -> Validator:
    return Validator(
        target,
        framework_source=framework_source,
        diff_ref=None,
        approval_records=[],
        enforce_approval_scope=False,
        change_packages=[],
        enforce_change_package=False,
        migration_diff=None,
        allow_placeholders=True,
        allow_local_paths=[],
        config=AdapterValidatorConfig(),
        validation_phase=validation_phase,
    )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def check_context_cache_regressions(
    target: Path,
    manifest: object,
    record_path: Path,
    record: dict[str, object],
    failures: list[str],
) -> None:
    permissions = record["tool_permissions"]
    assert isinstance(permissions, dict)
    permissions["alatyr_authorization_separate"] = False
    write_json(record_path, record)
    permission_validator = validator(target)
    permission_validator.check_assistant_instruction_capabilities(manifest)
    if "ASSISTANT_PERMISSION_AUTHORIZATION_CONFLICT" not in {
        finding.code for finding in permission_validator.findings
    }:
        failures.append("client permissions must not grant Alatyr authorization")
    permissions["alatyr_authorization_separate"] = True

    caching = record["context_caching"]
    assert isinstance(caching, dict)
    caching["provider_cache_mode"] = "explicit"
    write_json(record_path, record)
    cache_control_validator = validator(target)
    cache_control_validator.check_assistant_instruction_capabilities(manifest)
    if "ASSISTANT_CONTEXT_CACHE_CONTROL" not in {
        finding.code for finding in cache_control_validator.findings
    }:
        failures.append(
            "explicit-only provider caching must require exposed client controls"
        )

    caching["provider_cache_mode"] = "automatic"
    caching["context_window_reduction"] = True
    write_json(record_path, record)
    cache_claim_validator = validator(target)
    cache_claim_validator.check_assistant_instruction_capabilities(manifest)
    if "ASSISTANT_CONTEXT_CACHE_WINDOW_CLAIM" not in {
        finding.code for finding in cache_claim_validator.findings
    }:
        failures.append("context caching must not claim context-window reduction")
    caching["context_window_reduction"] = False

    caching["provider_cache_mode"] = "unsupported"
    write_json(record_path, record)
    cache_state_validator = validator(target)
    cache_state_validator.check_assistant_instruction_capabilities(manifest)
    if "ASSISTANT_CONTEXT_CACHE_STATE_CONFLICT" not in {
        finding.code for finding in cache_state_validator.findings
    }:
        failures.append("supported cache routes must reject unsupported provider mode")
    caching["provider_cache_mode"] = "automatic"
    write_json(record_path, record)


def check_core_contracts(failures: list[str]) -> None:
    parsed_registry = parse_registry_fact_entries(
        "### Fact Type: `business rule`\n\n"
        "Fact type: `business rule`\n"
        "Consistency map node: `fact-business-rule`\n"
    )
    if len(parsed_registry) != 1 or (
        parsed_registry[0].heading_fact_type,
        parsed_registry[0].declared_fact_type,
        parsed_registry[0].map_node_id,
    ) != ("business rule", "business rule", "fact-business-rule"):
        failures.append("registry Fact Type parser lost exact node identity")
    if not approval_enforcement_enabled(
        diff_ref="HEAD",
        approval_records=[Path("approval.json")],
        explicitly_enforced=False,
    ):
        failures.append("explicit approval plus diff must enable scope enforcement")
    if approval_enforcement_enabled(
        diff_ref="HEAD",
        approval_records=[],
        explicitly_enforced=False,
    ):
        failures.append("diff inspection without selected approval must remain advisory")
