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
python3 tools/alatyr.py doctor --target /path/to/target-repo
python3 tools/alatyr.py validate-adapter --target /path/to/target-repo
python3 tools/alatyr.py render-context --target /path/to/target-repo
python3 tools/alatyr.py render-context --target /path/to/target-repo --write
python3 tools/alatyr.py support-diff --target /path/to/target-repo
python3 tools/alatyr.py support-costs
python3 tools/alatyr.py support-costs --target /path/to/target-repo
python3 tools/alatyr.py impact --target /path/to/target-repo --diff-ref HEAD~1
python3 tools/alatyr.py generate-support --target /path/to/target-repo --check
python3 tools/alatyr.py assess-upgrade --target /path/to/target-repo --framework-source . --output-dir tmp/upgrade-assessment
python3 tools/alatyr.py inspect-extension --package /path/to/local-extension-checkout
python3 tools/alatyr.py inspect-extension --package /path/to/local-extension-checkout --target /path/to/target-repo
python3 tools/alatyr.py inspect-dependency-knowledge --source /path/to/local-package-export
python3 tools/alatyr.py clean-artifacts --older-than-days 7
python3 tools/alatyr.py clean-artifacts --older-than-days 7 --apply
```

Windows PowerShell:

```powershell
.\tools\alatyr.ps1 --help
.\tools\alatyr.ps1 doctor --target C:\path\to\target-repo
.\tools\alatyr.ps1 validate-adapter --target C:\path\to\target-repo
.\tools\alatyr.ps1 render-context --target C:\path\to\target-repo
.\tools\alatyr.ps1 render-context --target C:\path\to\target-repo --write
.\tools\alatyr.ps1 support-diff --target C:\path\to\target-repo
.\tools\alatyr.ps1 support-costs
.\tools\alatyr.ps1 support-costs --target C:\path\to\target-repo
.\tools\alatyr.ps1 impact --target C:\path\to\target-repo --diff-ref HEAD~1
.\tools\alatyr.ps1 generate-support --target C:\path\to\target-repo --check
.\tools\alatyr.ps1 assess-upgrade --target C:\path\to\target-repo --framework-source . --output-dir tmp\upgrade-assessment
.\tools\alatyr.ps1 inspect-extension --package C:\path\to\local-extension-checkout
.\tools\alatyr.ps1 inspect-extension --package C:\path\to\local-extension-checkout --target C:\path\to\target-repo
.\tools\alatyr.ps1 inspect-dependency-knowledge --source C:\path\to\local-package-export
.\tools\alatyr.ps1 clean-artifacts --older-than-days 7
```

Windows Command Prompt:

```bat
tools\alatyr.cmd --help
tools\alatyr.cmd doctor --target C:\path\to\target-repo
tools\alatyr.cmd validate-adapter --target C:\path\to\target-repo
tools\alatyr.cmd render-context --target C:\path\to\target-repo
tools\alatyr.cmd render-context --target C:\path\to\target-repo --write
tools\alatyr.cmd support-diff --target C:\path\to\target-repo
tools\alatyr.cmd support-costs
tools\alatyr.cmd support-costs --target C:\path\to\target-repo
tools\alatyr.cmd impact --target C:\path\to\target-repo --diff-ref HEAD~1
tools\alatyr.cmd generate-support --target C:\path\to\target-repo --check
tools\alatyr.cmd inspect-extension --package C:\path\to\local-extension-checkout
tools\alatyr.cmd inspect-extension --package C:\path\to\local-extension-checkout --target C:\path\to\target-repo
tools\alatyr.cmd inspect-dependency-knowledge --source C:\path\to\local-package-export
tools\alatyr.cmd clean-artifacts --older-than-days 7
```

The stable command set is:

- `check-source`: no writes
- `scaffold`: target structure writes only with `--write`
- `render-bootstrap`: target bootstrap regeneration only with `--write`
- `render-context`: installed recursive context-index regeneration only with
  `--write`; check mode is read-only
- `snapshot-support`: check support-state freshness or refresh it with explicit
  `--write`; generate this state after other support derivatives
- `support-diff`: read-only created/modified/removed support-surface report
- `support-costs`: read-only standing support-surface footprint report for a
  scaffold profile or installed target adapter
- `impact`: bounded changed-path/fact traversal through accepted target
  relationships; machine routing does not replace invariant reasoning
- `generate-support`: read-only plan/check by default; guarded apply is limited
  to declared staged deterministic outputs with current authorization and plan
  binding
- `validate-adapter`: optional explicit report output only
- `doctor`: read-only adapter health with at most three repair operation routes;
  no file output (use `validate-adapter` for an explicit report file)
- `migration-report`: optional explicit report output only
- `assess-upgrade`: explicit assessment output only; no adapter changes
- `context-costs`: optional source-template or `--target` installed context-cost
  report output only
- `inspect-extension`: read-only validation and digest calculation for a local
  extension checkout; no network access, execution, or target writes
- `inspect-dependency-knowledge`: read-only structural inspection of one local
  passive dependency export; no recursive discovery, network access,
  execution, package update, or target writes
- `prepare-conformance`: explicit conformance workspace output only; no
  assistant execution
- `check-conformance`: read-only prepared or captured matrix validation
- `prepare-benchmark`: explicit paired benchmark workspace output only; no
  assistant execution
- `check-benchmark`: read-only isolation, report, and review validation
- `summarize-benchmark`: read-only reviewed measurement comparison
- `clean-artifacts`: dry-run report by default; removes old ignored `tmp/`
  entries only with `--apply`

## Source Validation Runner

`check_all.py` loads the schema-version-2 `tools/check_manifest.json` and runs dependency-aware
source validation. The default `full` profile remains the acceptance gate.
`quick` checks routing, bootstrap, scaffold, and standing support-cost
guardrails without running the source unit suite. With `fast --changed-from`,
explicit `trigger_paths` select focused checks while a small invariant set
always runs; unmatched paths retain the conservative full-suite fallback.
`change --changed-from <ref>` uses the same ref as the release-drift baseline
when `--from-ref` is omitted. `release` adds tag-baseline migration checks.
`platform` runs the portable tooling contract slice used on macOS and Windows.
It validates this repository only; it is not a portable framework requirement
for target projects.

Each manifest check declares four separate concerns:

- `contract_inputs`: repository facts, templates, schemas, fixtures, or other
  artifacts whose content the check evaluates.
- `implementation_paths`: the checker command and direct local helper modules
  whose behavior determines the result.
- `trigger_paths`: changed paths that select the check for a focused run. They
  must include every declared contract and implementation path; additional
  broad triggers are allowed only when they make selection safer.
- `depends_on`: prerequisite checks that must pass before the check can run.

The manifest also declares `timeout_seconds` and `resource_class`. The runner
uses resource classes to avoid scheduling several heavy checks into the same
worker capacity and treats a timeout as a failed check; dependent checks are
reported as blocked. Current classes are `light`, `standard`, and `heavy`.
The configured timeout is per process and does not replace CI-level job
timeouts.

The manifest checker also reconciles the dynamically computed captured-evidence
contract with the `evidence-status` routes. Changing an executor contract,
context receipt, benchmark input, or other digest owner therefore selects the
freshness check instead of leaving older evidence apparently current.

Machine-readable reports use schema version 2. Each selected check is emitted
in manifest order with its resource class, timeout, elapsed duration, command,
output, exit status, and timeout state. A report records a blocked check
separately from a failed process so consumers can distinguish root failures
from dependency fallout. Durations are local runner observations, not a
cross-platform performance benchmark.

Machine-readable reports should normally be written outside the repository.
A repository-local `--report` path is accepted only under `tmp/` when Git
confirms that the path is ignored and untracked. Report generation is included
in the runner's final read-only source snapshot.

Install source-check dependencies first:

```sh
python3 -m pip install -r requirements-dev.txt -c constraints-ci.txt
```

Supported source tooling starts at Python 3.10. The machine-readable contract
is `tools/runtime-compatibility.json`. CI resolves `requirements-dev.txt`
through `constraints-ci.txt`; update and validate the complete pinned set as one
dependency change rather than allowing each platform to resolve unrelated
versions.

The workflow at `.github/workflows/cross-platform-source-checks.yml` runs the
full suite on the minimum and current Python versions on Linux and the portable
contract slice on macOS and Windows. Every job writes a machine-readable report
with exact checker output, interpreter, platform, and dependency versions, then
uploads it even when a check fails. It does not run paid assistant conformance
or effectiveness benchmarks.

Linux or macOS:

```sh
python3 tools/check_all.py
python3 tools/check_all.py --profile quick
python3 tools/check_all.py --profile fast --changed-from HEAD
python3 tools/check_all.py --profile change --changed-from HEAD~1
python3 tools/check_all.py --profile release
python3 tools/check_all.py --profile platform
python3 tools/check_all.py --profile full --report /tmp/alatyr-source-checks.json
python3 tools/check_all.py --list
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_all.py
py -3 .\tools\check_all.py --profile quick
py -3 .\tools\check_all.py --profile fast --changed-from HEAD
py -3 .\tools\check_all.py --profile change --changed-from HEAD~1
py -3 .\tools\check_all.py --profile release
py -3 .\tools\check_all.py --profile platform
py -3 .\tools\check_all.py --profile full --report C:\Temp\alatyr-source-checks.json
py -3 .\tools\check_all.py --list
```

## Target Contract Compatibility

`target-adapter-contract-compatibility.json` is the canonical
source-tooling matrix for current, supported, and migration-limited Debug,
engineering-evidence, and project-knowledge record/index versions. The target
validator reads this matrix instead of repeating compatibility mappings across
domain implementations.

Validate the matrix against schemas, target templates, and the generated human
reference with:

```sh
python3 tools/render_target_contract_compatibility.py --check
```

Regenerate `docs/target-adapter-contract-compatibility.md` after a reviewed
matrix change by omitting `--check`. This matrix does not own portable rule
semantics or target-project facts.

## Architecture Knowledge Check

`check_architecture_knowledge.py` validates the portable architecture
knowledge rule and the target architecture index, machine-readable catalog,
architecture-assistance operation, lazy context route, discussion and record
templates, gates, source-of-truth entry, manifest paths, and optional module.
It validates framework and template contracts; it cannot establish whether a
target project's architecture claims are true.

Linux or macOS:

```sh
python3 tools/check_architecture_knowledge.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_architecture_knowledge.py
```

## Approval Template Check

`check_approval_template.py` validates the target
`.ai/assistant/approvals/approval-template.md` and
`.ai/assistant/approvals/approval-record-template.json` templates in this
source repository. It checks approval identity, operation identity, plan and
diff binding, machine-readable allowed and excluded path scope, invalidation,
use result, validation, evidence, and residual risk. It is not a portable
framework requirement for target projects.

The optional target validator can enforce an actual operation diff:

```sh
python3 tools/validate_target_adapter.py --target /path/to/target --diff-ref origin/main --approval-record .ai/assistant/approvals/change.json --enforce-approval-scope
```

Strict mode requires explicit JSON records and checks committed, staged,
unstaged, renamed, deleted, and untracked paths. Without strict mode, legacy
Markdown approval checks remain advisory for compatibility.

Approval schema 2 also records changed-fact IDs, architecture areas, behavior
categories, excluded semantic effects, and permitted external effects for
change-package reconciliation.

Linux or macOS:

```sh
python3 tools/check_approval_template.py
```

## Action Authorization Check

`check_action_authorization.py` validates the portable current-scope phase
rule, target policy, operation request and preview fields, routed gates, final
evidence, and deterministic intent scenarios. It covers subject-only issue or
backlog transitions, implementation, commit, push, continuation, protected
approval, delegation, and live external action boundaries. Structural checks
do not prove that an assistant interpreted a real conversation correctly.

```sh
python3 tools/check_action_authorization.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_approval_template.py
```

## Change Package Check

`check_change_packages.py` validates the optional framework rule, lazy target
overlay, compact index, machine record, redacted report, semantic approval
fields, and explicit target-validator enforcement. It also exercises a real
temporary Git range. Structural validation does not prove domain invariants or
architecture correctness.

```sh
python3 tools/check_change_packages.py
python3 tools/validate_target_adapter.py --target /path/to/target --change-package .ai/assistant/change-packages/change.json --enforce-change-package
```

## Durable Engineering Evidence Check

`check_engineering_evidence.py` validates the required proportional capture
rule, compact target index and record contract, task/revision binding, privacy
and publication boundaries, index synchronization, and captured/skipped/
blocked conformance scenarios. It does not prove an invariant, root cause,
solution, or regression matrix is semantically correct.

```sh
python3 tools/check_engineering_evidence.py
```

## Project Knowledge Check

`check_project_knowledge.py` validates reviewed-discovery and direct decision-
owner guidance intake, kind/origin, canonical-owner and freshness binding,
target-owned narrowing and exceptions, mapped/known-gap/unknown coverage,
subsystem/architecture selectors, bounded two-stage delivery, contradiction
and supersession lineage, paired reuse evidence, and
shared constraints across supported assistant surfaces. It also runs mutation
cases for profile-only selection, stale owners, stale routing policy,
promotion drift, and asymmetric conflicts. It does not decide whether a human
should accept a candidate or whether the accepted project fact is true.

```sh
python3 tools/check_project_knowledge.py
```

## Debug Mode Check

`check_debug_mode.py` validates the optional per-task/session activation,
non-canonical evidence boundary, schema-5 executor/Alatyr-system/automation
roles, target-local actor identity, runtime provenance, correction disposition,
normalized event origins and causal chains, privacy declarations, timing
quality, event-derived supervision metrics,
lifecycle bounds, continuation lineage, typed evidence-event roles, complete
materiality, canonical skip references, claim-validation fidelity, compact
index synchronization, result binding, and clean-upstream projection. It
cannot prove event completeness, semantic attribution, domain claim
correctness, engineering quality, or an actual reduction in human supervision.

```sh
python3 tools/check_debug_mode.py
```

## Code Documentation Check

`check_code_documentation.py` validates the optional portable rule, bounded
target source-set profiles, style-proposal and generator contracts,
source-of-truth boundaries, derived-output policy, lazy routing, adapted skill,
installer wiring, and target validation support. It does not prove that
comments are semantically correct or that generated reference documentation is
complete.

```sh
python3 tools/check_code_documentation.py
```

## Project Vocabulary Check

`check_project_vocabulary.py` validates the optional portable vocabulary rule,
compact target catalog, scoped term records, data-dictionary links, aliases,
acronyms, term states, lazy routing, operation aliases, adapted skill, gates,
manifest paths, bridge coverage, and target-validator support. It checks
structure, not whether a project definition or relationship is true.

```sh
python3 tools/check_project_vocabulary.py
```

## Test-First Development Check

`check_test_first_development.py` validates the optional target-adapted
test-first rule, explicit configuration switch, bounded recommendation gate,
policy schema, RED/GREEN/refactor flow and evidence, operation routing, bridge
coverage, installer wiring, and structural-validation limitations.

```sh
python3 tools/check_test_first_development.py
```

## Extension Checks

`validate_extension_package.py` inspects a local extension package as
untrusted data. It validates `alatyr-extension.json`, declared item paths,
compatibility fields, allowed actions, and the v1 no-hooks/no-transitive-
dependencies boundary, then reports a deterministic package digest. It does
not clone repositories, execute package content, install dependencies, or
write target files.

With `--target`, the command reads the installed target manifest and rule
registry and compares framework, adapter schema, template, and required-rule
compatibility. This remains structural evidence, not semantic or runtime
compatibility proof.

`check_extensions.py` validates the portable extension rule, author template,
target catalog and lock templates, lazy operation route, gates, installer
wiring, bridge coverage, and positive and rejected package fixtures.

Linux or macOS:

```sh
python3 tools/alatyr.py inspect-extension --package /path/to/local-extension-checkout
python3 tools/check_extensions.py
```

Windows PowerShell or Command Prompt:

```powershell
.\tools\alatyr.ps1 inspect-extension --package C:\path\to\local-extension-checkout
py -3 .\tools\check_extensions.py
```

## Dependency Knowledge Checks

`validate_dependency_knowledge_export.py` inspects one local passive package
export without executing package content. It validates manifest identity,
the strict JSON Schema and undeclared-surface boundary, capability declaration,
export-root containment, symlink boundaries,
namespaced fact IDs, typed authority/stability/applicability fields, declared
public dependency references, required prohibitions, and file SHA-256 values.

`check_dependency_knowledge.py` validates the canonical framework rule, export
schema and author template, target projection templates, operation and intent
routing, installation guidance, structural checker, and accepted/rejected
fixtures. These checks do not prove semantic correctness or applicability.
The portable target validator separately checks normalized catalog, lock,
graph, and deviation record shapes and cross-references when the module is
enabled.

```sh
python3 tools/alatyr.py inspect-dependency-knowledge --source /path/to/local-package-export
python3 tools/check_dependency_knowledge.py
```

## Workspace Mode Checks

`check_workspace_modes.py` validates the canonical mode rule, per-mode target
structure, safe no-grants contract, operation and intent routing, and
installation guidance. The portable target validator additionally checks
accepted catalog/descriptor agreement, one active workspace root, inactive
nested adapters, target-relative context, user-owned acceptance, and safe
ambiguity behavior when the optional module is enabled. Structural checks do
not prove that a proposed mode is strategically correct.

```sh
python3 tools/check_workspace_modes.py
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

## AI Infrastructure Recommendation Check

`check_ai_infrastructure_recommendations.py` validates the portable
recommendation policy and target recommendation route, flow, report template,
project/assistant contour boundary, development-pattern index and lazy capture
flow, existing-item-first rule, cost and quality evidence, acceptance criteria,
read-only behavior, aliases, and manifest paths.
It is a source-template check, not a target recommendation engine or permission
to modify AI infrastructure.

Linux or macOS:

```sh
python3 tools/check_ai_infrastructure_recommendations.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_ai_infrastructure_recommendations.py
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
permission model, help, team-operation, and AI-infrastructure alias routing,
known limitations, and conformance checks. It is not a portable framework
requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_bridge_capability_matrix.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_bridge_capability_matrix.py
```

## Assistant Capability And Admission Checks

`check_assistant_capability_contract.py` validates every target surface record
against the schema-2 instruction-loading, skill, client-permission, diagram,
and delegation evidence contract. `check_assistant_surface_audits.py` then
checks all canonical surfaces against source lifecycle, official instruction
paths, precedence risks, static bridge controls, provider-neutral conformance,
and explicit runtime limits. These checks prove source integration readiness,
not that an external client followed Alatyr.

```sh
python3 tools/check_assistant_capability_contract.py
python3 tools/check_assistant_surface_audits.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_assistant_capability_contract.py
py -3 .\tools\check_assistant_surface_audits.py
```

## Discussion Diagram Check

`check_discussion_diagrams.py` validates the portable diagram rule, target
diagram-discussion operation, flow, ASCII grammar and width limits,
presentation template, manifest and module paths, stable lineage,
security/privacy, compact routing and capability projections, operation
conformance fixture, and presentation fields for every supported assistant
surface. It validates declared contracts, not actual external client
rendering.

Linux or macOS:

```sh
python3 tools/check_discussion_diagrams.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_discussion_diagrams.py
```

Prepare the same runtime fixture prompt for every supported assistant surface:

```sh
python3 tools/prepare_diagram_conformance_run.py --output tmp/diagram-conformance
```

Use `--assistant-surface <id>` for one surface. This prepares prompts but does
not run external clients or claim rendering conformance.

`check_diagram_conformance_results.py` validates the separate captured-result
contract. Pass `--results-dir <dir>` for reviewed assistant outputs and
`--require-all-surfaces` only when the run is expected to cover every declared
surface. It checks selected capability evidence, loaded context, pure-ASCII
characters, width, structural connectors, read-only repository behavior, and
residual risk; it does not run a client.

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\prepare_diagram_conformance_run.py --output tmp\diagram-conformance
```

## Context Router Check

`check_context_router.py` validates the target
`.ai/assistant/context-router.json` template in this source repository. It
checks canonical profile names, preloaded versus generated compact bootstrap,
schema-5 lazy profile and overlay descriptors, separated total/portable/target
budgets, cost scenarios, receipt fields, bounded candidates, intent/area
overlays, path references, duplicate route entries, and framework file routing
coverage. It is not a portable framework requirement for target projects.

Linux or macOS:

```sh
python3 tools/check_context_router.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_context_router.py
```

`bootstrap_index.py` builds the deterministic target bootstrap projection from
the adapter manifest, compact project map, and context router.
`render_target_bootstrap_index.py` checks it by default and rewrites it only
with `--write`; use `--stdout` for a non-writing preview.
`check_bootstrap_routing.py` verifies source hashes,
gate-index/profile coverage, budget headroom, and deterministic core scaffold
generation.

```sh
python3 tools/render_target_bootstrap_index.py --target /path/to/target-repo --check
python3 tools/render_target_bootstrap_index.py --target /path/to/target-repo --write
python3 tools/check_bootstrap_routing.py
```

## Operation Catalog Check

`check_operation_catalog.py` validates the target operation catalog, its exact
compact index derivative, bounded router candidates, single `Alatyr` entry,
automatic routing, read-only adapter health, risk-gated preview, and
manifest/help alignment. It checks source templates only.

`render_operation_index.py` checks that the tracked compact index is generated
from the canonical catalog. Use `--write` only after reviewing catalog changes.
`render_assistant_capability_index.py` does the same for separate per-surface
assistant capability records.

Linux or macOS:

```sh
python3 tools/check_operation_catalog.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_operation_catalog.py
```

## Consistency Map Check

`check_consistency_map.py` validates the optional target consistency-map JSON,
portable levels and relationship types, impact policy, human registry linkage,
exact Fact Type/node sync policy, manifest path, semantic routing descriptor,
and placeholder node/edge contract.

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

## Subagent Delegation Check

`check_subagent_delegation.py` validates the optional delegation rule, target
policy, six-role catalog, orchestration prompt, deterministic task plan,
bounded packet, normalized result, unsafe-decomposition fixtures, operation
routing, and per-surface worker/model/native-definition capability fields. It
proves structural coverage, not safe semantic decomposition or actual provider
model availability.

## Team Collaboration Check

`check_team_collaboration.py` validates the optional portable team rule,
target team policy, local identity boundary, lazy active-work overlay,
schema-2 task records, backend contract, coordination flows, records, gate,
adapted skill, operation catalog routes, help aliases, and manifest wiring. It
checks source templates, not current people, task truth, external trackers,
approvals, or business decisions.

Linux or macOS:

```sh
python3 tools/check_team_collaboration.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_team_collaboration.py
```

`check_team_collaboration_scenarios.py` exercises portable target-validator
fixtures for a valid repository-backed team, optimistic-concurrency conflict,
self-review rejection, stale active-work index, unknown local identity, and
stale merge-review evidence.

Linux or macOS:

```sh
python3 tools/check_team_collaboration_scenarios.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_team_collaboration_scenarios.py
```

Linux or macOS:

```sh
python3 tools/check_large_task_orchestration.py
python3 tools/check_subagent_delegation.py
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_large_task_orchestration.py
py -3 .\tools\check_subagent_delegation.py
```

## Scaffold Target Structure

`scaffold_target_structure.py` copies placeholder target templates and
framework files into an existing target directory. It is dry-run by default.
The `full` profile exposes the complete support-template set, while
assistant-native bridge files remain opt-in. Use repeatable
`--assistant-surface <id-or-alias>` selections only for clients the target
actually uses; no native bridge is scaffolded by default. Native bridge
selection currently requires `--profile full` because those compact bridges
route to the complete assistant support layer. Use `core` for required adapter
support surfaces or `standard` for common product and lifecycle operations. By
default, `--framework-pack matched` selects the
`core`, `standard`, or `complete` portable pack that matches the support
profile. Selective packs project their rule registry, ownership map, and file
inventory so omitted optional owners are explicit. The projection layer also
removes path claims for omitted surfaces, filters operation routes to installed
flows, derives the compact operation index and bootstrap index, and accepts
repeatable `--enable-module` capability IDs with dependency closure.

It does not inspect target facts, complete installation, approve overwrites, or
validate an installed adapter.

Generated projections are written as exact UTF-8 bytes with LF endings so
their inventory hashes remain stable across Linux, macOS, and Windows.

Linux or macOS:

```sh
python3 tools/scaffold_target_structure.py --target /path/to/target-repo
python3 tools/scaffold_target_structure.py --target /path/to/target-repo --profile core --write
python3 tools/scaffold_target_structure.py --target /path/to/target-repo --profile core --enable-module ai-infrastructure --write
python3 tools/scaffold_target_structure.py --target /path/to/target-repo --profile core --framework-pack complete --write
python3 tools/scaffold_target_structure.py --target /path/to/target-repo --profile full --assistant-surface claude --assistant-surface zed --write
```

Windows PowerShell:

```powershell
py -3 .\tools\scaffold_target_structure.py --target C:\path\to\target-repo
.\tools\scaffold_target_structure.ps1 --target C:\path\to\target-repo --profile standard
py -3 .\tools\scaffold_target_structure.py --target C:\path\to\target-repo --profile full --assistant-surface github-copilot --write
```

Windows Command Prompt:

```bat
tools\scaffold_target_structure.cmd --target C:\path\to\target-repo
tools\scaffold_target_structure.cmd --target C:\path\to\target-repo --profile full --assistant-surface cursor --write
```

Aliases are resolved through `conformance/runs/assistant-surfaces.json`.
Selection adds source bridge templates only; it does not prove that a target
client loaded them. Installation must still inspect precedence, competing
instruction sources, client version/configuration, and runtime loading
evidence. Use `--overwrite-existing` only after explicit approval for the exact
target path and protected surfaces.

`check_scaffold_profiles.py` verifies profile inheritance, required core
surfaces, full-template coverage, bridge isolation, and profile-to-pack
mapping. `check_framework_packs.py` validates pack inheritance, rule dependency
closure, projected registries, and inventories.

## Target Adapter Validator

`validate_target_adapter.py` validates structural consistency of an installed
Alatyr adapter in a target repository. It checks router/bootstrap references,
exact source-of-truth registry to consistency-map node coverage when that
module is enabled, consistency and AI-infrastructure routing contracts,
project-knowledge policy/index/promotion/shard linkage, owner freshness,
two-stage selectors, contradiction/supersession, and historical-state routing,
unresolved placeholders, hard-coded local paths, stale checker claims, stale
enabled-module status claims on live support surfaces, individual profile and
profile-plus-consistency context budgets, manifest fields,
target-local checker coverage, optional team actor/registry/claim/overlap and
revision-bound merge-readiness structure, optional approval scope against a
supplied git diff, and optional `.ai/framework` drift against an AlatyrCore
source checkout.

When `--diff-ref` and one or more explicit `--approval-record` values are
provided together, changed-file scope enforcement is automatic. The explicit
`--enforce-approval-scope` flag remains available for callers that want a
hard failure when either required input is absent.

An ordinary current-health or doctor run audits records in
`.ai/assistant/approvals` as historical archive evidence, including record
shape, target-relative scope, result declarations, and verifiable plan hashes.
It does not apply those records to the current diff. Only records selected with
`--approval-record` can participate in current-operation scope and patch-hash
validation.

Placeholder scanning always includes neutral `AGENTS.md` and
`AI_ASSISTANTS.md` entry points. Other assistant bridges are omitted only when
the generated capability index maps every owning surface to that bridge, every
owner is represented, every route is explicitly `unsupported`, and none is
selected in the target manifest. Missing, malformed, partial, or unknown
capability evidence remains active fail-safe.

Reusable manifest parsing, Git diff, hashing, and approval-scope primitives
live in `target_validation_support.py`; the validator remains the reporting and
contract orchestration surface.

It does not install Alatyr Core, inspect project business truth, approve
protected changes, run target validation, or replace assistant logical
integrity review.

Use `--json` or `--output <file>` when a target CI job or assistant recheck
needs machine-readable findings. The JSON output contains severity counts,
exit status, and stable finding objects with `level`, `code`, `message`, and
optional `path`.

Framework baseline and migration-evidence drift warnings are blocking by
default because silent success would make an update gate unreliable. Other
warnings remain advisory unless `--strict-warnings` is used. A target can
record an accepted deviation or an explicit severity override when reviewed
local policy permits the drift; hard structural errors cannot be demoted.

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
compatibility, exact registry/map identity findings, consistency and AI-router
routing, generated bridge ownership and fail-safe activation, enabled-module
status drift, approval-archive health, explicit approval-scope matching, broken
team merge-readiness findings, and current-state evidence classification. It
validates AlatyrCore source tooling only.

```sh
python3 tools/check_target_adapter_validator.py
```

```powershell
py -3 .\tools\check_target_adapter_validator.py
```

## Context Cost And Assistant Surface Checks

`report_context_costs.py` resolves target router paths to source templates and
reports declared files plus whitespace word counts for bootstrap, profiles,
intent overlays, consistency routing, migration-first routing, and compact
versus full-reference operation routes. It is a deterministic static estimate,
not model token usage.

```sh
python3 tools/alatyr.py context-costs
python3 tools/report_context_costs.py --output tmp/context-costs.json
python3 tools/check_context_costs.py
```

`report_support_costs.py` measures standing Alatyr support-surface footprint
for a scaffold profile or installed target adapter. Use it before enabling a
large profile or optional module so the assistant can discuss support cost from
evidence instead of loading broad directories. It reports files, words,
estimated tokens at four characters per token, largest groups, optional module
costs, projected operation count, and assistant-surface duplication signals.
It does not replace logical integrity review or prove model billing.

```sh
python3 tools/alatyr.py support-costs
python3 tools/alatyr.py support-costs --profile standard --format text
python3 tools/alatyr.py support-costs --target /path/to/target-repo --format text
python3 tools/check_support_costs.py
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
targets, flow references, sequential installed-operation steps, and the
`adapter-only` project-process evidence boundary across framework, installer,
and target request surfaces. It is not a portable framework requirement for
target projects.

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
release-process documentation for this repository. In tag-triggered GitHub CI
it also requires `GITHUB_REF_NAME` to equal `v<VERSION>`; maintainers can supply
the same name assertion locally with `--expected-release-tag`. Use
`--require-current-tag` only on the release commit to require that `v<VERSION>`
exists and points to `HEAD`; pre-tag release-candidate checks intentionally do
not claim publication. It is not a portable framework requirement for target
projects.

Linux or macOS:

```sh
python3 tools/check_versioning.py
python3 tools/check_versioning.py --expected-release-tag "v$(cat VERSION)"
python3 tools/check_versioning.py --require-current-tag
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\check_versioning.py
py -3 .\tools\check_versioning.py --expected-release-tag "v$(Get-Content VERSION)"
py -3 .\tools\check_versioning.py --require-current-tag
```

## Release Migration Report Check

`check_release_migration_template.py` validates the source release migration
report template and checks that `report_migration_diff.py` emits the same
evidence shape. It is not a portable framework requirement for target
projects.

`check_release_drift.py` compares framework, shipped schema, and target-template
changes with the latest reachable release tag. It requires the corresponding
source version files to advance, runs the migration reporter against the
materialized tag baseline, and verifies the committed report's exact baseline,
three versions, and contract-tree SHA-256 values. Use `--from-ref` for an
explicit baseline or `--report-output` to write generated evidence for review.
The check requires Git tags to be available in CI.

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
framework files, shipped schema contracts, target templates, and migration
action hints.

Use `--from-source-label` and `--to-source-label` for committed evidence so
the report records stable provenance such as a tag or `source-tree` instead of
temporary or workstation-local paths. Labels affect presentation only; the
explicit directory arguments still own the compared bytes.

Linux or macOS:

```sh
python3 tools/report_migration_diff.py --from-rules old-rule-registry.json
python3 tools/report_migration_diff.py --from-rules old-rule-registry.json --from-framework-dir /path/to/old/.ai/framework
python3 tools/report_migration_diff.py --from-rules old-rule-registry.json --from-schema-dir /path/to/old/schemas
python3 tools/report_migration_diff.py --from-rules old-rule-registry.json --from-template-dir /path/to/old/templates/target
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\report_migration_diff.py --from-rules old-rule-registry.json
py -3 .\tools\report_migration_diff.py --from-rules old-rule-registry.json --from-framework-dir C:\path\to\old\.ai\framework
py -3 .\tools\report_migration_diff.py --from-rules old-rule-registry.json --from-schema-dir C:\path\to\old\schemas
py -3 .\tools\report_migration_diff.py --from-rules old-rule-registry.json --from-template-dir C:\path\to\old\templates\target
```

`plan_target_upgrade.py`, also available as `alatyr.py assess-upgrade`, creates
`migration-report.md`, `upgrade-impact.json`, `adapter-validation.json`, and
`upgrade-assessment.md` in an explicit output directory. The machine-readable
impact file is the first upgrade-routing input and records evidence hashes,
installed pack/modules, affected owners, changed installed framework/template
surfaces, removals to review, and the full-corpus expansion trigger.
The helper compares the
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
It also validates every committed run registered under
`conformance/runs/assistant-results/index.json`. Use `--actual-root` for another
indexed run root. Use `--actual-dir` for one run directory, add
`--require-actual-reports` when it must contain reports, and add
`--require-all-fixtures` when that individual run should cover every fixture.

`summarize_conformance_reports.py` summarizes captured assistant-run reports by
assistant surface and fixture after validating the report contracts. It is for
comparing reviewed run outputs, context cost, logical-integrity evidence,
adapter evidence status, residual risks, and unresolved validation, not for
running assistants.

`render_evidence_status.py` derives `conformance/evidence-status.json` from the
declared assistant surfaces, captured run index, effectiveness suite, and
captured benchmark results. It binds current evidence to a deterministic digest
of assistant-facing framework, installer, template, schema, fixture, prompt,
preparation, execution, and validation contracts. A run from the same framework
version becomes historical when that contract digest changes.
Historical digests read the referenced Git tree and blob objects directly, so
current checkout attributes and line-ending policy cannot rewrite the identity
of earlier evidence.

Individual benchmark results must keep `broad_cost_claim_supported` false. A
reviewed result may set `aggregate_coverage_eligible` true only when all modes
are accepted, required quality metrics are comparable and non-regressing, and
the task class and repetition are explicit. Broad effectiveness coverage then
requires every suite task class, the recommended unique repetitions,
current-contract evidence, and an executed suite state.

```sh
python3 tools/render_evidence_status.py
python3 tools/render_evidence_status.py --check
```

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
python3 tools/check_conformance_reports.py --actual-root conformance/runs/assistant-results
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results/<run-id> --require-actual-reports
python3 tools/check_conformance_reports.py --actual-dir conformance/runs/assistant-results/<complete-run-id> --require-actual-reports --require-all-fixtures
python3 tools/summarize_conformance_reports.py --actual-root conformance/runs/assistant-results
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
py -3 .\tools\check_conformance_reports.py --actual-root conformance\runs\assistant-results
py -3 .\tools\check_conformance_reports.py --actual-dir conformance\runs\assistant-results\RUN_ID --require-actual-reports
py -3 .\tools\check_conformance_reports.py --actual-dir conformance\runs\assistant-results\COMPLETE_RUN_ID --require-actual-reports --require-all-fixtures
py -3 .\tools\summarize_conformance_reports.py --actual-root conformance\runs\assistant-results
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

Schema-3 benchmark reports can also qualify human active attention, review
cycles, intervention classes, and observed-only executor active time with
explicit evidence states. The source checker validates delayed-outcome and
adapter-maintenance record templates, but those records still need target or
external evidence and do not establish productivity ratios by themselves.

For controlled comparisons, `prepare_effectiveness_benchmark.py`, also
available as `alatyr.py prepare-benchmark`, copies user-supplied `none`,
`minimal`, and `full` snapshots into isolated workspaces. It rejects project
content drift outside declared adapter surfaces and writes
`prepared-not-executed` run prompts. Every task must select a `class_id` from
`conformance/benchmarks/benchmark-task-suite.json`; its `task_profile` must
match that declared class.

`check_effectiveness_benchmark.py` validates prepared isolation and, with
`--require-reports --require-reviewed`, requires every paired run plus
independent acceptance-criteria review. Reviewed paired results also reject a
cost or speed interpretation when
acceptance outcomes, hallucinated commands, validation errors, missed
companion updates, rework, or unresolved consistency gaps regress.
`summarize_effectiveness_benchmark.py`
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
boundary. Aggregate eligibility additionally requires a declared task class,
repetition, accepted modes, and non-regressing quality metrics. Complete
temporary targets and raw logs remain outside the source repository.

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

## Target Validator Findings

`render_target_validator_findings.py` derives the target validator's stable
finding-code catalog, family summary, and human reference directly from
validator source. This keeps integrations from maintaining a second manual
code list and makes growth visible without renaming stable codes. Use `--check`
in validation and run without it only when validator diagnostics change.

```sh
python3 tools/render_target_validator_findings.py --check
```
