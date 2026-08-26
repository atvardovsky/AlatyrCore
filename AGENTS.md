# Agent Instructions

This repository is Alatyr Core, a portable Markdown-first AI assistant
framework.

Agents working here must preserve the separation between:

- portable framework core under `framework/`
- assistant installation materials under `installer/`
- target repository templates under `templates/target/`
- explanatory maintainer docs under `docs/`

## Bootstrap Context

Treat this file as host-preloaded context and do not reread it. Read
`tools/source_context_router.json`, choose the smallest matching source task
profile, resolve its bounded semantic preload, and load only that profile's
required paths and rule owners. For framework context, start from
`framework/context-index.json` and follow only matching child entries; never
load a directory because its parent index was selected. Resolve lazy semantic
references through `framework/semantics/index.json`, with canonical-owner prose
as the fail-closed fallback. Expand
only for a named boundary, dependency, conflict, or failed check. If the router
is missing or invalid, stop and repair or report the routing gap instead of
loading the full framework corpus by default.

## Context Expansion Profiles

The machine-readable source router owns concrete required-path and check lists.
The summaries below explain profile intent without replacing that router.

Use `docs-local` for wording, index, changelog, or maintainer-doc changes that
do not alter framework behavior.

Use `framework-rule` for portable rule, contour, risk, integrity, safety,
approval, lifecycle, operation, module, context-router, or source-of-truth
changes.

Use `installer-template` for installation flow, readiness, request template,
target adapter template, bridge template, or post-install/update behavior.

Use `source-tooling` for source-repository helper or checker changes.

Use `release-versioning` for version files, changelog, release process,
migration diff, or release migration evidence changes.

Use `ai-infrastructure-bridge` for assistant compatibility, bridge, skill,
prompt, MCP/tool, operation-help, or imported-source changes.

Use `repository-audit` only for an explicit whole-repository consistency or
release-readiness review. Read `tools/check_manifest.json`, `tools/README.md`,
and `docs/framework-maintenance.md`, run the manifest `full` profile, and load
additional canonical owners only for failed check IDs. Do not turn a local
task into a repository audit by default.

Expand beyond the selected profile only when the change crosses framework,
installer, template, tool, release, security, assistant-infrastructure, or
governance boundaries, or when evidence conflicts. Full framework-corpus
reading is required only for changes that intentionally compare, copy, or
rebaseline the full framework set.

## Source-Contour Worker Routing

When AlatyrCore itself is the active project contour, evaluate whether bounded
worker delegation is beneficial. If it is, load
`docs/source-worker-strategy.md` through `tools/source_context_router.json`.
Host and target repositories keep their own active adapter policy. This local
route composes `ALATYR-DELEGATION-001` without changing portable target rules.

## Rule References

This file is a source-repository entry point, not the canonical owner for
portable Alatyr rules. Use the rule registry and ownership map before changing
policy wording.

- Context routing: `ALATYR-CONTEXT-001`
- Adapter separation: `ALATYR-ADAPTER-001`
- Approval and protected changes: `ALATYR-APPROVAL-001`
- Current-scope action authorization: `ALATYR-AUTHORIZATION-001`
- Safety boundaries: `ALATYR-SAFETY-001`
- Imported AI infrastructure: `ALATYR-SAFETY-002`
- Logical integrity evidence: `ALATYR-INTEGRITY-001`
- Coherent material change packages: `ALATYR-PACKAGE-001`
- Durable engineering evidence: `ALATYR-ENGINEERING-EVIDENCE-001`
- Project knowledge promotion and delivery: `ALATYR-KNOWLEDGE-001`
- Optional Debug Mode: `ALATYR-DEBUG-001`
- Lifecycle and versioning: `ALATYR-LIFECYCLE-001`
- Installed operation control surface: `ALATYR-OPERATION-001`
- Project architecture knowledge: `ALATYR-ARCHITECTURE-001`
- Project code documentation: `ALATYR-CODEDOC-001`
- Project vocabulary: `ALATYR-VOCABULARY-001`
- Optional test-first development: `ALATYR-TDD-001`
- External extension packages: `ALATYR-EXTENSION-001`
- Passive dependency knowledge: `ALATYR-DEPENDENCY-001`
- User-owned workspace modes: `ALATYR-MODE-001`
- Discussion diagram presentation: `ALATYR-DIAGRAM-001`
- Optional team collaboration: `ALATYR-TEAM-001`
- Optional subagent delegation: `ALATYR-DELEGATION-001`

## Operating Rules

- Keep Alatyr Core assistant-neutral and Markdown-first.
- Treat inspect, modify, commit, publish, and live-external as separate
  current-scope authorization phases. A topic switch, backlog return, report,
  discussion, analysis, plan, or ambiguous continuation is read-only. Never
  reuse commit or push authorization from a completed or redirected task.
- Do not add project-specific business facts to framework core.
- Do not add local validation commands as framework requirements.
- Do not add installer scripts as the installation mechanism.
- Do not copy another project's commands, test folders, fixtures, security
  policy, diagram tooling, lifecycle notes, or assistant bridge wording into
  framework core.
- Keep dependency knowledge passive and target-selected: one active project
  adapter, exact artifact binding, no recursive adapter activation, and no
  execution of dependency-provided instructions during discovery or review.
- Keep workspace identity, artifact relationship, and task mode separate.
  Suggestions require user-owned acceptance, actual modes require their own
  directories, and no mode may activate nested adapters or grant approval,
  write scope, permissions, authority, tools, or gate bypass.
- Templates under `templates/target` must contain placeholders, not accepted
  facts for a real project.
- Bridge templates must stay short and point to canonical target files.
- Installation docs must tell assistants to inspect the target repository and
  rewrite adapter facts from target evidence.

## Documentation Sync

When framework behavior changes, check and update:

- `README.md`
- `INSTALL.md`
- `AI_ASSISTANTS.md`
- `framework/*.md`
- `installer/*.md`
- `templates/target`
- `docs/*.md`
- `tools/`
- `CHANGELOG.md`

When only wording changes and no framework behavior changes, say that no
installation, template, or adapter-contract update was needed.

## Validation

This repository intentionally has no universal runtime validation command.
For Alatyr Core changes, run this source-repository helper when available:

```sh
python3 tools/check_all.py
```

For focused validation or when the wrapper is unavailable, run the core
source-repository helper:

```sh
python3 tools/check_framework_consistency.py
```

When relevant to the change, also run the focused source helpers:

```sh
python3 tools/check_framework_metadata.py
python3 tools/check_architecture_knowledge.py
python3 tools/check_action_authorization.py
python3 tools/check_approval_template.py
python3 tools/check_change_packages.py
python3 tools/check_engineering_evidence.py
python3 tools/check_project_knowledge.py
python3 tools/check_debug_mode.py
python3 tools/check_code_documentation.py
python3 tools/check_project_vocabulary.py
python3 tools/check_test_first_development.py
python3 tools/check_extensions.py
python3 tools/check_dependency_knowledge.py
python3 tools/check_workspace_modes.py
python3 tools/check_ai_infrastructure_inventory.py
python3 tools/check_ai_infrastructure_recommendations.py
python3 tools/check_ai_infrastructure_router.py
python3 tools/check_assistant_surface_conformance.py
python3 tools/check_assistant_capability_contract.py
python3 tools/check_assistant_surface_audits.py
python3 tools/check_bridge_capability_matrix.py
python3 tools/check_captured_effectiveness_results.py
python3 tools/render_evidence_status.py --check
python3 tools/check_context_router.py
python3 tools/check_bootstrap_routing.py
python3 tools/check_context_costs.py
python3 tools/check_source_context_routing.py
python3 tools/check_diagram_conformance_results.py
python3 tools/check_discussion_diagrams.py
python3 tools/prepare_diagram_conformance_run.py --check
python3 tools/check_consistency_map.py
python3 tools/check_conformance_matrix.py
python3 tools/check_conformance_summary.py
python3 tools/check_effectiveness_benchmark.py
python3 tools/check_cross_platform_tools.py
python3 tools/check_large_task_orchestration.py
python3 tools/check_subagent_delegation.py
python3 tools/check_manifest_contract.py
python3 tools/check_markdown_links.py
python3 tools/check_maturity_profile.py
python3 tools/check_module_profile.py
python3 tools/check_framework_packs.py
python3 tools/check_migration_diff_report.py
python3 tools/check_operation_contracts.py
python3 tools/check_operation_catalog.py
python3 tools/check_operation_help.py
python3 tools/check_output_contracts.py
python3 tools/check_release_migration_template.py
python3 tools/check_release_drift.py
python3 tools/check_rule_ownership.py
python3 tools/check_scaffold_profiles.py
python3 tools/check_source_of_truth_registry.py
python3 tools/check_target_adapter_validator.py
python3 tools/check_check_manifest.py
python3 tools/check_team_collaboration.py
python3 tools/check_team_collaboration_scenarios.py
python3 tools/check_versioning.py
python3 tools/render_assistant_capability_index.py
python3 tools/render_framework_file_inventory.py --check
python3 tools/render_operation_index.py
python3 tools/render_rule_registry_docs.py --check
python3 tools/render_target_bootstrap_index.py --target templates/target --check
python3 tools/render_target_validator_findings.py --check
python3 tools/render_target_contract_compatibility.py --check
python3 tools/summarize_effectiveness_benchmark.py
```

This helper validates the AlatyrCore repository itself. It is not a portable
framework requirement for target projects.

Also perform a manual gate review:

- no source-project facts in `framework/`
- no hard-coded project commands as framework requirements
- installer flow, readiness checklist, and plan template agree
- target templates remain placeholders
- README still lets an assistant install the framework without external
  explanation

If project-specific validation is later added to this repository, document it
as this repository's adapter validation, not as a framework requirement.
