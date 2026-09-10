"""Rule-registry and source-tool checks for framework consistency."""

from __future__ import annotations

import json

from .context import CheckContext


def check_rule_registry_contract(context: CheckContext) -> list[str]:
    failures: list[str] = []
    rule_registry = context.read_text("framework/rule-registry.md")
    required_rule_ids = [
        "ALATYR-CONTEXT-001",
        "ALATYR-SOURCE-001",
        "ALATYR-RISK-001",
        "ALATYR-APPROVAL-001",
        "ALATYR-AUTHORIZATION-001",
        "ALATYR-SAFETY-001",
        "ALATYR-SAFETY-002",
        "ALATYR-INTEGRITY-001",
        "ALATYR-CHANGE-001",
        "ALATYR-PACKAGE-001",
        "ALATYR-CODEDOC-001",
        "ALATYR-VOCABULARY-001",
        "ALATYR-ADAPTER-001",
        "ALATYR-MODULE-001",
        "ALATYR-OPERATION-001",
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

    rule_ownership = context.read_text("framework/rule-ownership.md")
    for required_ownership_text in [
        "Category: `CONTEXT`",
        "Category: `SOURCE`",
        "Category: `RISK`",
        "Category: `CODEDOC`",
        "Category: `VOCABULARY`",
        "Category: `APPROVAL`",
        "Category: `SAFETY`",
        "Category: `INTEGRITY`",
        "Category: `CHANGE`",
        "Category: `PACKAGE`",
        "Category: `ADAPTER`",
        "Category: `MODULE`",
        "Category: `OPERATION`",
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

    rule_registry_json = context.root / "framework" / "rule-registry.json"
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
                if not (context.root / canonical_source).is_file():
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
            elif not (context.root / owner_path).is_file():
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

    module_profile = " ".join(
        context.read_text("framework/module-profile.md").split()
    )
    for required_text in [
        "four ordered support profiles",
        "`kernel`: the minimum safe adapter contract",
        "`core`: kernel plus durable engineering evidence",
        "`standard`: core plus common blueprint",
        "`full`: standard plus the complete portable framework pack",
        "`full` support profile maps to the `complete` framework pack",
        "A broader pack does not activate a broader support profile",
    ]:
        if required_text not in module_profile:
            failures.append(f"framework/module-profile.md missing {required_text}")

    risk_model = " ".join(
        context.read_text("framework/change-risk-model.md").split()
    )
    for required_text in [
        "Classes are categories, not an ordered severity scale.",
        "`low`:",
        "`moderate`:",
        "`high`:",
        "`protected`:",
        "must not downgrade a framework-protected change",
    ]:
        if required_text not in risk_model:
            failures.append(f"framework/change-risk-model.md missing {required_text}")

    context_profiles = " ".join(
        context.read_text("framework/context-profiles.md").split()
    )
    for required_text in [
        "Recursive catalog selectors such as `path_terms`",
        "do not independently authorize or load a catalog branch",
        "conditional context path and load condition as `selected` or `omitted`",
    ]:
        if required_text not in context_profiles:
            failures.append(f"framework/context-profiles.md missing {required_text}")

    return failures


def check_core_source_tools(context: CheckContext) -> list[str]:
    failures: list[str] = []
    scaffolder = context.root / "tools" / "scaffold_target_structure.py"
    if not scaffolder.is_file():
        failures.append("missing tools/scaffold_target_structure.py")
    else:
        scaffolder_text = context.read_text("tools/scaffold_target_structure.py")
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
        if not (context.root / wrapper).is_file():
            failures.append(f"missing {wrapper}")
        elif "scaffold_target_structure.py" not in context.read_text(wrapper):
            failures.append(f"{wrapper} must delegate to scaffold_target_structure.py")

    source_runner = context.root / "tools" / "check_all.py"
    if not source_runner.is_file():
        failures.append("missing tools/check_all.py")
    else:
        source_runner_text = context.read_text("tools/check_all.py")
        for required_source_runner_text in [
            "check_manifest.json",
            "load_manifest",
            "ThreadPoolExecutor",
            'default="full"',
            "--changed-from",
        ]:
            if required_source_runner_text not in source_runner_text:
                failures.append(
                    "tools/check_all.py missing "
                    f"{required_source_runner_text}"
                )

    target_validator = context.root / "tools" / "validate_target_adapter.py"
    if not target_validator.is_file():
        failures.append("missing tools/validate_target_adapter.py")
    else:
        target_validator_text = context.read_text("tools/validate_target_adapter.py")
        for required_validator_text in [
            "optional helper",
            "does not install Alatyr Core",
            "Linux, macOS, and Windows",
            "--target",
            "--framework-source",
            "--diff-ref",
            "--migration-diff",
            "--json",
            "--output",
            "VALIDATOR_CONFIG_LOADED",
            "APPROVAL_PATCH_HASH_MISMATCH",
            "MIGRATION_DIFF_IMPACT",
            "--allow-local-path",
            "LOCAL_PATH_LEAKAGE",
            "STALE_CHECKER_MISSING_CLAIM",
            "FRAMEWORK_FILE_DRIFT",
        ]:
            if required_validator_text not in target_validator_text:
                failures.append(
                    "tools/validate_target_adapter.py missing "
                    f"{required_validator_text}"
                )

    for wrapper in [
        "tools/validate_target_adapter.cmd",
        "tools/validate_target_adapter.ps1",
    ]:
        if not (context.root / wrapper).is_file():
            failures.append(f"missing {wrapper}")
        elif "validate_target_adapter.py" not in context.read_text(wrapper):
            failures.append(f"{wrapper} must delegate to validate_target_adapter.py")

    tools_readme = "tools/README.md"
    if not (context.root / tools_readme).is_file():
        failures.append("missing tools/README.md")
    else:
        tools_readme_text = context.read_text(tools_readme)
        for required_tools_readme_text in [
            "Linux or macOS:",
            "Windows PowerShell:",
            "Windows Command Prompt:",
            "not portable framework requirements",
            "check_all.py",
            "check_approval_template.py",
            "check_change_packages.py",
            "check_bridge_capability_matrix.py",
            "check_discussion_diagrams.py",
            "check_framework_metadata.py",
            "check_ai_infrastructure_inventory.py",
            "check_ai_infrastructure_recommendations.py",
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
            "validate_target_adapter.py",
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
            "--json",
            "--migration-diff",
        ]:
            if required_tools_readme_text not in tools_readme_text:
                failures.append(
                    f"tools/README.md missing {required_tools_readme_text}"
                )

    for relpath in [
        "INSTALL.md",
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "validate_target_adapter.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing validate_target_adapter.py")

    framework_metadata_tool = context.root / "tools" / "check_framework_metadata.py"
    if not framework_metadata_tool.is_file():
        failures.append("missing tools/check_framework_metadata.py")
    else:
        framework_metadata_text = context.read_text("tools/check_framework_metadata.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_framework_metadata.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_framework_metadata.py")

    approval_template_tool = context.root / "tools" / "check_approval_template.py"
    if not approval_template_tool.is_file():
        failures.append("missing tools/check_approval_template.py")
    else:
        approval_template_tool_text = context.read_text("tools/check_approval_template.py")
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
    return failures


def check_context_source_tools(context: CheckContext) -> list[str]:
    failures: list[str] = []
    context_profiles = context.read_text("framework/context-profiles.md")
    context_router = context.read_text("framework/context-router.md")
    bridge_matrix = context.read_text("framework/bridge-capability-matrix.md")
    ordered_artifacts = [
        "bootstrap index",
        "bootstrap integrity sidecar",
        "recursive project and assistant context catalogs",
        "support state",
    ]
    for relpath, text, anchor in [
        (
            "framework/context-profiles.md",
            context_profiles,
            "Rebuild generated surfaces in this canonical order:",
        ),
        (
            "framework/context-router.md",
            context_router,
            "rebuild in canonical order:",
        ),
    ]:
        section = (
            " ".join(text[text.find(anchor) :].split()) if anchor in text else ""
        )
        positions = [section.find(marker) for marker in ordered_artifacts]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            failures.append(f"{relpath} has inconsistent generated-artifact order")
    for required_bootstrap_text in [
        "load only",
        ".ai/assistant/bootstrap-index.json",
        "recovery, audit, or routing-conflict",
    ]:
        if required_bootstrap_text not in bridge_matrix:
            failures.append(
                "framework/bridge-capability-matrix.md missing compact bootstrap "
                f"contract: {required_bootstrap_text}"
            )
    for relpath in [
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_approval_template.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_approval_template.py")

    for relpath in [
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_change_packages.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_change_packages.py")

    bridge_capability_tool = context.root / "tools" / "check_bridge_capability_matrix.py"
    if not bridge_capability_tool.is_file():
        failures.append("missing tools/check_bridge_capability_matrix.py")
    else:
        bridge_capability_tool_text = context.read_text(
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
        "docs/assistant-compatibility.md",
    ]:
        if "check_bridge_capability_matrix.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_bridge_capability_matrix.py")

    discussion_diagram_tool = context.root / "tools" / "check_discussion_diagrams.py"
    if not discussion_diagram_tool.is_file():
        failures.append("missing tools/check_discussion_diagrams.py")
    else:
        discussion_diagram_text = context.read_text("tools/check_discussion_diagrams.py")
        for required_discussion_diagram_text in [
            "discussion-diagram source and target template contracts",
            "diagram-discussion",
            "assistant-capabilities.json",
            "diagram-discussion.json",
            "assistant-surfaces.json",
            "OK: checked",
        ]:
            if required_discussion_diagram_text not in discussion_diagram_text:
                failures.append(
                    "tools/check_discussion_diagrams.py missing "
                    f"{required_discussion_diagram_text}"
                )
    for relpath in [
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
        "docs/assistant-compatibility.md",
    ]:
        if "check_discussion_diagrams.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_discussion_diagrams.py")

    context_router_tool = context.root / "tools" / "check_context_router.py"
    if not context_router_tool.is_file():
        failures.append("missing tools/check_context_router.py")
    else:
        context_router_tool_text = context.read_text("tools/check_context_router.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_context_router.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_context_router.py")

    manifest_contract_tool = context.root / "tools" / "check_manifest_contract.py"
    if not manifest_contract_tool.is_file():
        failures.append("missing tools/check_manifest_contract.py")
    else:
        manifest_contract_text = context.read_text("tools/check_manifest_contract.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_manifest_contract.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_manifest_contract.py")

    markdown_link_tool = context.root / "tools" / "check_markdown_links.py"
    if not markdown_link_tool.is_file():
        failures.append("missing tools/check_markdown_links.py")
    else:
        markdown_link_text = context.read_text("tools/check_markdown_links.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_markdown_links.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_markdown_links.py")

    maturity_profile_tool = context.root / "tools" / "check_maturity_profile.py"
    if not maturity_profile_tool.is_file():
        failures.append("missing tools/check_maturity_profile.py")
    else:
        maturity_profile_tool_text = context.read_text("tools/check_maturity_profile.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_maturity_profile.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_maturity_profile.py")

    module_profile_tool = context.root / "tools" / "check_module_profile.py"
    if not module_profile_tool.is_file():
        failures.append("missing tools/check_module_profile.py")
    else:
        module_profile_tool_text = context.read_text("tools/check_module_profile.py")
        for required_module_profile_tool_text in [
            "module profile template",
            "PROFILE_ITEMS",
            "capabilities.json",
            "OK: checked",
        ]:
            if required_module_profile_tool_text not in module_profile_tool_text:
                failures.append(
                    "tools/check_module_profile.py missing "
                    f"{required_module_profile_tool_text}"
                )
    return failures


def check_operation_source_tools(context: CheckContext) -> list[str]:
    failures: list[str] = []
    for relpath in [
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_module_profile.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_module_profile.py")

    operation_contract_tool = context.root / "tools" / "check_operation_contracts.py"
    if not operation_contract_tool.is_file():
        failures.append("missing tools/check_operation_contracts.py")
    else:
        operation_contract_text = context.read_text("tools/check_operation_contracts.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_operation_contracts.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_operation_contracts.py")

    operation_help_tool = context.root / "tools" / "check_operation_help.py"
    if not operation_help_tool.is_file():
        failures.append("missing tools/check_operation_help.py")
    else:
        operation_help_text = context.read_text("tools/check_operation_help.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_operation_help.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_operation_help.py")

    output_contracts_tool = context.root / "tools" / "check_output_contracts.py"
    if not output_contracts_tool.is_file():
        failures.append("missing tools/check_output_contracts.py")
    else:
        output_contracts_text = context.read_text("tools/check_output_contracts.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_output_contracts.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_output_contracts.py")

    ai_inventory_tool = context.root / "tools" / "check_ai_infrastructure_inventory.py"
    if not ai_inventory_tool.is_file():
        failures.append("missing tools/check_ai_infrastructure_inventory.py")
    else:
        ai_inventory_text = context.read_text("tools/check_ai_infrastructure_inventory.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_ai_infrastructure_inventory.py" not in context.read_text(relpath):
            failures.append(
                f"{relpath} missing check_ai_infrastructure_inventory.py"
            )

    ai_recommendation_tool = (
        context.root / "tools" / "check_ai_infrastructure_recommendations.py"
    )
    if not ai_recommendation_tool.is_file():
        failures.append("missing tools/check_ai_infrastructure_recommendations.py")
    else:
        ai_recommendation_text = context.read_text(
            "tools/check_ai_infrastructure_recommendations.py"
        )
        for required_ai_recommendation_text in [
            "AI infrastructure recommendation source and target contracts",
            "FRAMEWORK_TEXT",
            "PLACEHOLDER_FIELDS",
            "recommend route",
            "OK: checked",
        ]:
            if required_ai_recommendation_text not in ai_recommendation_text:
                failures.append(
                    "tools/check_ai_infrastructure_recommendations.py missing "
                    f"{required_ai_recommendation_text}"
                )
    for relpath in [
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_ai_infrastructure_recommendations.py" not in context.read_text(relpath):
            failures.append(
                f"{relpath} missing check_ai_infrastructure_recommendations.py"
            )

    rule_ownership_tool = context.root / "tools" / "check_rule_ownership.py"
    if not rule_ownership_tool.is_file():
        failures.append("missing tools/check_rule_ownership.py")
    else:
        rule_ownership_tool_text = context.read_text("tools/check_rule_ownership.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_rule_ownership.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_rule_ownership.py")

    source_registry_tool = context.root / "tools" / "check_source_of_truth_registry.py"
    if not source_registry_tool.is_file():
        failures.append("missing tools/check_source_of_truth_registry.py")
    else:
        source_registry_tool_text = context.read_text("tools/check_source_of_truth_registry.py")
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
        "tools/README.md",
        "docs/framework-maintenance.md",
        "docs/repository-layout.md",
    ]:
        if "check_source_of_truth_registry.py" not in context.read_text(relpath):
            failures.append(f"{relpath} missing check_source_of_truth_registry.py")

    versioning_tool = context.root / "tools" / "check_versioning.py"
    if not versioning_tool.is_file():
        failures.append("missing tools/check_versioning.py")
    else:
        versioning_tool_text = context.read_text("tools/check_versioning.py")
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
    return failures
