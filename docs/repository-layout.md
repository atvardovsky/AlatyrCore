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

## `docs/`

Maintainer-facing explanation of Alatyr Core itself.

Docs should explain how to work on this source repository without turning
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
`.ai/assistant/approvals/approval-template.md` template required approval,
scope, plan, invalidation, use-result, evidence, validation, and residual-risk
fields.

`tools/check_ai_infrastructure_inventory.py` validates the target
`.ai/assistant/templates/ai-infrastructure-inventory.md` template and
inventory flow fields for provenance, license, permissions, prompt-injection
risk, validation, approval, recommendations, and residual risk.

`tools/check_bridge_capability_matrix.py` validates the target
`.ai/assistant/bridge-capability-matrix.md` template baseline assistant
surfaces and required bridge path, loading, priority, skill/prompt,
permission, routing, limitation, and conformance fields.

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
`.ai/assistant/context-router.json` template against canonical context profile
names and framework file coverage.

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

`tools/scaffold_target_structure.py` is an optional dry-run-first helper for
copying placeholder structure. It is not the installation mechanism and does
not fill target facts.

`tools/validate_target_adapter.py` is an optional installed-adapter structural
validator. It checks target adapter files for router/bootstrap drift,
unresolved placeholders, hard-coded local paths, stale checker claims,
manifest issues, optional approval/diff scope, and optional framework baseline
drift. It does not prove target project facts or replace assistant review.

Windows wrappers under `tools/` delegate to the Python helpers. They should
stay thin and must not duplicate installation or validation logic.

`tools/report_migration_diff.py` compares machine-readable rule manifests and
prints migration evidence. `tools/check_conformance_fixtures.py` validates
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

- `README.md`: main assistant and maintainer entry point.
- `AGENTS.md`: canonical instructions for assistants working on Alatyr Core.
- `AI_ASSISTANTS.md`: generic assistant entry point.
- `INSTALL.md`: human-readable installation guide.
- `VERSION`: current framework version.
- `ADAPTER_SCHEMA_VERSION`: current installed-adapter schema version.
- `TEMPLATE_VERSION`: current target-template version.
- `CHANGELOG.md`: framework lifecycle notes.
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
