#!/usr/bin/env python3
"""Validate admission audits for newly named assistant surfaces.

This checks AlatyrCore's static integration contract. It does not run vendor
clients or prove that an external assistant loaded or followed instructions.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from target_adapter_validation.assistant_capabilities import (
    SURFACE_CAPABILITY_SCHEMA_VERSION,
    SURFACE_STATE_SCALAR_FIELDS,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
AUDITS = ROOT / "conformance" / "assistant-surface-integration-audits.json"
EXECUTORS = ROOT / "conformance" / "executors" / "executor-capabilities.json"
MATRIX = TARGET / ".ai" / "assistant" / "bridge-capability-matrix.md"
CAPABILITY_INDEX = TARGET / ".ai" / "assistant" / "assistant-capabilities.json"

REQUIRED_CONTROLS = {
    "bootstrap-routing": "bridge-static",
    "operation-routing": "bridge-static",
    "current-scope-authorization": "bridge-static",
    "tool-permission-separation": "runtime-verification-required",
    "skills-and-prompts": "canonical-routing-static-native-loading-unverified",
    "subagent-delegation": "runtime-verification-required",
    "diagram-presentation": "ascii-fallback-static-rich-output-unverified",
    "post-install-update-delivery": "runtime-verification-required",
    "runtime-evidence": "required-before-supported-runtime-claim",
}
REQUIRED_RUNTIME_CHECK_FRAGMENTS = {
    "auto-load",
    "exact alias",
    "read-only discussion",
    "tool permissions",
    "skills and prompts",
    "delegation backend",
    "ASCII diagram",
    "post-install or post-update",
}
REQUIRED_BRIDGE_REFS = {
    ".ai/assistant/operation-index.json",
    ".ai/assistant/operation-catalog.json",
    ".ai/assistant/help.md",
    ".ai/assistant/flows/operation-routing.flow.md",
}
REQUIRED_ROOT_REFS = REQUIRED_BRIDGE_REFS | {
    ".ai/assistant/bootstrap-index.json",
    ".ai/assistant/policies/action-authorization.json",
    ".ai/assistant/ai-infrastructure-router.json",
    ".ai/assistant/assistant-capabilities.json",
    ".ai/assistant/prompts/worker-orchestration.md",
}
OFFICIAL_HOSTS = {
    "agents": {"agents.md"},
    "codex": {"learn.chatgpt.com"},
    "claude": {"code.claude.com"},
    "gemini": {"github.com"},
    "github-copilot": {"docs.github.com"},
    "cursor": {"docs.cursor.com", "cursor.com"},
    "devin-cascade": {"docs.devin.ai"},
    "windsurf": {"docs.windsurf.com", "docs.devin.ai"},
    "junie": {"junie.jetbrains.com"},
    "cline": {"docs.cline.bot"},
    "roo-code": {"github.com"},
    "kiro": {"kiro.dev"},
    "zed-agent": {"zed.dev"},
    "opencode": {"opencode.ai"},
}
ENTRY_HEADING = re.compile(r"^### Assistant Surface: `([^`]+)`\s*$", re.MULTILINE)


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def matrix_entries(text: str) -> dict[str, str]:
    matches = list(ENTRY_HEADING.finditer(text))
    entries: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries[match.group(1)] = text[match.end() : end]
    return entries


def string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item for item in value
    )


def validate_contracts(
    surfaces_data: dict[str, Any],
    audits_data: dict[str, Any],
    executors_data: dict[str, Any],
    capability_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    failures: list[str] = []
    surfaces = surfaces_data.get("surfaces")
    audits = audits_data.get("audits")
    if not isinstance(surfaces, list):
        return ["assistant surfaces must be a list"]
    if not isinstance(audits, list):
        return ["assistant surface audits must be a list"]

    surface_by_id = {
        item.get("id"): item
        for item in surfaces
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    audit_by_id = {
        item.get("id"): item
        for item in audits
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    required_audits = {
        item.get("admission_audit")
        for item in surfaces
        if isinstance(item, dict) and isinstance(item.get("admission_audit"), str)
    }
    if set(audit_by_id) != required_audits:
        failures.append(
            "admission audit IDs differ from audited assistant surfaces: "
            f"expected {sorted(required_audits)}, got {sorted(audit_by_id)}"
        )

    required_controls = audits_data.get("required_controls")
    if not isinstance(required_controls, list) or set(required_controls) != set(
        REQUIRED_CONTROLS
    ):
        failures.append("assistant audit required_controls are incomplete")
    control_defaults = audits_data.get("control_dispositions")
    if control_defaults != REQUIRED_CONTROLS:
        failures.append("assistant audit control defaults are incomplete")
    runtime_checks = audits_data.get("required_runtime_checks")
    if not string_list(runtime_checks):
        failures.append("assistant audit required_runtime_checks must be non-empty")
        runtime_checks = []
    runtime_text = " ".join(runtime_checks)
    for fragment in REQUIRED_RUNTIME_CHECK_FRAGMENTS:
        if fragment not in runtime_text:
            failures.append(f"assistant runtime checks omit {fragment}")

    matrix = matrix_entries(MATRIX.read_text(encoding="utf-8"))
    capability_index = load_object(CAPABILITY_INDEX).get("surfaces")
    if not isinstance(capability_index, dict):
        failures.append("assistant capability index surfaces must be an object")
        capability_index = {}
    root_bridge = (TARGET / "AGENTS.md").read_text(encoding="utf-8")
    for required in REQUIRED_ROOT_REFS:
        if required not in root_bridge:
            failures.append(f"root AGENTS.md omits {required}")

    executors = executors_data.get("executors")
    manual = next(
        (
            item
            for item in executors
            if isinstance(item, dict) and item.get("id") == "manual-import"
        ),
        None,
    ) if isinstance(executors, list) else None
    manual_surfaces = set(manual.get("supported_surfaces", [])) if isinstance(manual, dict) else set()

    for audit_id in sorted(required_audits):
        audit = audit_by_id.get(audit_id)
        surface = surface_by_id.get(audit_id)
        if not isinstance(audit, dict) or not isinstance(surface, dict):
            continue
        if audit.get("surface_id") != audit_id:
            failures.append(f"{audit_id} audit surface identity differs")
        lifecycle = surface.get("product_lifecycle")
        support_status = surface.get("support_status")
        expected_audit_status = {
            "protocol": "protocol-static-contract-runtime-unverified",
            "legacy": "legacy-static-contract-runtime-unverified",
            "archived": "legacy-static-contract-runtime-unverified",
            "active": "static-contract-ready-runtime-unverified",
        }.get(lifecycle)
        if audit.get("status") != expected_audit_status:
            failures.append(f"{audit_id} audit has the wrong lifecycle status")
        if lifecycle not in {"protocol", "active", "legacy", "archived"}:
            failures.append(f"{audit_id} product lifecycle is invalid")
        expected_support = {
            "protocol": "protocol-static-admission-runtime-unverified",
            "legacy": "legacy-static-admission-runtime-unverified",
            "archived": "legacy-static-admission-runtime-unverified",
            "active": "named-static-admission-runtime-unverified",
        }.get(lifecycle)
        if support_status != expected_support:
            failures.append(f"{audit_id} source support status is invalid")
        if audit.get("runtime_execution_claimed") is not False:
            failures.append(f"{audit_id} audit must not claim runtime execution")
        bridge_paths = surface.get("bridge_paths")
        if audit.get("selected_bridge_paths") != bridge_paths:
            failures.append(f"{audit_id} audit bridge paths differ from surface contract")
            bridge_paths = []
        for field in [
            "documented_instruction_paths",
            "precedence_risks",
            "compatibility_paths_to_inspect",
            "residual_limits",
        ]:
            if not string_list(audit.get(field)):
                failures.append(f"{audit_id} audit {field} must be non-empty strings")
        if not isinstance(audit.get("loading_behavior"), str) or not audit["loading_behavior"]:
            failures.append(f"{audit_id} audit loading_behavior must be recorded")
        official_sources = audit.get("official_sources")
        if audit_id == "generic":
            if official_sources != [] or not string_list(audit.get("contract_sources")):
                failures.append("generic audit must use local contract sources")
        elif not string_list(official_sources):
            failures.append(f"{audit_id} audit official_sources must be non-empty strings")
        if audit.get("control_dispositions", control_defaults) != REQUIRED_CONTROLS:
            failures.append(f"{audit_id} audit control dispositions are incomplete")
        if audit_id == "opencode":
            if audit.get("runtime_variants") != ["v1", "v2"]:
                failures.append("opencode audit must distinguish V1 and V2")
            variant_loading = audit.get("variant_loading")
            if not isinstance(variant_loading, dict) or set(variant_loading) != {"v1", "v2"}:
                failures.append("opencode audit must record both loading contracts")

        allowed_hosts = OFFICIAL_HOSTS.get(audit_id, set())
        for source in audit.get("official_sources", []):
            parsed = urlparse(source)
            if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
                failures.append(f"{audit_id} has non-official audit source {source}")

        for relpath in bridge_paths if isinstance(bridge_paths, list) else []:
            path = TARGET / relpath
            if not path.is_file():
                failures.append(f"{audit_id} bridge is missing: {relpath}")
                continue
            text = path.read_text(encoding="utf-8")
            if relpath != "AGENTS.md" and "AGENTS.md" not in text:
                failures.append(f"{audit_id} bridge {relpath} does not route root AGENTS.md")
            for required in REQUIRED_BRIDGE_REFS:
                if required not in text:
                    failures.append(f"{audit_id} bridge {relpath} omits {required}")

        block = matrix.get(audit_id, "")
        label = surface.get("label")
        if not block or f"Assistant: `{label}`" not in block:
            failures.append(f"{audit_id} bridge matrix entry is missing or mislabeled")
        expected_capability = f".ai/assistant/assistant-capabilities/{audit_id}.json"
        if capability_index.get(audit_id) != expected_capability:
            failures.append(f"{audit_id} capability index path is missing")
        capability_path = TARGET / expected_capability
        if not capability_path.is_file():
            failures.append(f"{audit_id} capability record is missing")
        else:
            capability = (
                capability_overrides.get(audit_id)
                if capability_overrides and audit_id in capability_overrides
                else load_object(capability_path)
            )
            if capability.get("assistant_surface") != audit_id:
                failures.append(f"{audit_id} capability record identity differs")
            if capability.get("schema_version") != SURFACE_CAPABILITY_SCHEMA_VERSION:
                failures.append(
                    f"{audit_id} capability record must use schema "
                    f"{SURFACE_CAPABILITY_SCHEMA_VERSION}"
                )
            state = capability.get("surface_state")
            if not isinstance(state, dict):
                failures.append(f"{audit_id} capability record lacks surface_state")
            else:
                for field in sorted(SURFACE_STATE_SCALAR_FIELDS):
                    value = state.get(field)
                    if not isinstance(value, str) or "{" not in value:
                        failures.append(
                            f"{audit_id} capability surface_state.{field} must remain placeholder-based"
                        )
            for section_name in ["instruction_loading", "skills", "tool_permissions"]:
                if not isinstance(capability.get(section_name), dict):
                    failures.append(f"{audit_id} capability record lacks {section_name}")
            permissions = capability.get("tool_permissions")
            if not isinstance(permissions, dict) or permissions.get(
                "alatyr_authorization_separate"
            ) is not True:
                failures.append(f"{audit_id} client permissions can grant Alatyr authorization")
            diagram = capability.get("diagram_discussion")
            if not isinstance(diagram, dict) or diagram.get("readable_fallback") != "ascii":
                failures.append(f"{audit_id} capability record has no ASCII fallback")
            if not isinstance(capability.get("subagent_delegation"), dict):
                failures.append(f"{audit_id} capability record has no delegation contract")
        if audit_id not in manual_surfaces:
            failures.append(f"{audit_id} is absent from provider-neutral manual import")

    return failures


def main() -> int:
    failures: list[str] = []
    try:
        surfaces = load_object(SURFACES)
        audits = load_object(AUDITS)
        executors = load_object(EXECUTORS)
        if audits.get("schema_version") != 1:
            failures.append("assistant audit schema_version must be 1")
        if audits.get("audit_kind") != "alatyr-assistant-surface-integration-admission":
            failures.append("assistant audit kind is invalid")
        failures.extend(validate_contracts(surfaces, audits, executors))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    audit_count = len(audits.get("audits", [])) if isinstance(audits.get("audits"), list) else 0
    print(
        f"OK: audited {audit_count} assistant admissions with lifecycle, "
        "static contracts, and runtime limits"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
