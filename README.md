# AlatyrCore

**Your project should remember why it was built this way.**

AlatyrCore is a vendor-neutral project guardian for software teams and AI
coding agents. It keeps project knowledge, architectural intent, decision
boundaries, and validation guidance with the repository so they can survive
changes in people, tools, agents, and time.

- Persistent project memory owned by the project
- Architectural continuity without treating code as the whole design record
- Conversational project reference for developers and maintainers
- Onboarding support designed to reduce project discovery time
- Safer AI-assisted change through project-specific boundaries and validation
- Interchangeable assistant support without vendor-owned project memory

Other systems add AI to a project. AlatyrCore gives the project memory, a
voice, and continuity.

## What AlatyrCore Is

AlatyrCore is not another coding agent. It is a repository-owned framework and
project adapter that gives compatible AI assistants a shared way to discover
what the project knows, distinguish evidence from decisions, route questions,
and prepare changes with the right context, approvals, validation, and final
evidence.

The project remains the owner. AI assistants are replaceable execution and
interaction surfaces over project-owned sources of truth. The canonical
boundaries for this model are the
[project adapter contract](framework/project-adapter-contract.md),
[source-of-truth registry](framework/source-of-truth-registry.md), and
[framework guarantees and limits](framework/guarantees.md).

The same project memory is intended to support onboarding, daily reference,
architecture discussion, implementation planning, validation, review, and
knowledge transfer. Developers can ask how the project works, why a decision
was recorded, and what a safe change requires without learning AlatyrCore's
internal rule structure first.

## The Problem It Solves

Project knowledge is usually fragmented across code, architecture decisions,
runbooks, tests, CI, diagrams, review history, and the memories of individual
people. AI coding agents can produce useful local changes, but they do not
automatically preserve the intent and constraints distributed across those
surfaces.

AlatyrCore is designed to give each supported assistant the same project-owned
starting point. It routes a request to the smallest relevant context, identifies
fact owners, separates observed implementation from accepted intent, and
requires validation and residual-risk evidence before consistency is claimed.
The canonical process is defined by
[context profiles](framework/context-profiles.md),
[architecture knowledge](framework/architecture-knowledge.md), and
[logical integrity](framework/logical-integrity.md).

## See It In Action

The following conversations are illustrative. Angle-bracketed sources describe
target-project evidence; they are not paths or facts from this repository.

```text
Developer:
Why can the billing module not write directly to the order database?

Alatyr:
The accepted ownership rule assigns order lifecycle state to the Order Service.
Direct writes are restricted because they bypass validation and event
publication.

Sources:
- <canonical architecture source>
- <relevant ownership or decision record>
```

```text
Developer:
Add retry handling to payment processing.

Alatyr:
This change may affect the payment state invariant, idempotency contract,
failure classification, observability requirements, and related tests.

Before implementation, I need to inspect:
- <relevant source>
- <relevant contract>
- <relevant validation>
```

AlatyrCore does not contain those example business rules. An installed project
adapter must resolve answers from that target repository or report that the
required fact is missing. See the
[documentation-only quick demo](docs/human/quick-demo.md).

## Who It Is For

- Developers who need a reliable explanation of an unfamiliar project before
  making a change
- Maintainers who need project decisions, validation, and known gaps to remain
  discoverable
- Architects who want intended architecture distinguished from implementation
  that merely happens to exist
- Teams using one or more AI coding assistants across onboarding, daily work,
  review, and knowledge transfer
- Platform and developer-experience teams that need repository-owned AI
  operating boundaries rather than vendor-specific memory

The intended team outcomes require validation in real projects. AlatyrCore does
not claim to eliminate onboarding time, prevent every AI mistake, or make
project facts correct by itself.

## How It Works

1. The target repository identifies canonical project sources, owners,
   architecture states, validation, and known gaps.
2. A repository-aware project adapter connects those facts to portable
   AlatyrCore rules and supported assistant surfaces.
3. A compact router selects the smallest task and project-area context for a
   question or change.
4. The assistant explains the project or follows the matching project workflow,
   including approvals for protected changes.
5. Deterministic checks validate structural contracts where possible; human and
   assistant reasoning still decide semantic correctness.

Optional target modules can add project-owned vocabulary, code-documentation
profiles, architecture knowledge, team coordination, and test-first
development. Test-first support is explicitly enabled from target evidence and
may be suggested for defects, changed invariants or contracts, and risky
refactoring without being imposed on every code task.

### Core Differentiators

1. **Agent memory belongs to the project.** Knowledge is recorded in
   repository-owned sources rather than entrusted to one agent session or
   vendor.
2. **The framework adapts to the target repository.** AlatyrCore supplies the
   process; each project supplies its own facts, commands, policies, and
   validation.
3. **The assistant performs repository-aware installation.** It inspects the
   target, prepares a plan, and rewrites adapter placeholders from target
   evidence.
4. **Architecture is not inferred solely from code.** Observed implementation,
   proposals, accepted decisions, restrictions, deprecations, contradictions,
   and unknowns remain distinct.
5. **Project knowledge is versioned with the repository.** Sources, adapter
   metadata, decisions, and gaps can evolve through normal repository review.
6. **Humans interact through natural language.** `Alatyr` and related phrases
   are assistant request shortcuts backed by target files, not a universal
   daemon or shell command.
7. **Checks complement reasoning.** Source and optional target validators can
   detect structural drift, but they do not prove business truth or replace
   logical integrity review.

## Agent-Driven Installation

AlatyrCore is installed through assistant reasoning, not blind application of
a universal installer. The assistant reads this repository, inspects the
target repository, creates an installation plan, and adapts only the framework
and project-adapter surfaces the target can support. Existing instructions and
protected changes remain subject to approval.

To our knowledge, AlatyrCore is among the first publicly documented AI
engineering frameworks whose primary installation model is repository-aware
adaptation performed by an AI assistant rather than blind application of a
universal installer.

Start with [INSTALL.md](INSTALL.md). Assistants should also use the
[installation flow](installer/assistant-installation.flow.md) and
[readiness checklist](installer/readiness-checklist.md). Optional scaffolding
creates placeholder structure only; it does not complete installation.

## Start With The Smallest Profile

Do not install every optional capability by default. Establish the required
core profile first, then enable optional modules only when the target needs and
can maintain them. The source scaffolder exposes `core`, `standard`, and `full`
support profiles, but each remains a starting structure that requires target
inspection and adaptation. Matching `core`, `standard`, and `complete`
framework packs can also avoid installing unused optional rule owners. Existing
complete installations stay complete unless a reviewed migration explicitly
changes the pack.

The [module profile](framework/module-profile.md) defines required and optional
capabilities. The [context router](framework/context-router.md) keeps routine
tasks from loading the complete framework or project corpus.

## Current Maturity And Limitations

The source [VERSION](VERSION) currently records `0.1.0-alpha.10`. Implemented
repository assets include portable framework contracts, target templates,
assistant-driven installation guidance, source consistency checks, conformance fixtures,
optional scaffolding, and an optional installed-adapter structural validator.

Important limits:

- There is no complete runnable demonstration target in this repository; the
  current quick demo is a documentation-only walkthrough.
- AlatyrCore is not a hosted service, universal runtime, autonomous coding
  agent, or portable shell command.
- Source checks prove selected repository structures and references, not the
  correctness of target business facts or architecture.
- Static bridge and prompt checks do not prove that every external assistant
  client auto-loads or follows instructions identically.
- Onboarding, quality, rework, and cost benefits require broader validation in
  real teams and projects.
- Optional modules are useful only when a target provides owners, evidence,
  maintenance, and validation.

The authoritative claim boundaries are documented in
[framework guarantees and limits](framework/guarantees.md).

## Documentation

Human-oriented guides:

- [What is AlatyrCore?](docs/human/what-is-alatyr.md)
- [The project guardian concept](docs/human/project-guardian-concept.md)
- [Quick demonstration](docs/human/quick-demo.md)
- [Team use cases](docs/human/team-use-cases.md)
- [Team collaboration workflow](docs/human/team-collaboration-workflow.md)
- [Frequently asked questions](docs/human/faq.md)

Installation and technical reference:

- [Installation guide](INSTALL.md)
- [Assistant entry point](AI_ASSISTANTS.md)
- [Framework index](framework/README.md)
- [Project adapter contract](framework/project-adapter-contract.md)
- [Architecture knowledge](framework/architecture-knowledge.md)
- [Installed operation help](framework/operation-help.md)
- [Repository layout](docs/repository-layout.md)
- [Source tooling reference](tools/README.md)

Human guides explain the product; they do not own framework policy. Canonical
rules remain in the referenced framework documents and
[rule registry](framework/rule-registry.md).

## Contributing

Before changing AlatyrCore, read [AGENTS.md](AGENTS.md) and the
[framework maintenance guide](docs/framework-maintenance.md). Keep portable
framework rules, installation material, target templates, and explanatory docs
separate. Run the documented source checks and report residual risk. A separate
`CONTRIBUTING.md` guide does not currently exist.

## License

AlatyrCore is licensed under the Apache License, Version 2.0.
See [`LICENSE`](LICENSE) for the complete terms.

Unless a file explicitly states otherwise, the license covers this
repository's framework documents, source tools, templates, schemas, and public
documentation. It does not change the ownership or licensing of target-project
source code, architecture, business rules, project-specific documentation, or
project-specific adapter content generated during installation. Those remain
subject to the target repository's ownership and licensing rules.

The Apache License 2.0 covers the AlatyrCore source, framework documents,
templates, and tools. It does not grant rights to use the AlatyrCore name or
visual identity to imply that a derived product is an official AlatyrCore
release.

## Assistant Installation Reference

If a programmer gives you this repository and asks you to install Alatyr Core
into another project, do this:

1. Treat `AGENTS.md` as preloaded and read `installer/context-router.json`.
   Select the current installation stage before loading framework prose.
2. Inspect the target repository before creating files.
3. Identify existing AI instructions, project docs, tests, commands, CI,
   diagrams, security policy, generated files, and assistant bridge files.
4. Create an installation plan from
   `installer/installation-plan-template.md`.
5. Separate portable framework core from target project adapter facts.
6. Use `framework/file-inventory.json` for deterministic copy and hash
   comparison. Read only selected or changed canonical framework owners.
7. Rewrite target adapter files from the target repository, using
   `templates/target` only as placeholders.
8. Apply the canonical rule references instead of copying policy text:
   `ALATYR-ADAPTER-001`, `ALATYR-APPROVAL-001`,
   `ALATYR-SAFETY-001`, `ALATYR-SAFETY-002`,
   `ALATYR-INTEGRITY-001`, `ALATYR-OPERATION-001`,
   `ALATYR-DIAGRAM-001`, `ALATYR-TEAM-001`, and
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
- `templates/extension/`: declarative authoring template for extension
  repositories; package content remains untrusted until target review.
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
- `python3 tools/check_all.py --profile fast`
- `python3 tools/check_all.py --profile full --jobs 4`
- `python3 tools/check_framework_metadata.py`
- `python3 tools/check_approval_template.py`
- `python3 tools/check_change_packages.py`
- `python3 tools/check_test_first_development.py`
- `python3 tools/check_extensions.py`
- `python3 tools/alatyr.py inspect-extension --package <local-checkout>`
- `python3 tools/check_ai_infrastructure_inventory.py`
- `python3 tools/check_ai_infrastructure_recommendations.py`
- `python3 tools/check_ai_infrastructure_router.py`
- `python3 tools/check_assistant_surface_conformance.py`
- `python3 tools/check_bridge_capability_matrix.py`
- `python3 tools/check_discussion_diagrams.py`
- `python3 tools/prepare_diagram_conformance_run.py --check`
- `python3 tools/check_context_router.py`
- `python3 tools/check_context_costs.py`
- `python3 tools/check_framework_packs.py`
- `python3 tools/check_source_context_routing.py`
- `python3 tools/render_framework_file_inventory.py --check`
- `python3 tools/render_rule_registry_docs.py --check`
- `python3 tools/render_target_validator_findings.py --check`
- `python3 tools/render_operation_index.py`
- `python3 tools/render_assistant_capability_index.py`
- `python3 tools/check_diagram_conformance_results.py`
- `python3 tools/check_release_drift.py`
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
- `python3 tools/check_team_collaboration.py`
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
- a compact machine-readable context router index with lazy profile, intent,
  migration, consistency, and task-scale descriptors, project-area overlays,
  budgets, and context receipts
- a machine-readable operation catalog with one conversational `Alatyr` entry,
  automatic routing, read-only adapter health, and risk-gated pre-change
  preview
- machine-readable rule manifest for deterministic migration checks
- adapter ownership, review cadence, and CODEOWNERS-equivalent guidance
- required core and optional module profile guidance
- adapter output contracts for installation, update, and recheck evidence
- optional safe scaffolding guidance that does not replace installation review
- deterministic `core`, `standard`, and `full` scaffold support profiles that
  reduce unused target-template files, paired with dependency-closed `core`,
  `standard`, and `complete` portable framework packs; selective packs project
  registry, ownership, inventory, manifest, and route claims to installed files
- optional target adapter validator guidance for installed-adapter structural
  checks
- context discovery and source-of-truth decisions
- context profiles for smaller task-specific reading sets
- compact bootstrap routing that keeps blueprints, registries, module profiles,
  contours, and human profile rationale out of routine startup
- optional large-task orchestration that loads only the active workstream's
  context and preserves resumable checkpoints plus final convergence evidence
- optional change packages that bind coherent material outcomes to semantic
  approval scope, companion decisions, implementation corrections,
  validation, and reproducible repository provenance
- optional team collaboration with target-owned actors, local user attribution,
  authority, priority, review, and backend policy plus compact active-work
  preflight, conflict-safe per-task records, claims, checkpoints, handoffs,
  decisions, and revision-bound merge-readiness evidence
- source-of-truth registry guidance and source-template checks for fact
  ownership, derived surfaces, sync direction, validation, and conflict
  resolution
- optional consistency-map guidance and source checks for bounded fact,
  contract, area, system, and adapter impact traversal
- optional project-owned architecture knowledge with a compact catalog,
  evidence-backed pattern and area records, discussion and comparison,
  architecture review, documentation maintenance, and accepted-decision
  handoff
- optional project-owned code documentation with bounded frontend, backend,
  shared-library, or infrastructure profiles, evidence-backed comment-style
  proposals, target-specific generators, and derived-output validation
- optional project-owned vocabulary with scoped term definitions, aliases,
  acronyms, ambiguity states, and links to canonical project and data sources
- optional declarative extensions from other repositories with offline package
  inspection, compatibility and permission review, target-owned bindings,
  compact catalog, immutable source and installed-file lock, safe updates, and
  ownership-aware removal
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
- optional structured-comment and generated code-reference synchronization
  without treating generated output as project truth
- stack-aware testing guidance without hard-coded commands
- security/safety reasoning without hard-coded policies
- prompt-injection handling for imported AI infrastructure
- diagram guidance without hard-coded diagram tooling
- optional ASCII-first diagram discussion that works across every assistant
  surface, with recorded native inline or target-rendered views as supplements
- generated assistant-capability index, separate freshness-aware surface
  records, and captured diagram-result conformance contracts
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
- release drift enforcement against an explicit change baseline or the prior
  changelog release tag, with required framework, adapter-schema, and template
  version movement
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
and prompts. When the optional team module is enabled, the same entry point can
report team state, coordinate tasks and claims, detect changed-fact overlap,
capture handoffs and decisions, and perform revision-bound review checks.

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
router/bootstrap references, local path leakage, stale checker claims,
manifest fields, optional consistency and AI infrastructure route maps,
installed extension catalog/lock agreement and file hashes, optional team
registry and merge-readiness state, and optional framework baseline drift. It can emit
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

For reusable bundles, an extension repository may provide
`alatyr-extension.json` plus declarative items under `items/`. Use `Alatyr
inspect extension <source>` in an installed adapter, or inspect an already
available local checkout without network access or execution:

```sh
python3 tools/alatyr.py inspect-extension --package /path/to/local-extension-checkout
```

Inspection does not install or trust the package. Canonical integration is a
separate target operation that resolves source policy, immutable revision and
digest, license, compatibility, bindings, permissions, approval, ownership,
validation, catalog, and lock evidence. Extensions cannot replace framework
core or own target project facts.

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
- `.ai/project/architecture/README.md` and
  `.ai/project/architecture/catalog.json` when architecture knowledge is enabled
- `.ai/project/documentation/README.md`,
  `.ai/project/documentation/catalog.json`, and
  `.ai/project/documentation/profiles.json` when code documentation is enabled
- `.ai/project/vocabulary/README.md`, catalog, scoped term records, and data-
  dictionary links when project vocabulary is enabled
- `.ai/project/team-policy.json` and its human-oriented
  `.ai/project/team-operating-model.md` when team collaboration is enabled
- `.ai/project/context` or equivalent project source-of-truth docs
- `.ai/assistant/contour.md`
- `.ai/assistant/context-router.json`
- `.ai/assistant/context/profiles/*.json`
- `.ai/assistant/context-profiles.md`
- `.ai/assistant/module-profile.md`
- `.ai/assistant/maturity-profile.md`
- `.ai/assistant/bridge-capability-matrix.md`
- `.ai/assistant/assistant-capabilities.json`
- `.ai/assistant/assistant-capabilities/<assistant>.json` when diagrams or
  client-specific presentation behavior is enabled
- `.ai/assistant/templates/ascii-diagram.md` when diagram discussion is enabled
- `.ai/assistant/context/intents/architecture-request.json`,
  `.ai/assistant/flows/architecture-assistance.flow.md`, and architecture
  pattern/area/result templates when architecture knowledge is enabled
- `.ai/assistant/context/intents/code-documentation.json`, the documentation
  flow, profile-review template, and adapted code-documentation skill when the
  optional module is enabled
- `.ai/assistant/context/intents/vocabulary-request.json`, the project-
  vocabulary flow, term-review template, and adapted vocabulary skill when the
  optional module is enabled
- `.ai/assistant/ai-infrastructure-router.json` when AI infrastructure is used
- `.ai/assistant/extensions/catalog.json`, lock, intent, lifecycle flow, gate,
  and evidence templates when extensions are supported
- `.ai/assistant/team/context-overlay.json`, active-work index, registry
  metadata, backend contract, and per-task record template when team
  collaboration is enabled; current actor selection stays ignored under
  `.ai/local/`
- `.ai/assistant/help.md`
- `.ai/assistant/help-reference.md`
- `.ai/assistant/operation-index.json`
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
- `.ai/assistant/change-packages/index.json`, change-package flow, machine
  record, and redacted report templates when coherent material-change evidence
  is enabled
- `.ai/assistant/templates/migration-note.md`
- `.ai/assistant/templates/effectiveness-report.md`
- `.ai/assistant/templates/post-install-message.md`
- `.ai/assistant/templates/post-update-message.md`
- optional skills, prompts, bridge files, diagrams, and consistency checks
- `.ai/project/consistency-map.json` when bounded relationship routing is
  enabled

The target adapter decides actual validation commands and supported assistant
bridges.
