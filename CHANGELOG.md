# Changelog

## Unreleased

- Added a machine-readable target operation catalog and one conversational
  `Alatyr` entry that routes clear requests automatically while keeping the
  full catalog outside routine bootstrap context.
- Added read-only `Alatyr status` and `Alatyr doctor` adapter-health routing
  with current evidence state, actionable finding owners, and at most three
  prioritized repair operations.
- Added risk-gated pre-change preview for semantic, protected, cross-boundary,
  external-effect, or unclear-scope work without treating preview as approval.
- Extended target templates, installer contracts, generated bridges,
  cross-platform tools, scaffold profiles, portable validation, and source
  checks for the operation control surface across every supported assistant.
- Added `ALATYR-OPERATION-001` with `framework/operation-help.md` as its
  canonical owner.
- Clarified that `adapter-only` may update normalized project-process and
  adapter-effectiveness evidence without permitting accepted product,
  business, architecture, data, or runtime fact changes, and added source
  checks for allowed-action drift and installed-operation step sequencing.
- Added an evidence-based `ai-infrastructure-recommendation` operation with
  `alatyr-suggest-ai <scope>` and `alatyr-improve-ai <item-id>` request aliases.
- Added read-only recommendation routing and report contracts for new items and
  improvement, consolidation, replacement, retirement, or retention of
  existing skills, prompts, gates, checkers, flows, tools/MCP configs, bridges,
  wrappers, and templates.
- Required recommendations to use bounded project-contour need and outcome
  evidence while keeping recommendation records and item mechanics in the
  assistant contour.
- Added existing-item-first review, quality/context/maintenance cost evidence,
  acceptance criteria, safe adaptation handoff, all-surface bridge routing, and
  deterministic source checks for recommendation contracts.
- Added a compact target-owned development-pattern index and lazy capture flow
  for recurring requests, corrections, review findings, rework, validation
  failures, and context expansion, with bounded references and retention/privacy
  controls.
- Prohibited target recommendation evidence from directly changing installed
  framework files, AlatyrCore source, or portable rules, and extended the target
  validator to check populated development-pattern contracts.
- Changed the derived commitment for `ALATYR-ADAPTER-001`; no rule ID was added
  or removed.

## 0.1.0-alpha.3 - 2026-07-14

- Increased the framework version to `0.1.0-alpha.3`, adapter schema version
  to `2`, and target template version to `3`.
- Added a canonical machine-readable approval record and strict target-adapter
  validation that binds approval to an explicit Git base and enforces the
  approved scope across committed, staged, unstaged, renamed, deleted, and
  untracked paths.
- Required logical integrity review to re-derive project invariants and
  reconcile related review items by shared facts and contracts instead of
  accepting isolated local fixes as combined evidence.
- Added manual invariant closure when the optional consistency map is disabled
  or incomplete, plus external-boundary evidence for distinguishable failure
  classes when target contracts require it.
- Changed `ALATYR-APPROVAL-001`, `ALATYR-INTEGRITY-001`,
  `ALATYR-RISK-001`, `ALATYR-SOURCE-001`, and `ALATYR-CHANGE-001`; no rule IDs
  were added or removed.
- Updated target manifests, context profiles, source-of-truth registry fields,
  operations, flows, gates, output contracts, installer evidence, scaffold
  profiles, conformance snapshots, and static context-cost baselines.
- Existing adapters must add the JSON approval template and manifest path
  before claiming deterministic approval-scope enforcement. Protected target
  adapter updates still require target-owned approval.

## 0.1.0-alpha.2 - 2026-07-14

- Fixed Windows path separators in framework index checks and protected-file
  scaffold evidence.
- Fixed macOS scaffold snapshots when temporary paths traverse the `/var` to
  `/private/var` filesystem alias.
- Verified the complete 38-check source suite on native Ubuntu, macOS, and
  Windows GitHub-hosted runners.

## 0.1.0-alpha.1 - 2026-07-14

- Released the first tagged AlatyrCore source baseline with framework version
  `0.1.0-alpha.1`, adapter schema version `1`, and template version `2`.
- Added migration evidence from source baseline commit `afbc9e0` and documented
  required review actions for installed target adapters.
- Added deterministic `core`, `standard`, and `full` target scaffold profiles,
  preserving the full portable framework baseline while reducing unused target
  adapter support files.
- Added scaffold-profile contract validation and installation evidence fields
  for the selected profile.
- Added staged-adapter conformance preparation outside the source tree and a
  Codex executor that records fresh-process isolation, exact CLI token usage,
  durations, bridge discovery, and validated fixture reports.
- Captured source-bootstrap and optimized staged-core Codex evidence; the
  comparable backend run reduced loaded words by 79.6% and cumulative input
  tokens by 41.5% while preserving the required conformance behaviors.
- Added an isolated Codex paired-benchmark executor that records exact runtime
  token and duration evidence while preserving independent review as a
  separate required step.
- Captured and independently reviewed a no/minimal/full docs-local benchmark;
  all modes passed, minimal was 24.7% faster with 0.4% more total tokens, and
  full used 67.0% more tokens, so broad cost claims remain unsupported.
- Added native Ubuntu, macOS, and Windows GitHub Actions coverage for the full
  source check suite, including cross-platform tool and scaffold smoke tests.

- Increased `TEMPLATE_VERSION` to 2 for compact migration-first upgrade routing,
  routed-context migration evidence, and updated target operation contracts.

- Reworked target context routing around host-preloaded instructions, a
  compact schema-v2 bootstrap, explicit file/word budgets, project-area
  overlays, and context receipts for measured expansion.
- Added optional large-task orchestration with a task-scale router overlay,
  bounded workstreams, resumable operation packets, checkpoints, and global
  logical-integrity convergence evidence.
- Added an optional multi-level consistency map that routes changed fact IDs
  through applicable contract, area, system, evidence, and
  assistant-governance relationships to build a bounded impact closure.
- Added compact AI infrastructure routing for skills, prompts, gates, checkers,
  tools/MCP configs, bridges, and wrappers, plus durable adaptation records for
  provenance, permissions, rejected source instructions, validation, and
  output contracts.
- Hardened the portable target adapter validator with consistency-map and AI
  infrastructure router checks, schema-1 router compatibility, explicit
  approval-scope matching, plan and diff evidence binding, and current-state
  versus historical evidence classification.
- Added a cross-platform optional tool entry point and a read-only target
  upgrade assessment that composes migration diff and structural validation
  before any target adapter changes.
- Added deterministic bootstrap/profile context-cost baselines, expanded
  effectiveness and assistant-run logical-integrity evidence, and all-surface
  compact bridge conformance checks.
- Added cross-platform all-surface conformance matrix preparation, per-run
  provenance, and completeness validation for externally captured reports.
- Added isolated no/minimal/full effectiveness benchmark preparation with
  project-drift rejection, independent review gates, and conservative relative
  cost and quality summaries.

- Initial Alatyr Core standalone framework repository.
- Added portable framework docs, assistant installation flow, readiness
  checklist, installation plan template, and target adapter templates.
- Added first-class logical integrity, blueprint-driven change, and skill
  adaptation framework guidance with matching target adapter flow templates.
- Added an AlatyrCore source-repository consistency checker under `tools/`.
- Added a human-facing README rationale, canonical logical integrity target
  flow naming, and an adapted-skill placeholder template.
- Added installed-operation guidance, post-install request template, and target
  flows for blueprint creation and adapter rechecks.
- Added operation help, ambiguous-request routing, and post-install/update
  assistant chat-message templates for installed adapters.
- Documented `alatyr-adaptation <source>` as an optional installed adapter
  alias for AI infrastructure adaptation from local, Git, HTTPS, native,
  package/plugin, or pasted sources.
- Added AI infrastructure inventory guidance and target flow with
  `alatyr-ai-inventory` and `alatyr-add-ai <source>` request aliases.
- Added supported-assistant bridge routing for Alatyr help and AI
  infrastructure aliases across generic, AGENTS/Codex, Claude, Gemini, GitHub
  Copilot, Cursor, Devin/Cascade, and Windsurf surfaces.
- Reworked target Alatyr help from a table into operation blocks, added
  operation type aliases, and added Allowed actions to installed operation
  request templates.
- Added allowed-action surface mapping and an AI infrastructure source-access
  policy target template for installed adapters.
- Added session bootstrap guidance so root entry points, bridge files, and
  post-install/update messages route future assistants back to the installed
  adapter.
- Documented self-application reviews and ignored root-local trial adapter
  artifacts for this source repository.
- Added framework, adapter schema, and template version files plus a target
  `.ai/alatyr.yaml` manifest template.
- Added context-profile guidance and target context profiles to reduce
  mandatory context loading for installed adapters.
- Added a target context router JSON template and source checks so assistants
  can select task context from a machine-readable profile map.
- Added approval-record and prompt-injection framework guidance with matching
  target templates and installed-operation routing.
- Split target help into short default help and full help reference, and
  extended the source-repository checker for manifest, profile, approval, and
  prompt-injection contracts.
- Added source-of-truth registry guidance, task-specific maturity profile,
  bridge capability matrix, and migration-note templates for installed
  adapters.
- Clarified framework guarantees as process commitments with machine-checkable,
  target-dependent, and non-guarantee boundaries.
- Added canonical rule IDs, scaffolding boundaries, migration diff guidance,
  effectiveness metrics, source conformance fixtures, and a dry-run-first
  scaffolder helper for placeholder target structure.
- Added Windows Command Prompt and PowerShell wrappers plus cross-platform
  usage docs for the scaffolder helper.
- Added a machine-readable rule registry, migration diff reporter, conformance
  fixture expectations, and a conformance metadata checker.
- Added required-core and optional-module profile guidance with a target module
  profile template and manifest wiring.
- Extended migration diff reporting to include optional framework file-list
  and content-hash comparison.
- Added a source bridge-template conformance checker for supported assistant
  surfaces.
- Added machine-readable conformance fixture manifests for target repository
  shapes and missing adapter surfaces.
- Added a bridge template manifest and source renderer with check mode for
  generated bridge-template drift.
- Added an effectiveness report summarizer and generic source sample data for
  pilot metric checks.
- Added generated fixture scaffold conformance checks for source templates and
  scaffolder behavior.
- Added golden assistant-result report contracts and a source checker for
  fixture evidence, expected behaviors, and forbidden claims.
- Added a target CODEOWNERS placeholder plus adapter owner and review-cadence
  wiring in manifests, lifecycle guidance, and installation evidence.
- Added golden scaffolded-adapter snapshots and snapshot drift checking to the
  source conformance scaffold runner.
- Added an assistant-run conformance report template and opt-in actual-report
  validation for captured fixture runs.
- Added a seed-only conformance fixture materializer for real assistant-run
  starting repositories.
- Added a conformance run preparer that generates fixture targets, per-fixture
  assistant prompts, and report directories for selected assistant surfaces.
- Added a machine-readable conformance assistant surface list and validation
  in the conformance run preparer.
- Added full-fixture coverage enforcement for captured assistant-run
  conformance reports.
- Added a captured conformance report summarizer for assistant-surface and
  fixture coverage comparison.
- Added a source Markdown link checker for deterministic local documentation
  reference validation.
- Added a source operation contract checker for installed-operation aliases
  and flow references.
- Added a source manifest contract checker for the target `.ai/alatyr.yaml`
  template.
- Added a rule ownership map and source checker to keep rule categories,
  canonical owners, and derived documentation aligned.
- Added structured `alatyr_doc` metadata on framework rule-owner documents and
  a source checker for owned rules, dependencies, and task-profile scope.
- Added source release-process documentation and a versioning checker for
  framework, adapter schema, template, and changelog structure.
- Added a source release migration report template and aligned migration-diff
  output with rule-owner, framework-file, and target-template evidence.
- Replaced full-corpus source bootstrap lists with source task-profile routing
  and checker guards against mandatory full-framework reads.
- Added rule-reference blocks and checker coverage so derived docs route
  repeated policy through canonical Alatyr rule IDs.
- Added baseline source-of-truth registry entries and a source checker for
  owner, derived-surface, sync, validation, conflict, approval, and evidence
  fields.
- Added baseline task-specific maturity entries and a source checker for
  supported work, context, owners, validation, approval, blockers, residual
  risks, and final evidence fields.
- Added baseline bridge capability matrix entries and a source checker for
  supported assistant surfaces, bridge paths, loading behavior, permission
  model, alias routing, limitations, and conformance fields.
- Added approval-record template enforcement for approval source, protected
  scope, plan hash, invalidation, use result, evidence, validation, and
  residual risk fields.
- Added adapter output-contract templates plus source checkers for output
  contracts, module profiles, operation help shape, and AI infrastructure
  inventory evidence.
- Extended migration-diff reports with adapter contract impact, affected rule
  categories, task profiles, canonical sources, action hints, and executable
  output-shape validation.
- Extended conformance and effectiveness evidence with operation help status,
  adapter output contract status, AI infrastructure inventory status, task
  profile, operation id, context volume, command hallucination, and protected
  change metrics.
- Tightened target adapter routing and recheck templates so installed
  adapters preserve context-router bootstrap, report adapter drift checks, and
  record local path leakage plus target-local checker status.
- Added an optional target adapter validator helper with Linux, macOS, and
  Windows entry points for installed-adapter structural drift checks.
- Added a source `check_all.py` validation runner for Linux, macOS, and
  Windows-compatible source checks.
- Extended the optional target adapter validator with JSON output, optional
  validator config, approval plan/patch hash evidence checks, and migration
  diff impact evidence.
- Extended real assistant-run conformance report templates with bridge
  behavior evidence for entry files, auto-load observations, help discovery,
  context-router discovery, and assistant-surface limitations.
