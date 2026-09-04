---
alatyr_doc:
  id: framework.lifecycle
  type: framework-rule-owner
  owns_rules:
    - ALATYR-LIFECYCLE-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - framework-upgrade
---
# AI Framework Lifecycle

This file defines portable lifecycle rules for maintaining and upgrading the AI
framework itself.

The framework lifecycle is separate from product architecture decisions. A
project may mirror selected lifecycle notes into its adapter docs, but product
ADRs remain project-owned.

## Versioning

Each installed framework should identify:

- framework version
- adapter schema version
- template version when templates were used
- installed framework pack and its projected file inventory
- framework source or baseline
- installation or upgrade date
- local adapter owner
- adapter review cadence and last review date
- CODEOWNERS or equivalent owner map for `.ai/*`, root assistant entry
  points, and supported bridge files when the target repository supports file
  ownership metadata
- supported assistants
- required core profile and optional module states
- known deviations from the source framework
- unresolved adapter gaps
- support-information policy and current support-state digest

The source repository may store these facts in simple files such as `VERSION`,
`ADAPTER_SCHEMA_VERSION`, and `TEMPLATE_VERSION`. Installed adapters should
record them in a discoverable manifest such as `.ai/alatyr.yaml` or a
target-owned equivalent.

## Adapter Installation State

The target manifest records one explicit installation state:

- `scaffolded`: placeholder structure exists, but target facts have not been
  adapted or accepted.
- `staged`: repository-aware adaptation or upgrade work is in progress; active
  placeholders, unresolved required facts, or acceptance evidence remain.
- `accepted`: strict validation passed for the branch and revision being
  accepted, required target facts are resolved, enabled module state agrees
  across canonical surfaces, and no blocking finding remains.
- `degraded`: an adapter that was accepted no longer satisfies, or cannot
  currently prove, its accepted contract because of blocking drift, stale
  critical evidence, or an invalid required surface.

Scaffolding always starts in `scaffolded`. Beginning repository-aware
adaptation moves it to `staged`. Only explicit strict acceptance evidence may
move `staged` to `accepted`. An accepted adapter enters `staged` while an
approved upgrade introduces unresolved work, or `degraded` when current
evidence discovers contract failure outside a controlled staging process.
Repair moves `degraded` to `staged`; strict validation is required before
returning to `accepted`. No transition grants modify, commit, publication, or
live-external authorization.

Health and maturity are separate projections. `ready` health requires the
manifest state `accepted`; `scaffolded`, `staged`, and `degraded` must never be
reported as `ready`. Unresolved active placeholders always prevent acceptance.

The manifest points to a machine-readable installation-state record. That
record preserves an ordered transition chain with the previous and next state,
operation ID, repository revision, current-scope authorization evidence,
approval evidence when applicable, validation result, reason, and observation
time. Its final state must equal the manifest state. Direct jumps, broken
history, or `staged` to `accepted` without passed strict validation invalidate
acceptance. A transition record documents evidence; it does not create user
authorization or approval.

An adapter installed before transition records existed must not reconstruct
events it cannot prove. Its update may start a new record at `staged` with
reason `legacy-migration-baseline`, the current repository revision, and an
explicit unavailable-history explanation. Strict validation is still required
for the next `accepted` transition.

## Upgrade Process

Before upgrading framework files in a target project:

1. Load the compact bootstrap and the generated upgrade impact only. Verify
   the installed semantic-codebook index and resolve the bootstrap preload;
   then use recursive contour indexes for every additional migration surface.
2. Inspect the current target manifest, installed framework pack and baseline,
   projected inventory, local deviations, and adapter owner evidence.
3. Prepare or review a migration assessment before changing target files. It
   should compare rule registries, framework files, versions, and structural
   adapter state and emit a hash-bound machine-readable impact projection.
   Bind the assessment to the checked-out target branch and revision. Evidence
   for one branch does not establish adapter state on another branch.
4. Use the impact projection's changed rule IDs, categories, task profiles,
   canonical sources, template surfaces, enabled modules, and bridge
   capabilities to select additional context. Load the full framework corpus
   only when impact is ambiguous, validation disproves the boundary, or a full
   compatibility audit is explicitly requested.
   Rebuild affected framework, project, and assistant context indexes from the
   installed result, not from an unrelated branch or unprojected source
   template. Verify indexed paths, content digests, word estimates, parentage,
   depth, semantic references, and codebook shard digests before accepting the
   update. Preserve target-owned `project:*` terms and do not silently redefine
   installed `alatyr:*` term versions.
5. Identify framework-core changes versus target-adapter changes.
6. Preserve target project facts.
7. Compare supported assistant bridge needs and limitations. Merge source
   surface additions by ID without overwriting target capability evidence.
   Recheck exact runtime variant, selected entry path, competing instruction
   sources, toggles/configuration, observed auto-load, skill source, and client
   permissions. New or changed clients remain runtime-unverified until target
   evidence exists; client permissions never grant Alatyr authorization.
8. Identify new approval, testing, security, diagram, or validation guidance.
9. Compare required core profile, installed framework pack, and optional module
   states. Expand the pack before enabling a module whose portable owner is not
   installed; do not replace target facts while changing the pack.
   Resolve every shared capability surface from all enabled producers, apply
   its catalog merge strategy, and preserve it when another enabled module
   still requires it or its lifecycle contract says `preserve_on_disable`.
   A source scaffolder must preserve an existing target-owned shared surface;
   an assistant performs the target-aware merge under exact current-scope
   authorization and records the retained or merged result.
   When `team-collaboration` is enabled, compare its rule, structured policy,
   local-identity boundary, registry and task schemas, active-work index,
   backend contract, lazy overlay, operation routes, and operating model.
   When `change-packages` is enabled, compare its record schema, semantic
   approval fields, provenance policy, lazy route, and validator support.
   Compare the required support policy and state contract. Preserve target-owned
   classifications, exclusions, accepted relationships, relationship
   candidates, and generator bindings. Rebuild affected context indexes,
   consistency reverse index, and optional support-generation index before
   generating support state last.
   For required durable engineering evidence, compare its policy, compact
   index, contract version, authoring-template record schema, lazy route,
   capture gate, repository binding state/lineage, Git object and ancestry
   checks, reciprocal Debug session lineage, privacy, publication boundary, and
   validator support.
   When `debug-mode` is enabled, compare its explicit activation/expiry rule,
   non-canonical storage policy, index/record schema, lazy overlay, operation,
   flow, gate, summary, contract and authoring-template schema, versioned actor/
   causality/intervention/contribution attribution, lifecycle-bounded timing,
   immutable completion and continuation, capture quality, metric derivation,
   structured architectural-impact and decision-effect fields, direction-
   change hypothesis/replacement causality, typed evidence-event roles,
   complete materiality, canonical skip preservation, claim-validation
   fidelity, durable engineering-evidence decision/reference resolution,
   repository-binding state/lineage, lifecycle phase coverage, candidate
   disposition closure, reciprocal evidence links,
   active-versus-finalized comparison boundary, clean-upstream boundary, and
   validator support.
   When `code-documentation` is enabled, compare its catalog/profile schemas,
   source-set selectors, accepted states, canonical-owner boundaries,
   generators, output/publication policies, adapted skill, lazy route, and
   validator support.
   When `project-vocabulary` is enabled, compare its catalog, term, and data-
   link schemas, state and acceptance model, normalization policy, canonical-
   owner boundaries, adapted skill, lazy route, and validator support.
   When `test-first-development` is enabled, compare policy schema and revision,
   owners, recommendation behavior, triggers, modes, levels, commands,
   isolation, exceptions, adapted skill/gate, lazy route, evidence contract,
   and validator support.
   When `extensions` is enabled, compare extension API, catalog/lock schemas,
   package compatibility, installed ownership and hashes, target bindings,
   permissions, lifecycle flow, gates, operation/bridge routing, historical
   records, and validator support.
   When `dependency-knowledge` is enabled, compare its export API, target
   policy/catalog/knowledge-lock/deviation schemas, passive activation
   boundary, independent semantic state axes, artifact identity, retention,
   intent route, flow, gate, operation, and validator support.
   When `subagent-delegation` is enabled, compare its policy schema, selected
   assistant capability records, role catalog/prompts, role/model and native-
   definition bindings, client/runtime freshness, task-plan, packet, result,
   and overlay contracts, write isolation, retries/conflicts, fallbacks,
   privacy, validation, and primary convergence.
10. Prepare a target migration note or installation plan from reviewed
    assessment evidence.
11. Require approval before overwriting existing target AI instructions.
12. Recheck the installed adapter for framework references, bridge files, gates,
   prompts, skills, lifecycle notes, and maturity gaps.
    Recheck recursive contour-index coverage, semantic-codebook resolution,
    compact preload limits, context-packet compatibility, and the absence of
    stale index entries left by removed or moved files.
13. Recheck adapter owners, review cadence, CODEOWNERS or equivalent owner
    map, operation catalog, help, routing/health/preview flows, and post-update
    chat message
    templates.
    Recheck the action-authorization policy, phase list, scope invalidation,
    operation request, preview, core/final gates, bridge routing, and intent
    conformance scenarios. Preserve stricter target authorization rules, but
    never preserve reusable cross-scope commit or publication permission.
    Preserve active team task IDs, actor references, claims, checkpoints,
    handoffs, decisions, and external references. Never replace current team
    state with the source placeholder registry.
    Preserve target change-package records. Never replace historical package
    evidence with the source placeholder templates.
    Preserve target durable engineering-evidence IDs, records, task/revision
    bindings and prior-binding lineage, and storage/publication policy. Never replace historical records
    with source placeholders or move them into an external contribution patch
    contrary to target policy.
    Preserve Project Development Model guidance IDs, origins, kinds, promotion
    and direct-decision dispositions, canonical owner bindings and digests,
    route-shard IDs, narrowing/exception and contradiction/supersession
    lineage, mapped/known-gap/unknown coverage, adoption state, reuse evidence,
    retention policy, and review
    authority. Revalidate active accepted facts against their canonical owners,
    rebuild only derived routing and coverage surfaces, and never promote
    historical evidence, arbitrary messages, or source placeholders during an
    update. Version-1 and version-2 knowledge indexes remain historical-
    compatible; new indexes use contract version 3 and classify enabled-empty,
    populated, or reuse-observed adoption without inventing reuse evidence.
    Preserve target Debug Mode IDs, completed records, active-scope state,
    event attribution, timing evidence, publication policy, and compact index.
    Never replace records with source placeholders, silently reactivate a
    closed scope, or move debug files into a clean external contribution.
    Preserve schema-version-1 through version-4 Debug events and records as
    migration-limited evidence; do not silently infer executor versus
    Alatyr-system attribution for versions 1 through 3, or infer actor identity,
    runtime provenance, correction disposition, materiality, claim fidelity,
    continuation, phase coverage, candidate closure, or binding lineage that a
    historical record did not contain. Install Debug contract version 5,
    authoring templates, and derived index projections for new records. In a
    version-5 index, project older records with `legacy` lifecycle scope, empty
    covered phases and candidate IDs, and no expected continuation. Repair
    invalid lifecycle bounds, event roles, durable evidence decisions/references,
    canonical skip claims, and keep active records out of finalized
    comparisons. Never append to a completed record; create a linked
    continuation after explicit activation.
    Preserve engineering-evidence schemas 1 and 2 without fabricated Debug
    links; new schema-version-3 records use reciprocal task-lineage links.
    A finalized historical
    snapshot that no longer matches the current worktree is a reproducibility
    warning, not a reason to rewrite or invalidate the old record.
    Preserve completed effectiveness reports and their measurement evidence
    states. Never rewrite unavailable values as zero or infer executor active
    time from elapsed duration. Preserve delayed-outcome records as append-only
    linked evidence, and retain adapter-maintenance evidence separately from
    product-change effort. Install current authoring templates for later
    records without fabricating historical attention, outcomes, or maintenance
    cost.
    Preserve target code-documentation profiles and decisions. Never replace
    accepted frontend, backend, shared, or infrastructure conventions with
    source placeholders or a universal style.
    Preserve target test-first policies and historical cycle evidence. Never
    replace target commands, trigger severity, isolation, exceptions, CI, or
    merge requirements with source placeholders or silently enable stricter
    behavior.
    Preserve installed extension catalog and lock entries, immutable source
    provenance, target bindings, local deviations, installed-file ownership,
    permissions, approvals, and lifecycle history. Never auto-update an
    extension or replace target bindings with source defaults.
    Preserve dependency knowledge policy, reviewed package-instance state,
    target deviations, retention decisions, and permitted historical
    snapshots. Never activate nested adapters, replace target facts with
    dependency claims, or mark stale exports current during a framework update.
    Preserve accepted workspace identity, modes, per-mode support directories,
    root context, relationships, defaults, and user decision evidence. New
    source templates may produce suggestions but must not replace or silently
    activate target modes.
    Preserve target vocabulary term IDs, definitions, states, owners, aliases,
    acronyms, links, and decisions. Never replace accepted project language
    with source placeholders or inferred definitions.
    Preserve target delegation roles/prompts, role/model and native-definition
    bindings, capability evidence, limits, privacy policy, fallbacks, and
    historical plan/packet/result evidence. Never replace them with source
    placeholders or assume a newly documented model or worker format is
    available on the installed client.
    Preserve target instruction-loading, skill, permission, context-caching,
    diagram, and delegation evidence by assistant ID. Migrate capability
    records to the current schema and add new source surfaces as unknown;
    never replace selected assistant, provider, model, client/runtime, cache
    control, or telemetry facts with template placeholders or evidence from
    another branch, client, account, or runtime variant. If caching cannot be
    reverified, keep the bounded-routing fallback and mark caching unknown.
14. Recheck root assistant entry points and supported bridge files so future
    sessions can find the installation note, operation catalog, health, help,
    and routing flow.
15. Run or report target validation.
    A migration-staging run may retain unresolved target placeholders while
    work is in progress, but it must report `staged`, never `ready` or
    accepted. Resolve active policy, flow, routing, manifest, module-profile,
    and enabled-capability placeholders, then run strict acceptance validation
    on the branch and revision being accepted. Enabled manifest modules and
    human module-profile states must agree before acceptance.
16. Send a post-update assistant chat message that names updated surfaces,
    recommended recheck operation, validation, and unresolved gaps.

Do not use an installer script as the framework mechanism. Do not overwrite
target-specific rules just because the source framework changed.

For an AlatyrCore source release, the release tag must equal `v<VERSION>`.
Reviewed migration evidence must name the exact baseline and all three version
values, compare every shipped schema contract, and bind the baseline and
destination framework, schema, target-template, and version-file trees with
deterministic SHA-256 values. A generated temporary report does not validate a
different committed migration report.

## Change Log Expectations

Framework lifecycle notes should record:

- new framework files or removed files
- framework version, adapter schema version, or template version changes
- added, changed, removed, or deprecated rule IDs
- changed guarantees
- changed adapter contract requirements
- changed portability boundaries
- changed logical integrity, blueprint-driven change, or skill-adaptation
  guidance
- changed approval, safety, testing, diagram, or validation expectations
- support-information rule, policy/state schemas, consistency-map shards and
  reverse index, relationship-candidate lifecycle, impact planner, optional
  generation registry/index, and validator migration
- bridge or supported-assistant compatibility changes
- migration actions required by project adapters
- migration-note requirements for installed adapters
- migration-diff requirements for framework baseline comparisons
- migration-assessment evidence and intentionally omitted context
- adapter recheck results for installed framework updates
- help/routing and post-update chat-message migration needs
- current-scope action-authorization rule, target policy, phase gates,
  conformance scenarios, bridge routing, and final-evidence migration needs
- team-collaboration rule, policy, identity boundary, registry/task schemas,
  active-work route, backend contract, optimistic-concurrency behavior,
  schema-1 record migration, active-record preservation, and post-update stale-
  state review when that module is enabled
- change-package rule, record schema, lazy route, target retention policy,
  provenance grades, and validator migration when that module is enabled
- durable engineering-evidence rule, policy, index/record schema, lazy route,
  capture gate, task/revision binding, privacy/publication boundary, existing-
  record preservation, and validator migration
- Project Development Model guidance rule, direct decision-owner and reviewed
  discovery intake, promotion/index/route-shard schemas, guidance kinds,
  target-owned exceptions, coverage gaps, canonical owner bindings, semantic
  bundle receipts, two-stage routing, authority/freshness states, contradiction
  and supersession lineage, retained target decisions, and validator migration
- Debug Mode rule, module dependencies, explicit activation/expiry, non-
  canonical index/record schema, executor/Alatyr-system/automation role and
  actor identity/provenance attribution, correction disposition,
  timing/capture quality,
  structured architectural impacts, direction-change hypothesis/replacement
  causality, supervision metrics, exact durable evidence reference resolution,
  active-versus-finalized comparison, clean-upstream boundary, record
  preservation, operation, lazy route, and validator migration when that module
  is enabled
- effectiveness metrics schema, evidence-qualified human attention and
  observed-only executor timing, append-only delayed outcomes, adapter-
  maintenance evidence, target storage policy, and validator migration when
  that module is enabled
- code-documentation rule, catalog/profile schemas, source-set selection,
  accepted style decisions, generator/output policy, adapted skill, lazy
  route, and validator migration when that module is enabled
- project-vocabulary rule, catalog/term/data-link schemas, scoped meanings,
  acceptance decisions, normalization policy, adapted skill, lazy route, and
  validator migration when that module is enabled
- test-first rule, policy schema, recommendation/enablement boundaries,
  triggers, modes, commands, isolation, exceptions, evidence, adapted skill,
  lazy route, and validator migration when that module is enabled
- extension rule, extension API and package template, catalog/lock schemas,
  lifecycle operation, ownership/removal behavior, bindings, permissions,
  bridges, lazy route, inspection tooling, and validator migration when that
  module is enabled
- dependency knowledge rule, export API and package template, target policy,
  catalog, knowledge lock, deviations, snapshot policy, routing, gate,
  operation, and validator migration when that module is enabled
- workspace-mode rule, catalog, root context, per-mode descriptor contract,
  suggestion/selection flow, preflight, routing, gate, operation, and validator
  migration when that module is enabled
- subagent delegation rule, target policy, worker roles/prompts, capability
  records, role/model/native-definition bindings, task-plan/packet/result and
  overlay contracts, retry/conflict fallbacks, and validator migration when
  that module is enabled

## Deprecation

When a framework rule is replaced:

- mark the old rule as deprecated or remove it in the same coherent update
- update adapters, prompts, skills, bridge files, and consistency checks that
  refer to it
- explain the migration path
- avoid leaving two canonical owners for the same rule

## Rejection Criteria

Reject lifecycle changes that:

- silently change framework guarantees
- weaken adapter requirements without explicit rationale
- overwrite target adapter facts during upgrade
- copy source project commands or business facts into framework core
- omit migration notes for supported assistants or bridge files
- omit bridge capability changes from upgrade evidence
- preserve stale or unsupported provider-cache claims after the selected
  assistant, model, account, or client changes
- overwrite active team records from a source template or omit enabled-team
  migration evidence
- claim upgrade success without validation or residual-risk evidence
- claim an update is complete from migration-staging evidence, unresolved
  active placeholders, module manifest/profile drift, or validation performed
  on a different branch or revision
