#!/usr/bin/env python3
"""Source-repository consistency checks for Alatyr Core.

This validates the AlatyrCore repository itself. It is not a portable framework
requirement for target projects.
"""

from __future__ import annotations

import sys
from pathlib import Path

from framework_consistency import (
    CheckContext,
    check_bridges_and_git_visibility,
    check_conformance_tools,
    check_context_source_tools,
    check_core_source_tools,
    check_evidence_and_messages,
    check_operation_source_tools,
    check_release_tools,
    check_rule_registry_contract,
    check_target_governance_surfaces,
    check_target_operation_surfaces,
    check_target_runtime_policies,
)

from check_bridge_templates import BRIDGE_FILES, REQUIRED_BRIDGE_REFS


ROOT = Path(__file__).resolve().parents[1]

BASE_RULE_REFS = (
    "ALATYR-ADAPTER-001",
    "ALATYR-APPROVAL-001",
    "ALATYR-SAFETY-001",
    "ALATYR-SAFETY-002",
    "ALATYR-DECOMPOSITION-001",
    "ALATYR-EVIDENCE-001",
    "ALATYR-OPERATION-001",
)
CONTEXT_RULE_REFS = ("ALATYR-CONTEXT-001",)
SOURCE_RULE_REFS = ("ALATYR-SOURCE-001",)
RISK_RULE_REFS = ("ALATYR-RISK-001",)
INTEGRITY_RULE_REFS = ("ALATYR-INTEGRITY-001",)
CHANGE_RULE_REFS = ("ALATYR-CHANGE-001",)
LIFECYCLE_RULE_REFS = ("ALATYR-LIFECYCLE-001",)
MODULE_RULE_REFS = ("ALATYR-MODULE-001",)

DERIVED_RULE_REFERENCE_DOCS = {
    "AGENTS.md": (
        *CONTEXT_RULE_REFS,
        "ALATYR-ADAPTER-001",
        "ALATYR-APPROVAL-001",
        "ALATYR-SAFETY-001",
        "ALATYR-SAFETY-002",
        *INTEGRITY_RULE_REFS,
        "ALATYR-DECOMPOSITION-001",
        *LIFECYCLE_RULE_REFS,
        "ALATYR-OPERATION-001",
    ),
    "README.md": (
        "ALATYR-ADAPTER-001",
        "ALATYR-APPROVAL-001",
        "ALATYR-SAFETY-001",
        "ALATYR-SAFETY-002",
        *INTEGRITY_RULE_REFS,
        "ALATYR-DECOMPOSITION-001",
        "ALATYR-EVIDENCE-001",
        "ALATYR-OPERATION-001",
    ),
    "INSTALL.md": (
        *CONTEXT_RULE_REFS,
        *SOURCE_RULE_REFS,
        *RISK_RULE_REFS,
        "ALATYR-APPROVAL-001",
        "ALATYR-SAFETY-001",
        "ALATYR-SAFETY-002",
        "ALATYR-DECOMPOSITION-001",
        "ALATYR-ADAPTER-001",
        *MODULE_RULE_REFS,
        *LIFECYCLE_RULE_REFS,
        "ALATYR-OPERATION-001",
    ),
    "AI_ASSISTANTS.md": (
        *CONTEXT_RULE_REFS,
        *BASE_RULE_REFS,
    ),
    "installer/assistant-installation.flow.md": (
        *CONTEXT_RULE_REFS,
        *SOURCE_RULE_REFS,
        *RISK_RULE_REFS,
        "ALATYR-APPROVAL-001",
        "ALATYR-SAFETY-001",
        "ALATYR-SAFETY-002",
        "ALATYR-DECOMPOSITION-001",
        "ALATYR-ADAPTER-001",
        *MODULE_RULE_REFS,
        *LIFECYCLE_RULE_REFS,
        "ALATYR-EVIDENCE-001",
        "ALATYR-OPERATION-001",
    ),
    "installer/assistant-request-template.md": (
        *CONTEXT_RULE_REFS,
        *BASE_RULE_REFS,
    ),
    "installer/installed-operation-request-template.md": (
        *CONTEXT_RULE_REFS,
        *SOURCE_RULE_REFS,
        *RISK_RULE_REFS,
        "ALATYR-APPROVAL-001",
        "ALATYR-SAFETY-001",
        "ALATYR-SAFETY-002",
        *INTEGRITY_RULE_REFS,
        *CHANGE_RULE_REFS,
        "ALATYR-DECOMPOSITION-001",
        "ALATYR-ADAPTER-001",
        *MODULE_RULE_REFS,
        "ALATYR-EVIDENCE-001",
        "ALATYR-OPERATION-001",
    ),
    "templates/target/.ai/assistant/gates/checklist.md": (
        *CONTEXT_RULE_REFS,
        *SOURCE_RULE_REFS,
        *RISK_RULE_REFS,
        "ALATYR-APPROVAL-001",
        "ALATYR-SAFETY-001",
        "ALATYR-SAFETY-002",
        *INTEGRITY_RULE_REFS,
        *CHANGE_RULE_REFS,
        "ALATYR-DECOMPOSITION-001",
        "ALATYR-ADAPTER-001",
        *MODULE_RULE_REFS,
        "ALATYR-EVIDENCE-001",
        "ALATYR-OPERATION-001",
    ),
}


def read_text(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def line_count(relpath: str) -> int:
    return len(read_text(relpath).splitlines())


def framework_files() -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "framework").glob("*.md")
        if path.is_file()
    )



def main() -> int:
    failures: list[str] = []
    fw_files = framework_files()

    source_bootstrap_docs = {
        "AGENTS.md": [
            "## Bootstrap Context",
            "## Context Expansion Profiles",
            "tools/source_context_router.json",
            "choose the smallest matching source task",
            "loading the full framework corpus by default",
        ],
        "README.md": [
            "installer/context-router.json",
            "framework/file-inventory.json",
            "Read only selected or changed canonical framework owners",
            "AI_ASSISTANTS.md",
            "tools/README.md",
        ],
        "INSTALL.md": [
            "## Source Bootstrap",
            "installer/context-router.json",
            "framework/file-inventory.json",
            "Copying an unchanged file does not require loading its prose",
        ],
        "AI_ASSISTANTS.md": [
            "installer/context-router.json",
            "framework/file-inventory.json",
            "Load only stage-required canonical owners",
        ],
        "installer/assistant-installation.flow.md": [
            "## Source Bootstrap",
            "installer/context-router.json",
            "framework/file-inventory.json",
            "Unchanged framework files do not need to be loaded",
        ],
    }
    max_bootstrap_framework_refs = 18
    for doc, required_texts in source_bootstrap_docs.items():
        text = read_text(doc)
        for required_text in required_texts:
            if required_text not in text:
                failures.append(f"{doc} missing source bootstrap text: {required_text}")
        listed_framework_files = [relpath for relpath in fw_files if relpath in text]
        if len(listed_framework_files) > max_bootstrap_framework_refs:
            failures.append(
                f"{doc} lists {len(listed_framework_files)} framework files; "
                "source entry points should route through bootstrap and task "
                "profiles instead of full-framework mandatory context"
            )
        if all(relpath in text for relpath in fw_files):
            failures.append(f"{doc} reintroduces a full framework reading list")

    for doc, rule_ids in DERIVED_RULE_REFERENCE_DOCS.items():
        text = read_text(doc)
        for rule_id in rule_ids:
            if rule_id not in text:
                failures.append(f"{doc} missing derived rule reference {rule_id}")

    for doc in [
        "INSTALL.md",
        "installer/assistant-installation.flow.md",
        "installer/assistant-request-template.md",
        "installer/installed-operation-request-template.md",
        "templates/target/AGENTS.md",
    ]:
        text = read_text(doc)
        for duplicated_policy_marker in [
            "Explicit programmer approval is required before:",
            "Require explicit programmer approval before:",
            "Ask for explicit approval before changing architecture",
        ]:
            if duplicated_policy_marker in text:
                failures.append(
                    f"{doc} repeats approval policy marker instead of routing "
                    "through ALATYR-APPROVAL-001"
                )

    framework_index = read_text("framework/README.md")
    for relpath in fw_files:
        target_path = f".ai/{relpath}"
        if target_path not in framework_index:
            failures.append(f"framework/README.md does not index {target_path}")

    target_agents = read_text("templates/target/AGENTS.md")
    for required_target_agent_ref in [
        "## Bootstrap",
        "## Authority",
        "## Work",
        "## Evidence",
        ".ai/assistant/bootstrap-index.json",
        ".ai/assistant/entry-packet.json",
        ".ai/assistant/policies/action-authorization.json",
        ".ai/assistant/task-decomposition.json",
        "Treat this file as host-preloaded context",
        "Use bootstrap-selected rule owners",
    ]:
        if required_target_agent_ref not in target_agents:
            failures.append(
                f"templates/target/AGENTS.md missing {required_target_agent_ref}"
            )
    target_framework_paths = [f".ai/{relpath}" for relpath in fw_files]
    for relpath in ["templates/target/AGENTS.md", *BRIDGE_FILES]:
        text = read_text(relpath)
        listed_target_framework_files = [
            target_path for target_path in target_framework_paths if target_path in text
        ]
        if len(listed_target_framework_files) > 10:
            failures.append(
                f"{relpath} lists {len(listed_target_framework_files)} copied "
                "framework files; target entry points and bridges should route "
                "through bootstrap context and task profiles"
            )
        if all(target_path in text for target_path in target_framework_paths):
            failures.append(
                f"{relpath} reintroduces a full copied-framework reading list"
            )

    ai_assistants = read_text("AI_ASSISTANTS.md")
    if "Read all files under `framework/`" in ai_assistants:
        failures.append(
            "AI_ASSISTANTS.md should use source bootstrap routing, not a "
            "mandatory full-framework read"
        )

    target_ai_assistants = read_text("templates/target/AI_ASSISTANTS.md")
    for required_target_ai_ref in [
        ".ai/assistant/bootstrap-index.json",
        ".ai/alatyr.yaml",
        ".ai/README.md",
        ".ai/assistant/context-router.json",
        ".ai/assistant/context-profiles.md",
        "Ensure `AGENTS.md` is loaded once",
        "preloaded by the host",
        "post-install/update message templates",
    ]:
        if required_target_ai_ref not in target_ai_assistants:
            failures.append(
                f"templates/target/AI_ASSISTANTS.md missing {required_target_ai_ref}"
            )

    required_target_templates = [
        "templates/target/CODEOWNERS",
        "templates/target/.ai/alatyr.yaml",
        "templates/target/.ai/project/source-of-truth-registry.md",
        "templates/target/.ai/project/development-evidence.json",
        "templates/target/.ai/project/documentation/README.md",
        "templates/target/.ai/project/documentation/catalog.json",
        "templates/target/.ai/project/documentation/profiles.json",
        "templates/target/.ai/project/vocabulary/README.md",
        "templates/target/.ai/project/vocabulary/catalog.json",
        "templates/target/.ai/project/vocabulary/terms.json",
        "templates/target/.ai/project/vocabulary/data-dictionary-links.json",
        "templates/target/.ai/project/testing/README.md",
        "templates/target/.ai/project/testing/test-first-policy.json",
        "templates/target/.ai/assistant/bridge-capability-matrix.md",
        "templates/target/.ai/assistant/context-router.json",
        "templates/target/.ai/assistant/context-profiles.md",
        "templates/target/.ai/assistant/context/intents/code-documentation.json",
        "templates/target/.ai/assistant/context/intents/vocabulary-request.json",
        "templates/target/.ai/assistant/context/intents/test-first-request.json",
        "templates/target/.ai/assistant/help.md",
        "templates/target/.ai/assistant/help-reference.md",
        "templates/target/.ai/assistant/operation-index.json",
        "templates/target/.ai/assistant/operation-catalog.json",
        "templates/target/.ai/assistant/assistant-capabilities.json",
        "templates/target/.ai/assistant/module-profile.md",
        "templates/target/.ai/assistant/maturity-profile.md",
        "templates/target/.ai/assistant/flows/ai-infrastructure-inventory.flow.md",
        "templates/target/.ai/assistant/flows/ai-infrastructure-recommendation.flow.md",
        "templates/target/.ai/assistant/flows/development-evidence-capture.flow.md",
        "templates/target/.ai/assistant/flows/adapter-recheck.flow.md",
        "templates/target/.ai/assistant/flows/blueprint-driven-change.flow.md",
        "templates/target/.ai/assistant/flows/documentation-sync.flow.md",
        "templates/target/.ai/assistant/flows/project-vocabulary.flow.md",
        "templates/target/.ai/assistant/flows/test-first-configuration.flow.md",
        "templates/target/.ai/assistant/flows/test-first-change.flow.md",
        "templates/target/.ai/assistant/flows/diagram-discussion.flow.md",
        "templates/target/.ai/assistant/flows/logical-integrity-review.flow.md",
        "templates/target/.ai/assistant/flows/operation-routing.flow.md",
        "templates/target/.ai/assistant/flows/adapter-health.flow.md",
        "templates/target/.ai/assistant/flows/project-blueprint-creation.flow.md",
        "templates/target/.ai/assistant/flows/skill-adaptation.flow.md",
        "templates/target/.ai/assistant/approvals/approval-template.md",
        "templates/target/.ai/assistant/approvals/approval-record-template.json",
        "templates/target/.ai/assistant/policies/ai-infrastructure-source-access.md",
        "templates/target/.ai/assistant/policies/prompt-injection.md",
        "templates/target/.ai/assistant/skills/example/SKILL.md",
        "templates/target/.ai/assistant/skills/code-documentation/SKILL.md",
        "templates/target/.ai/assistant/skills/project-vocabulary/SKILL.md",
        "templates/target/.ai/assistant/skills/test-first-development/SKILL.md",
        "templates/target/.ai/assistant/templates/adapter-output-contracts.md",
        "templates/target/.ai/assistant/templates/code-documentation-profile-review.md",
        "templates/target/.ai/assistant/templates/vocabulary-term-review.md",
        "templates/target/.ai/assistant/templates/test-first-evidence.md",
        "templates/target/.ai/assistant/templates/diagram-presentation.md",
        "templates/target/.ai/assistant/templates/ai-infrastructure-inventory.md",
        "templates/target/.ai/assistant/templates/ai-infrastructure-recommendation.md",
        "templates/target/.ai/assistant/templates/operation-request.md",
        "templates/target/.ai/assistant/templates/pre-change-preview.md",
        "templates/target/.ai/assistant/templates/migration-note.md",
        "templates/target/.ai/assistant/templates/effectiveness-report.md",
        "templates/target/.ai/assistant/templates/post-install-message.md",
        "templates/target/.ai/assistant/templates/post-update-message.md",
    ]
    for relpath in required_target_templates:
        if not (ROOT / relpath).is_file():
            failures.append(f"missing target template: {relpath}")

    placeholder_templates = [
        "templates/target/CODEOWNERS",
        "templates/target/.ai/alatyr.yaml",
        "templates/target/.ai/README.md",
        "templates/target/.ai/project/contour.md",
        "templates/target/.ai/project/source-of-truth-registry.md",
        "templates/target/.ai/project/development-evidence.json",
        "templates/target/.ai/project/documentation/README.md",
        "templates/target/.ai/project/documentation/catalog.json",
        "templates/target/.ai/project/documentation/profiles.json",
        "templates/target/.ai/project/vocabulary/README.md",
        "templates/target/.ai/project/vocabulary/catalog.json",
        "templates/target/.ai/project/vocabulary/terms.json",
        "templates/target/.ai/project/vocabulary/data-dictionary-links.json",
        "templates/target/.ai/project/testing/README.md",
        "templates/target/.ai/project/testing/test-first-policy.json",
        "templates/target/.ai/assistant/bridge-capability-matrix.md",
        "templates/target/.ai/assistant/contour.md",
        "templates/target/.ai/assistant/context-router.json",
        "templates/target/.ai/assistant/context-profiles.md",
        "templates/target/.ai/assistant/context/intents/code-documentation.json",
        "templates/target/.ai/assistant/context/intents/vocabulary-request.json",
        "templates/target/.ai/assistant/context/intents/test-first-request.json",
        "templates/target/.ai/assistant/help.md",
        "templates/target/.ai/assistant/help-reference.md",
        "templates/target/.ai/assistant/operation-catalog.json",
        "templates/target/.ai/assistant/assistant-capabilities.json",
        "templates/target/.ai/assistant/module-profile.md",
        "templates/target/.ai/assistant/maturity-profile.md",
        "templates/target/.ai/assistant/gates/checklist.md",
        "templates/target/.ai/assistant/flows/ai-infrastructure-inventory.flow.md",
        "templates/target/.ai/assistant/flows/ai-infrastructure-recommendation.flow.md",
        "templates/target/.ai/assistant/flows/development-evidence-capture.flow.md",
        "templates/target/.ai/assistant/flows/adapter-recheck.flow.md",
        "templates/target/.ai/assistant/flows/blueprint-driven-change.flow.md",
        "templates/target/.ai/assistant/flows/documentation-sync.flow.md",
        "templates/target/.ai/assistant/flows/project-vocabulary.flow.md",
        "templates/target/.ai/assistant/flows/test-first-configuration.flow.md",
        "templates/target/.ai/assistant/flows/test-first-change.flow.md",
        "templates/target/.ai/assistant/flows/diagram-discussion.flow.md",
        "templates/target/.ai/assistant/flows/logical-integrity-review.flow.md",
        "templates/target/.ai/assistant/flows/operation-routing.flow.md",
        "templates/target/.ai/assistant/flows/adapter-health.flow.md",
        "templates/target/.ai/assistant/flows/project-blueprint-creation.flow.md",
        "templates/target/.ai/assistant/flows/skill-adaptation.flow.md",
        "templates/target/.ai/assistant/approvals/approval-template.md",
        "templates/target/.ai/assistant/approvals/approval-record-template.json",
        "templates/target/.ai/assistant/policies/ai-infrastructure-source-access.md",
        "templates/target/.ai/assistant/policies/prompt-injection.md",
        "templates/target/.ai/assistant/skills/example/SKILL.md",
        "templates/target/.ai/assistant/skills/code-documentation/SKILL.md",
        "templates/target/.ai/assistant/skills/project-vocabulary/SKILL.md",
        "templates/target/.ai/assistant/skills/test-first-development/SKILL.md",
        "templates/target/.ai/assistant/templates/adapter-output-contracts.md",
        "templates/target/.ai/assistant/templates/code-documentation-profile-review.md",
        "templates/target/.ai/assistant/templates/vocabulary-term-review.md",
        "templates/target/.ai/assistant/templates/test-first-evidence.md",
        "templates/target/.ai/assistant/templates/diagram-presentation.md",
        "templates/target/.ai/assistant/templates/ai-infrastructure-inventory.md",
        "templates/target/.ai/assistant/templates/ai-infrastructure-recommendation.md",
        "templates/target/.ai/assistant/templates/installation-note.md",
        "templates/target/.ai/assistant/templates/operation-request.md",
        "templates/target/.ai/assistant/templates/pre-change-preview.md",
        "templates/target/.ai/assistant/templates/migration-note.md",
        "templates/target/.ai/assistant/templates/effectiveness-report.md",
        "templates/target/.ai/assistant/templates/post-install-message.md",
        "templates/target/.ai/assistant/templates/post-update-message.md",
    ]
    for relpath in placeholder_templates:
        if "{" not in read_text(relpath):
            failures.append(f"{relpath} should remain placeholder-based")

    context = CheckContext(
        root=ROOT,
        framework_files=tuple(fw_files),
        bridge_files=tuple(BRIDGE_FILES),
        required_bridge_refs=tuple(REQUIRED_BRIDGE_REFS),
    )
    failures.extend(check_target_operation_surfaces(context))
    failures.extend(check_target_governance_surfaces(context))
    failures.extend(check_rule_registry_contract(context))
    failures.extend(check_core_source_tools(context))
    failures.extend(check_context_source_tools(context))
    failures.extend(check_operation_source_tools(context))
    failures.extend(check_release_tools(context))
    failures.extend(check_conformance_tools(context))
    failures.extend(check_evidence_and_messages(context))
    failures.extend(check_target_runtime_policies(context))
    failures.extend(check_bridges_and_git_visibility(context))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: checked {len(fw_files)} framework docs and target templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
