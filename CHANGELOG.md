# Changelog

## Unreleased

- No unreleased changes.

## 0.1.0-alpha.26 - 2026-08-24

- Increased the framework version to `0.1.0-alpha.26`; adapter schema and
  target template versions remain `24` because no installed-adapter or target
  template contract changed.
- Bound assistant conformance and effectiveness status to a deterministic
  evidence-contract digest so same-version source changes cannot retain stale
  current-evidence status.
- Replaced the unreachable per-result broad-cost condition with validated
  aggregate coverage eligibility while preserving narrow claims for every
  individual benchmark result.
- Hardened source-check report outputs so repository-local reports must be
  ignored and untracked and report generation remains inside the final
  read-only source snapshot.
- Added focused evidence, aggregation, digest, and report-path regression tests
  and synchronized reproducible dependency and evidence documentation. No
  framework rule IDs, adapter schema contracts, or target template contracts
  changed.

## 0.1.0-alpha.25 - 2026-08-24

- Increased the framework version to `0.1.0-alpha.25` and adapter schema
  version to `24`; target template version remains `24` because no target
  template shape changed.
- Enforced read-only source-check write scopes with deterministic tracked and
  non-ignored source snapshots, and added machine-readable run reports with
  exact checker, platform, interpreter, and dependency evidence.
- Rejected target-relative traversal and symlink resolution outside the target
  root while preserving explicitly selected external migration-report inputs.
- Expanded deterministic lifecycle conformance across accepted `core`,
  `standard`, and `full` support profiles, including approval scope, blocking
  drift, synthetic update, and post-update validation.
- Tightened Debug schema versions 1 and 2 so they cannot carry the version-3
  continuation contract, with focused compatibility and rejection coverage.
- Added an exact current-release tag binding gate and separated pre-tag release
  candidate consistency from actual `v<VERSION>` publication evidence.
- Added generated real-run evidence status so historical Codex runs, prepared
  assistant surfaces, and incomplete effectiveness benchmarks cannot be
  represented as current cross-assistant or broad cost proof.
- Pinned CI dependencies and GitHub Actions revisions, added Python 3.10 and
  3.13 Linux coverage, retained cross-platform diagnostic artifacts, and added
  Dependabot, contribution, and security guidance.
- Added focused source-state, target-containment, and release-binding unit
  tests, and portable provenance labels for committed migration evidence. No
  framework rule IDs or target template contracts changed.

## 0.1.0-alpha.24 - 2026-08-23

- Increased the framework version to `0.1.0-alpha.24`, adapter schema version
  to `23`, and target template version to `24` for Debug lifecycle,
  materiality, and validation-claim integrity.
- Added Debug session schema version 3. Completed records are immutable,
  concrete event timestamps must remain inside lifecycle and causal order, and
  related later work starts a newly activated record with one closed
  predecessor.
- Replaced parallel evidence trigger IDs and labels with typed supporting-event
  links plus an exhaustive materiality evaluation that keeps implementation
  and validation support separate from durable-capture reasons.
- Required skipped material evidence to resolve every applicable conclusion to
  an existing canonical source registered for the named project fact type;
  unknown materiality now prevents skipping.
- Added exact-reproducer, representative, partial, unavailable, and not-
  applicable claim-validation fidelity. Partial or unavailable completed
  results must retain residual uncertainty.
- Preserved schema-version-1 and version-2 records as migration-limited
  historical evidence instead of silently inventing continuation, materiality,
  or claim-fidelity facts.
- Added generic field regression coverage for independent dependency findings,
  compatibility/public-contract reasoning, broad validation, unresolved
  authority, zero human intervention, and mandatory durable evidence capture.
- Updated installation, adapter recheck, lifecycle, context routing, target
  templates, validator findings, and compact index projections for deterministic
  upgrades from any target branch.
- Changed `ALATYR-DEBUG-001`, `ALATYR-ENGINEERING-EVIDENCE-001`, and
  `ALATYR-LIFECYCLE-001`; no rule IDs were added or removed.

## 0.1.0-alpha.23 - 2026-08-23

- Increased the framework version to `0.1.0-alpha.23`, adapter schema version
  to `22`, and target template version to `23` for versioned Debug attribution,
  deterministic evidence closure, and repository-binding lifecycle checks.
- Added Debug session schema version 2 with separate actor, causal class,
  intervention kind, contribution kind, and category fields. Initial task scope
  is not an intervention; validation requests and generic external input are
  no longer counted as implementation or maintainer corrections.
- Required completed version-2 Debug sessions to close a durable Engineering
  Evidence decision and account for material rejected hypotheses, corrections,
  and direction changes through capture, blocking, or canonical preservation.
- Added version-2 Debug and Engineering Evidence bindings with provisional/final
  state, immutable Git object checks, commit ancestry, true tree-object support,
  and explicit `prior_bindings` lineage.
- Preserved schema-version-1 records as legacy evidence without inventing new
  attribution. Later worktree changes now produce historical-snapshot warnings
  instead of retroactively invalidating finalized evidence.
- Added contract versions and schema-3 compact index projections so installed
  validation detects stale authoring templates, binding state, attribution
  model, and Debug evidence-decision drift.
- Extended change-package provenance with Git-range ancestry checks and the
  same non-corrupting treatment of finalized historical snapshots.
- Routed installed-validator findings back into upgrade impact context, kept
  update evidence branch-specific, and added deterministic regression coverage
  for tree bindings, reversed ranges, legacy compatibility, attribution
  boundaries, evidence closure, historical drift, and selective scaffolding.
- Changed `ALATYR-DEBUG-001`, `ALATYR-ENGINEERING-EVIDENCE-001`, and
  `ALATYR-LIFECYCLE-001`; no rule IDs were added or removed.

## 0.1.0-alpha.22 - 2026-08-23

- Increased the framework version to `0.1.0-alpha.22`, adapter schema version
  to `21`, and target template version to `22` for portable worker
  orchestration across supported assistant surfaces.
- Replaced the delegation policy's embedded example role/model binding with a
  target-owned six-role catalog and reusable project prompts for exploration,
  bounded implementation, test execution, documentation, review, and fast
  focused work.
- Added deterministic worker task readiness, dependency and write-conflict
  review, bounded packet identity, normalized result evidence, scoped retries,
  stale-baseline handling, and primary-owned convergence contracts.
- Expanded every assistant capability record with exact client/runtime,
  explicit/automatic invocation, native worker-definition format and paths,
  tool restrictions, write isolation, background/nested behavior, and per-role
  model binding evidence.
- Kept provider-native worker definitions target-generated and thin. Install
  or update creates them only after current evidence verifies support in the
  exact client; unsupported surfaces use suggestion-only or sequential-primary
  fallback.
- Extended source and installed-target validation with role/catalog closure,
  unsafe native path checks, unsupported invocation/model checks, shared-write
  warnings, and five deterministic delegation conformance scenarios.
- Updated installation, update, lifecycle, bridge, capability, module, and
  assistant documentation so all supported agents route through the same
  portable worker contracts without claiming runtime parity.
- Changed `ALATYR-ADAPTER-001`, `ALATYR-BRIDGE-001`,
  `ALATYR-DELEGATION-001`, `ALATYR-LIFECYCLE-001`, and
  `ALATYR-MODULE-001`; no rule IDs were added or removed.

## 0.1.0-alpha.21 - 2026-08-22

- Increased the framework version to `0.1.0-alpha.21`, adapter schema version
  to `20`, and target template version to `21` for deterministic Debug Mode
  architectural-supervision and durable-evidence linkage.
- Added optional structured `architectural_impacts` and `decision_effect`
  fields to Debug events. New records classify accepted-invariant, canonical-
  source, public-contract, subsystem-responsibility, solution-class,
  compatibility, lifecycle, and authority-boundary interventions without
  invalidating legacy records that lack these fields.
- Required direction-changing corrections to preserve a causal sequence from
  correction through a rejected hypothesis with counter-evidence to a
  replacement invariant or architecture direction.
- Required every non-empty Debug `engineering_evidence_ids` value to resolve
  exactly once in the target Engineering Evidence index and rejected Debug
  event IDs, unknown IDs, and duplicate index resolution.
- Added migration warnings for legacy unstructured classifications, hard
  failures for explicit structured contradictions, completed-record comparison
  boundaries, and generic conformance coverage for the reported field failure.
- Updated installation, adapter recheck, post-update, help, lifecycle, module,
  evidence, and context-routing surfaces so any target branch can receive and
  validate the complete contract without silently inferring historical facts.
- Changed `ALATYR-ADAPTER-001`, `ALATYR-DEBUG-001`, `ALATYR-EVIDENCE-001`,
  `ALATYR-LIFECYCLE-001`, and `ALATYR-MODULE-001`; no rule IDs were added or
  removed.

## 0.1.0-alpha.20 - 2026-08-22

- Increased the framework version to `0.1.0-alpha.20`, adapter schema version
  to `19`, and target template version to `20` for deterministic installed-
  adapter update acceptance.
- Split structural validation into strict `acceptance` and non-accepting
  `migration-staging` phases. The deprecated `--allow-placeholders` option now
  maps to staging and can no longer produce `passed`, `ready`, or acceptance-
  eligible evidence.
- Made active placeholder scanning capability-aware across required core,
  support-profile, manifest-referenced, and enabled-module live surfaces while
  preserving placeholders in explicit reusable authoring templates.
- Required one-to-one agreement between manifest-enabled modules and
  `enabled` or `required` blocks in the human module profile.
- Upgraded Debug Mode and durable engineering-evidence indexes to schema 2,
  added explicit redaction policy, and added deterministic machine-index to
  human-README policy projection checks.
- Bound validator, upgrade-impact, and assessment evidence to the checked-out
  target branch and revision. Acceptance on one branch no longer implies that
  another branch is updated.
- Added regression coverage for staged versus accepted placeholders, missing
  enabled-module profile blocks, policy projection drift, and arbitrary target
  branches on Linux, macOS, and Windows compatible tooling.
- Changed `ALATYR-ADAPTER-001`, `ALATYR-EVIDENCE-001`,
  `ALATYR-LIFECYCLE-001`, and `ALATYR-MODULE-001`; no rule IDs were added or
  removed.

## 0.1.0-alpha.19 - 2026-08-21

- Increased the framework version to `0.1.0-alpha.19`, adapter schema version
  to `18`, and target template version to `19` for optional task-local Debug
  Mode observability.
- Added `ALATYR-DEBUG-001`, an explicitly activated per-task/session contract
  that distinguishes independent Alatyr findings, human interventions,
  consequences derived after human direction, and external maintainer input.
- Added normalized event, timing, capture-quality, metric, final-result,
  privacy, and clean-upstream projection contracts without storing raw
  conversations, prompts, private reasoning, secrets, or unrelated data.
- Added target-owned non-canonical debug policy/index/record surfaces, a lazy
  context overlay, operation aliases, flow, gate, compact final summary, and
  installation/update preservation guidance across supported assistants.
- Extended the portable target validator with schema, causal attribution,
  event-derived metric, timing, index synchronization, repository-binding,
  privacy, and external-projection checks. Added deterministic conformance
  scenarios for valid and invalid records.
- Kept Debug Mode independent from current-scope engineering authorization:
  activation permits only target-approved debug evidence writes and never
  grants code, commit, publish, live, protected-change, or tool authority.
- Added `ALATYR-DEBUG-001`; changed `ALATYR-ADAPTER-001`,
  `ALATYR-CONTEXT-001`, `ALATYR-EVIDENCE-001`, `ALATYR-LIFECYCLE-001`,
  `ALATYR-MODULE-001`, and `ALATYR-OPERATION-001`; no rule IDs were removed.

## 0.1.0-alpha.18 - 2026-08-21

- Increased the framework version to `0.1.0-alpha.18`, adapter schema version
  to `17`, and target template version to `18` for required proportional
  durable engineering-evidence capture.
- Added `ALATYR-ENGINEERING-EVIDENCE-001`. Material semantic,
  architectural, and non-obvious repair work now asks whether reusable
  knowledge would be lost after the session and records a compact capture,
  skip, or block result before completion.
- Added project-owned evidence policy/index and record contracts for task and
  repository binding, affected architecture, invariants, confirmed/rejected/
  unresolved hypotheses, root cause, solution rationale, material alternatives,
  impact, invariant-driven regression cases, validation, and uncertainty.
- Prohibited raw chat, chain-of-thought, prompts, secrets, credentials,
  personal data, unrelated session history, complete diffs, and verbose logs
  from durable records. Added a target-owned retained-storage and external-
  contribution boundary so support evidence need not pollute upstream patches.
- Kept capture proportional and independent from change-package activation:
  small self-explanatory fixes may skip with a fact-specific reason, while an
  active package links evidence IDs instead of duplicating conclusions.
- Added a lazy task-scale route, target operation and aliases, capture flow,
  gate, JSON Schema, final-evidence field, installation/update preservation,
  and post-install/update guidance across supported assistant surfaces.
- Extended the portable target validator with index/record synchronization,
  revision resolution, selected-file snapshot hashing, privacy, publication,
  and prohibited-field checks. Added Git-backed source fixtures and captured,
  skipped, read-only-blocked, and clean-upstream conformance scenarios.
- Added `ALATYR-ENGINEERING-EVIDENCE-001`; changed
  `ALATYR-ADAPTER-001`, `ALATYR-CHANGE-001`, `ALATYR-CONTEXT-001`,
  `ALATYR-EVIDENCE-001`, `ALATYR-INTEGRITY-001`, `ALATYR-LIFECYCLE-001`,
  `ALATYR-MODULE-001`, `ALATYR-OPERATION-001`, and `ALATYR-PACKAGE-001`; no
  rule IDs were removed.

## 0.1.0-alpha.17 - 2026-08-21

- Increased the framework version to `0.1.0-alpha.17`, adapter schema version
  to `16`, and target template version to `17` for current-scope action
  authorization across every supported assistant surface.
- Added `ALATYR-AUTHORIZATION-001` and a required target policy that evaluates
  `inspect`, `modify`, `commit`, `publish`, and `live-external` independently
  against the newest user request and current logical scope.
- Made issue/backlog returns, status, discussion, analysis, plans, reports, and
  ambiguous continuation read-only by default. Implementation no longer
  implies commit or publication, commit no longer implies publication, and
  authorization from a completed or redirected task cannot be reused.
- Extended the boundary to local Git index/history/ref mutations, remote pull
  request/issue/review/release mutations, live operational effects,
  delegation, team assignment, allowed-action modes, protected approval,
  project decisions, tool permissions, and successful validation.
- Added 15 deterministic intent-conformance scenarios, a portable source
  checker, installed-target structural findings, validator regressions, and
  the required `current_user_authorization` final-evidence field. These checks
  validate declared contracts; they cannot prove that an assistant interpreted
  an arbitrary conversation correctly.
- Synchronized framework packs, capabilities, source/target manifests,
  installer planning and readiness, required-core maturity, operation routing,
  gates, output contracts, subagent packets, bridge capability records, and
  post-install/update messages around the same phase boundary.
- Added `ALATYR-AUTHORIZATION-001`; changed `ALATYR-ADAPTER-001`,
  `ALATYR-APPROVAL-001`, `ALATYR-BRIDGE-001`, `ALATYR-DELEGATION-001`,
  `ALATYR-EVIDENCE-001`, `ALATYR-LIFECYCLE-001`, `ALATYR-MODULE-001`,
  `ALATYR-OPERATION-001`, and `ALATYR-TEAM-001`; no rule IDs were removed.

## 0.1.0-alpha.16 - 2026-08-21

- Increased the framework version to `0.1.0-alpha.16`, adapter schema version
  to `15`, and target template version to `16` for exact source-of-truth
  registry and consistency-map synchronization.
- Required every live registry Fact Type in an enabled consistency map to
  reference one resolved, unique node whose `fact_type` matches exactly;
  additional derived contract, area, system, and adapter nodes remain allowed.
- Changed semantic routing to load the target registry and map together while
  keeping the portable consistency-model explanation conditional.
- Added a measured compact semantic-consistency scenario so registry/map
  routing changes remain inside declared context budgets without dropping
  target-owned evidence; installed validation also checks each composed
  profile against total, portable, reserved-target, and file limits.
- Added target-validator findings for missing, reused, unresolved, duplicate,
  and mismatched registry/map identities and for stale unavailable-state claims
  about enabled modules on live support surfaces.
- Synchronized installation, planning, recheck, logical-integrity, blueprint,
  module-capability, maintenance, and validation guidance around one reviewed
  registry/map/routing/budget/bootstrap adapter change set.
- Changed `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`, and
  `ALATYR-ADAPTER-001`; no rule IDs were added or removed.

## 0.1.0-alpha.15 - 2026-08-21

- Increased the framework version to `0.1.0-alpha.15`, adapter schema version
  to `14`, and target template version to `15` for ownership, dependency
  discovery, release-evidence, and conformance enforcement changes.
- Separated category routing owners from per-rule canonical semantic owners in
  generated rule documentation and source checks, removing the ambiguous dual
  ownership of `ALATYR-SAFETY-002` without changing its canonical owner.
- Required dependency package sources to identify locators as
  `native-package-metadata-key`; target validation now rejects executable or
  adapter-style locator contracts.
- Bound release validation to the exact `v<VERSION>` tag in tag-triggered CI,
  included every shipped schema in contract classification and migration diffs,
  and bound reviewed migration evidence to deterministic baseline and
  destination contract-tree SHA-256 values.
- Added a machine-readable captured-conformance run index. Canonical source
  checks now validate every committed run and reject missing, unexpected, or
  unregistered captured report sets; aggregate checking and summarization use
  the indexed run-root contract.
- Corrected installation and maintenance guidance so generated registries,
  ownership maps, and captured-run parent directories are not presented as
  semantic owners or direct report directories.

## 0.1.0-alpha.14 - 2026-08-21

- Increased the framework version to `0.1.0-alpha.14`, adapter schema version
  to `13`, and target template version to `14` for optional passive dependency
  knowledge and user-owned workspace modes.
- Added `ALATYR-DEPENDENCY-001` and a canonical protocol that permits one
  active project adapter to consume bounded documentation and contract exports
  from exact resolved dependency artifacts without activating nested adapters.
- Added a strict dependency export schema and cross-platform, read-only source
  validator covering declared paths, digests, strict fields, graph references,
  and prohibited executable or assistant-control surfaces.
- Added target-owned dependency policy, catalog, knowledge lock, deviations,
  retained-snapshot boundary, routed operation, flow, gate, report, and intent
  templates. Trust, freshness, authority, and applicability remain independent
  decisions.
- Defined and enforced normalized catalog package/export, exact lock-instance,
  bounded graph, and target-deviation record contracts, including duplicate
  and dangling-reference detection.
- Extended installation, update, bootstrap, module selection, operation help,
  source-of-truth, safety, lifecycle, and target validation contracts. Native
  package metadata owns discovery; dependency content remains untrusted data
  and is never routine bootstrap context.
- Added source consistency, target-validator dispatch, manifest, framework-pack,
  context-routing, and cross-platform command coverage for the new module.
- Added `ALATYR-MODE-001` and an optional project-owned mode catalog with
  explicit workspace identity, artifact relationships, one support directory
  per actual mode, optional shared root support, evidence-bound installation
  suggestions, user-owned acceptance, safe ambiguity handling, and per-task
  selection preflight.
- Added a routed workspace-mode operation, post-install/update suggestion and
  preservation behavior, compact context-cost evidence, source checks, and
  installed-target enforcement for catalog/descriptor agreement, one active
  root, inactive nested adapters, target-relative context, and explicit
  no-grants fields. Router schema 6 composes one selected mode before the
  ordinary task profile and project-area overlays.
- Added `ALATYR-DEPENDENCY-001` and `ALATYR-MODE-001`; changed `ALATYR-CONTEXT-001`,
  `ALATYR-SOURCE-001`, `ALATYR-SAFETY-002`, `ALATYR-INTEGRITY-001`,
  `ALATYR-ADAPTER-001`, `ALATYR-MODULE-001`, `ALATYR-LIFECYCLE-001`,
  `ALATYR-OPERATION-001`, and `ALATYR-EVIDENCE-001`; no rule IDs were removed.

## 0.1.0-alpha.13 - 2026-08-20

- Increased the framework version to `0.1.0-alpha.13`, adapter schema version
  to `12`, and target template version to `13` for compact generated bootstrap
  routing and capability-selected target projections.
- Replaced the routine installed-target bootstrap corpus with a deterministic
  `.ai/assistant/bootstrap-index.json` projection. Router schema 5 starts from
  that index and loads project sources, gate fragments, and optional module
  context only when the selected task profile requires them.
- Split the monolithic gate checklist into an indexed core plus focused
  documentation, code-and-tests, semantic-integrity, security-approval, and
  final-evidence fragments while retaining the checklist as a canonical
  explanatory surface.
- Reduced the core scaffold and added repeatable `--enable-module` capability
  selection with dependency closure, minimum-pack enforcement, target-file
  projection, and generated bootstrap output. Optional modules remain disabled
  unless target evidence and policy enable them.
- Changed installed-target validation to run universal contracts for every
  adapter and optional deep checks only for enabled modules. Added source tests
  for validator dispatch and capability projection.
- Added machine-readable upgrade-impact evidence and delta-first upgrade
  routing so an installed adapter begins from changed owners, rules, profiles,
  and surfaces before considering full-corpus expansion.
- Made changed-path source validation use declared trigger paths while retaining
  invariant checks and conservative full-suite fallback for unowned paths.
- Extended effectiveness benchmarks with framework-upgrade and team-scale task
  classes plus a quality non-regression contract. Existing captured results
  are not reinterpreted as evidence of cost savings.
- Changed `ALATYR-CONTEXT-001`, `ALATYR-ADAPTER-001`, `ALATYR-MODULE-001`,
  `ALATYR-BRIDGE-001`, `ALATYR-LIFECYCLE-001`, and `ALATYR-EVIDENCE-001`; no
  rule IDs were added or removed.

## 0.1.0-alpha.12 - 2026-08-20

- Increased the framework version to `0.1.0-alpha.12`, adapter schema version
  to `11`, and target template version to `12` for the optional delegation
  policy and per-assistant capability contracts.
- Added optional model-aware subagent delegation under new rule
  `ALATYR-DELEGATION-001`, with primary-agent responsibility, bounded packet
  decomposition, non-delegable semantic/protected decisions, disjoint writes,
  capability negotiation, fallback, result review, and evidence boundaries.
- Added a target-owned delegation policy, lazy delegated-execution overlay,
  subagent flow, task/result packet, large-task integration, operation request
  preference, and installation/update migration guidance.
- Extended all nine assistant capability templates and the bridge matrix with
  native, external, suggestion-only, or unsupported dispatch backends,
  external-dispatcher item binding, worker launch, model override, parallel
  dispatch, actual-model evidence, freshness, and fallback behavior. Model
  bindings remain target-verified and vendor-neutral; Codex Spark is
  documented as an optional current example, not a portable requirement.
- Added source and installed-target structural validation for delegation
  policy, required guards, role/model bindings, supported surfaces, packet
  routing, and primary convergence. These checks do not prove decomposition
  quality, actual model availability, latency, or cost savings.
- Reworked the public README into a shorter human-oriented product, usage,
  installation, maturity, and navigation guide while preserving explicit
  capability and claim boundaries.
- Expanded `AI_ASSISTANTS.md` into the dedicated assistant-facing route for
  source work, installation, installed operation, compact context, bridge,
  infrastructure, and evidence behavior.
- Made the consistency checker keep detailed source-tool references in their
  canonical `tools/README.md` owner instead of forcing that inventory into the
  public README.
- Fixed selective framework-pack scaffolding, validator fixtures, and lifecycle
  conformance updates to preserve generated projections as byte-exact UTF-8
  with LF endings, preventing Windows newline conversion from invalidating
  projected framework evidence.

## 0.1.0-alpha.11 - 2026-08-19

- Increased the framework version to `0.1.0-alpha.11`, adapter schema version
  to `10`, and target template version to `11`.
- Made framework baseline and missing migration evidence blocking by default
  while retaining explicit accepted-deviation and severity policy. Supplying a
  Git diff base with explicit approval records now enables complete changed-
  path scope enforcement automatically.
- Replaced eager dependency submission in the source runner with dependency-
  gated parallel execution. Failed prerequisites now block transitive
  dependents while independent checks continue, with focused unit coverage.
- Added JSON Schema validation for the adapter manifest, consolidated YAML
  parsing with line-aware diagnostics, and added a canonical capability graph
  for all 18 optional modules. Enabled target modules now require dependency,
  pack, rule, installed-framework-file, target-file, and source-check closure.
- Added a deterministic lifecycle walking skeleton that proves a Git-scoped
  approved core installation, placeholder-free structural acceptance,
  blocking framework drift, synthetic update application, and post-update
  acceptance without claiming AI execution or project-semantic validation.
- Changed source routes to canonical check IDs and added an explicit full
  repository-audit route. `.ai/assistant` context is now correctly measured as
  project-owned target context rather than portable framework context.
- Split CI so Linux runs the full suite once and macOS and Windows run the
  portable lifecycle/tooling contract. Added declared source-check
  dependencies and a tested dry-run-first cleanup command for ignored local
  artifacts.
- Changed release drift recovery to use the nearest reachable prior changelog
  tag while requiring migration reports for intervening untagged versions.
  This preserves a real auditable baseline without fabricating historical tags.
- Changed `ALATYR-APPROVAL-001`, `ALATYR-MODULE-001`, and
  `ALATYR-EVIDENCE-001`; no rule IDs were added or removed.

## 0.1.0-alpha.10 - 2026-08-19

- Increased the framework version to `0.1.0-alpha.10`, adapter schema version
  to `9`, and target template version to `10`, with migration evidence from
  committed source state `f62354c` (`0.1.0-alpha.9`).
- Replaced broad source and installation bootstrap lists with compact
  machine-readable routers and a generated framework file inventory. Target
  context routing now uses schema 4 with separate total, portable, and reserved
  target-word budgets plus checked cost scenarios and expansion receipts.
- Added installed-target context-cost enforcement and target reporting while
  keeping logical integrity, source-of-truth selection, and semantic review as
  reasoning responsibilities rather than pretending that word-count checks
  prove correctness.
- Added a dependency-aware source check manifest with `fast`, `full`, `change`,
  and `release` profiles, bounded parallel execution, changed-path selection,
  and conservative full-suite fallback for unmatched paths. Full source checks
  now complete in roughly four seconds on the recorded development host rather
  than roughly sixteen seconds before this change; host timings are not a
  cross-platform guarantee.
- Split cached target validation support from the monolithic entry point and
  generated a catalog of 634 stable finding codes from validator source.
- Made rule-registry and rule-ownership Markdown generated derivatives of the
  machine-readable registry and added framework rule-dependency cycle checks.
- Added a seven-class effectiveness benchmark coverage contract spanning
  narrow docs, local regression, business, architecture, data, security, and
  large resumable work. The contract explicitly contains no execution results
  and supports no effectiveness or cost claim by itself.
- Added dependency-closed `core`, `standard`, and `complete` framework packs.
  Scaffolding matches them to support profiles, projects registry/ownership/
  inventory surfaces for selective packs, and validates selective baselines
  without treating intentional optional-file omission as drift.
- Strengthened release drift checks with explicit change and release modes,
  prior-release tag requirements, public version checks, and dedicated release
  CI entry points with complete Git history.
- Kept the routine target bootstrap at 1,899 words under its unchanged
  1,900-word soft and 2,000-word hard limits. Static compact-route reductions
  remain between about 63% and 93% for the checked optional operation routes;
  these measurements are whitespace-word proxies, not model-token or billing
  evidence.
- Changed `ALATYR-CONTEXT-001`, `ALATYR-ADAPTER-001`,
  `ALATYR-MODULE-001`, and `ALATYR-LIFECYCLE-001`; no rule IDs were added or
  removed.

## 0.1.0-alpha.9 - 2026-08-19

- Increased the framework version to `0.1.0-alpha.9`, adapter schema version
  to `8`, and target template version to `9`, with migration evidence from the
  committed `0.1.0-alpha.8` source state.
- Replaced the optional team module's mixed Markdown/JSON actor and task state
  with a target-owned schema-2 team policy, registry metadata, independently
  updateable task records, a generated compact active-work index, and an
  explicit coordination-backend capability contract.
- Added assistant-driven local identity selection through `Alatyr set actor`,
  `Alatyr who am I`, and `Alatyr clear actor`. Local selection is ignored
  repository state used for attribution only; it does not authenticate a user,
  grant authority, modify global Git configuration, or silently enroll an
  unknown actor.
- Added automatic compact active-work preflight before state-changing
  operations. Full team policy, task records, and human operating guidance are
  loaded only when overlap, ownership, authority, handoff, review, or backend
  evidence requires expansion.
- Added optimistic-concurrency fields, claim leases, transition-policy checks,
  self-review rejection, active-index freshness and parity checks, and
  revision-bound merge-review evidence to reduce silent concurrent updates and
  stale merge readiness.
- Added an adapted team collaboration skill, one aggregate collaboration-
  improvement review, and target-evidenced recommendations for existing skills,
  prompts, gates, checks, flows, and tools without ranking individual people.
- Added portable target-validator scenarios covering a valid repository-backed
  team, revision conflict, self-review, stale active-work index, unknown local
  identity, and stale merge-review evidence.
- Defined extension-mediated provider integration for external trackers or
  collaboration services. Core remains vendor-neutral and requires explicit
  backend capabilities, synchronization direction, permissions, provenance,
  approval, and failure behavior.
- Defined an atomic adapter migration from schema-1 embedded task arrays to
  schema-2 per-task records. Existing actors, tasks, claims, reviews, handoffs,
  decisions, external links, and local identity must be preserved; placeholder
  replacement is prohibited.
- Kept routine bootstrap at 1,899 words, under the unchanged 1,900-word soft
  limit. The team compact preflight loads 3 files and about 796 words versus 17
  files and about 11,123 words for the full team reference union, a 92.8%
  static word reduction. Combined large-task and team overlays remain about
  2,255 words; framework-update routing retains an 85.9% static word reduction
  from the complete candidate union.
- Changed `ALATYR-TEAM-001`, `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
  `ALATYR-ADAPTER-001`, `ALATYR-OPERATION-001`, `ALATYR-BRIDGE-001`,
  `ALATYR-EXTENSION-001`, `ALATYR-LIFECYCLE-001`, and
  `ALATYR-EVIDENCE-001`; no rule IDs were added or removed.

## 0.1.0-alpha.8 - 2026-08-12

- Increased the framework version to `0.1.0-alpha.8`, adapter schema version
  to `7`, and target template version to `8`, with migration evidence from the
  committed `0.1.0-alpha.7` source state.
- Added optional project-owned test-first development under new rule
  `ALATYR-TDD-001`, with explicit policy assessment, enablement, revision,
  disablement, and review instead of a universal TDD mandate.
- Added target-configurable strict TDD, regression-first,
  characterization-first, contract-first, and justified test-after modes,
  while preserving target ownership of commands, test levels, fixtures,
  isolation, exceptions, CI, and merge policy.
- Added a bounded recommendation gate that classifies test-first work as
  `required`, `recommended`, `not-indicated`, or `blocked` from changed-fact
  and risk evidence. Suggestions are limited to once per task, suppressed
  after decline, and do not block ordinary work when the module is disabled.
- Added a lazy test-first intent, separate configuration and execution
  operations, target policy and index, RED/GREEN/refactor gate, evidence
  record, adapted skill, help aliases, installation and update guidance, and
  routing across all nine supported assistant surfaces.
- Required RED to fail for the expected behavior reason, GREEN to prove the
  same focused contract, useful tests not to be weakened for a pass, and
  broader validation to follow changed risk and boundary crossings.
- Extended the portable target validator with enabled-module file, manifest,
  policy metadata, mode, trigger, test-level, command, exception-reference,
  isolation, operation, and router checks. Structural checks explicitly do
  not prove assertion semantics or expected-failure causality.
- Added deterministic source checking and scaffold conformance for the new
  module. The compact test-first route loads 4 files and about 2,756 words
  versus 14 files and about 8,445 words for the full reference union, a 67.4%
  static word reduction.
- Added optional declarative extensions under new rule
  `ALATYR-EXTENSION-001`, including an external repository package manifest,
  authoring template, read-only local inspection, compatibility and permission
  review, target-owned bindings, compact catalog, immutable source and
  installed-file lock, explicit lifecycle, and ownership-aware removal.
- Kept extension packages non-executable: version 1 rejects arbitrary
  lifecycle hooks, transitive extension dependencies, path escapes, symlinks,
  framework replacement, project-fact ownership, automatic updates, and
  unapproved permission expansion.
- Added `extension-management` and read-only extension recommendation aliases
  across all nine assistant surfaces, while keeping package items outside
  routine bootstrap and routing normalized items lazily through existing AI
  infrastructure contracts.
- Extended source tooling with the cross-platform `inspect-extension` command
  and installed-target checks for enabled module files, catalog/lock identity,
  immutable provenance, compatibility, bindings, approval evidence, exact
  installed-file ownership and hashes, operation routing, and drift.
- The compact extension route loads 6 files and about 3,067 words versus 14
  resolved files and about 8,691 words for the full reference union, a 64.7%
  static word reduction.
- Kept the routine bootstrap at 1,835 words, below the unchanged 2,000-word
  hard limit. The bootstrap soft headroom increased from 1,700 to 1,900 words
  for the test-first and extension manifest and lazy-router declarations.
- Changed `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`, `ALATYR-RISK-001`,
  `ALATYR-INTEGRITY-001`, `ALATYR-CHANGE-001`, `ALATYR-ADAPTER-001`,
  `ALATYR-MODULE-001`, `ALATYR-OPERATION-001`, `ALATYR-BRIDGE-001`,
  `ALATYR-SAFETY-002`, `ALATYR-LIFECYCLE-001`, and `ALATYR-EVIDENCE-001`;
  added `ALATYR-TDD-001` and
  `ALATYR-EXTENSION-001`; no rule IDs were removed.

## 0.1.0-alpha.7 - 2026-08-07

- Increased the framework version to `0.1.0-alpha.7`, adapter schema version
  to `6`, and target template version to `7`, with migration evidence from the
  committed `0.1.0-alpha.6` source state.
- Added optional project vocabulary under new rule
  `ALATYR-VOCABULARY-001`, with explicit `observed`, `proposed`, `accepted`,
  `deprecated`, `contradicted`, and `unknown` term states.
- Added a compact project-owned term, alias, and acronym catalog; full scoped
  term records; data-dictionary links; a lazy vocabulary intent; term-review
  evidence; an adapted target skill; and a dedicated conversational operation.
- Kept glossary meaning separate from schemas, APIs, data dictionaries, code,
  business rules, architecture decisions, security policy, and operational
  facts. Vocabulary records link to those canonical owners rather than
  replacing them.
- Required target authority before accepted terminology can drive
  normalization. Multiple accepted meanings remain scoped by domain and must
  not be resolved silently; observed frequency does not prove accepted meaning.
- Added aliases for `Alatyr glossary`, `Alatyr define term`, `propose glossary
  entry`, `check terminology`, and `review project vocabulary`, routed through
  the same canonical operation index and bridge capability contract for all
  nine supported assistant surfaces.
- Added installation, upgrade, post-install/update, source-of-truth, logical-
  integrity, code-documentation, architecture, lifecycle, and help integration
  while preserving target vocabulary records across framework updates.
- Added source checks and optional target validation for required files,
  manifest paths, term and link schemas, duplicate IDs, catalog references,
  accepted-term evidence, same-domain accepted lookup ambiguity, lazy routing,
  operation contracts, and structural evidence limitations.
- Added deterministic context-cost evidence: the project-vocabulary compact
  route loads 5 files and about 2,421 words versus 13 files and about 6,908
  words for the full reference union, a 65.0% static word reduction; routine
  bootstrap remains 1,693 words and below its soft budget.
- Changed `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
  `ALATYR-INTEGRITY-001`, `ALATYR-ARCHITECTURE-001`,
  `ALATYR-CODEDOC-001`, `ALATYR-ADAPTER-001`, `ALATYR-MODULE-001`,
  `ALATYR-OPERATION-001`, `ALATYR-BRIDGE-001`,
  `ALATYR-LIFECYCLE-001`, and `ALATYR-EVIDENCE-001`; added
  `ALATYR-VOCABULARY-001`; no rule IDs were removed.

## 0.1.0-alpha.6 - 2026-08-07

- Increased the framework version to `0.1.0-alpha.6`, adapter schema version
  to `5`, and target template version to `6`, with migration evidence from the
  committed `0.1.0-alpha.5` source state.
- Added optional project code documentation under new rule
  `ALATYR-CODEDOC-001`, with bounded source-set profiles so frontend, backend,
  shared-library, infrastructure, and other project areas may use different
  evidence-backed comment styles and semantic content contracts.
- Added a compact project documentation index and catalog, machine-readable
  profile selection, profile-review report, lazy intent route, adapted target
  skill, documentation-sync modes, operation aliases, installation/update
  guidance, and target structural validation.
- Defined deterministic reference generation through target-recorded language
  or ecosystem tools, with `ci-artifact`, `committed-generated`, `local-only`,
  `external-publish`, and unresolved output policies. Generated output is
  derived and must not be edited directly.
- Required assistants to inspect existing target comments, generators,
  compiler/linter/IDE/CI support, canonical specifications, ownership, and
  maintenance evidence before proposing a style. Only one unambiguous accepted
  profile may direct routine source-comment or generation work.
- Preserved source-of-truth boundaries: comments may own bounded symbol-level
  explanations only when the target registry assigns them ownership, while
  business, architecture, security, API, data, and operational owners remain
  canonical.
- Added source checks and optional target validation for module files, manifest
  paths, profile states, required fields, duplicate IDs, exact accepted-profile
  ambiguity, generated-output direct-edit policy, lazy routing, and contract
  completeness. Structural checks do not prove comment truth or generated-
  reference quality.
- Added deterministic context-cost evidence: the code-documentation compact
  route loads 6 files and about 2,938 words versus 14 files and about 9,288
  words for the full reference union, a 68.4% static word reduction; routine
  bootstrap remains below its soft budget.
- Changed `ALATYR-CONTEXT-001`, `ALATYR-SOURCE-001`,
  `ALATYR-INTEGRITY-001`, `ALATYR-ADAPTER-001`, `ALATYR-MODULE-001`,
  `ALATYR-OPERATION-001`, `ALATYR-LIFECYCLE-001`, and
  `ALATYR-EVIDENCE-001`; added `ALATYR-CODEDOC-001`; no rule IDs were removed.

## 0.1.0-alpha.5 - 2026-08-06

- Increased the framework version to `0.1.0-alpha.5`, adapter schema version
  to `4`, and target template version to `5`, with migration evidence from the
  last committed `0.1.0-alpha.4` source state.
- Added optional change packages under new rule `ALATYR-PACKAGE-001` for
  coherent material outcomes that need semantic multi-surface approval,
  companion-surface decisions, implementation correction evidence, compact
  architecture discussion, validation, and reproducible before-to-after
  provenance.
- Added a lazy change-package context overlay, compact empty target index,
  machine record, redacted human report, target flow, manifest/module wiring,
  installation/update guidance, scaffold projection, and conformance evidence
  without adding package cost to ordinary local tasks.
- Advanced the machine approval record template to schema 2 with allowed
  changed-fact IDs, architecture areas, behavior categories, excluded semantic
  effects, permitted external effects, and declared semantic-scope result.
- Extended the portable target validator with explicit `--change-package` and
  `--enforce-change-package` checks for plan hashes, Git ranges, snapshot
  digests, declared semantic/path scope, linked approvals, companion decisions,
  correction/reapproval impact, and public evidence strength. These checks do
  not replace project invariant derivation or logical integrity review.
- Installed adapters that enable `change-packages` must add the package index,
  lazy overlay, flow, record/report templates, retention/redaction policy, and
  validator support. Existing historical target records must be preserved.
- Changed `ALATYR-APPROVAL-001`, `ALATYR-CHANGE-001`,
  `ALATYR-INTEGRITY-001`, `ALATYR-CONTEXT-001`, `ALATYR-MODULE-001`,
  `ALATYR-LIFECYCLE-001`, and `ALATYR-EVIDENCE-001`; added
  `ALATYR-PACKAGE-001`; no rule IDs were removed.

- Added optional project-owned architecture knowledge with canonical area and
  pattern records, explicit observed/proposed/accepted lifecycle statuses,
  source evidence, decision authority, and maintenance triggers.
- Added one `architecture-assistance` operation for architecture inventory,
  explanation, discussion, comparison, review, and documentation across every
  supported assistant surface, with problem-first alternatives and an
  approval-bound handoff into product changes.
- Added a compact architecture intent route, target catalog and record
  templates, installation/update integration, source and target validation,
  and deterministic context-cost evidence for lazy architecture discussions.
- Added a portable ASCII diagram grammar for architecture flows, sequences,
  hierarchies, states, relationship graphs, and quantitative charts.
- Made bounded pure ASCII mandatory for every `diagram-discussion` result,
  while retaining native inline rendering and generated artifacts as optional
  capability-checked supplements.
- Added target ASCII presentation/readability templates and deterministic
  result checks for character set, tabs, width, direction, structural marks,
  and reported longest line across all supported assistant surfaces.
- Replaced the legacy `text-fallback` diagram result mode with `ascii` and
  routed the detailed grammar and reusable layout template conditionally so
  ordinary diagram discussions retain compact context loading.

## 0.1.0-alpha.4 - 2026-08-02

- Increased the framework version to `0.1.0-alpha.4`, adapter schema version
  to `3`, and target template version to `4`, with migration evidence bound to
  the previous Git release tag.
- Replaced inline context-profile contracts with a compact schema-3 router and
  lazy profile, intent, migration, consistency, and task-scale descriptors;
  reduced the static bootstrap from 1,997 to 1,363 words.
- Made `core`, `standard`, and `full` scaffolds project manifest, router,
  operation, and capability claims to files actually present in each support
  profile, and validate all three projected adapters.
- Made operation and assistant-capability indexes generated derivatives of
  canonical records, with separate freshness-aware capability evidence per
  supported assistant surface.
- Added captured diagram-result validation for selected capability evidence,
  loaded context, readable fallback, read-only behavior, and residual risk.
- Added release drift enforcement against the latest reachable Git tag and
  extracted reusable target-validator parsing, Git, hashing, and approval-scope
  helpers from the validator orchestration module.
- Added `ALATYR-DIAGRAM-001` and an optional `diagram-discussion` operation for
  showing, comparing, and revising diagrams during assistant conversations.
- Added target flow and presentation contracts that distinguish drafts,
  accepted sources, and derived views; bind views to source revision evidence;
  and prevent read-only discussion from changing repository files or accepted
  project facts.
- Added a compact per-assistant capability projection with constrained route
  and artifact enums, readable fallback, client version, verification time,
  and evidence for every supported surface.
- Added stable diagram IDs and draft lineage, mandatory revision evidence for
  accepted/derived views, security/privacy/redaction and external-renderer
  policy, plus a cross-assistant operation conformance fixture.
- Added a checked compact operation index derived exactly from the canonical
  catalog, and a profile-independent diagram intent overlay so exact aliases
  avoid full catalog, help, module-profile, and bridge-matrix loading.
- Added optional `team-collaboration` under canonical rule
  `ALATYR-TEAM-001`, separating target-owned actors, authority, priority,
  review, backend, storage, and privacy facts from assistant-owned task,
  claim, conflict, checkpoint, handoff, decision, and merge-readiness records.
- Added a lazy `team-active` context overlay and seven catalog operations for
  team status, task coordination, conflict review, handoff, decision, review,
  and revision-bound merge checks across every supported assistant bridge.
- Added installation and framework-update contracts that initialize empty
  team state from target evidence, preserve active records during migration,
  and never overwrite target state with source placeholders.
- Extended the portable target validator and source checks for actor
  references, lifecycle values, allowed actions, overlap and claim state,
  stale registry revisions, and merge-ready validation/reviewer/revision
  evidence without replacing project logical review.
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
