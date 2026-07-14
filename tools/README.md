# Alatyr Core Tools

These helpers belong to the AlatyrCore source repository.
They are not portable framework requirements for target projects.

## Cross-Platform Entry Point

`alatyr.py` exposes the stable optional source tools through one command
manifest. It does not turn Alatyr into a runtime service or replace the
assistant-led installation process. Each command reports its write scope in
help.

Linux or macOS:

```sh
python3 tools/alatyr.py --help
python3 tools/alatyr.py validate-adapter --target /path/to/target-repo
python3 tools/alatyr.py assess-upgrade --target /path/to/target-repo --framework-source . --output-dir tmp/upgrade-assessment
```

Windows PowerShell:

```powershell
.\tools\alatyr.ps1 --help
.\tools\alatyr.ps1 validate-adapter --target C:\path\to\target-repo
.\tools\alatyr.ps1 assess-upgrade --target C:\path\to\target-repo --framework-source . --output-dir tmp\upgrade-assessment
```

Windows Command Prompt:

```bat
tools\alatyr.cmd --help
tools\alatyr.cmd validate-adapter --target C:\path\to\target-repo
```

The stable command set is:

- `check-source`: no writes
- `scaffold`: target structure writes only with `--write`
- `validate-adapter`: optional explicit report output only
- `migration-report`: optional explicit report output only
- `assess-upgrade`: explicit assessment output only; no adapter changes
- `context-costs`: optional static context-cost report output only
- `prepare-conformance`: explicit conformance workspace output only; no
  assistant execution
- `check-conformance`: read-only prepared or captured matrix validation
- `prepare-benchmark`: explicit paired benchmark workspace output only; no
  assistant execution
- `check-benchmark`: read-only isolation, report, and review validation
- `summarize-benchmark`: read-only reviewed measurement comparison

## Source Validation Runner

`check_all.py` runs the stable source-repository checks for AlatyrCore source
maintenance. It validates this repository only; it is not a portable framework
requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_all.py
python3 tools/check_all.py --list
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_all.py
py -3 .\tools\check_all.py --list
```

## Approval Template Check

`check_approval_template.py` validates the target
`.ai/assistant/approvals/approval-template.md` template in this source
repository. It checks approval identity, operation identity, plan version and
hash, protected scope, allowed files or surfaces, excluded actions, approval
source, invalidation rule, use result, validation, evidence, and residual-risk
fields. It is not a portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_approval_template.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_approval_template.py
```

## AI Infrastructure Inventory Check

`check_ai_infrastructure_inventory.py` validates the target
`.ai/assistant/templates/ai-infrastructure-inventory.md` template and matching
inventory flow in this source repository. It checks source/provenance,
license, hash or commit, permissions, prompt-injection risk, validation,
approval, recommendation, and residual-risk fields. It is not a portable
framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_ai_infrastructure_inventory.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_ai_infrastructure_inventory.py
```

## AI Infrastructure Router Check

`check_ai_infrastructure_router.py` validates the target capability router,
lazy route-specific context, item contracts, permissions, gates, validation,
output contracts, adaptation-record fields, and manifest paths.

Linux or macOS:

```sh
python3 tools/check_ai_infrastructure_router.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_ai_infrastructure_router.py
```

## Bridge Capability Matrix Check

`check_bridge_capability_matrix.py` validates the target
`.ai/assistant/bridge-capability-matrix.md` template in this source
repository. It checks assistant surfaces from
`conformance/runs/assistant-surfaces.json` plus bridge paths, auto-load
behavior, instruction priority, supported rule/prompt/skill surfaces, tool
permission model, help and AI-infrastructure alias routing, known limitations,
and conformance checks. It is not a portable framework requirement for target
projects.

Linux or macOS:

```sh
python3 tools/check_bridge_capability_matrix.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_bridge_capability_matrix.py
```

## Context Router Check

`check_context_router.py` validates the target
`.ai/assistant/context-router.json` template in this source repository. It
checks canonical profile names, preloaded versus compact bootstrap context,
budgets, receipt fields, area overlays, path references, duplicate route
entries, and framework file routing coverage. It is not a portable framework
requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_context_router.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_context_router.py
```

## Consistency Map Check

`check_consistency_map.py` validates the optional target consistency-map JSON,
portable levels and relationship types, impact policy, human registry linkage,
manifest path, and placeholder node/edge contract.

Linux or macOS:

```sh
python3 tools/check_consistency_map.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_consistency_map.py
```

## Large-Task Orchestration Check

`check_large_task_orchestration.py` validates the optional large-task
framework guidance, target task-scale route, orchestration flow, resumable
packet fields, and manifest path. It does not validate target project facts or
workstream completion.

Linux or macOS:

```sh
python3 tools/check_large_task_orchestration.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_large_task_orchestration.py
```

## Scaffold Target Structure

`scaffold_target_structure.py` copies placeholder target templates and
framework files, including `framework/rule-registry.json`, into an existing
target directory. It is dry-run by default. The `full` profile preserves the
historical all-template behavior. Use `core` for required adapter support
surfaces or `standard` for core plus common product and lifecycle operations.
Every profile copies the complete portable framework baseline; profile
selection filters target adapter templates only.

It does not inspect target facts, complete installation, approve overwrites, or
validate an installed adapter.

Linux or macOS:

```sh
python3 tools/scaffold_target_structure.py --target /path/to/target-repo
python3 tools/scaffold_target_structure.py --target /path/to/target-repo --profile core --write
```

Windows PowerShell:

```powershell
py -3 .\tools\scaffold_target_structure.py --target C:\path\to\target-repo
.\tools\scaffold_target_structure.ps1 --target C:\path\to\target-repo --profile standard
```

Windows Command Prompt:

```bat
tools\scaffold_target_structure.cmd --target C:\path\to\target-repo
tools\scaffold_target_structure.cmd --target C:\path\to\target-repo --profile full --write
```

Use `--overwrite-existing` only after explicit approval for the exact target
path and protected surfaces.

`check_scaffold_profiles.py` verifies profile inheritance, required core
surfaces, full-template coverage, and bridge isolation.

## Target Adapter Validator

`validate_target_adapter.py` validates structural consistency of an installed
Alatyr adapter in a target repository. It checks router/bootstrap references,
consistency-map and AI-infrastructure-router schemas when present, unresolved
placeholders, hard-coded local paths, stale checker claims, manifest fields,
target-local checker coverage, optional approval scope against a supplied git
diff, and optional `.ai/framework` drift against an AlatyrCore source checkout.

It does not install Alatyr Core, inspect project business truth, approve
protected changes, run target validation, or replace assistant logical
integrity review.

Use `--json` or `--output <file>` when a target CI job or assistant recheck
needs machine-readable findings. The JSON output contains severity counts,
exit status, and stable finding objects with `level`, `code`, `message`, and
optional `path`.

Validator JSON classifies its findings as `current-state-structural` evidence.
It does not treat current files as proof that historical installation,
approval, update, or validation actions occurred. Supply dated repository
records separately when historical evidence is required.

An installed adapter may optionally provide
`.ai/assistant/validator-config.json`. The config can add allowed local path
substrings, choose target-local checker coverage terms, promote or demote
warning/info finding severities, and record accepted deviations with reasons.
Config cannot silence hard structural errors.

Example config:

```json
{
  "schema_version": 1,
  "allow_local_path_patterns": ["C:\\\\project-fixtures"],
  "required_checker_coverage": [
    "context-router",
    "placeholder",
    "local path",
    "stale",
    "manifest"
  ],
  "severity_overrides": {
    "TARGET_CHECKER_MISSING": "info"
  },
  "accepted_deviations": [
    {
      "code": "TARGET_CHECKER_COVERAGE_GAP",
      "reason": "Adapter records manual review instead of local checker coverage."
    }
  ]
}
```

Linux or macOS:

```sh
python3 tools/validate_target_adapter.py --target /path/to/target-repo
python3 tools/validate_target_adapter.py --target /path/to/target-repo --framework-source /path/to/AlatyrCore
python3 tools/validate_target_adapter.py --target /path/to/target-repo --diff-ref origin/main
python3 tools/validate_target_adapter.py --target /path/to/target-repo --diff-ref origin/main --approval-record .ai/assistant/approvals/change-approval.md
python3 tools/validate_target_adapter.py --target /path/to/target-repo --json --output tmp/alatyr-adapter-report.json
python3 tools/validate_target_adapter.py --target /path/to/target-repo --framework-source /path/to/AlatyrCore --migration-diff /path/to/migration-report.md
```

Windows PowerShell:

```powershell
py -3 .\tools\validate_target_adapter.py --target C:\path\to\target-repo
.\tools\validate_target_adapter.ps1 --target C:\path\to\target-repo
py -3 .\tools\validate_target_adapter.py --target C:\path\to\target-repo --json --output tmp\alatyr-adapter-report.json
```

Windows Command Prompt:

```bat
tools\validate_target_adapter.cmd --target C:\path\to\target-repo
```

## Target Adapter Validator Contract Check

`check_target_adapter_validator.py` exercises the source validator's schema
compatibility, consistency-map and AI-router findings, explicit approval-scope
matching, and current-state evidence classification. It validates AlatyrCore
source tooling only.

```sh
python3 tools/check_target_adapter_validator.py
```

```powershell
py -3 .\tools\check_target_adapter_validator.py
```

## Context Cost And Assistant Surface Checks

`report_context_costs.py` resolves target router paths to source templates and
reports declared files plus whitespace word counts for bootstrap, profiles,
and migration-first routing. It is a deterministic static estimate, not model
token usage.

```sh
python3 tools/alatyr.py context-costs
python3 tools/report_context_costs.py --output tmp/context-costs.json
python3 tools/check_context_costs.py
```

`check_assistant_surface_conformance.py` checks compact bridge routing and
prepares one fixture prompt for every supported assistant surface without
running an assistant:

```sh
python3 tools/check_assistant_surface_conformance.py
```

## Framework Metadata Check

`check_framework_metadata.py` validates `alatyr_doc` front matter on
framework rule-owner documents in this source repository. It checks document
IDs, owned rule IDs, dependencies, task-profile scope, and agreement with
`framework/rule-registry.json`. It is not a portable framework requirement
for target projects.

Linux or macOS:

```sh
python3 tools/check_framework_metadata.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_framework_metadata.py
```

## Manifest Contract Check

`check_manifest_contract.py` validates the target `.ai/alatyr.yaml` template
contract in this source repository. It checks required sections, placeholder
fields, list shape, and path references to target template surfaces or known
framework-copy outputs. It is not a portable framework requirement for target
projects.

Linux or macOS:

```sh
python3 tools/check_manifest_contract.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_manifest_contract.py
```

## Markdown Link Check

`check_markdown_links.py` validates local Markdown link destinations in this
source repository. It skips external URLs, anchors-only links, and placeholder
template references. It is not a portable framework requirement for target
projects.

Linux or macOS:

```sh
python3 tools/check_markdown_links.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_markdown_links.py
```

## Maturity Profile Check

`check_maturity_profile.py` validates the target
`.ai/assistant/maturity-profile.md` template in this source repository. It
checks baseline task areas plus maturity level, supported work, required
context, owners, validation, approval needs, blockers, residual risks, and
final evidence fields. It is not a portable framework requirement for target
projects.

Linux or macOS:

```sh
python3 tools/check_maturity_profile.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_maturity_profile.py
```

## Module Profile Check

`check_module_profile.py` validates the target
`.ai/assistant/module-profile.md` template in this source repository. It
checks required core items, optional modules, required files, evidence,
validation, approval, residual-risk, and next-action fields. It is not a
portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_module_profile.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_module_profile.py
```

## Operation Contract Check

`check_operation_contracts.py` validates installed-operation template
contracts in this source repository. It checks operation names, alias route
targets, and flow references in the target help templates. It is not a
portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_operation_contracts.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_operation_contracts.py
```

## Operation Help Check

`check_operation_help.py` validates installed-operation help templates in this
source repository. It checks that short help stays compact, avoids tables,
points to the full reference, documents allowed actions, and keeps each
reference operation block shaped with use, flow, and minimum-input fields. It
is not a portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_operation_help.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_operation_help.py
```

## Output Contract Check

`check_output_contracts.py` validates target adapter output contracts in this
source repository. It checks installation, framework-update, and adapter
recheck evidence fields, including adapter drift, local path leakage, and
target-local checker status evidence, and verifies the installation flow and
installation note point to the contract template. It is not a portable
framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_output_contracts.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_output_contracts.py
```

## Rule Ownership Check

`check_rule_ownership.py` validates rule category ownership metadata in this
source repository. It checks `framework/rule-registry.json` category owners,
rule IDs, owner paths, and the human `framework/rule-ownership.md` map. It is
not a portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_rule_ownership.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_rule_ownership.py
```

## Source Of Truth Registry Check

`check_source_of_truth_registry.py` validates the target
`.ai/project/source-of-truth-registry.md` template in this source repository.
It checks baseline fact types plus canonical owner, derived surfaces, sync
direction, validation, conflict resolver, approval trigger, and final evidence
fields. It is not a portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_source_of_truth_registry.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_source_of_truth_registry.py
```

## Versioning Check

`check_versioning.py` validates source version files, changelog structure, and
release-process documentation for this repository. It is not a portable
framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_versioning.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_versioning.py
```

## Release Migration Report Check

`check_release_migration_template.py` validates the source release migration
report template and checks that `report_migration_diff.py` emits the same
evidence shape. It is not a portable framework requirement for target
projects.

Linux or macOS:

```sh
python3 tools/check_release_migration_template.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_release_migration_template.py
```

## Migration Diff Report

`report_migration_diff.py` compares two machine-readable rule registries and
prints a Markdown release migration report using
`docs/release-migration-report-template.md`. The report is evidence only. It
does not apply target changes. The report includes adapter contract impact,
affected rule categories, affected task profiles, affected canonical sources,
and migration action hints.

Linux or macOS:

```sh
python3 tools/report_migration_diff.py --from-rules old-rule-registry.json
python3 tools/report_migration_diff.py --from-rules old-rule-registry.json --from-framework-dir /path/to/old/.ai/framework
python3 tools/report_migration_diff.py --from-rules old-rule-registry.json --from-template-dir /path/to/old/templates/target
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\report_migration_diff.py --from-rules old-rule-registry.json
py -3 .\tools\report_migration_diff.py --from-rules old-rule-registry.json --from-framework-dir C:\path\to\old\.ai\framework
py -3 .\tools\report_migration_diff.py --from-rules old-rule-registry.json --from-template-dir C:\path\to\old\templates\target
```

`plan_target_upgrade.py`, also available as `alatyr.py assess-upgrade`, creates
`migration-report.md`, `adapter-validation.json`, and
`upgrade-assessment.md` in an explicit output directory. It compares the
installed framework baseline with the selected AlatyrCore source and runs the
structural validator before any upgrade edits. A non-zero result means the
assessment contains findings that require review; generated evidence remains
available. Use `--overwrite` only to replace an existing assessment directory.

`check_migration_diff_report.py` executes the reporter against the current
source baseline and validates the generated report shape. It is not a
portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_migration_diff_report.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_migration_diff_report.py
```

## Conformance Fixtures

`check_conformance_fixtures.py` validates source conformance fixture metadata,
including target-shape manifests and expected evidence contracts. It does not
install Alatyr Core into a target repository.

`materialize_conformance_fixtures.py` creates seed-only fixture repositories
under a chosen output directory. Use those repositories as the starting point
for real assistant conformance runs.

`prepare_conformance_run.py` creates fixture repositories, per-fixture
assistant prompts, a local report template, and a reports directory for a
selected assistant surface. By default targets are seed-only. Use
`--staged-adapter-profile core` to test target bridge and compact-router
discovery against placeholder adapter structure without claiming installation.
Staged runs must use an output directory outside the AlatyrCore checkout so a
parent source `AGENTS.md` cannot contaminate target auto-load evidence.
It validates the surface against `conformance/runs/assistant-surfaces.json`
unless `--allow-custom-surface` is provided. It does not run the assistant or
claim installation success.

`run_codex_conformance.py` prepares staged targets and runs one fresh,
ephemeral Codex CLI process per fixture. It disables user configuration, roots
each process in the fixture target, captures JSONL locally, records exact CLI
token usage and duration in `execution-summary.json`, and validates all reports.
This is an explicit cost-incurring source conformance operation, not a stable
check run by `check_all.py`.

`prepare_conformance_matrix.py`, also available as `alatyr.py
prepare-conformance`, creates one run workspace for every selected assistant
surface and fixture. It records expected report counts, source commit, run IDs,
and `prepared-not-executed` status in matrix and run manifests. It never runs
an assistant.

`check_conformance_matrix.py`, also available as `alatyr.py
check-conformance`, validates those manifests and prepared prompt/target
coverage. Add `--require-reports` only after external assistants have produced
reports; that mode requires every planned surface/fixture pair and verifies
run ID, assistant surface, source commit, and report provenance.

`check_conformance_reports.py` validates golden assistant-result report
contracts for each fixture. It checks expected behaviors and required evidence
fields, but it does not run an assistant or validate a real target adapter.
It can also validate captured assistant-run reports when `--actual-dir` points
to a directory of JSON reports. Add `--require-actual-reports` when CI should
fail if the directory has no captured reports, and `--require-all-fixtures`
when a full run should cover every fixture.

`summarize_conformance_reports.py` summarizes captured assistant-run reports by
assistant surface and fixture after validating the report contracts. It is for
comparing reviewed run outputs, context cost, logical-integrity evidence,
adapter evidence status, residual risks, and unresolved validation, not for
running assistants.

`check_conformance_summary.py` exercises that validator and summary using
synthetic source-only records. It does not represent an actual assistant run.

`run_conformance_scaffold.py` materializes temporary fixture repositories and
checks that the source scaffolder preserves seed files while creating
placeholder adapter structure. It also compares the generated scaffold output
with golden snapshots under `conformance/golden/scaffolded-adapters`. It is
not an assistant installation test.

Linux or macOS:

```sh
python3 tools/check_conformance_fixtures.py
python3 tools/materialize_conformance_fixtures.py --output tmp/conformance-targets
python3 tools/prepare_conformance_run.py --output tmp/conformance-run --assistant-surface codex
python3 tools/prepare_conformance_run.py --output /tmp/conformance-run --assistant-surface codex --staged-adapter-profile core
python3 tools/run_codex_conformance.py --output /tmp/codex-conformance
python3 tools/alatyr.py prepare-conformance --output tmp/conformance-matrix
python3 tools/alatyr.py check-conformance --matrix tmp/conformance-matrix/matrix.json
python3 tools/alatyr.py check-conformance --matrix tmp/conformance-matrix/matrix.json --require-reports
python3 tools/check_conformance_reports.py
python3 tools/check_conformance_summary.py
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-actual-reports
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-actual-reports --require-all-fixtures
python3 tools/summarize_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-all-fixtures
python3 tools/summarize_conformance_reports.py --matrix tmp/conformance-matrix/matrix.json
python3 tools/run_conformance_scaffold.py
python3 tools/run_conformance_scaffold.py --write-golden-snapshots
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_conformance_fixtures.py
py -3 .\tools\materialize_conformance_fixtures.py --output tmp\conformance-targets
py -3 .\tools\prepare_conformance_run.py --output tmp\conformance-run --assistant-surface codex
py -3 .\tools\prepare_conformance_run.py --output C:\Temp\conformance-run --assistant-surface codex --staged-adapter-profile core
py -3 .\tools\run_codex_conformance.py --output C:\Temp\codex-conformance
py -3 .\tools\alatyr.py prepare-conformance --output tmp\conformance-matrix
py -3 .\tools\alatyr.py check-conformance --matrix tmp\conformance-matrix\matrix.json
py -3 .\tools\alatyr.py check-conformance --matrix tmp\conformance-matrix\matrix.json --require-reports
py -3 .\tools\check_conformance_reports.py
py -3 .\tools\check_conformance_summary.py
py -3 .\tools\check_conformance_reports.py --actual-dir conformance\runs\assistant-results
py -3 .\tools\check_conformance_reports.py --actual-dir conformance\runs\assistant-results --require-actual-reports
py -3 .\tools\check_conformance_reports.py --actual-dir conformance\runs\assistant-results --require-actual-reports --require-all-fixtures
py -3 .\tools\summarize_conformance_reports.py --actual-dir conformance\runs\assistant-results --require-all-fixtures
py -3 .\tools\summarize_conformance_reports.py --matrix tmp\conformance-matrix\matrix.json
py -3 .\tools\run_conformance_scaffold.py
py -3 .\tools\run_conformance_scaffold.py --write-golden-snapshots
```

Use `--write-golden-snapshots` only after reviewing intended scaffold output
changes.

## Effectiveness Reports

`summarize_effectiveness_reports.py` validates and summarizes JSON or JSONL
effectiveness reports for pilots and conformance work. It does not prove
framework quality by itself and is not a target validation requirement. The
sample includes task profile, operation id, context volume, hallucinated
command evidence, protected changes blocked, rework, and residual risk.

For controlled comparisons, `prepare_effectiveness_benchmark.py`, also
available as `alatyr.py prepare-benchmark`, copies user-supplied `none`,
`minimal`, and `full` snapshots into isolated workspaces. It rejects project
content drift outside declared adapter surfaces and writes
`prepared-not-executed` run prompts.

`check_effectiveness_benchmark.py` validates prepared isolation and, with
`--require-reports --require-reviewed`, requires every paired run plus
independent acceptance-criteria review. `summarize_effectiveness_benchmark.py`
reports averages and relative deltas only from complete reviewed reports. It
marks unknown or zero-reference comparisons as non-computable. Token and
monetary-cost readiness requires comparable evidence across every paired run.

`run_codex_effectiveness_benchmark.py` executes a prepared benchmark with one
fresh Codex process per mode/repetition. It disables user configuration,
captures local JSONL, writes completion-event token and duration evidence into
assistant reports, and leaves independent acceptance review pending. It incurs
real model usage and is not part of `check_all.py`.

`check_captured_effectiveness_results.py` validates compact committed benchmark
evidence under `conformance/benchmarks/results`: reviewed mode reports,
execution-summary token alignment, review hashes, and the narrow claim
boundary. Complete temporary targets and raw logs remain outside the source
repository.

Linux or macOS:

```sh
python3 tools/summarize_effectiveness_reports.py --input conformance/golden/effectiveness-sample.json
python3 tools/alatyr.py prepare-benchmark --plan benchmark.json --output tmp/benchmark
python3 tools/run_codex_effectiveness_benchmark.py --benchmark /tmp/benchmark/benchmark.json
python3 tools/check_captured_effectiveness_results.py
python3 tools/alatyr.py check-benchmark --benchmark tmp/benchmark/benchmark.json --require-reports --require-reviewed
python3 tools/alatyr.py summarize-benchmark --benchmark tmp/benchmark/benchmark.json
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\summarize_effectiveness_reports.py --input conformance\golden\effectiveness-sample.json
py -3 .\tools\alatyr.py prepare-benchmark --plan benchmark.json --output tmp\benchmark
py -3 .\tools\run_codex_effectiveness_benchmark.py --benchmark C:\Temp\benchmark\benchmark.json
py -3 .\tools\check_captured_effectiveness_results.py
py -3 .\tools\alatyr.py check-benchmark --benchmark tmp\benchmark\benchmark.json --require-reports --require-reviewed
py -3 .\tools\alatyr.py summarize-benchmark --benchmark tmp\benchmark\benchmark.json
```

## Bridge Templates

`check_bridge_templates.py` validates supported assistant bridge templates in
the source repository. It checks that bridge files stay short, point back to
canonical target files, and route Alatyr help plus AI infrastructure aliases.

`render_bridge_templates.py` checks that bridge templates match
`tools/bridge_template_manifest.json`. Use `--write` only when intentionally
refreshing tracked source templates.

Linux or macOS:

```sh
python3 tools/check_bridge_templates.py
python3 tools/render_bridge_templates.py
python3 tools/render_bridge_templates.py --write
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_bridge_templates.py
py -3 .\tools\render_bridge_templates.py
py -3 .\tools\render_bridge_templates.py --write
```
