"""Target-template and bridge checks for framework consistency."""

from __future__ import annotations

import json

from .context import CheckContext


def check_target_operation_surfaces(context: CheckContext) -> list[str]:
    failures: list[str] = []
    help_template = context.read_text("templates/target/.ai/assistant/help.md")
    if "| Operation |" in help_template:
        failures.append(
            "templates/target/.ai/assistant/help.md should use operation blocks, not a table"
        )
    if context.line_count("templates/target/.ai/assistant/help.md") > 150:
        failures.append("templates/target/.ai/assistant/help.md should stay short")
    for required_help_text in [
        "Operation: `help`",
        "Full operation reference: `.ai/assistant/help-reference.md`",
        "These aliases are chat/request shortcuts, not shell commands.",
        "Default routing:",
        'requires_paths":[".ai/assistant/flows/adapter-health.flow.md"]',
    ]:
        if required_help_text not in help_template:
            failures.append(
                f"templates/target/.ai/assistant/help.md missing {required_help_text}"
            )

    help_reference = context.read_text("templates/target/.ai/assistant/help-reference.md")
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

    target_context_profiles = context.read_text(
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
    for relpath in context.framework_files:
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

    module_profile = context.read_text("templates/target/.ai/assistant/module-profile.md")
    for required_module_text in [
        "## Kernel And Core Profiles",
        "Kernel item: `contours`",
        "Kernel item: `manifest-and-versioning`",
        "Kernel item: `adapter-ownership`",
        "Kernel item: `context-profiles`",
        "Kernel item: `source-of-truth-registry`",
        "Kernel item: `risk-approval-integrity`",
        "Kernel item: `current-scope-action-authorization`",
        "Kernel item: `validation-and-final-evidence`",
        "Kernel item: `support-information-state`",
        "Core profile addition: `durable-engineering-evidence`",
        "Core profile addition: `project-knowledge-delivery`",
        "Module: `blueprint-change`",
        "Module: `diagrams`",
        "Module: `ai-infrastructure`",
        "Module: `multi-assistant-bridges`",
        "Module: `installed-operations`",
        "Module: `durable-approvals`",
        "Module: `change-packages`",
        "Module: `migration-diff`",
        "Module: `effectiveness-metrics`",
        "Module: `scaffolding`",
    ]:
        if required_module_text not in module_profile:
            failures.append(
                "templates/target/.ai/assistant/module-profile.md missing "
                f"{required_module_text}"
            )

    manifest = context.read_text("templates/target/.ai/alatyr.yaml")
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
        "change_packages:",
        "policies:",
        "known_gaps:",
        "local_deviations:",
    ]:
        if required_manifest_text not in manifest:
            failures.append(
                f"templates/target/.ai/alatyr.yaml missing {required_manifest_text}"
            )

    return failures


def check_target_governance_surfaces(context: CheckContext) -> list[str]:
    failures: list[str] = []
    source_registry = context.read_text("templates/target/.ai/project/source-of-truth-registry.md")
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

    maturity_profile = context.read_text(
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

    bridge_matrix = context.read_text(
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
    try:
        required_bridge_surfaces = [
            f"### Assistant Surface: `{surface['id']}`"
            for surface in context.assistant_surfaces()
            if isinstance(surface.get("id"), str)
        ]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        required_bridge_surfaces = []
    for required_bridge_surface in required_bridge_surfaces:
        if required_bridge_surface not in bridge_matrix:
            failures.append(
                "templates/target/.ai/assistant/bridge-capability-matrix.md "
                f"missing {required_bridge_surface}"
            )

    migration_note = context.read_text(
        "templates/target/.ai/assistant/templates/migration-note.md"
    )
    for required_migration_text in [
        "From framework version:",
        "To framework version:",
        "From adapter schema version:",
        "To adapter schema version:",
        "Evidence basis:",
        "Migration assessment:",
        "## Routed Context",
        "Affected canonical framework sources:",
        "Candidate context intentionally omitted:",
        "## Changed Framework Rules",
        "## Required Target Actions",
        "## Optional Target Actions",
        ".ai/assistant/module-profile.md",
        "Approval needed:",
        "Assessment completed before target changes:",
        "Migration result:",
    ]:
        if required_migration_text not in migration_note:
            failures.append(
                "templates/target/.ai/assistant/templates/migration-note.md "
                f"missing {required_migration_text}"
            )

    effectiveness_report = context.read_text(
        "templates/target/.ai/assistant/templates/effectiveness-report.md"
    )
    for required_effectiveness_text in [
        "Task:",
        "Task profile:",
        "Adapter mode:",
        "Context files loaded:",
        "Approximate context volume:",
        "Context expansions:",
        "Context receipt reused:",
        "Context budget exceeded:",
        "Clarifications:",
        "Approvals requested:",
        "Validation:",
        "Missed companion updates:",
        "Rework count:",
        "Changed facts identified:",
        "Consistency relationships reviewed:",
        "Companion surfaces checked:",
        "Unresolved consistency gaps:",
        "Duration seconds:",
        "Residual risks:",
        "Outcome:",
    ]:
        if required_effectiveness_text not in effectiveness_report:
            failures.append(
                "templates/target/.ai/assistant/templates/effectiveness-report.md "
                f"missing {required_effectiveness_text}"
            )

    return failures


def check_target_runtime_policies(context: CheckContext) -> list[str]:
    failures: list[str] = []
    gates = context.read_text("templates/target/.ai/assistant/gates/checklist.md")
    core_gate = context.read_text("templates/target/.ai/assistant/gates/core.md")
    for required_risk_text in [
        "every applicable risk class",
        "`low`,",
        "`moderate`,",
        "`high`,",
        "`protected`",
        "cannot be downgraded",
    ]:
        if required_risk_text not in core_gate:
            failures.append(
                "templates/target/.ai/assistant/gates/core.md missing risk "
                f"severity contract: {required_risk_text}"
            )

    install_flow = context.read_text("installer/assistant-installation.flow.md")
    if "Use schema version 6 for" not in install_flow or (
        "preserve schema versions 1 through 5" not in install_flow
    ):
        failures.append("installer Debug record guidance must require schema version 6")
    evidence_records = context.read_text(
        "templates/target/.ai/project/engineering-evidence/records/README.md"
    )
    evidence_records = " ".join(evidence_records.split())
    if "schema version 3" not in evidence_records or (
        "schema versions 1 and 2" not in evidence_records
    ):
        failures.append(
            "Engineering Evidence record guidance must require schema version 3"
        )
    if "Module profile checked" not in gates:
        failures.append(
            "templates/target/.ai/assistant/gates/checklist.md missing module "
            "profile gate"
        )
    for required_gate_text in [
        ".ai/assistant/gates/index.json",
        "Adapter drift checks",
        "hard-coded local machine paths",
        "stale checker",
        "duplicate context-profile references",
        "target-local adapter checker evidence",
    ]:
        if required_gate_text not in gates:
            failures.append(
                "templates/target/.ai/assistant/gates/checklist.md missing "
                f"{required_gate_text}"
            )

    operation_routing = context.read_text(
        "templates/target/.ai/assistant/flows/operation-routing.flow.md"
    )
    for required_routing_text in [
        "Context router: `.ai/assistant/context-router.json`",
        "Load bootstrap context only:",
        "Select the smallest matching context profile from",
        "Do not load all",
        ".ai/framework",
        ".ai/project",
    ]:
        if required_routing_text not in operation_routing:
            failures.append(
                "templates/target/.ai/assistant/flows/"
                f"operation-routing.flow.md missing {required_routing_text}"
            )
    if "Load `AGENTS.md`, `AI_ASSISTANTS.md`, `.ai/README.md`, `.ai/framework`" in operation_routing:
        failures.append(
            "templates/target/.ai/assistant/flows/operation-routing.flow.md "
            "must not require broad framework/project loading before routing"
        )

    adapter_recheck = context.read_text(
        "templates/target/.ai/assistant/flows/adapter-recheck.flow.md"
    )
    for required_recheck_text in [
        "adapter drift hazards",
        "hard-coded local machine paths",
        "stale",
        "required-context references",
        ".ai/assistant/context-router.json",
        "target-local adapter checker evidence",
    ]:
        if required_recheck_text not in adapter_recheck:
            failures.append(
                "templates/target/.ai/assistant/flows/"
                f"adapter-recheck.flow.md missing {required_recheck_text}"
            )

    output_contracts = context.read_text(
        "templates/target/.ai/assistant/templates/adapter-output-contracts.md"
    )
    for required_output_text in [
        "Adapter drift checks result:",
        "Local path leakage result:",
        "Target-local checker status:",
    ]:
        if required_output_text not in output_contracts:
            failures.append(
                "templates/target/.ai/assistant/templates/"
                f"adapter-output-contracts.md missing {required_output_text}"
            )

    installed_operations = context.read_text("framework/installed-operations.md")
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

    source_policy = context.read_text(
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
        "target-local adapter checker status",
    ]:
        if required_source_policy_text not in source_policy:
            failures.append(
                "templates/target/.ai/assistant/policies/"
                f"ai-infrastructure-source-access.md missing {required_source_policy_text}"
            )

    prompt_injection_policy = context.read_text(
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

    approval_template = context.read_text(
        "templates/target/.ai/assistant/approvals/approval-template.md"
    )
    for required_approval_text in [
        "Approval ID:",
        "Operation ID:",
        "Plan version:",
        "Plan hash:",
        "Approval source/message:",
        "Scope invalidation rule:",
        "Machine-readable record:",
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

    return failures


def check_bridges_and_git_visibility(context: CheckContext) -> list[str]:
    failures: list[str] = []
    for relpath in context.bridge_files:
        if context.line_count(relpath) > 25:
            failures.append(f"{relpath} is too long for a bridge/template wrapper")
        text = context.read_text(relpath)
        for required_ref in context.required_bridge_refs:
            if required_ref not in text:
                failures.append(f"{relpath} does not route {required_ref}")

    hidden_template_paths: list[str] = []
    for path in (context.root / "templates" / "target").rglob("*"):
        if not path.is_file():
            continue
        relpath = path.relative_to(context.root).as_posix()
        if any(part.startswith(".") for part in path.relative_to(context.root).parts):
            hidden_template_paths.append(relpath)
    try:
        ignored_template_paths = context.git_ignored_no_index(hidden_template_paths)
    except RuntimeError as exc:
        failures.append(str(exc))
    else:
        for relpath in sorted(ignored_template_paths):
            failures.append(f"{relpath} is hidden by .gitignore")

    return failures
