# Agent Instructions

This repository is Alatyr Core, a portable Markdown-first AI assistant
framework.

Agents working here must preserve the separation between:

- portable framework core under `framework/`
- assistant installation materials under `installer/`
- target repository templates under `templates/target/`
- explanatory maintainer docs under `docs/`

## Bootstrap Context

At the start of an AlatyrCore source-repository task, read only the bootstrap
context first:

- `README.md`
- `AGENTS.md`
- `framework/README.md`
- `framework/context-router.md`
- `framework/context-profiles.md`
- `framework/rule-ownership.md`
- `framework/rule-registry.md`
- `docs/framework-maintenance.md`

Then choose the smallest matching source task profile below and read the
profile-required files before editing. Do not load every framework file by
default.

## Context Expansion Profiles

Use `docs-local` for wording, index, changelog, or maintainer-doc changes
that do not alter framework behavior. Read the edited file, its linked
neighbors, and `docs/framework-maintenance.md`.

Use `framework-rule` for portable rule, contour, risk, integrity, safety,
approval, lifecycle, operation, module, context-router, or source-of-truth
changes. Read the owning `framework/*.md` file, its `alatyr_doc` dependencies
when present, `framework/rule-registry.md`, `framework/rule-registry.json`,
`framework/rule-ownership.md`, and affected installer/template surfaces.

Use `installer-template` for installation flow, readiness, request template,
target adapter template, bridge template, or post-install/update behavior
changes. Read `INSTALL.md`, `installer/assistant-installation.flow.md`,
`installer/readiness-checklist.md`, `installer/installation-plan-template.md`,
the affected `templates/target` files, and the owning framework rule files
named by the changed behavior.

Use `source-tooling` for source-repository helper or checker changes. Read the
tool being changed, `tools/README.md`, `docs/framework-maintenance.md`, and
the framework, installer, or template contracts the tool validates.

Use `release-versioning` for version files, changelog, release process,
migration diff, or release migration evidence changes. Read `VERSION`,
`ADAPTER_SCHEMA_VERSION`, `TEMPLATE_VERSION`, `CHANGELOG.md`,
`docs/release-process.md`, `docs/release-migration-report-template.md`,
`framework/lifecycle.md`, and `framework/migration-diff.md`.

Use `ai-infrastructure-bridge` for assistant compatibility, bridge, skill,
prompt, MCP/tool, operation-help, or imported-source changes. Read
`AI_ASSISTANTS.md`, `docs/assistant-compatibility.md`,
`framework/bridge-capability-matrix.md`, `framework/skill-adaptation.md`,
`framework/ai-infrastructure-routing.md`,
`framework/prompt-injection.md`, `framework/operation-help.md`, and affected
bridge or target assistant files.

Expand beyond the selected profile only when the change crosses framework,
installer, template, tool, release, security, assistant-infrastructure, or
governance boundaries, or when evidence conflicts. Full framework-corpus
reading is required only for changes that intentionally compare, copy, or
rebaseline the full framework set.

## Rule References

This file is a source-repository entry point, not the canonical owner for
portable Alatyr rules. Use the rule registry and ownership map before changing
policy wording.

- Context routing: `ALATYR-CONTEXT-001`
- Adapter separation: `ALATYR-ADAPTER-001`
- Approval and protected changes: `ALATYR-APPROVAL-001`
- Safety boundaries: `ALATYR-SAFETY-001`
- Imported AI infrastructure: `ALATYR-SAFETY-002`
- Logical integrity evidence: `ALATYR-INTEGRITY-001`
- Lifecycle and versioning: `ALATYR-LIFECYCLE-001`
- Installed operation control surface: `ALATYR-OPERATION-001`

## Operating Rules

- Keep Alatyr Core assistant-neutral and Markdown-first.
- Do not add project-specific business facts to framework core.
- Do not add local validation commands as framework requirements.
- Do not add installer scripts as the installation mechanism.
- Do not copy another project's commands, test folders, fixtures, security
  policy, diagram tooling, lifecycle notes, or assistant bridge wording into
  framework core.
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
python3 tools/check_approval_template.py
python3 tools/check_ai_infrastructure_inventory.py
python3 tools/check_ai_infrastructure_recommendations.py
python3 tools/check_ai_infrastructure_router.py
python3 tools/check_assistant_surface_conformance.py
python3 tools/check_bridge_capability_matrix.py
python3 tools/check_captured_effectiveness_results.py
python3 tools/check_context_router.py
python3 tools/check_context_costs.py
python3 tools/check_consistency_map.py
python3 tools/check_conformance_matrix.py
python3 tools/check_conformance_summary.py
python3 tools/check_effectiveness_benchmark.py
python3 tools/check_cross_platform_tools.py
python3 tools/check_large_task_orchestration.py
python3 tools/check_manifest_contract.py
python3 tools/check_markdown_links.py
python3 tools/check_maturity_profile.py
python3 tools/check_module_profile.py
python3 tools/check_migration_diff_report.py
python3 tools/check_operation_contracts.py
python3 tools/check_operation_catalog.py
python3 tools/check_operation_help.py
python3 tools/check_output_contracts.py
python3 tools/check_release_migration_template.py
python3 tools/check_rule_ownership.py
python3 tools/check_scaffold_profiles.py
python3 tools/check_source_of_truth_registry.py
python3 tools/check_target_adapter_validator.py
python3 tools/check_versioning.py
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
