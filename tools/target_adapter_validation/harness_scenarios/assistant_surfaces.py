"""Target-validator scenarios for assistant surfaces."""

from __future__ import annotations

from .common import (
    CAPABILITY_INDEX_KIND,
    CAPABILITY_INDEX_SCHEMA_VERSION,
    STATE_EVIDENCE_TEXT,
    SURFACE_CAPABILITY_KIND,
    SURFACE_CAPABILITY_SCHEMA_VERSION,
    capability_record_path,
    check_context_cache_regressions,
    json,
    parse_manifest,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    instruction_target = target / "instruction-capabilities"
    (instruction_target / ".ai/assistant/assistant-capabilities").mkdir(
        parents=True
    )
    (instruction_target / "AGENTS.md").write_text(
        "# Test instructions\n", encoding="utf-8"
    )
    (instruction_target / ".ai/alatyr.yaml").parent.mkdir(
        parents=True, exist_ok=True
    )
    (instruction_target / ".ai/alatyr.yaml").write_text(
        "schema_version: 27\nsupported_assistants:\n  - generic\n",
        encoding="utf-8",
    )
    instruction_index = {
        "schema_version": CAPABILITY_INDEX_SCHEMA_VERSION,
        "capability_kind": CAPABILITY_INDEX_KIND,
        "state_evidence": {
            "state_model": STATE_EVIDENCE_TEXT,
            "selected_surface": "generic",
            "selected_surface_evidence": "fixture manifest",
            "capability_records_are_authoritative": True,
            "unknown_means_not_verified": True,
            "stale_or_expired_evidence_requires_recheck": True,
        },
        "surfaces": {
            "generic": capability_record_path("generic")
        },
    }
    write_json(
        instruction_target / ".ai/assistant/assistant-capabilities.json",
        instruction_index,
    )
    evidence = {
        "verified_at": "2026-08-25",
        "client_version": "fixture-1",
        "evidence": "fixture observation",
        "expires_at": "review-trigger: client changed",
        "review_triggers": ["client changed"],
    }
    instruction_record = {
        "schema_version": SURFACE_CAPABILITY_SCHEMA_VERSION,
        "capability_kind": SURFACE_CAPABILITY_KIND,
        "assistant_surface": "generic",
        "surface_state": {
            "overall": "supported",
            "selected_for_target": "yes",
            "evidence_state": "current",
            "advertised_by_surface": "yes",
            "verified_for_target": "yes",
            "limitations": ["fixture-only capability evidence"],
            "review_triggers": ["client changed"],
        },
        "instruction_loading": {
            **evidence,
            "route": "supported",
            "runtime_variant": "fixture",
            "selected_entry_path": "AGENTS.md",
            "competing_sources": [],
            "auto_load_observed": "yes",
            "precedence_evidence": "fixture observation",
            "configuration_state": "fixture default",
        },
        "skills": {
            **evidence,
            "route": "unsupported",
            "discovery_paths": [],
            "selected_source": "none",
            "activation_mode": "disabled",
        },
        "tool_permissions": {
            **evidence,
            "client_permission_mode": "ask",
            "effective_restrictions": "fixture read/write prompt",
            "alatyr_authorization_separate": True,
        },
        "context_caching": {
            **evidence,
            "route": "supported",
            "provider": "fixture-provider",
            "model": "fixture-model",
            "provider_cache_mode": "automatic",
            "client_control_exposure": "unsupported",
            "client_telemetry_exposure": "supported",
            "retention": "fixture-session",
            "minimum_cacheable_tokens": "1",
            "stable_prefix_ordering": True,
            "context_window_reduction": False,
            "fallback": "bounded-context-routing",
        },
        "diagram_discussion": {},
        "subagent_delegation": {},
    }
    instruction_path = (
        instruction_target
        / ".ai/assistant/assistant-capabilities/generic.json"
    )
    write_json(instruction_path, instruction_record)
    instruction_validator = validator(instruction_target)
    instruction_manifest = parse_manifest(
        instruction_target / ".ai/alatyr.yaml"
    )
    instruction_validator.check_assistant_instruction_capabilities(
        instruction_manifest
    )
    instruction_errors = {
        finding.code
        for finding in instruction_validator.findings
        if finding.level == "error"
    }
    if instruction_errors:
        failures.append(
            "valid assistant instruction capability produced errors: "
            + ", ".join(sorted(instruction_errors))
        )

    invalid_index = dict(instruction_index)
    invalid_index["surfaces"] = {
        "generic": ".ai/assistant/assistant-capabilities/wrong.json"
    }
    write_json(
        instruction_target / ".ai/assistant/assistant-capabilities.json",
        invalid_index,
    )
    invalid_index_validator = validator(instruction_target)
    invalid_index_validator.check_assistant_instruction_capabilities(
        instruction_manifest
    )
    if "ASSISTANT_CAPABILITY_INDEX_ENTRY" not in {
        finding.code for finding in invalid_index_validator.findings
    }:
        failures.append("assistant capability index path drift must be rejected")
    write_json(
        instruction_target / ".ai/assistant/assistant-capabilities.json",
        instruction_index,
    )

    instruction_record["instruction_loading"]["auto_load_observed"] = "no"
    write_json(instruction_path, instruction_record)
    unproven_validator = validator(instruction_target)
    unproven_validator.check_assistant_instruction_capabilities(
        instruction_manifest
    )
    if "ASSISTANT_AUTO_LOAD_UNPROVEN" not in {
        finding.code for finding in unproven_validator.findings
    }:
        failures.append("supported assistant route must require observed auto-load")

    instruction_record["instruction_loading"]["auto_load_observed"] = "yes"
    instruction_record["tool_permissions"]["alatyr_authorization_separate"] = True
    check_context_cache_regressions(
        instruction_target,
        instruction_manifest,
        instruction_path,
        instruction_record,
        failures,
    )

    inactive_bridge_target = target / "inactive-assistant-bridge"
    (inactive_bridge_target / ".ai/assistant/assistant-capabilities").mkdir(
        parents=True
    )
    (inactive_bridge_target / "AGENTS.md").write_text(
        "# Active instructions\n", encoding="utf-8"
    )
    (inactive_bridge_target / "AI_ASSISTANTS.md").write_text(
        "Neutral example: size={24}\n", encoding="utf-8"
    )
    (inactive_bridge_target / "CLAUDE.md").write_text(
        "Legacy example: size={24}\n", encoding="utf-8"
    )
    inactive_manifest_path = inactive_bridge_target / ".ai/alatyr.yaml"
    inactive_manifest_path.write_text(
        "supported_assistants:\n  - codex\n", encoding="utf-8"
    )
    write_json(
        inactive_bridge_target / ".ai/assistant/assistant-capabilities.json",
        {
            "schema_version": CAPABILITY_INDEX_SCHEMA_VERSION,
            "capability_kind": CAPABILITY_INDEX_KIND,
            "state_evidence": {
                "state_model": STATE_EVIDENCE_TEXT,
                "selected_surface": "codex",
                "selected_surface_evidence": "fixture manifest",
                "capability_records_are_authoritative": True,
                "unknown_means_not_verified": True,
                "stale_or_expired_evidence_requires_recheck": True,
            },
            "surfaces": {
                "codex": capability_record_path("codex"),
                "claude": capability_record_path("claude"),
            },
            "bridge_paths": {
                "codex": ["AGENTS.md", "AI_ASSISTANTS.md"],
                "claude": ["CLAUDE.md"],
            },
        },
    )
    write_json(
        inactive_bridge_target
        / ".ai/assistant/assistant-capabilities/codex.json",
        {
            "surface_state": {
                "overall": "supported",
                "selected_for_target": "yes",
                "evidence_state": "current",
                "advertised_by_surface": "yes",
                "verified_for_target": "yes",
            },
            "instruction_loading": {"route": "supported"},
        },
    )
    write_json(
        inactive_bridge_target
        / ".ai/assistant/assistant-capabilities/claude.json",
        {
            "surface_state": {
                "overall": "unsupported",
                "selected_for_target": "no",
                "evidence_state": "current",
                "advertised_by_surface": "yes",
                "verified_for_target": "yes",
            },
            "instruction_loading": {"route": "unsupported"},
        },
    )
    inactive_manifest = parse_manifest(inactive_manifest_path)
    inactive_bridge_validator = validator(
        inactive_bridge_target, validation_phase="acceptance"
    )
    inactive_bridge_validator.check_placeholders(
        inactive_manifest, "core", set()
    )
    if any(
        finding.code == "PLACEHOLDER_UNRESOLVED"
        and finding.path == "CLAUDE.md:1"
        for finding in inactive_bridge_validator.findings
    ):
        failures.append(
            "explicitly unsupported unselected assistant bridges must not be "
            "scanned as active adapter surfaces"
        )
    if not any(
        finding.code == "PLACEHOLDER_UNRESOLVED"
        and finding.path == "AI_ASSISTANTS.md:1"
        for finding in inactive_bridge_validator.findings
    ):
        failures.append(
            "neutral assistant entry points must remain active regardless of "
            "surface capability routes"
        )

    capability_index_path = (
        inactive_bridge_target / ".ai/assistant/assistant-capabilities.json"
    )
    partial_index = json.loads(capability_index_path.read_text(encoding="utf-8"))
    partial_index["bridge_paths"]["unrepresented"] = ["CLAUDE.md"]
    write_json(capability_index_path, partial_index)
    partial_index_validator = validator(
        inactive_bridge_target, validation_phase="acceptance"
    )
    partial_index_validator.check_placeholders(
        inactive_manifest, "core", set()
    )
    if not any(
        finding.code == "PLACEHOLDER_UNRESOLVED"
        and finding.path == "CLAUDE.md:1"
        for finding in partial_index_validator.findings
    ):
        failures.append(
            "partially represented bridge ownership must remain active fail-safe"
        )
    partial_index["bridge_paths"].pop("unrepresented")
    write_json(capability_index_path, partial_index)

    inactive_manifest_path.write_text(
        "supported_assistants:\n  - claude\n", encoding="utf-8"
    )
    selected_inactive_manifest = parse_manifest(inactive_manifest_path)
    selected_inactive_validator = validator(
        inactive_bridge_target, validation_phase="acceptance"
    )
    selected_inactive_validator.check_placeholders(
        selected_inactive_manifest, "core", set()
    )
    if not any(
        finding.code == "PLACEHOLDER_UNRESOLVED"
        and finding.path == "CLAUDE.md:1"
        for finding in selected_inactive_validator.findings
    ):
        failures.append(
            "a manifest-selected assistant bridge must remain active even when "
            "its capability route is inconsistent"
        )
