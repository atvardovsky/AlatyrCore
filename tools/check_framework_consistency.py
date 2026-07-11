#!/usr/bin/env python3
"""Source-repository consistency checks for Alatyr Core.

This validates the AlatyrCore repository itself. It is not a portable framework
requirement for target projects.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from check_bridge_templates import BRIDGE_FILES, REQUIRED_BRIDGE_REFS


ROOT = Path(__file__).resolve().parents[1]


def read_text(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def line_count(relpath: str) -> int:
    return len(read_text(relpath).splitlines())


def framework_files() -> list[str]:
    return sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "framework").glob("*.md")
        if path.is_file()
    )


def git_check_ignore_no_index(relpath: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", relpath],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    failures: list[str] = []
    fw_files = framework_files()

    source_bootstrap_docs = {
        "AGENTS.md": [
            "## Bootstrap Context",
            "## Context Expansion Profiles",
            "Do not load every framework file by",
            "framework/context-router.md",
            "framework/context-profiles.md",
            "framework/rule-ownership.md",
            "framework/rule-registry.md",
            "docs/framework-maintenance.md",
        ],
        "README.md": [
            "Read the source bootstrap",
            "framework/context-profiles.md",
            "framework/context-router.md",
            "framework/project-adapter-contract.md",
            "framework/rule-registry.json",
            "Read each framework file before copying or adapting",
        ],
        "INSTALL.md": [
            "## Source Bootstrap",
            "framework/context-profiles.md",
            "framework/context-router.md",
            "framework/project-adapter-contract.md",
            "framework/rule-registry.json",
            "not as a default bootstrap",
        ],
        "AI_ASSISTANTS.md": [
            "framework/context-profiles.md",
            "framework/context-router.md",
            "framework/project-adapter-contract.md",
            "framework/rule-registry.json",
            "full-core installs read the full framework corpus",
        ],
        "installer/assistant-installation.flow.md": [
            "## Source Bootstrap",
            "framework/context-profiles.md",
            "framework/context-router.md",
            "framework/project-adapter-contract.md",
            "framework/rule-registry.json",
            "not as a default bootstrap",
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

    derived_rule_reference_docs = {
        "AGENTS.md": [
            "ALATYR-CONTEXT-001",
            "ALATYR-ADAPTER-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-INTEGRITY-001",
            "ALATYR-LIFECYCLE-001",
        ],
        "README.md": [
            "ALATYR-ADAPTER-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-INTEGRITY-001",
            "ALATYR-EVIDENCE-001",
        ],
        "INSTALL.md": [
            "ALATYR-CONTEXT-001",
            "ALATYR-SOURCE-001",
            "ALATYR-RISK-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-ADAPTER-001",
            "ALATYR-MODULE-001",
            "ALATYR-LIFECYCLE-001",
        ],
        "AI_ASSISTANTS.md": [
            "ALATYR-CONTEXT-001",
            "ALATYR-ADAPTER-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-EVIDENCE-001",
        ],
        "installer/assistant-installation.flow.md": [
            "ALATYR-CONTEXT-001",
            "ALATYR-SOURCE-001",
            "ALATYR-RISK-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-ADAPTER-001",
            "ALATYR-MODULE-001",
            "ALATYR-LIFECYCLE-001",
            "ALATYR-EVIDENCE-001",
        ],
        "installer/assistant-request-template.md": [
            "ALATYR-CONTEXT-001",
            "ALATYR-ADAPTER-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-EVIDENCE-001",
        ],
        "installer/installed-operation-request-template.md": [
            "ALATYR-CONTEXT-001",
            "ALATYR-SOURCE-001",
            "ALATYR-RISK-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-INTEGRITY-001",
            "ALATYR-CHANGE-001",
            "ALATYR-ADAPTER-001",
            "ALATYR-MODULE-001",
            "ALATYR-EVIDENCE-001",
        ],
        "templates/target/AGENTS.md": [
            "ALATYR-CONTEXT-001",
            "ALATYR-SOURCE-001",
            "ALATYR-RISK-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-INTEGRITY-001",
            "ALATYR-CHANGE-001",
            "ALATYR-ADAPTER-001",
            "ALATYR-MODULE-001",
            "ALATYR-EVIDENCE-001",
        ],
        "templates/target/.ai/assistant/gates/checklist.md": [
            "ALATYR-CONTEXT-001",
            "ALATYR-SOURCE-001",
            "ALATYR-RISK-001",
            "ALATYR-APPROVAL-001",
            "ALATYR-SAFETY-001",
            "ALATYR-SAFETY-002",
            "ALATYR-INTEGRITY-001",
            "ALATYR-CHANGE-001",
            "ALATYR-ADAPTER-001",
            "ALATYR-MODULE-001",
            "ALATYR-EVIDENCE-001",
        ],
    }
    for doc, rule_ids in derived_rule_reference_docs.items():
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
        "## Bootstrap Context",
        "## Session Bootstrap",
        ".ai/alatyr.yaml",
        ".ai/assistant/context-router.json",
        ".ai/assistant/context-profiles.md",
        ".ai/assistant/module-profile.md",
        ".ai/assistant/templates/installation-note.md",
        ".ai/assistant/templates/post-install-message.md",
        ".ai/assistant/templates/post-update-message.md",
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
        ".ai/alatyr.yaml",
        ".ai/assistant/context-router.json",
        ".ai/assistant/context-profiles.md",
        ".ai/assistant/module-profile.md",
        ".ai/assistant/templates/installation-note.md",
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
        "templates/target/.ai/assistant/bridge-capability-matrix.md",
        "templates/target/.ai/assistant/context-router.json",
        "templates/target/.ai/assistant/context-profiles.md",
        "templates/target/.ai/assistant/help.md",
        "templates/target/.ai/assistant/help-reference.md",
        "templates/target/.ai/assistant/module-profile.md",
        "templates/target/.ai/assistant/maturity-profile.md",
        "templates/target/.ai/assistant/flows/ai-infrastructure-inventory.flow.md",
        "templates/target/.ai/assistant/flows/adapter-recheck.flow.md",
        "templates/target/.ai/assistant/flows/blueprint-driven-change.flow.md",
        "templates/target/.ai/assistant/flows/documentation-sync.flow.md",
        "templates/target/.ai/assistant/flows/logical-integrity-review.flow.md",
        "templates/target/.ai/assistant/flows/operation-routing.flow.md",
        "templates/target/.ai/assistant/flows/project-blueprint-creation.flow.md",
        "templates/target/.ai/assistant/flows/skill-adaptation.flow.md",
        "templates/target/.ai/assistant/approvals/approval-template.md",
        "templates/target/.ai/assistant/policies/ai-infrastructure-source-access.md",
        "templates/target/.ai/assistant/policies/prompt-injection.md",
        "templates/target/.ai/assistant/skills/example/SKILL.md",
        "templates/target/.ai/assistant/templates/adapter-output-contracts.md",
        "templates/target/.ai/assistant/templates/ai-infrastructure-inventory.md",
        "templates/target/.ai/assistant/templates/operation-request.md",
        "templates/target/.ai/assistant/templates/migration-note.md",
        "templates/target/.ai/assistant/templates/effectiveness-report.md",
        "templates/target/.ai/assistant/templates/post-install-message.md",
        "templates/target/.ai/assistant/templates/post-update-message.md",
    ]
    for relpath in required_target_templates:
        if not (ROOT / relpath).is_file():
            failures.append(f"missing target template: {relpath}")

    placeholder_templates = [
        "templates/target/AGENTS.md",
        "templates/target/CODEOWNERS",
        "templates/target/.ai/alatyr.yaml",
        "templates/target/.ai/README.md",
        "templates/target/.ai/project/contour.md",
        "templates/target/.ai/project/source-of-truth-registry.md",
        "templates/target/.ai/assistant/bridge-capability-matrix.md",
        "templates/target/.ai/assistant/contour.md",
        "templates/target/.ai/assistant/context-router.json",
        "templates/target/.ai/assistant/context-profiles.md",
        "templates/target/.ai/assistant/help.md",
        "templates/target/.ai/assistant/help-reference.md",
        "templates/target/.ai/assistant/module-profile.md",
        "templates/target/.ai/assistant/maturity-profile.md",
        "templates/target/.ai/assistant/gates/checklist.md",
        "templates/target/.ai/assistant/flows/ai-infrastructure-inventory.flow.md",
        "templates/target/.ai/assistant/flows/adapter-recheck.flow.md",
        "templates/target/.ai/assistant/flows/blueprint-driven-change.flow.md",
        "templates/target/.ai/assistant/flows/documentation-sync.flow.md",
        "templates/target/.ai/assistant/flows/logical-integrity-review.flow.md",
        "templates/target/.ai/assistant/flows/operation-routing.flow.md",
        "templates/target/.ai/assistant/flows/project-blueprint-creation.flow.md",
        "templates/target/.ai/assistant/flows/skill-adaptation.flow.md",
        "templates/target/.ai/assistant/approvals/approval-template.md",
        "templates/target/.ai/assistant/policies/ai-infrastructure-source-access.md",
        "templates/target/.ai/assistant/policies/prompt-injection.md",
        "templates/target/.ai/assistant/skills/example/SKILL.md",
        "templates/target/.ai/assistant/templates/adapter-output-contracts.md",
        "templates/target/.ai/assistant/templates/ai-infrastructure-inventory.md",
        "templates/target/.ai/assistant/templates/installation-note.md",
        "templates/target/.ai/assistant/templates/operation-request.md",
        "templates/target/.ai/assistant/templates/migration-note.md",
        "templates/target/.ai/assistant/templates/effectiveness-report.md",
        "templates/target/.ai/assistant/templates/post-install-message.md",
        "templates/target/.ai/assistant/templates/post-update-message.md",
    ]
    for relpath in placeholder_templates:
        if "{" not in read_text(relpath):
            failures.append(f"{relpath} should remain placeholder-based")

    help_template = read_text("templates/target/.ai/assistant/help.md")
    if "| Operation |" in help_template:
        failures.append(
            "templates/target/.ai/assistant/help.md should use operation blocks, not a table"
        )
    if line_count("templates/target/.ai/assistant/help.md") > 150:
        failures.append("templates/target/.ai/assistant/help.md should stay short")
    for required_help_text in [
        "Operation: `help`",
        "Full operation reference: `.ai/assistant/help-reference.md`",
        "These aliases are chat/request shortcuts, not shell commands.",
        "Default routing:",
    ]:
        if required_help_text not in help_template:
            failures.append(
                f"templates/target/.ai/assistant/help.md missing {required_help_text}"
            )

    help_reference = read_text("templates/target/.ai/assistant/help-reference.md")
    for required_help_reference_text in [
        "## Operation Type Aliases",
        "Allowed actions guide:",
        "alatyr-ai-inventory",
        "alatyr-adaptation {AI_INFRASTRUCTURE_SOURCE}",
        "alatyr-add-ai {AI_INFRASTRUCTURE_SOURCE}",
    ]:
        if required_help_reference_text not in help_reference:
            failures.append(
                "templates/target/.ai/assistant/help-reference.md missing "
                f"{required_help_reference_text}"
            )

    target_context_profiles = read_text(
        "templates/target/.ai/assistant/context-profiles.md"
    )
    for profile_name in [
        "docs-local",
        "code-local",
        "business-change",
        "architecture-change",
        "data-change",
        "security-sensitive",
        "ai-infrastructure",
        "framework-upgrade",
    ]:
        if f"Profile: `{profile_name}`" not in target_context_profiles:
            failures.append(
                "templates/target/.ai/assistant/context-profiles.md missing "
                f"profile {profile_name}"
            )
    for relpath in fw_files:
        target_path = f".ai/{relpath}"
        if target_path not in target_context_profiles:
            failures.append(
                "templates/target/.ai/assistant/context-profiles.md does not "
                f"route {target_path}"
            )
    if ".ai/assistant/context-router.json" not in target_context_profiles:
        failures.append(
            "templates/target/.ai/assistant/context-profiles.md missing "
            ".ai/assistant/context-router.json"
        )
    if ".ai/framework/rule-registry.json" not in target_context_profiles:
        failures.append(
            "templates/target/.ai/assistant/context-profiles.md missing "
            ".ai/framework/rule-registry.json"
        )

    module_profile = read_text("templates/target/.ai/assistant/module-profile.md")
    for required_module_text in [
        "## Required Core Profile",
        "Core item: `contours`",
        "Core item: `manifest-and-versioning`",
        "Core item: `adapter-ownership`",
        "Core item: `context-profiles`",
        "Core item: `source-of-truth-registry`",
        "Core item: `risk-approval-integrity`",
        "Core item: `validation-and-final-evidence`",
        "Module: `blueprint-change`",
        "Module: `diagrams`",
        "Module: `ai-infrastructure`",
        "Module: `multi-assistant-bridges`",
        "Module: `installed-operations`",
        "Module: `durable-approvals`",
        "Module: `migration-diff`",
        "Module: `effectiveness-metrics`",
        "Module: `scaffolding`",
    ]:
        if required_module_text not in module_profile:
            failures.append(
                "templates/target/.ai/assistant/module-profile.md missing "
                f"{required_module_text}"
            )

    manifest = read_text("templates/target/.ai/alatyr.yaml")
    for required_manifest_text in [
        "schema_version:",
        "framework:",
        "version:",
        "template_version:",
        "rule_registry:",
        "installation:",
        "owner:",
        "review_cadence:",
        "codeowners:",
        "supported_assistants:",
        "contours:",
        "source_of_truth:",
        "context_router:",
        "module_profile:",
        "modules:",
        "core_profile:",
        "enabled:",
        "deferred:",
        "blocked:",
        "validation:",
        "operations:",
        "output_contracts:",
        "ai_infrastructure_inventory:",
        "migration_note:",
        "effectiveness_report:",
        "maturity:",
        "bridges:",
        "approvals:",
        "policies:",
        "known_gaps:",
        "local_deviations:",
    ]:
        if required_manifest_text not in manifest:
            failures.append(
                f"templates/target/.ai/alatyr.yaml missing {required_manifest_text}"
            )

    source_registry = read_text("templates/target/.ai/project/source-of-truth-registry.md")
    for required_registry_text in [
        "Fact type:",
        "Canonical owner:",
        "Derived surfaces:",
        "Sync direction:",
        "Validation or manual review:",
        "Conflict resolver:",
        "Approval trigger:",
        "Final evidence:",
    ]:
        if required_registry_text not in source_registry:
            failures.append(
                "templates/target/.ai/project/source-of-truth-registry.md "
                f"missing {required_registry_text}"
            )
    for required_fact_type in [
        "### Fact Type: `product behavior`",
        "### Fact Type: `business rule`",
        "### Fact Type: `architecture decision`",
        "### Fact Type: `data model`",
        "### Fact Type: `validation command`",
        "### Fact Type: `security policy`",
        "### Fact Type: `assistant operation`",
        "### Fact Type: `AI infrastructure item`",
    ]:
        if required_fact_type not in source_registry:
            failures.append(
                "templates/target/.ai/project/source-of-truth-registry.md "
                f"missing {required_fact_type}"
            )

    maturity_profile = read_text(
        "templates/target/.ai/assistant/maturity-profile.md"
    )
    for required_maturity_text in [
        "Task area: `documentation`",
        "Task area: `code-changes`",
        "Task area: `architecture`",
        "Task area: `data`",
        "Task area: `security`",
        "Task area: `ai-infrastructure`",
        "Task area: `framework-upgrade`",
        "Supported work:",
        "Required context:",
        "## Blocking Criteria",
        "Validation or manual review:",
        "Approval needs:",
        "Residual risks:",
        "Final evidence:",
    ]:
        if required_maturity_text not in maturity_profile:
            failures.append(
                "templates/target/.ai/assistant/maturity-profile.md missing "
                f"{required_maturity_text}"
            )

    bridge_matrix = read_text(
        "templates/target/.ai/assistant/bridge-capability-matrix.md"
    )
    for required_bridge_matrix_text in [
        "Assistant:",
        "Surface id:",
        "Bridge paths:",
        "Auto-load behavior:",
        "Instruction priority:",
        "Supported rule/prompt/skill surfaces:",
        "Tool permission model:",
        "Routes operation help:",
        "Routes `alatyr-ai-inventory`:",
        "Routes `alatyr-adaptation`:",
        "Routes `alatyr-add-ai`:",
        "Known limitations:",
        "Conformance check:",
    ]:
        if required_bridge_matrix_text not in bridge_matrix:
            failures.append(
                "templates/target/.ai/assistant/bridge-capability-matrix.md "
                f"missing {required_bridge_matrix_text}"
            )
    for required_bridge_surface in [
        "### Assistant Surface: `generic`",
        "### Assistant Surface: `agents`",
        "### Assistant Surface: `codex`",
        "### Assistant Surface: `claude`",
        "### Assistant Surface: `gemini`",
        "### Assistant Surface: `github-copilot`",
        "### Assistant Surface: `cursor`",
        "### Assistant Surface: `devin-cascade`",
        "### Assistant Surface: `windsurf`",
    ]:
        if required_bridge_surface not in bridge_matrix:
            failures.append(
                "templates/target/.ai/assistant/bridge-capability-matrix.md "
                f"missing {required_bridge_surface}"
            )

    migration_note = read_text(
        "templates/target/.ai/assistant/templates/migration-note.md"
    )
    for required_migration_text in [
        "From framework version:",
        "To framework version:",
        "From adapter schema version:",
        "To adapter schema version:",
        "## Changed Framework Rules",
        "## Required Target Actions",
        "## Optional Target Actions",
        ".ai/assistant/module-profile.md",
        "Approval needed:",
        "Migration result:",
    ]:
        if required_migration_text not in migration_note:
            failures.append(
                "templates/target/.ai/assistant/templates/migration-note.md "
                f"missing {required_migration_text}"
            )

    effectiveness_report = read_text(
        "templates/target/.ai/assistant/templates/effectiveness-report.md"
    )
    for required_effectiveness_text in [
        "Task:",
        "Task profile:",
        "Adapter mode:",
        "Context files loaded:",
        "Clarifications:",
        "Approvals requested:",
        "Validation:",
        "Missed companion updates:",
        "Rework count:",
        "Residual risks:",
        "Outcome:",
    ]:
        if required_effectiveness_text not in effectiveness_report:
            failures.append(
                "templates/target/.ai/assistant/templates/effectiveness-report.md "
                f"missing {required_effectiveness_text}"
            )

    rule_registry = read_text("framework/rule-registry.md")
    required_rule_ids = [
        "ALATYR-CONTEXT-001",
        "ALATYR-SOURCE-001",
        "ALATYR-RISK-001",
        "ALATYR-APPROVAL-001",
        "ALATYR-SAFETY-001",
        "ALATYR-SAFETY-002",
        "ALATYR-INTEGRITY-001",
        "ALATYR-CHANGE-001",
        "ALATYR-ADAPTER-001",
        "ALATYR-MODULE-001",
        "ALATYR-BRIDGE-001",
        "ALATYR-LIFECYCLE-001",
        "ALATYR-EVIDENCE-001",
    ]
    for required_rule_id in required_rule_ids:
        if required_rule_id not in rule_registry:
            failures.append(f"framework/rule-registry.md missing {required_rule_id}")
    if "framework/rule-registry.json" not in rule_registry:
        failures.append("framework/rule-registry.md must point to rule-registry.json")
    if "framework/rule-ownership.md" not in rule_registry:
        failures.append("framework/rule-registry.md must point to rule-ownership.md")

    rule_ownership = read_text("framework/rule-ownership.md")
    for required_ownership_text in [
        "Category: `CONTEXT`",
        "Category: `SOURCE`",
        "Category: `RISK`",
        "Category: `APPROVAL`",
        "Category: `SAFETY`",
        "Category: `INTEGRITY`",
        "Category: `CHANGE`",
        "Category: `ADAPTER`",
        "Category: `MODULE`",
        "Category: `BRIDGE`",
        "Category: `LIFECYCLE`",
        "Category: `EVIDENCE`",
        "framework/rule-registry.json",
        "Derived documents should reference the owner",
    ]:
        if required_ownership_text not in rule_ownership:
            failures.append(
                f"framework/rule-ownership.md missing {required_ownership_text}"
            )

    rule_registry_json = ROOT / "framework" / "rule-registry.json"
    if not rule_registry_json.is_file():
        failures.append("missing framework/rule-registry.json")
    else:
        try:
            rule_data = json.loads(rule_registry_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"framework/rule-registry.json is invalid JSON: {exc}")
            rule_data = {}

        if rule_data.get("schema_version") != 1:
            failures.append("framework/rule-registry.json schema_version must be 1")
        rules = rule_data.get("rules")
        if not isinstance(rules, list) or not rules:
            failures.append("framework/rule-registry.json must contain a rules list")
            rules = []
        seen_rule_ids: set[str] = set()
        rule_categories: dict[str, str] = {}
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                failures.append(
                    f"framework/rule-registry.json rule {index} must be an object"
                )
                continue
            for required_key in [
                "id",
                "category",
                "canonical_source",
                "summary",
                "applies_to",
                "enforcement",
            ]:
                if required_key not in rule:
                    failures.append(
                        "framework/rule-registry.json rule "
                        f"{rule.get('id', index)} missing {required_key}"
                    )
            rule_id = rule.get("id")
            if not isinstance(rule_id, str) or not rule_id:
                failures.append(
                    f"framework/rule-registry.json rule {index} missing string id"
                )
            elif rule_id in seen_rule_ids:
                failures.append(f"duplicate rule id in rule-registry.json: {rule_id}")
            else:
                seen_rule_ids.add(rule_id)
                category = rule.get("category")
                if isinstance(category, str):
                    rule_categories[rule_id] = category
                if rule_id not in rule_registry:
                    failures.append(
                        f"framework/rule-registry.md missing JSON rule {rule_id}"
                    )
            canonical_source = rule.get("canonical_source")
            if isinstance(canonical_source, str) and canonical_source:
                if not (ROOT / canonical_source).is_file():
                    failures.append(
                        "framework/rule-registry.json canonical_source does not "
                        f"exist: {canonical_source}"
                    )
            else:
                failures.append(
                    f"framework/rule-registry.json rule {rule_id or index} "
                    "missing canonical_source"
                )
            applies_to = rule.get("applies_to")
            if not isinstance(applies_to, list) or not applies_to:
                failures.append(
                    f"framework/rule-registry.json rule {rule_id or index} "
                    "must have non-empty applies_to"
                )
        for missing_rule_id in sorted(set(required_rule_ids) - seen_rule_ids):
            failures.append(
                f"framework/rule-registry.json missing required rule {missing_rule_id}"
            )
        category_owners = rule_data.get("category_owners")
        if not isinstance(category_owners, list) or not category_owners:
            failures.append(
                "framework/rule-registry.json must contain category_owners"
            )
            category_owners = []
        seen_owner_categories: set[str] = set()
        seen_owner_rule_ids: set[str] = set()
        for index, owner in enumerate(category_owners):
            if not isinstance(owner, dict):
                failures.append(
                    f"framework/rule-registry.json category_owners {index} "
                    "must be an object"
                )
                continue
            category = owner.get("category")
            owner_path = owner.get("owner")
            owner_rule_ids = owner.get("rule_ids")
            derived_surfaces = owner.get("derived_surfaces")
            if not isinstance(category, str) or not category:
                failures.append(
                    "framework/rule-registry.json category owner missing category"
                )
                continue
            if category in seen_owner_categories:
                failures.append(f"duplicate category owner: {category}")
            seen_owner_categories.add(category)
            if not isinstance(owner_path, str) or not owner_path:
                failures.append(f"{category} category owner missing owner path")
            elif not (ROOT / owner_path).is_file():
                failures.append(f"{category} category owner path does not exist")
            if not isinstance(owner_rule_ids, list) or not owner_rule_ids:
                failures.append(f"{category} category owner missing rule_ids")
                owner_rule_ids = []
            for owner_rule_id in owner_rule_ids:
                if owner_rule_id not in rule_categories:
                    failures.append(
                        f"{category} category owner references unknown rule "
                        f"{owner_rule_id}"
                    )
                    continue
                if rule_categories[owner_rule_id] != category:
                    failures.append(
                        f"{category} category owner references {owner_rule_id}, "
                        f"but registry category is {rule_categories[owner_rule_id]}"
                    )
                if owner_rule_id in seen_owner_rule_ids:
                    failures.append(f"rule id has multiple category owners: {owner_rule_id}")
                seen_owner_rule_ids.add(owner_rule_id)
            if not isinstance(derived_surfaces, list) or not derived_surfaces:
                failures.append(f"{category} category owner missing derived_surfaces")
        for missing_category in sorted(set(rule_categories.values()) - seen_owner_categories):
            failures.append(
                f"framework/rule-registry.json category_owners missing {missing_category}"
            )
        for missing_owner_rule_id in sorted(set(rule_categories) - seen_owner_rule_ids):
            failures.append(
                "framework/rule-registry.json category_owners missing rule "
                f"{missing_owner_rule_id}"
            )

    scaffolder = ROOT / "tools" / "scaffold_target_structure.py"
    if not scaffolder.is_file():
        failures.append("missing tools/scaffold_target_structure.py")
    else:
        scaffolder_text = read_text("tools/scaffold_target_structure.py")
        for required_scaffolder_text in [
            "not the Alatyr installation mechanism",
            "Linux, macOS, and Windows",
            ".json",
            "--write",
            "--overwrite-existing",
            "DRY-RUN",
        ]:
            if required_scaffolder_text not in scaffolder_text:
                failures.append(
                    "tools/scaffold_target_structure.py missing "
                    f"{required_scaffolder_text}"
                )

    for wrapper in [
        "tools/scaffold_target_structure.cmd",
        "tools/scaffold_target_structure.ps1",
    ]:
        if not (ROOT / wrapper).is_file():
            failures.append(f"missing {wrapper}")
        elif "scaffold_target_structure.py" not in read_text(wrapper):
            failures.append(f"{wrapper} must delegate to scaffold_target_structure.py")

    tools_readme = "tools/README.md"
    if not (ROOT / tools_readme).is_file():
        failures.append("missing tools/README.md")
    else:
        tools_readme_text = read_text(tools_readme)
        for required_tools_readme_text in [
            "Linux or macOS:",
            "Windows PowerShell:",
            "Windows Command Prompt:",
            "not portable framework requirements",
            "check_approval_template.py",
            "check_bridge_capability_matrix.py",
            "check_framework_metadata.py",
            "check_ai_infrastructure_inventory.py",
            "check_context_router.py",
            "check_manifest_contract.py",
            "check_markdown_links.py",
            "check_maturity_profile.py",
            "check_module_profile.py",
            "check_migration_diff_report.py",
            "check_operation_contracts.py",
            "check_operation_help.py",
            "check_output_contracts.py",
            "check_release_migration_template.py",
            "check_rule_ownership.py",
            "check_source_of_truth_registry.py",
            "check_versioning.py",
            "report_migration_diff.py",
            "check_conformance_fixtures.py",
            "materialize_conformance_fixtures.py",
            "prepare_conformance_run.py",
            "check_conformance_reports.py",
            "summarize_conformance_reports.py",
            "--actual-dir",
            "run_conformance_scaffold.py",
            "--write-golden-snapshots",
            "check_bridge_templates.py",
            "render_bridge_templates.py",
            "bridge_template_manifest.json",
            "summarize_effectiveness_reports.py",
        ]:
            if required_tools_readme_text not in tools_readme_text:
                failures.append(
                    f"tools/README.md missing {required_tools_readme_text}"
                )

    framework_metadata_tool = ROOT / "tools" / "check_framework_metadata.py"
    if not framework_metadata_tool.is_file():
        failures.append("missing tools/check_framework_metadata.py")
    else:
        framework_metadata_text = read_text("tools/check_framework_metadata.py")
        for required_framework_metadata_text in [
            "framework metadata",
            "portable",
            "alatyr_doc",
            "owns_rules",
            "depends_on",
            "applies_to",
            "OK: checked",
        ]:
            if required_framework_metadata_text not in framework_metadata_text:
                failures.append(
                    "tools/check_framework_metadata.py missing "
                    f"{required_framework_metadata_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_framework_metadata.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_framework_metadata.py")

    approval_template_tool = ROOT / "tools" / "check_approval_template.py"
    if not approval_template_tool.is_file():
        failures.append("missing tools/check_approval_template.py")
    else:
        approval_template_tool_text = read_text("tools/check_approval_template.py")
        for required_approval_template_tool_text in [
            "approval-record template",
            "portable",
            "REQUIRED_FIELDS",
            "REQUIRED_LIST_FIELDS",
            "REQUIRED_CODE_BLOCK_FIELDS",
            "OK: checked",
        ]:
            if required_approval_template_tool_text not in approval_template_tool_text:
                failures.append(
                    "tools/check_approval_template.py missing "
                    f"{required_approval_template_tool_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_approval_template.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_approval_template.py")

    bridge_capability_tool = ROOT / "tools" / "check_bridge_capability_matrix.py"
    if not bridge_capability_tool.is_file():
        failures.append("missing tools/check_bridge_capability_matrix.py")
    else:
        bridge_capability_tool_text = read_text(
            "tools/check_bridge_capability_matrix.py"
        )
        for required_bridge_capability_tool_text in [
            "bridge capability matrix template",
            "portable",
            "REQUIRED_FIELDS",
            "PLACEHOLDER_FIELDS",
            "assistant-surfaces.json",
            "OK: checked",
        ]:
            if required_bridge_capability_tool_text not in bridge_capability_tool_text:
                failures.append(
                    "tools/check_bridge_capability_matrix.py missing "
                    f"{required_bridge_capability_tool_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
        "docs/assistant-compatibility.md",
    ]:
        if "check_bridge_capability_matrix.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_bridge_capability_matrix.py")

    context_router_tool = ROOT / "tools" / "check_context_router.py"
    if not context_router_tool.is_file():
        failures.append("missing tools/check_context_router.py")
    else:
        context_router_tool_text = read_text("tools/check_context_router.py")
        for required_context_router_tool_text in [
            "context router template",
            "portable",
            "CANONICAL_PROFILES",
            "PROFILE_FIELDS",
            "OK: checked",
        ]:
            if required_context_router_tool_text not in context_router_tool_text:
                failures.append(
                    "tools/check_context_router.py missing "
                    f"{required_context_router_tool_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_context_router.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_context_router.py")

    manifest_contract_tool = ROOT / "tools" / "check_manifest_contract.py"
    if not manifest_contract_tool.is_file():
        failures.append("missing tools/check_manifest_contract.py")
    else:
        manifest_contract_text = read_text("tools/check_manifest_contract.py")
        for required_manifest_contract_text in [
            "manifest contract",
            "portable framework requirement",
            "REQUIRED_SCALARS",
            "PLACEHOLDER_LISTS",
            "PATH_SCALARS",
            "OK: checked",
        ]:
            if required_manifest_contract_text not in manifest_contract_text:
                failures.append(
                    "tools/check_manifest_contract.py missing "
                    f"{required_manifest_contract_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_manifest_contract.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_manifest_contract.py")

    markdown_link_tool = ROOT / "tools" / "check_markdown_links.py"
    if not markdown_link_tool.is_file():
        failures.append("missing tools/check_markdown_links.py")
    else:
        markdown_link_text = read_text("tools/check_markdown_links.py")
        for required_markdown_link_text in [
            "local Markdown links",
            "portable framework requirement",
            "OK: checked",
            "SKIP_SCHEMES",
        ]:
            if required_markdown_link_text not in markdown_link_text:
                failures.append(
                    "tools/check_markdown_links.py missing "
                    f"{required_markdown_link_text}"
                )
    for relpath in [
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_markdown_links.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_markdown_links.py")

    maturity_profile_tool = ROOT / "tools" / "check_maturity_profile.py"
    if not maturity_profile_tool.is_file():
        failures.append("missing tools/check_maturity_profile.py")
    else:
        maturity_profile_tool_text = read_text("tools/check_maturity_profile.py")
        for required_maturity_profile_tool_text in [
            "maturity profile template",
            "portable",
            "REQUIRED_TASK_AREAS",
            "REQUIRED_FIELDS",
            "OK: checked",
        ]:
            if required_maturity_profile_tool_text not in maturity_profile_tool_text:
                failures.append(
                    "tools/check_maturity_profile.py missing "
                    f"{required_maturity_profile_tool_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_maturity_profile.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_maturity_profile.py")

    module_profile_tool = ROOT / "tools" / "check_module_profile.py"
    if not module_profile_tool.is_file():
        failures.append("missing tools/check_module_profile.py")
    else:
        module_profile_tool_text = read_text("tools/check_module_profile.py")
        for required_module_profile_tool_text in [
            "module profile template",
            "portable",
            "CORE_ITEMS",
            "OPTIONAL_MODULES",
            "OK: checked",
        ]:
            if required_module_profile_tool_text not in module_profile_tool_text:
                failures.append(
                    "tools/check_module_profile.py missing "
                    f"{required_module_profile_tool_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_module_profile.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_module_profile.py")

    operation_contract_tool = ROOT / "tools" / "check_operation_contracts.py"
    if not operation_contract_tool.is_file():
        failures.append("missing tools/check_operation_contracts.py")
    else:
        operation_contract_text = read_text("tools/check_operation_contracts.py")
        for required_operation_contract_text in [
            "operation contracts",
            "alias route target",
            "not a portable",
            "OK: checked",
            "REQUIRED_OPERATIONS",
        ]:
            if required_operation_contract_text not in operation_contract_text:
                failures.append(
                    "tools/check_operation_contracts.py missing "
                    f"{required_operation_contract_text}"
                )
    for relpath in [
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_operation_contracts.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_operation_contracts.py")

    operation_help_tool = ROOT / "tools" / "check_operation_help.py"
    if not operation_help_tool.is_file():
        failures.append("missing tools/check_operation_help.py")
    else:
        operation_help_text = read_text("tools/check_operation_help.py")
        for required_operation_help_text in [
            "operation help template",
            "portable",
            "SHORT_HELP_REQUIRED",
            "ALLOWED_ACTIONS",
            "OK: checked",
        ]:
            if required_operation_help_text not in operation_help_text:
                failures.append(
                    "tools/check_operation_help.py missing "
                    f"{required_operation_help_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_operation_help.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_operation_help.py")

    output_contracts_tool = ROOT / "tools" / "check_output_contracts.py"
    if not output_contracts_tool.is_file():
        failures.append("missing tools/check_output_contracts.py")
    else:
        output_contracts_text = read_text("tools/check_output_contracts.py")
        for required_output_contracts_text in [
            "output contract templates",
            "portable",
            "REQUIRED_CONTRACTS",
            "REQUIRED_FIELDS",
            "OK: checked",
        ]:
            if required_output_contracts_text not in output_contracts_text:
                failures.append(
                    "tools/check_output_contracts.py missing "
                    f"{required_output_contracts_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_output_contracts.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_output_contracts.py")

    ai_inventory_tool = ROOT / "tools" / "check_ai_infrastructure_inventory.py"
    if not ai_inventory_tool.is_file():
        failures.append("missing tools/check_ai_infrastructure_inventory.py")
    else:
        ai_inventory_text = read_text("tools/check_ai_infrastructure_inventory.py")
        for required_ai_inventory_text in [
            "AI infrastructure inventory target template",
            "portable",
            "REQUIRED_TEMPLATE_TEXT",
            "PLACEHOLDER_FIELDS",
            "OK: checked",
        ]:
            if required_ai_inventory_text not in ai_inventory_text:
                failures.append(
                    "tools/check_ai_infrastructure_inventory.py missing "
                    f"{required_ai_inventory_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_ai_infrastructure_inventory.py" not in read_text(relpath):
            failures.append(
                f"{relpath} missing check_ai_infrastructure_inventory.py"
            )

    rule_ownership_tool = ROOT / "tools" / "check_rule_ownership.py"
    if not rule_ownership_tool.is_file():
        failures.append("missing tools/check_rule_ownership.py")
    else:
        rule_ownership_tool_text = read_text("tools/check_rule_ownership.py")
        for required_rule_ownership_tool_text in [
            "rule category ownership",
            "portable",
            "category_owners",
            "rule_ids",
            "OK: checked",
        ]:
            if required_rule_ownership_tool_text not in rule_ownership_tool_text:
                failures.append(
                    "tools/check_rule_ownership.py missing "
                    f"{required_rule_ownership_tool_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_rule_ownership.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_rule_ownership.py")

    source_registry_tool = ROOT / "tools" / "check_source_of_truth_registry.py"
    if not source_registry_tool.is_file():
        failures.append("missing tools/check_source_of_truth_registry.py")
    else:
        source_registry_tool_text = read_text("tools/check_source_of_truth_registry.py")
        for required_source_registry_tool_text in [
            "source-of-truth registry template",
            "portable",
            "REQUIRED_FACT_TYPES",
            "REQUIRED_FIELDS",
            "OK: checked",
        ]:
            if required_source_registry_tool_text not in source_registry_tool_text:
                failures.append(
                    "tools/check_source_of_truth_registry.py missing "
                    f"{required_source_registry_tool_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_source_of_truth_registry.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_source_of_truth_registry.py")

    versioning_tool = ROOT / "tools" / "check_versioning.py"
    if not versioning_tool.is_file():
        failures.append("missing tools/check_versioning.py")
    else:
        versioning_tool_text = read_text("tools/check_versioning.py")
        for required_versioning_tool_text in [
            "source versioning",
            "portable",
            "VERSION",
            "ADAPTER_SCHEMA_VERSION",
            "TEMPLATE_VERSION",
            "CHANGELOG.md",
            "docs/release-process.md",
            "OK: checked",
        ]:
            if required_versioning_tool_text not in versioning_tool_text:
                failures.append(
                    "tools/check_versioning.py missing "
                    f"{required_versioning_tool_text}"
                )
    release_process = ROOT / "docs" / "release-process.md"
    if not release_process.is_file():
        failures.append("missing docs/release-process.md")
    else:
        release_process_text = read_text("docs/release-process.md")
        for required_release_text in [
            "not an installed target adapter requirement",
            "`VERSION`",
            "`ADAPTER_SCHEMA_VERSION`",
            "`TEMPLATE_VERSION`",
            "`CHANGELOG.md`",
            "`framework/rule-registry.json`",
            "`framework/rule-ownership.md`",
            "`docs/release-migration-report-template.md`",
            "`tools/report_migration_diff.py`",
            "`tools/check_release_migration_template.py`",
            "`tools/check_migration_diff_report.py`",
            "`tools/check_versioning.py`",
            "`docs/framework-maintenance.md`",
            "`recheck-after-framework-update`",
        ]:
            if required_release_text not in release_process_text:
                failures.append(
                    f"docs/release-process.md missing {required_release_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_versioning.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_versioning.py")

    release_migration_template_tool = (
        ROOT / "tools" / "check_release_migration_template.py"
    )
    if not release_migration_template_tool.is_file():
        failures.append("missing tools/check_release_migration_template.py")
    else:
        release_template_tool_text = read_text(
            "tools/check_release_migration_template.py"
        )
        for required_release_template_tool_text in [
            "release migration report template",
            "portable",
            "REQUIRED_TEMPLATE_TEXT",
            "REQUIRED_REPORTER_TEXT",
            "OK: checked",
        ]:
            if required_release_template_tool_text not in release_template_tool_text:
                failures.append(
                    "tools/check_release_migration_template.py missing "
                    f"{required_release_template_tool_text}"
                )
    release_migration_template = (
        ROOT / "docs" / "release-migration-report-template.md"
    )
    if not release_migration_template.is_file():
        failures.append("missing docs/release-migration-report-template.md")
    else:
        release_template_text = read_text("docs/release-migration-report-template.md")
        for required_release_template_text in [
            "# Alatyr Release Migration Report",
            "## Version Scope",
            "## Adapter Contract Impact",
            "## Affected Rule Categories",
            "## Affected Task Profiles",
            "## Affected Canonical Sources",
            "## Migration Action Hints",
            "## Rule Changes",
            "## Rule Owner Changes",
            "## Framework File Changes",
            "## Target Template Surface Changes",
            "## Required Target Actions",
            "## Optional Target Actions",
            "## Approval Needs",
            "## Validation Run",
            "## Residual Risks",
            "## Safety",
            "evidence only",
        ]:
            if required_release_template_text not in release_template_text:
                failures.append(
                    "docs/release-migration-report-template.md missing "
                    f"{required_release_template_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_release_migration_template.py" not in read_text(relpath):
            failures.append(
                f"{relpath} missing check_release_migration_template.py"
            )

    migration_diff_tool = ROOT / "tools" / "report_migration_diff.py"
    if not migration_diff_tool.is_file():
        failures.append("missing tools/report_migration_diff.py")
    else:
        migration_diff_text = read_text("tools/report_migration_diff.py")
        for required_migration_tool_text in [
            "--from-rules",
            "--to-rules",
            "--from-framework-dir",
            "--from-template-dir",
            "Alatyr Release Migration Report",
            "Rule Owner Changes",
            "Adapter Contract Impact",
            "Affected Rule Categories",
            "Affected Task Profiles",
            "Affected Canonical Sources",
            "Migration Action Hints",
            "Framework File Changes",
            "Target Template Surface Changes",
            "evidence only",
            "framework/rule-registry.json",
            "release-migration-report-template.md",
        ]:
            if required_migration_tool_text not in migration_diff_text:
                failures.append(
                    "tools/report_migration_diff.py missing "
                    f"{required_migration_tool_text}"
                )

    migration_diff_report_tool = ROOT / "tools" / "check_migration_diff_report.py"
    if not migration_diff_report_tool.is_file():
        failures.append("missing tools/check_migration_diff_report.py")
    else:
        migration_diff_report_text = read_text("tools/check_migration_diff_report.py")
        for required_migration_diff_report_text in [
            "migration diff reporter output shape",
            "portable",
            "REQUIRED_OUTPUT_TEXT",
            "ZERO_CHANGE_TEXT",
            "OK: checked",
        ]:
            if required_migration_diff_report_text not in migration_diff_report_text:
                failures.append(
                    "tools/check_migration_diff_report.py missing "
                    f"{required_migration_diff_report_text}"
                )
    for relpath in [
        "AGENTS.md",
        "README.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
        "docs/release-process.md",
    ]:
        if "check_migration_diff_report.py" not in read_text(relpath):
            failures.append(f"{relpath} missing check_migration_diff_report.py")

    conformance_tool = ROOT / "tools" / "check_conformance_fixtures.py"
    if not conformance_tool.is_file():
        failures.append("missing tools/check_conformance_fixtures.py")
    else:
        conformance_tool_text = read_text("tools/check_conformance_fixtures.py")
        if "OK: checked conformance fixture metadata" not in conformance_tool_text:
            failures.append(
                "tools/check_conformance_fixtures.py missing success message"
            )

    fixture_materializer_tool = ROOT / "tools" / "materialize_conformance_fixtures.py"
    if not fixture_materializer_tool.is_file():
        failures.append("missing tools/materialize_conformance_fixtures.py")
    else:
        fixture_materializer_text = read_text(
            "tools/materialize_conformance_fixtures.py"
        )
        for required_fixture_materializer_text in [
            "seed-only conformance fixture repositories",
            "does not scaffold Alatyr",
            "--output",
            "--fixture",
            "--overwrite",
        ]:
            if required_fixture_materializer_text not in fixture_materializer_text:
                failures.append(
                    "tools/materialize_conformance_fixtures.py missing "
                    f"{required_fixture_materializer_text}"
                )

    conformance_run_preparer_tool = ROOT / "tools" / "prepare_conformance_run.py"
    if not conformance_run_preparer_tool.is_file():
        failures.append("missing tools/prepare_conformance_run.py")
    else:
        conformance_run_preparer_text = read_text("tools/prepare_conformance_run.py")
        for required_conformance_run_preparer_text in [
            "per-fixture prompt files",
            "does not run an assistant",
            "assistant-surfaces.json",
            "--allow-custom-surface",
            "--assistant-surface",
            "assistant-run-result",
            "check_conformance_reports.py --actual-dir",
        ]:
            if required_conformance_run_preparer_text not in conformance_run_preparer_text:
                failures.append(
                    "tools/prepare_conformance_run.py missing "
                    f"{required_conformance_run_preparer_text}"
                )

    conformance_reports_tool = ROOT / "tools" / "check_conformance_reports.py"
    if not conformance_reports_tool.is_file():
        failures.append("missing tools/check_conformance_reports.py")
    else:
        conformance_reports_text = read_text("tools/check_conformance_reports.py")
        for required_conformance_reports_text in [
            "not an assistant installation test",
            "assistant-run-result",
            "--actual-dir",
            "--require-actual-reports",
            "--require-all-fixtures",
            "source_commit",
            "assistant-result-conformance",
            "forbidden_claims_absent",
            "OK: checked golden conformance reports",
        ]:
            if required_conformance_reports_text not in conformance_reports_text:
                failures.append(
                    "tools/check_conformance_reports.py missing "
                    f"{required_conformance_reports_text}"
                )

    conformance_summary_tool = ROOT / "tools" / "summarize_conformance_reports.py"
    if not conformance_summary_tool.is_file():
        failures.append("missing tools/summarize_conformance_reports.py")
    else:
        conformance_summary_text = read_text("tools/summarize_conformance_reports.py")
        for required_conformance_summary_text in [
            "Summarize captured assistant-run conformance reports",
            "validate_actual_reports",
            "Surface Coverage",
            "Fixture Coverage",
            "Residual Risk Counts",
            "Unresolved Validation Counts",
            "Adapter Evidence Counts",
            "does not run an assistant",
        ]:
            if required_conformance_summary_text not in conformance_summary_text:
                failures.append(
                    "tools/summarize_conformance_reports.py missing "
                    f"{required_conformance_summary_text}"
                )

    for conformance_run_file in [
        "conformance/runs/README.md",
        "conformance/runs/assistant-results/README.md",
        "conformance/runs/assistant-run-report-template.json",
        "conformance/runs/assistant-surfaces.json",
    ]:
        if not (ROOT / conformance_run_file).is_file():
            failures.append(f"missing {conformance_run_file}")

    surfaces_path = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
    if surfaces_path.is_file():
        try:
            surface_data = json.loads(surfaces_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(
                f"conformance/runs/assistant-surfaces.json invalid JSON: {exc}"
            )
            surface_data = {}
        surfaces = surface_data.get("surfaces")
        if not isinstance(surfaces, list) or not surfaces:
            failures.append("assistant-surfaces.json must contain surfaces")
        else:
            surface_ids = {
                surface.get("id")
                for surface in surfaces
                if isinstance(surface, dict)
            }
            for required_surface in [
                "generic",
                "agents",
                "codex",
                "claude",
                "gemini",
                "github-copilot",
                "cursor",
                "devin-cascade",
                "windsurf",
            ]:
                if required_surface not in surface_ids:
                    failures.append(
                        f"assistant-surfaces.json missing {required_surface}"
                    )

    scaffold_conformance_tool = ROOT / "tools" / "run_conformance_scaffold.py"
    if not scaffold_conformance_tool.is_file():
        failures.append("missing tools/run_conformance_scaffold.py")
    else:
        scaffold_conformance_text = read_text("tools/run_conformance_scaffold.py")
        for required_scaffold_conformance_text in [
            "not an assistant installation test",
            "REQUIRED_SCAFFOLD_FILES",
            "PLACEHOLDER_FILES",
            "PLACEHOLDER_PATTERN",
            "scaffold snapshot drift",
            "--write-golden-snapshots",
            "scaffold conformance fixtures passed",
            "scaffold_plan",
        ]:
            if required_scaffold_conformance_text not in scaffold_conformance_text:
                failures.append(
                    "tools/run_conformance_scaffold.py missing "
                    f"{required_scaffold_conformance_text}"
                )

    scaffold_snapshots = ROOT / "conformance" / "golden" / "scaffolded-adapters"
    if not (scaffold_snapshots / "README.md").is_file():
        failures.append("missing conformance/golden/scaffolded-adapters/README.md")
    for fixture_name in [
        "backend-api-minimal",
        "frontend-app-minimal",
        "monorepo-mixed",
        "python-cli-existing-ai",
    ]:
        snapshot_path = scaffold_snapshots / f"{fixture_name}.json"
        if not snapshot_path.is_file():
            failures.append(f"missing scaffolded-adapter snapshot: {snapshot_path}")
            continue
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{snapshot_path} is invalid JSON: {exc}")
            continue
        if snapshot.get("snapshot_kind") != "scaffolded-adapter":
            failures.append(f"{snapshot_path} must be scaffolded-adapter snapshot")
        if snapshot.get("claims_installation_complete") is not False:
            failures.append(f"{snapshot_path} must not claim completed installation")
        for key in [
            "created_paths",
            "preserved_seed_paths",
            "skipped_existing_paths",
            "placeholder_paths",
        ]:
            if not isinstance(snapshot.get(key), list):
                failures.append(f"{snapshot_path} missing list {key}")

    bridge_tool = ROOT / "tools" / "check_bridge_templates.py"
    if not bridge_tool.is_file():
        failures.append("missing tools/check_bridge_templates.py")
    else:
        bridge_tool_text = read_text("tools/check_bridge_templates.py")
        for required_bridge_tool_text in [
            "OK: checked",
            "bridge templates",
            "alatyr-ai-inventory",
            "alatyr-adaptation",
            "alatyr-add-ai",
        ]:
            if required_bridge_tool_text not in bridge_tool_text:
                failures.append(
                    "tools/check_bridge_templates.py missing "
                    f"{required_bridge_tool_text}"
                )

    bridge_manifest = ROOT / "tools" / "bridge_template_manifest.json"
    if not bridge_manifest.is_file():
        failures.append("missing tools/bridge_template_manifest.json")
    else:
        try:
            bridge_manifest_data = json.loads(bridge_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"tools/bridge_template_manifest.json is invalid JSON: {exc}")
            bridge_manifest_data = {}
        if bridge_manifest_data.get("schema_version") != 1:
            failures.append("tools/bridge_template_manifest.json schema_version must be 1")
        templates = bridge_manifest_data.get("templates")
        if not isinstance(templates, list) or not templates:
            failures.append(
                "tools/bridge_template_manifest.json must contain templates"
            )
        else:
            manifest_paths = sorted(
                template.get("path")
                for template in templates
                if isinstance(template, dict)
            )
            if manifest_paths != sorted(BRIDGE_FILES):
                failures.append(
                    "tools/bridge_template_manifest.json paths must match bridge files"
                )

    bridge_renderer = ROOT / "tools" / "render_bridge_templates.py"
    if not bridge_renderer.is_file():
        failures.append("missing tools/render_bridge_templates.py")
    else:
        bridge_renderer_text = read_text("tools/render_bridge_templates.py")
        for required_renderer_text in [
            "bridge_template_manifest.json",
            "--write",
            "not an installation",
            "OK: checked",
        ]:
            if required_renderer_text not in bridge_renderer_text:
                failures.append(
                    "tools/render_bridge_templates.py missing "
                    f"{required_renderer_text}"
                )

    for relpath in [
        "conformance/README.md",
        "conformance/golden/README.md",
        "conformance/golden/shared-expectations.json",
        "conformance/golden/effectiveness-sample.json",
        "conformance/fixtures/python-cli-existing-ai/README.md",
        "conformance/fixtures/python-cli-existing-ai/fixture.json",
        "conformance/fixtures/python-cli-existing-ai/expected.json",
        "conformance/fixtures/backend-api-minimal/README.md",
        "conformance/fixtures/backend-api-minimal/fixture.json",
        "conformance/fixtures/backend-api-minimal/expected.json",
        "conformance/fixtures/frontend-app-minimal/README.md",
        "conformance/fixtures/frontend-app-minimal/fixture.json",
        "conformance/fixtures/frontend-app-minimal/expected.json",
        "conformance/fixtures/monorepo-mixed/README.md",
        "conformance/fixtures/monorepo-mixed/fixture.json",
        "conformance/fixtures/monorepo-mixed/expected.json",
    ]:
        if not (ROOT / relpath).is_file():
            failures.append(f"missing conformance fixture: {relpath}")

    effectiveness_tool = ROOT / "tools" / "summarize_effectiveness_reports.py"
    if not effectiveness_tool.is_file():
        failures.append("missing tools/summarize_effectiveness_reports.py")
    else:
        effectiveness_tool_text = read_text("tools/summarize_effectiveness_reports.py")
        for required_effectiveness_tool_text in [
            "REQUIRED_FIELDS",
            "adapter_mode",
            "task_profile",
            "hallucinated_commands",
            "protected_changes_blocked",
            "outcome",
            "OK: loaded",
            "not",
            "portable validation requirement",
        ]:
            if required_effectiveness_tool_text not in effectiveness_tool_text:
                failures.append(
                    "tools/summarize_effectiveness_reports.py missing "
                    f"{required_effectiveness_tool_text}"
                )

    try:
        effectiveness_sample = json.loads(
            read_text("conformance/golden/effectiveness-sample.json")
        )
    except json.JSONDecodeError as exc:
        failures.append(f"conformance/golden/effectiveness-sample.json invalid: {exc}")
        effectiveness_sample = []
    if not isinstance(effectiveness_sample, list) or not effectiveness_sample:
        failures.append(
            "conformance/golden/effectiveness-sample.json must contain a report list"
        )

    for version_file in [
        "VERSION",
        "ADAPTER_SCHEMA_VERSION",
        "TEMPLATE_VERSION",
    ]:
        if not read_text(version_file).strip():
            failures.append(f"{version_file} must be non-empty")

    for relpath in [
        "installer/installed-operation-request-template.md",
        "templates/target/.ai/assistant/templates/operation-request.md",
    ]:
        if "Allowed actions:" not in read_text(relpath):
            failures.append(f"{relpath} missing Allowed actions")

    for relpath in [
        "templates/target/.ai/assistant/templates/installation-note.md",
        "templates/target/.ai/assistant/templates/post-install-message.md",
        "templates/target/.ai/assistant/templates/post-update-message.md",
    ]:
        text = read_text(relpath)
        if "AGENTS.md" not in text:
            failures.append(f"{relpath} missing AGENTS.md bootstrap reference")
        if ".ai/assistant/context-router.json" not in text:
            failures.append(f"{relpath} missing context router bootstrap reference")
        if ".ai/assistant/module-profile.md" not in text:
            failures.append(f"{relpath} missing module profile bootstrap reference")
        if "Do not rely" not in text and "Future assistants should not rely" not in text:
            failures.append(f"{relpath} missing chat-history bootstrap warning")

    gates = read_text("templates/target/.ai/assistant/gates/checklist.md")
    if "Module profile checked" not in gates:
        failures.append(
            "templates/target/.ai/assistant/gates/checklist.md missing module "
            "profile gate"
        )

    installed_operations = read_text("framework/installed-operations.md")
    for required_action in [
        "`read-only`",
        "`docs-only`",
        "`adapter-only`",
        "`code-and-tests`",
        "`full-with-approval`",
    ]:
        if required_action not in installed_operations:
            failures.append(
                f"framework/installed-operations.md missing {required_action}"
            )

    source_policy = read_text(
        "templates/target/.ai/assistant/policies/ai-infrastructure-source-access.md"
    )
    for required_source_policy_text in [
        "Local paths:",
        "Git URLs:",
        "HTTPS URLs:",
        "Pasted content:",
        "Package or plugin references:",
        "Review-only work:",
        "Canonical integration into repository files:",
    ]:
        if required_source_policy_text not in source_policy:
            failures.append(
                "templates/target/.ai/assistant/policies/"
                f"ai-infrastructure-source-access.md missing {required_source_policy_text}"
            )

    prompt_injection_policy = read_text(
        "templates/target/.ai/assistant/policies/prompt-injection.md"
    )
    for required_prompt_policy_text in [
        "untrusted data",
        "Do not execute",
        "Do not provide secrets",
        "commit SHA",
        "license",
        "Two-Stage Adaptation",
        "canonical integration",
    ]:
        if required_prompt_policy_text not in prompt_injection_policy:
            failures.append(
                "templates/target/.ai/assistant/policies/prompt-injection.md "
                f"missing {required_prompt_policy_text}"
            )

    approval_template = read_text(
        "templates/target/.ai/assistant/approvals/approval-template.md"
    )
    for required_approval_text in [
        "Approval ID:",
        "Operation ID:",
        "Plan version:",
        "Plan hash:",
        "Approval source/message:",
        "Scope invalidation rule:",
        "Allowed protected changes:",
        "Allowed files or surfaces:",
        "Excluded actions:",
        "Approved by:",
        "Approved at:",
        "Used by operation/change:",
        "Result/evidence:",
        "Residual risk:",
    ]:
        if required_approval_text not in approval_template:
            failures.append(
                "templates/target/.ai/assistant/approvals/approval-template.md "
                f"missing {required_approval_text}"
            )

    for relpath in BRIDGE_FILES:
        if line_count(relpath) > 25:
            failures.append(f"{relpath} is too long for a bridge/template wrapper")
        text = read_text(relpath)
        for required_ref in REQUIRED_BRIDGE_REFS:
            if required_ref not in text:
                failures.append(f"{relpath} does not route {required_ref}")

    for path in (ROOT / "templates" / "target").rglob("*"):
        if not path.is_file():
            continue
        relpath = str(path.relative_to(ROOT))
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            if git_check_ignore_no_index(relpath):
                failures.append(f"{relpath} is hidden by .gitignore")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: checked {len(fw_files)} framework docs and target templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
