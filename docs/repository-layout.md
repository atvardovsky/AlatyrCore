# Repository Layout

Alatyr Core is split by ownership.

## `framework/`

Portable framework core.

These files describe reusable assistant operating rules. They must not contain
target project business facts, local commands, test folders, security policy,
diagram tooling, or lifecycle facts from one project.

An assistant normally adapts these files into a target repository under
`.ai/framework`.

## `installer/`

Assistant-readable installation and post-install request process.

These files tell an assistant how to inspect a target repository, prepare an
installation plan, classify files by contour, request approval when needed,
operate an installed adapter through request templates, and report final
evidence. They also define how installation or update completion should be
reported back in assistant chat.

## `templates/target/`

Starter files for a target project.

These files are intentionally incomplete. They contain placeholders and
instructions. The installing assistant must rewrite them from target facts
before claiming installation is complete.

Hidden adapter templates under this directory, such as `.ai`, `.github`, or
`.cursor` examples, are tracked source templates. Root-local directories with
the same names are self-application scratch paths and are ignored.

## `templates/extension/`

Starter package contract for an independently versioned declarative Alatyr
extension repository. The package manifest and item examples are authoring
surfaces, not trusted or installed target content.

## `docs/`

Human-oriented product explanation and maintainer-facing guidance for
AlatyrCore itself.

`docs/human/` explains the project guardian concept, intended team use,
documentation-only demonstration path, and public limitations. These guides
must link to canonical framework owners and must not become a second source of
rule or target-project truth.

Other docs explain how to work on this source repository without turning
source repository details into framework requirements.

`docs/release-process.md` defines the source repository release and versioning
workflow. It is maintainer guidance, not a target adapter requirement.

`docs/release-migration-report-template.md` defines the source release
migration evidence shape. It is not the installed target adapter migration
note.

## `tools/`

Source-repository maintenance helpers for Alatyr Core itself.

These tools may validate indexes, templates, and source-repository consistency.
They are not portable framework requirements and must not be copied into target
repositories as required validation.

`tools/check_approval_template.py` validates the target
`.ai/assistant/approvals/approval-template.md` provides human approval
evidence; `.ai/assistant/approvals/approval-record-template.json` provides
machine-readable diff-base and path-scope enforcement. The source check covers
scope, plan, invalidation, use-result, evidence, validation, and residual-risk
fields.

`tools/check_change_packages.py` validates the optional coherent-change
package rule, target index/flow/records, semantic approval fields, provenance
grades, and explicit target-validator enforcement. It does not prove target
domain or architecture correctness.

`tools/check_architecture_knowledge.py` validates the portable architecture
knowledge rule and target architecture catalog, operation, lazy route,
templates, gates, source-of-truth entry, manifest paths, and optional module.
It checks source contracts, not the truth of a target project's architecture.

`tools/check_code_documentation.py` validates the optional portable
code-documentation rule, target source-set profiles, style proposal,
generator/output contracts, lazy route, adapted skill, gates, source-of-truth
entry, manifest paths, and target-validator support. It does not prove comment
truth or generated-reference quality.

`tools/check_project_vocabulary.py` validates the optional portable vocabulary
rule, compact catalog, scoped term and data-link records, aliases, operations,
lazy route, adapted skill, gates, manifest paths, bridge coverage, and target-
validator support. It does not prove a definition, relationship, owner, or
acceptance decision is semantically correct.

`tools/check_test_first_development.py` validates the optional test-first rule,
target policy switch, bounded suggestion behavior, configuration and execution
routes, gate, adapted skill, RED/GREEN/refactor evidence, bridge coverage, and
target-validator support. It does not prove command execution, expected RED
causality, assertion quality, or contract correctness.

`tools/check_team_collaboration.py` validates the source contract for
target-owned actors, local identity selection, active-work routing, per-task
records, backend capabilities, collaboration operations, and aggregate review.
`tools/check_team_collaboration_scenarios.py` then exercises target-validator
fixtures for concurrency, review separation, index freshness, identity, and
merge-evidence failure modes. Neither checker authenticates people or verifies
external tracker state.

`tools/validate_extension_package.py` performs offline, non-executing
structural inspection and deterministic digest calculation for a local
extension checkout. `tools/check_extensions.py` validates the framework,
authoring, target lifecycle, routing, bridge, installer, and checker contracts.
The installed target validator additionally checks enabled catalog/lock state,
target bindings, file ownership, and locked hashes. These checks do not prove
source trust, legal compatibility, semantic quality, or runtime safety.

`tools/check_ai_infrastructure_inventory.py` validates the target
`.ai/assistant/templates/ai-infrastructure-inventory.md` template and
inventory flow fields for provenance, license, permissions, prompt-injection
risk, validation, approval, recommendations, and residual risk.

`tools/check_ai_infrastructure_recommendations.py` validates the portable
recommendation policy plus target recommendation route, flow, report,
project-contour evidence boundary, cost/quality gate, existing-item review,
development-pattern index and lazy capture flow, privacy/framework boundaries,
help aliases, and manifest paths.

`tools/check_bridge_capability_matrix.py` validates the target
`.ai/assistant/bridge-capability-matrix.md` template baseline assistant
surfaces and required bridge path, loading, priority, skill/prompt,
permission, routing, limitation, and conformance fields.

`tools/check_discussion_diagrams.py` validates the portable discussion-diagram
rule and ASCII grammar, target operation, compact routing/capability
projections, security, revision lineage, operation fixture, module, manifest,
help, and per-assistant presentation contracts. It does not prove client
rendering behavior.

`tools/prepare_diagram_conformance_run.py` renders the same operation fixture
prompt for one or all supported assistant surfaces on Linux, macOS, and
Windows; actual client runs remain external evidence.

`tools/check_markdown_links.py` validates local Markdown link destinations in
source docs and templates.

`tools/check_maturity_profile.py` validates the target
`.ai/assistant/maturity-profile.md` template baseline task areas and required
supported-work, context, owner, validation, approval, blocker, residual-risk,
and evidence fields.

`tools/check_module_profile.py` validates the target
`.ai/assistant/module-profile.md` template required core items and optional
module fields.

`tools/check_framework_metadata.py` validates `alatyr_doc` front matter on
framework rule-owner documents.

`tools/check_context_router.py` validates the target
`.ai/assistant/context-router.json` compact index, lazy descriptors, canonical
context profile names, and framework file coverage.

`tools/bootstrap_index.py` and `tools/render_target_bootstrap_index.py` create
or check the hash-bound compact target bootstrap. Routed gate fragments live
under `templates/target/.ai/assistant/gates/`; `tools/check_bootstrap_routing.py`
checks profile coverage and deterministic scaffold projection.

`tools/check_manifest_contract.py` validates the target `.ai/alatyr.yaml`
template contract, including required sections, placeholder fields, list
shape, and path references.

`tools/check_operation_contracts.py` validates operation names, aliases, and
flow references in installed-operation target help templates.

`tools/check_operation_help.py` validates short help and full help-reference
shape, allowed-action text, aliases, and operation block fields.

`tools/check_output_contracts.py` validates target installation, framework
update, and adapter-recheck output contract templates.

`tools/check_release_migration_template.py` validates the source release
migration report template and migration-diff report shape.

`tools/check_rule_ownership.py` validates rule category owners, rule IDs, and
the human rule ownership map.

`tools/check_source_of_truth_registry.py` validates the target
`.ai/project/source-of-truth-registry.md` template baseline fact types and
required owner, sync, validation, conflict, approval, and evidence fields.

`tools/check_versioning.py` validates source version files, changelog
structure, and release-process documentation.

`tools/check_release_drift.py` compares the working release with the latest
reachable Git tag and runs real migration evidence against that baseline.

`tools/scaffold_target_structure.py` is an optional dry-run-first helper for
copying profile-projected placeholder structure. `tools/scaffold_projection.py`
and `tools/capability_catalog.py` keep manifest, router, operation, selected
module dependency, target-file, and framework-pack claims aligned. Neither
tool is the installation mechanism or fills target facts.

`tools/validate_target_adapter.py` is an optional installed-adapter structural
validator. It checks target adapter files for router/bootstrap drift,
unresolved placeholders, hard-coded local paths, stale checker claims,
manifest issues, optional approval/diff scope, and optional framework baseline
drift. It does not prove target project facts or replace assistant review.
Reusable parsing, Git, hashing, and approval-scope helpers live in
`tools/target_validation_support.py`. Cached and domain-specific validator
components live under `tools/target_adapter_validation`; its generated finding
catalog is documented in `docs/target-adapter-validator-findings.md`.
Source tool dependencies are declared in `requirements.txt`; source acceptance
and CI dependencies are routed through `requirements-dev.txt`.

`tools/check_manifest.json` is the dependency-aware source-check catalog used
by `tools/check_all.py` for fast, full, change, platform, and release profiles.
`tools/source_context_router.json` and `installer/context-router.json` keep
source maintenance and installation bootstrap bounded. The generated
`framework/file-inventory.json` and `framework/framework-packs.json` define the
complete source baseline and dependency-closed selective installation packs.

Windows wrappers under `tools/` delegate to the Python helpers. They should
stay thin and must not duplicate installation or validation logic.

`tools/report_migration_diff.py` compares machine-readable rule manifests and
prints human migration evidence plus an optional machine-readable upgrade
impact projection. `tools/plan_target_upgrade.py` enriches that projection with
target pack/module and source-hash evidence before structural validation.
`tools/check_conformance_fixtures.py` validates
source fixture metadata. `tools/check_conformance_reports.py` validates golden
assistant-result report contracts for those fixtures.

`tools/check_migration_diff_report.py` executes
`tools/report_migration_diff.py` against the current source baseline and
validates the generated report shape.

`tools/check_bridge_templates.py` validates source bridge templates for
supported assistant surfaces.

`tools/render_bridge_templates.py` checks or refreshes tracked source bridge
templates from `tools/bridge_template_manifest.json`.

`tools/summarize_effectiveness_reports.py` validates and summarizes source
effectiveness report data for pilots and conformance work, including task
profile, operation id, context volume, command hallucination evidence,
protected changes blocked, rework, and residual risk.

`tools/prepare_effectiveness_benchmark.py` creates paired no/minimal/full
workspaces from explicit snapshots after checking non-adapter project
equivalence. The check and summary companions require reviewed evidence before
presenting comparative deltas.

`tools/materialize_conformance_fixtures.py` creates seed-only fixture
repositories for actual assistant conformance runs.

`tools/prepare_conformance_run.py` creates a run workspace with fixture
targets, assistant prompts, and a reports directory for actual assistant-run
conformance capture.

`tools/prepare_conformance_matrix.py` composes those workspaces across selected
assistant surfaces and fixtures while preserving `prepared-not-executed`
status. `tools/check_conformance_matrix.py` checks planned coverage and can
require externally captured reports without claiming that source preparation
ran an assistant.

`tools/summarize_conformance_reports.py` summarizes reviewed assistant-run
reports by assistant surface, fixture coverage, residual risks, and unresolved
validation, including adapter evidence status for operation help, output
contracts, and AI infrastructure inventory.

`tools/run_conformance_scaffold.py` materializes temporary fixture repositories
and checks source scaffolder behavior without claiming assistant installation.

## `conformance/`

Fixture descriptions, seed files, expected behavior contracts, and golden
assistant-result reports for future conformance checks. Scaffolded-adapter
snapshots under `conformance/golden/scaffolded-adapters` record deterministic
source scaffolder output; they are not completed target installations.

`tools/run_codex_conformance.py` is an explicit, cost-incurring conformance
executor. It runs fresh Codex processes against staged fixture adapters outside
the source tree and records runtime usage separately from static scaffold or
golden contracts.
Captured assistant-run report templates and reviewed run outputs live under
`conformance/runs`.

Paired effectiveness plan and report templates live under
`conformance/benchmarks`; generated snapshots, run workspaces, and real project
facts do not.

`conformance/benchmarks/results` stores compact reviewed effectiveness
evidence. `tools/check_captured_effectiveness_results.py` ties each committed
report to execution usage and historical review hashes without treating the
omitted temporary workspaces as current-state evidence.

These files describe target shapes and expected Alatyr behavior. They are not
real target adapters and must not contain project-specific business facts.

## Root Files

- `README.md`: public product entry point plus assistant and maintainer
  reference.
- `AGENTS.md`: canonical instructions for assistants working on Alatyr Core.
- `AI_ASSISTANTS.md`: generic assistant entry point.
- `INSTALL.md`: human-readable installation guide.
- `VERSION`: current framework version.
- `ADAPTER_SCHEMA_VERSION`: current installed-adapter schema version.
- `TEMPLATE_VERSION`: current target-template version.
- `CHANGELOG.md`: framework lifecycle notes.
- `LICENSE`: official Apache License, Version 2.0 terms for this repository
  unless a file explicitly states otherwise.
- `docs/release-process.md`: source release and versioning process.

## Ownership Rule

If a fact describes how assistants should generally work, it may belong in
`framework/`.

If a fact describes how to install Alatyr Core into a target project, it may
belong in `installer/`.

If a fact describes how to request work from an already installed target
adapter, it may belong in `installer/` as a request template or in
`templates/target/.ai/assistant` as a placeholder flow/template.

If a fact describes target adapter metadata, context routing, task-specific
maturity, module state, bridge capability, approval records, migration notes,
effectiveness reports, or imported-source policy, it may belong in
`templates/target/.ai/alatyr.yaml` or `templates/target/.ai/assistant`, but it
must remain placeholder-based.

If a fact describes target file ownership for adapter surfaces, it may belong
in `templates/target/CODEOWNERS` or an equivalent placeholder owner map, but
it must not name real project owners.

If a fact describes target source-of-truth ownership, it may belong in
`templates/target/.ai/project/source-of-truth-registry.md`, but it must remain
placeholder-based.

If a fact describes how an installed adapter should show available operations,
route unclear requests, or format post-install/update chat messages, it may
belong in `templates/target/.ai/assistant` as placeholder adapter
infrastructure.

If a fact describes an example target file shape, it may belong in
`templates/target/`, but it must remain placeholder-based.

If a fact describes one real project, it does not belong in Alatyr Core.
