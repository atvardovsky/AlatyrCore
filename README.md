# Alatyr Core

Alatyr Core is a Markdown-first AI assistant framework for software
repositories.

It gives an assistant a portable way to work on a project without guessing:
load the right context, separate framework rules from project facts, classify
risk, request approval for protected changes, keep documentation synchronized,
and report evidence.

Alatyr Core is not tied to PHP, Symfony, Node, Python, Go, Java, a database,
or a specific assistant vendor.

## Why This Exists

AI agents are good at producing local code changes, but weak at preserving
system-wide consistency unless the repository gives them a process. Alatyr Core
turns AI-assisted work into a controlled change pipeline: context discovery,
risk classification, logical integrity review, blueprint-driven update,
validation, and final evidence.

## If You Are An AI Assistant

If a programmer gives you this repository and asks you to install Alatyr Core
into another project, do this:

1. Read the source bootstrap: this `README.md`, `AGENTS.md`, `INSTALL.md`,
   `framework/README.md`, `framework/context-profiles.md`,
   `framework/context-router.md`,
   `framework/project-adapter-contract.md`, `framework/portability.md`,
   `framework/module-profile.md`, `framework/operation-help.md`,
   `framework/rule-ownership.md`,
   `framework/rule-registry.md`, `framework/rule-registry.json`,
   `installer/assistant-installation.flow.md`,
   `installer/readiness-checklist.md`, and
   `installer/installation-plan-template.md`.
2. Inspect the target repository before creating files.
3. Identify existing AI instructions, project docs, tests, commands, CI,
   diagrams, security policy, generated files, and assistant bridge files.
4. Create an installation plan from
   `installer/installation-plan-template.md`.
5. Separate portable framework core from target project adapter facts.
6. Read each framework file before copying or adapting it into the target
   repository. Full installs that copy the whole core must read
   `framework/*.md` and `framework/rule-registry.json` at that stage.
7. Rewrite target adapter files from the target repository, using
   `templates/target` only as placeholders.
8. Apply the canonical rule references instead of copying policy text:
   `ALATYR-ADAPTER-001`, `ALATYR-APPROVAL-001`,
   `ALATYR-SAFETY-001`, `ALATYR-SAFETY-002`,
   `ALATYR-INTEGRITY-001`, `ALATYR-OPERATION-001`, and
   `ALATYR-EVIDENCE-001`.
9. Run only target validation that exists in the target repository. If a check
   is unknown or unavailable, report it as unresolved instead of inventing a
   command.

For details, use [INSTALL.md](INSTALL.md). For a copyable installation prompt,
use
[installer/assistant-request-template.md](installer/assistant-request-template.md).
For post-install work in a target repository that already has Alatyr Core, use
[installer/installed-operation-request-template.md](installer/installed-operation-request-template.md).

## Repository Layout

- `framework/`: portable Alatyr Core framework documents. These are the core
  files an assistant adapts into a target `.ai/framework` directory.
- `installer/`: assistant-readable installation flow, readiness checklist,
  installation plan template, assistant request template, and installed
  operation request template.
- `templates/target/`: starter files for a target repository adapter. These
  files contain placeholders and must be rewritten from target facts.
- `docs/`: public explanation for maintainers and assistant compatibility.
- `conformance/`: fixture descriptions and golden expectations for future
  conformance checks.
- `tools/`: source-repository maintenance checks and optional scaffolding
  helpers for Alatyr Core itself.
- `AGENTS.md`: canonical instructions for assistants working on Alatyr Core
  itself.
- `AI_ASSISTANTS.md`: generic assistant entry point.

## Self-Application Notes

Alatyr Core can be used to review this source repository, but generated target
adapter output from that exercise is scratch material.

Use ignored local paths such as `tmp/` or root-local assistant adapter paths
when drafting self-installation plans, trial `.ai` trees, or bridge files.
Promote reusable findings by editing the canonical source files under
`framework/`, `installer/`, `templates/target/`, `docs/`, or the root docs
instead of committing generated self-installation output.

For Alatyr Core source-repository maintenance, run
`python3 tools/check_all.py` when available, or
`python3 tools/check_framework_consistency.py` for the core consistency check.
These helpers are not portable validation requirements for target projects.

Additional source-repository helpers include:

- `python3 tools/alatyr.py --help`
- `python3 tools/alatyr.py doctor --target <target-repo>`
- `python3 tools/check_all.py`
- `python3 tools/check_framework_metadata.py`
- `python3 tools/check_approval_template.py`
- `python3 tools/check_ai_infrastructure_inventory.py`
- `python3 tools/check_ai_infrastructure_recommendations.py`
- `python3 tools/check_ai_infrastructure_router.py`
- `python3 tools/check_assistant_surface_conformance.py`
- `python3 tools/check_bridge_capability_matrix.py`
- `python3 tools/check_context_router.py`
- `python3 tools/check_context_costs.py`
- `python3 tools/check_consistency_map.py`
- `python3 tools/check_cross_platform_tools.py`
- `python3 tools/check_large_task_orchestration.py`
- `python3 tools/check_manifest_contract.py`
- `python3 tools/check_markdown_links.py`
- `python3 tools/check_maturity_profile.py`
- `python3 tools/check_module_profile.py`
- `python3 tools/check_migration_diff_report.py`
- `python3 tools/check_operation_contracts.py`
- `python3 tools/check_operation_catalog.py`
- `python3 tools/check_operation_help.py`
- `python3 tools/check_output_contracts.py`
- `python3 tools/check_release_migration_template.py`
- `python3 tools/check_rule_ownership.py`
- `python3 tools/check_source_of_truth_registry.py`
- `python3 tools/check_target_adapter_validator.py`
- `python3 tools/check_versioning.py`
- `python3 tools/validate_target_adapter.py --target <target-repo>`
- `python3 tools/validate_target_adapter.py --target <target-repo> --json --output <report.json>`
- `python3 tools/report_migration_diff.py --from-rules <old-rule-registry.json>`
- `python3 tools/report_migration_diff.py --from-rules <old-rule-registry.json> --from-framework-dir <old-framework-dir>`
- `python3 tools/alatyr.py assess-upgrade --target <target-repo> --framework-source . --output-dir <assessment-dir>`
- `python3 tools/alatyr.py context-costs`
- `python3 tools/check_bridge_templates.py`
- `python3 tools/render_bridge_templates.py`
- `python3 tools/check_conformance_fixtures.py`
- `python3 tools/materialize_conformance_fixtures.py --output tmp/conformance-targets`
- `python3 tools/prepare_conformance_run.py --output tmp/conformance-run --assistant-surface codex`
- `python3 tools/alatyr.py prepare-conformance --output tmp/conformance-matrix`
- `python3 tools/alatyr.py check-conformance --matrix tmp/conformance-matrix/matrix.json`
- `python3 tools/check_conformance_reports.py`
- `python3 tools/check_conformance_summary.py`
- `python3 tools/alatyr.py prepare-benchmark --plan <benchmark.json> --output tmp/benchmark`
- `python3 tools/alatyr.py check-benchmark --benchmark tmp/benchmark/benchmark.json`
- `python3 tools/alatyr.py summarize-benchmark --benchmark tmp/benchmark/benchmark.json`
- `python3 tools/summarize_conformance_reports.py --actual-dir conformance/runs/assistant-results --require-all-fixtures`
- `python3 tools/run_conformance_scaffold.py`
- `python3 tools/summarize_effectiveness_reports.py --input conformance/golden/effectiveness-sample.json`

## What Alatyr Core Provides

- framework/project/repository-adapter contour separation
- stable rule identifiers for migration and adapter references
- rule category ownership map to keep repeated docs aligned with canonical
  owners
- structured metadata on rule-owner framework docs for deterministic owner,
  dependency, and task-profile checks
- a machine-readable context router template that maps tasks to the smallest
  required startup context, project-area overlays, budgets, and context
  receipts
- a machine-readable operation catalog with one conversational `Alatyr` entry,
  automatic routing, read-only adapter health, and risk-gated pre-change
  preview
- machine-readable rule manifest for deterministic migration checks
- adapter ownership, review cadence, and CODEOWNERS-equivalent guidance
- required core and optional module profile guidance
- adapter output contracts for installation, update, and recheck evidence
- optional safe scaffolding guidance that does not replace installation review
- deterministic `core`, `standard`, and `full` scaffold support profiles that
  reduce unused target-template files without changing the portable framework
  baseline
- optional target adapter validator guidance for installed-adapter structural
  checks
- context discovery and source-of-truth decisions
- context profiles for smaller task-specific reading sets
- compact bootstrap routing that keeps blueprints, registries, module profiles,
  contours, and human profile rationale out of routine startup
- optional large-task orchestration that loads only the active workstream's
  context and preserves resumable checkpoints plus final convergence evidence
- source-of-truth registry guidance and source-template checks for fact
  ownership, derived surfaces, sync direction, validation, and conflict
  resolution
- optional consistency-map guidance and source checks for bounded fact,
  contract, area, system, and adapter impact traversal
- compact AI infrastructure routing that selects one skill, prompt, gate,
  checker, tool/MCP config, bridge, or wrapper plus its permissions, gates,
  validation, and output contract
- evidence-based, read-only AI infrastructure recommendations that compare
  bounded project-contour needs with existing items before proposing additions
  or improvements
- target-owned development-pattern evidence that learns from repeated requests,
  corrections, reviews, rework, validation failures, and context expansion
  without storing raw chat or changing portable framework rules
- durable adaptation records for imported or materially changed assistant
  infrastructure
- task-specific maturity profile guidance and source-template checks for
  supported work, context, validation, approvals, blockers, residual risks,
  and final evidence
- semantic change decision
- first-class logical integrity review
- blueprint-driven product-change workflow
- change-risk classification and approval triggers
- approval-record guidance and source-template checks for protected changes
  that need durable evidence
- machine-readable approval records and strict complete changed-path scope
  enforcement against an explicitly selected Git diff base
- documentation-sync and final-evidence patterns
- stack-aware testing guidance without hard-coded commands
- security/safety reasoning without hard-coded policies
- prompt-injection handling for imported AI infrastructure
- diagram guidance without hard-coded diagram tooling
- AI infrastructure inventory and third-party skill/assistant-infrastructure
  adaptation guidance
- AI infrastructure inventory and recommendation report templates plus
  source-template checks
- task-specific adapter maturity and lifecycle guidance
- bridge capability matrix guidance and source-template checks for supported
  assistant surfaces
- migration diff and effectiveness measurement guidance
- source release/version workflow for framework, adapter schema, and template
  version tracking
- source release migration report template for framework update evidence
- executable migration-diff output validation for adapter contract impact,
  affected categories, task profiles, canonical sources, and action hints
- source-repository migration diff, conformance fixture, scaffold snapshot,
  seed materialization, run preparation, golden report, and captured-run
  summary checks
- isolated staged-adapter Codex conformance with exact CLI token and duration
  evidence, kept outside stable source checks because it incurs model usage
- one Python-based optional tool entry point with PowerShell and Command Prompt
  launchers for Linux, macOS, and Windows
- native GitHub Actions source checks on Linux, macOS, and Windows without paid
  assistant execution
- migration-first target upgrade assessment that writes evidence without
  applying adapter changes
- deterministic context file/word baselines plus captured-run context and
  logical-integrity evidence contracts
- reviewed no/minimal/full effectiveness evidence with exact Codex token and
  duration measurements and an explicit no-broad-cost-claim boundary
- all-surface bridge and conformance-prompt checks for every supported
  assistant ID
- all-surface conformance matrix preparation with run provenance, expected
  report counts, and completeness checks for externally captured evidence
- paired no/minimal/full benchmark preparation that checks project-snapshot
  equivalence, independent review, comparable measurements, and explicit
  relative deltas
- installed-adapter operation and recheck guidance
- compact progressive help and automatic operation routing for clear requests
- bridge-file pattern for modern assistants

## What Alatyr Core Does Not Provide

- project business rules
- project architecture facts
- local commands, scripts, package managers, CI jobs, hooks, or test tools
- project-specific security policy, live-service allowlists, dependency
  scanners, diagram formats, render commands, or lifecycle notes
- a universal installer script

All of those belong to the target project or its repository adapter.

## Installation Summary

Alatyr Core is installed by an assistant, not by a script.

The assistant reads this repository, inspects the target repository, writes an
installation plan, and then creates or updates target files according to the
plan. Fresh installs can usually proceed after the plan when the programmer has
asked for installation and no protected target files or behaviors are changed.
Overwrites and protected changes require explicit programmer approval.

The source repository may provide optional helper tools for maintainers, such
as a dry-run-first scaffolder or an installed-adapter structural validator.
These helpers can copy placeholder structure or check adapter files for
machine-detectable drift, but they do not complete installation, inspect
target business truth, approve overwrites, or replace logical integrity review.

## After Installation

After Alatyr Core is installed in a target repository, programmers can ask an
assistant to use the installed adapter for follow-up operations: creating or
repairing project blueprints, rechecking the adapter after a framework update,
reviewing drift, running blueprint-driven product changes, or adapting skills
and prompts.

Use
[installer/installed-operation-request-template.md](installer/installed-operation-request-template.md)
for a copyable post-install request. This is still assistant reasoning over
Markdown files, not a universal Alatyr command or runtime service. The request
can bound the assistant with `Allowed actions`, such as `read-only`,
`docs-only`, `adapter-only`, `code-and-tests`, or `full-with-approval`.

Send `Alatyr` as the single conversational entry. A complete target adapter
returns current evidence status and no more than three relevant actions. Send
`Alatyr status` or `Alatyr doctor` for a read-only health check. Clear ordinary
requests route automatically without requiring an operation ID; genuine
ambiguity uses compact help. Semantic, protected, cross-boundary, external, or
unclear-scope changes receive a bounded pre-change preview before edits. The
preview is not approval.

To check an installed adapter structurally from this source repository, a
maintainer may run:

```sh
python3 tools/validate_target_adapter.py --target /path/to/target-repo
python3 tools/validate_target_adapter.py --target /path/to/target-repo --json --output tmp/alatyr-adapter-report.json
python3 tools/alatyr.py doctor --target /path/to/target-repo
```

This helper reports adapter health and checks structure, operation catalog,
router/bootstrap references, local path
leakage, stale checker claims, manifest fields, optional consistency and AI
infrastructure route maps, and optional framework baseline drift. It can emit
machine-readable current-state evidence and compare explicitly listed approval
scope or migration-diff evidence when the target provides those inputs. It
does not verify project business facts, prove historical actions, or approve
changes.

For skills, prompts, wrappers, bridge files, rules, MCP/tool configs, gates,
checkers, or other AI infrastructure, a target adapter may define request
aliases such as `alatyr-ai-inventory`, `alatyr-adaptation <source>`, or
`alatyr-add-ai <source>`. For read-only suggestions, adapters may expose
`alatyr-suggest-ai <scope>` and `alatyr-improve-ai <item-id>`. These aliases
are chat/request shortcuts, not shell
commands. Sources can be local paths, Git URLs, HTTPS URLs, assistant-native
references, packages/plugins, or pasted content, but existing infrastructure,
provenance, permissions, safety, and approval are reviewed before anything
becomes canonical.

## Suggested Target Shape

A mature target installation usually has:

- `AGENTS.md`
- `AI_ASSISTANTS.md`
- `CODEOWNERS` or equivalent owner map when the target uses file ownership
- `.ai/alatyr.yaml`
- `.ai/README.md`
- `.ai/framework/*.md`
- `.ai/framework/rule-registry.json`
- `.ai/project/contour.md`
- `.ai/project/source-of-truth-registry.md`
- `.ai/project/development-evidence.json` when pattern-based recommendations are
  enabled
- `.ai/project/context` or equivalent project source-of-truth docs
- `.ai/assistant/contour.md`
- `.ai/assistant/context-router.json`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- `.ai/assistant/maturity-profile.md`
- `.ai/assistant/bridge-capability-matrix.md`
- `.ai/assistant/ai-infrastructure-router.json` when AI infrastructure is used
- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`
- `.ai/assistant/operation-catalog.json`
- `.ai/assistant/flows`
- `.ai/assistant/gates/checklist.md`
- `.ai/assistant/policies/ai-infrastructure-source-access.md` when AI
  infrastructure can be inventoried or adapted
- `.ai/assistant/policies/prompt-injection.md` when third-party or remote AI
  infrastructure can be reviewed or adapted
- `.ai/assistant/approvals/approval-template.md` when protected-change
  approvals need durable evidence
- `.ai/assistant/approvals/approval-record-template.json` when approval scope
  must be enforced against the complete Git change set
- `.ai/assistant/templates/installation-note.md`
- `.ai/assistant/templates/operation-request.md`
- `.ai/assistant/templates/pre-change-preview.md`
- `.ai/assistant/templates/ai-infrastructure-adaptation-record.md` when items
  are imported or materially changed
- `.ai/assistant/templates/large-task-operation-packet.md` when large or
  resumable operations are enabled
- `.ai/assistant/templates/migration-note.md`
- `.ai/assistant/templates/effectiveness-report.md`
- `.ai/assistant/templates/post-install-message.md`
- `.ai/assistant/templates/post-update-message.md`
- optional skills, prompts, bridge files, diagrams, and consistency checks
- `.ai/project/consistency-map.json` when bounded relationship routing is
  enabled

The target adapter decides actual validation commands and supported assistant
bridges.
