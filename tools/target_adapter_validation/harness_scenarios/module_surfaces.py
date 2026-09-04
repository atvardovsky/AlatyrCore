"""Target-validator scenarios for module surfaces."""

from __future__ import annotations

from .common import (
    CAPABILITY_INDEX_KIND,
    CAPABILITY_INDEX_SCHEMA_VERSION,
    STATE_EVIDENCE_TEXT,
    SURFACE_CAPABILITY_KIND,
    capability_record_path,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    module_profile_path = target / ".ai" / "assistant" / "module-profile.md"
    module_profile_path.write_text(
        "# Module Profile\n\nModule: `diagrams`\nState: `enabled`\n",
        encoding="utf-8",
    )
    diagrams = validator(target)
    diagrams.check_discussion_diagrams(None)
    diagram_codes = {finding.code for finding in diagrams.findings}
    for required in [
        "DIAGRAM_REQUIRED_FILE_MISSING",
        "DIAGRAM_OPERATION_MISSING",
        "DIAGRAM_OPERATION_UNROUTED",
        "DIAGRAM_BRIDGE_CAPABILITY_MISSING",
    ]:
        if required not in diagram_codes:
            failures.append(f"broken diagram module missing finding {required}")

    diagram_flow = (
        target / ".ai" / "assistant" / "flows" / "diagram-discussion.flow.md"
    )
    diagram_flow.parent.mkdir(parents=True, exist_ok=True)
    diagram_flow.write_text(
        "`read-only` current assistant surface record portable ASCII view "
        "hard maximum of 100 columns stable diagram ID "
        "Classify data sensitivity\n",
        encoding="utf-8",
    )
    diagram_presentation = (
        target / ".ai" / "assistant" / "templates" / "diagram-presentation.md"
    )
    diagram_presentation.parent.mkdir(parents=True, exist_ok=True)
    diagram_presentation.write_text(
        "Presentation mode:\nPortable ASCII presentation:\n"
        "ASCII readability check:\nDiagram ID:\n"
        "Data classification:\nExternal renderer or network action:\n"
        "is not project source of truth\n",
        encoding="utf-8",
    )
    ascii_presentation = (
        target / ".ai" / "assistant" / "templates" / "ascii-diagram.md"
    )
    ascii_presentation.write_text(
        "Hard maximum width: `100`\n"
        "printable 7-bit ASCII plus line feeds\n"
        "Longest line at most 100 columns\n",
        encoding="utf-8",
    )
    matrix_path = target / ".ai" / "assistant" / "bridge-capability-matrix.md"
    matrix_path.write_text(
        "### Assistant Surface: `generic`\n\n"
        "Diagram capability record: "
        "`.ai/assistant/assistant-capabilities/generic.json`\n",
        encoding="utf-8",
    )
    write_json(
        target / ".ai" / "assistant" / "assistant-capabilities.json",
        {
            "schema_version": CAPABILITY_INDEX_SCHEMA_VERSION,
            "capability_kind": CAPABILITY_INDEX_KIND,
            "state_evidence": {
                "state_model": STATE_EVIDENCE_TEXT,
                "selected_surface": "generic",
                "selected_surface_evidence": "fixture",
                "capability_records_are_authoritative": True,
                "unknown_means_not_verified": True,
                "stale_or_expired_evidence_requires_recheck": True,
            },
            "surfaces": {
                "generic": capability_record_path("generic")
            },
        },
    )
    write_json(
        target / ".ai" / "assistant" / "assistant-capabilities" / "generic.json",
        {
            "schema_version": 1,
            "capability_kind": SURFACE_CAPABILITY_KIND,
            "assistant_surface": "generic",
            "diagram_discussion": {
                "route": "maybe",
                "native_inline_syntaxes": ["unknown"],
                "artifact_presentation": "maybe",
                "readable_fallback": "text",
                "verified_at": "unknown",
                "expires_at": "unknown",
                "review_triggers": [],
                "client_version": "unknown",
                "evidence": "manual review",
            },
        },
    )
    capability_validator = validator(target)
    capability_validator.check_discussion_diagrams(None)
    capability_codes = {
        finding.code for finding in capability_validator.findings
    }
    for required in [
        "DIAGRAM_CAPABILITY_ROUTE",
        "DIAGRAM_CAPABILITY_ARTIFACT",
        "DIAGRAM_CAPABILITY_FRESHNESS",
        "DIAGRAM_CAPABILITY_CLIENT_VERSION",
        "DIAGRAM_CAPABILITY_ASCII_FALLBACK",
    ]:
        if required not in capability_codes:
            failures.append(
                f"invalid diagram capability missing finding {required}"
            )

    module_profile_path.write_text(
        "# Module Profile\n\n"
        "Module: `architecture-knowledge`\nState: `enabled`\n",
        encoding="utf-8",
    )
    architecture = validator(target)
    architecture.check_architecture_knowledge(None)
    if "ARCHITECTURE_REQUIRED_FILE_MISSING" not in {
        finding.code for finding in architecture.findings
    }:
        failures.append(
            "enabled architecture knowledge must report missing contracts"
        )

    module_profile_path.write_text(
        "# Module Profile\n\n"
        "Module: `code-documentation`\nState: `enabled`\n",
        encoding="utf-8",
    )
    code_documentation = validator(target)
    code_documentation.check_code_documentation(None)
    if "CODEDOC_REQUIRED_FILE_MISSING" not in {
        finding.code for finding in code_documentation.findings
    }:
        failures.append(
            "enabled code documentation must report missing contracts"
        )

    module_profile_path.write_text(
        "# Module Profile\n\n"
        "Module: `project-vocabulary`\nState: `enabled`\n",
        encoding="utf-8",
    )
    project_vocabulary = validator(target)
    project_vocabulary.check_project_vocabulary(None)
    if "VOCABULARY_REQUIRED_FILE_MISSING" not in {
        finding.code for finding in project_vocabulary.findings
    }:
        failures.append(
            "enabled project vocabulary must report missing contracts"
        )

    module_profile_path.write_text(
        "# Module Profile\n\n"
        "Module: `test-first-development`\nState: `enabled`\n",
        encoding="utf-8",
    )
    test_first = validator(target)
    test_first.check_test_first_development(None)
    if "TDD_REQUIRED_FILE_MISSING" not in {
        finding.code for finding in test_first.findings
    }:
        failures.append(
            "enabled test-first development must report missing contracts"
        )

    test_first_paths = [
        ".ai/project/testing/README.md",
        ".ai/project/testing/test-first-policy.json",
        ".ai/assistant/context/intents/test-first-request.json",
        ".ai/assistant/flows/test-first-configuration.flow.md",
        ".ai/assistant/flows/test-first-change.flow.md",
        ".ai/assistant/gates/test-first-development.md",
        ".ai/assistant/templates/test-first-evidence.md",
        ".ai/assistant/skills/test-first-development/SKILL.md",
        ".ai/framework/test-first-development.md",
    ]
    for relpath in test_first_paths:
        path = target / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test-first contract fixture\n", encoding="utf-8")
    write_json(
        target / ".ai/project/testing/test-first-policy.json",
        {
            "schema_version": 1,
            "policy_kind": "target-test-first-development-policy",
            "project": "fixture",
            "state": "enabled",
            "owner": "test-owner",
            "decision_authority": "test-authority",
            "last_reviewed": "2026-08-12",
            "evidence_revision": "fixture-revision",
            "suggestion": {
                "mode": "advisory",
                "minimum_result": "recommended",
                "max_per_task": 1,
                "suppress_after_decline": True,
                "cost_statement_required": True,
            },
            "available_modes": ["regression-first"],
            "activation_triggers": [
                {
                    "id": "defect",
                    "state": "recommended",
                    "changed_fact_classes": ["behavior"],
                    "conditions": ["reproducible defect"],
                    "mode": "regression-first",
                    "test_level_ids": ["missing-level"],
                    "exceptions": ["missing-exception"],
                }
            ],
            "test_levels": [
                {
                    "id": "unit",
                    "purpose": "observable behavior",
                    "paths": ["tests"],
                    "command_ids": ["missing-command"],
                    "feedback_time": "fast",
                    "fixtures_and_helpers": ["fixture builder"],
                }
            ],
            "commands": [
                {
                    "id": "unit-test",
                    "command": "fixture test command",
                    "scope": "unit",
                    "live_external_actions": "forbidden",
                }
            ],
            "isolation": {
                "clock": "fake",
                "randomness": "seeded",
                "database": "isolated",
                "queue": "fake",
                "filesystem": "temporary",
                "network": "forbidden",
                "secrets": "not available",
            },
            "exceptions": [],
            "evidence_requirements": ["RED and GREEN"],
            "known_gaps": [],
        },
    )
    bad_references = validator(target)
    bad_references.check_test_first_development(None)
    bad_reference_codes = {
        finding.code for finding in bad_references.findings
    }
    for required in [
        "TDD_COMMAND_REFERENCE",
        "TDD_TEST_LEVEL_REFERENCE",
        "TDD_EXCEPTION_REFERENCE",
    ]:
        if required not in bad_reference_codes:
            failures.append(
                f"test-first policy must reject invalid references with {required}"
            )
