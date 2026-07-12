# Alatyr Core Tools

These helpers belong to the AlatyrCore source repository.
They are not portable framework requirements for target projects.

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
checks canonical profile names, bootstrap context, required fields, path
references, duplicate route entries, and framework file routing coverage. It
is not a portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_context_router.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_context_router.py
```

## Scaffold Target Structure

`scaffold_target_structure.py` copies placeholder target templates and
framework files, including `framework/rule-registry.json`, into an existing
target directory. It is dry-run by default.

It does not inspect target facts, complete installation, approve overwrites, or
validate an installed adapter.

Linux or macOS:

```sh
python3 tools/scaffold_target_structure.py --target /path/to/target-repo
python3 tools/scaffold_target_structure.py --target /path/to/target-repo --write
```

Windows PowerShell:

```powershell
py -3 .\tools\scaffold_target_structure.py --target C:\path\to\target-repo
.\tools\scaffold_target_structure.ps1 --target C:\path\to\target-repo
```

Windows Command Prompt:

```bat
tools\scaffold_target_structure.cmd --target C:\path\to\target-repo
tools\scaffold_target_structure.cmd --target C:\path\to\target-repo --write
```

Use `--overwrite-existing` only after explicit approval for the exact target
path and protected surfaces.

## Target Adapter Validator

`validate_target_adapter.py` validates structural consistency of an installed
Alatyr adapter in a target repository. It checks router/bootstrap references,
unresolved placeholders, hard-coded local paths, stale checker claims,
manifest fields, target-local checker coverage, optional approval scope
against a supplied git diff, and optional `.ai/framework` drift against an
AlatyrCore source checkout.

It does not install Alatyr Core, inspect project business truth, approve
protected changes, run target validation, or replace assistant logical
integrity review.

Use `--json` or `--output <file>` when a target CI job or assistant recheck
needs machine-readable findings. The JSON output contains severity counts,
exit status, and stable finding objects with `level`, `code`, `message`, and
optional `path`.

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

`prepare_conformance_run.py` creates seed-only fixture repositories, per-fixture
assistant prompts, and a reports directory for a selected assistant surface.
It validates the surface against `conformance/runs/assistant-surfaces.json`
unless `--allow-custom-surface` is provided. It does not run the assistant or
claim installation success.

`check_conformance_reports.py` validates golden assistant-result report
contracts for each fixture. It checks expected behaviors and required evidence
fields, but it does not run an assistant or validate a real target adapter.
It can also validate captured assistant-run reports when `--actual-dir` points
to a directory of JSON reports. Add `--require-actual-reports` when CI should
fail if the directory has no captured reports, and `--require-all-fixtures`
when a full run should cover every fixture.

`summarize_conformance_reports.py` summarizes captured assistant-run reports by
assistant surface and fixture after validating the report contracts. It is for
comparing reviewed run outputs, adapter evidence status, residual risks, and
unresolved validation, not for running assistants.

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
python3 tools/check_conformance_reports.py
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-actual-reports
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-actual-reports --require-all-fixtures
python3 tools/summarize_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-all-fixtures
python3 tools/run_conformance_scaffold.py
python3 tools/run_conformance_scaffold.py --write-golden-snapshots
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_conformance_fixtures.py
py -3 .\tools\materialize_conformance_fixtures.py --output tmp\conformance-targets
py -3 .\tools\prepare_conformance_run.py --output tmp\conformance-run --assistant-surface codex
py -3 .\tools\check_conformance_reports.py
py -3 .\tools\check_conformance_reports.py --actual-dir conformance\runs\assistant-results
py -3 .\tools\check_conformance_reports.py --actual-dir conformance\runs\assistant-results --require-actual-reports
py -3 .\tools\check_conformance_reports.py --actual-dir conformance\runs\assistant-results --require-actual-reports --require-all-fixtures
py -3 .\tools\summarize_conformance_reports.py --actual-dir conformance\runs\assistant-results --require-all-fixtures
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

Linux or macOS:

```sh
python3 tools/summarize_effectiveness_reports.py --input conformance/golden/effectiveness-sample.json
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\summarize_effectiveness_reports.py --input conformance\golden\effectiveness-sample.json
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
