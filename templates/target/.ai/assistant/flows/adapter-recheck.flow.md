# Adapter Recheck Flow

Use this flow after installing or updating Alatyr Core in `{PROJECT_NAME}`, or
when the programmer asks whether the installed adapter is still coherent.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Framework baseline/source: `{ALATYR_CORE_SOURCE_OR_BASELINE}`
- Adapter manifest: `.ai/alatyr.yaml`
- Installation or update note: `{INSTALLATION_OR_UPDATE_NOTE}`
- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Consistency map: `.ai/project/consistency-map.json`
- Context router: `.ai/assistant/context-router.json`
- Context profiles: `.ai/assistant/context-profiles.md`
- Module profile: `.ai/assistant/module-profile.md`
- Maturity profile: `.ai/assistant/maturity-profile.md`
- Bridge capability matrix: `.ai/assistant/bridge-capability-matrix.md`
- Target validation: `{TARGET_VALIDATION}`
- Supported assistants: `{SUPPORTED_ASSISTANTS}`
- Operation index, catalog, help, routing, health, and preview:
  `.ai/assistant/operation-index.json`,
  `.ai/assistant/operation-catalog.json`, `.ai/assistant/help.md`,
  `.ai/assistant/flows/operation-routing.flow.md`,
  `.ai/assistant/flows/adapter-health.flow.md`,
  `.ai/assistant/templates/pre-change-preview.md`
- Diagram discussion: `.ai/assistant/flows/diagram-discussion.flow.md`,
  `.ai/assistant/templates/diagram-presentation.md`,
  `.ai/assistant/assistant-capabilities.json`, and its human bridge-matrix
  reference
- Architecture knowledge: `.ai/project/architecture/README.md`,
  `.ai/project/architecture/catalog.json`,
  `.ai/assistant/context/intents/architecture-request.json`,
  `.ai/assistant/flows/architecture-assistance.flow.md`, and architecture
  pattern/area/result templates
- Code documentation: `.ai/project/documentation/README.md`,
  `.ai/project/documentation/catalog.json`,
  `.ai/project/documentation/profiles.json`,
  `.ai/assistant/context/intents/code-documentation.json`, documentation flow,
  profile-review template, and adapted skill
- Project vocabulary: `.ai/project/vocabulary/README.md`, catalog, full term
  records, data-dictionary links, vocabulary intent, flow, term-review
  template, and adapted skill
- Test-first development: `.ai/project/testing/README.md`, accepted policy,
  intent, configuration/change flows, gate, evidence template, and adapted skill
- Extensions: `.ai/assistant/extensions/README.md`, catalog, lock, intent,
  lifecycle flow, gate, review/lifecycle records, bindings, normalized items,
  installed-file ownership, and adaptation evidence
- AI infrastructure inventory:
  `.ai/assistant/flows/ai-infrastructure-inventory.flow.md`
- AI infrastructure recommendation:
  `.ai/assistant/flows/ai-infrastructure-recommendation.flow.md`,
  `.ai/assistant/templates/ai-infrastructure-recommendation.md`
- Development pattern evidence:
  `.ai/project/development-evidence.json`,
  `.ai/assistant/flows/development-evidence-capture.flow.md`
- Durable engineering evidence: `.ai/project/engineering-evidence/README.md`,
  compact index, selected records, task-scale overlay, capture flow, gate, and
  machine template
- Debug Mode when enabled: `.ai/project/debug/README.md`, compact index,
  selected records, task-scale overlay, operation flow, gate, machine record,
  and summary template
- AI infrastructure router, recommendation, and adaptation record:
  `.ai/assistant/ai-infrastructure-router.json`,
  `.ai/assistant/templates/ai-infrastructure-adaptation-record.md`
- Chat-message templates: `.ai/assistant/templates/post-install-message.md`,
  `.ai/assistant/templates/post-update-message.md`
- Migration note template: `.ai/assistant/templates/migration-note.md`
- Effectiveness report template:
  `.ai/assistant/templates/effectiveness-report.md`
- Large-task flow and packet: `.ai/assistant/flows/large-task-orchestration.flow.md`,
  `.ai/assistant/templates/large-task-operation-packet.md`
- Change-package index, flow, and record:
  `.ai/assistant/change-packages/index.json`,
  `.ai/assistant/flows/change-package.flow.md`,
  `.ai/assistant/templates/change-package-record.json`
- Team collaboration: `.ai/project/team-operating-model.md`,
  `.ai/assistant/team/context-overlay.json`,
  `.ai/assistant/team/work-registry.json`,
  `.ai/assistant/flows/team-task-coordination.flow.md`,
  `.ai/assistant/flows/team-handoff.flow.md`,
  `.ai/assistant/flows/team-decision.flow.md`,
  `.ai/assistant/flows/team-review.flow.md`,
  `.ai/assistant/gates/team-collaboration.md`
- Known adapter gaps: `{KNOWN_GAPS}`

## Steps

1. Treat `AGENTS.md` as preloaded, load the compact bootstrap, and select the
   `framework-upgrade` profile plus only affected adapter areas. Do not load
   all `.ai/project` or `.ai/assistant` files before identifying the recheck
   scope.
2. Identify whether this is a post-installation recheck, framework update
   recheck, bridge compatibility review, or maturity audit.
3. Prepare or review migration assessment evidence before target changes.
   Compare rule registries, installed and next framework files, framework
   version, adapter schema version, template version, and current structural
   validator findings.
4. Use affected canonical sources, rule categories, task profiles, template
   surfaces, bridge capabilities, and local deviations from that assessment to
   select additional context. Do not load the full framework corpus by default.
5. Compare installed framework files against the recorded framework baseline or
   update source.
6. Compare framework version, adapter schema version, template version, module
   states, known gaps, local deviations, and owner facts in `.ai/alatyr.yaml`.
7. Check required core and optional module state in
   `.ai/assistant/module-profile.md`. Require every manifest-enabled module to
   have exactly one `enabled` or `required` profile block, and reject a profile
   block in either state when the manifest does not enable it.
8. Check target adapter references to framework files, operation help, routing
   flows, AI infrastructure inventory, recommendation and item router, gates,
   prompts, skills, recommendation/adaptation records, bridge files,
   checker rules, operation catalog and health/preview contracts, large-task
   flow and packet, change-package index/flow/schema, team operating
   model/registry/flows/gate/templates,
   durable engineering-evidence policy/index/overlay/flow/gate/schema,
   Debug Mode policy/index/overlay/operation/flow/gate/schema/summary when
   enabled,
   chat-message templates, and final-evidence expectations.
9. Check adapter drift hazards: hard-coded local machine paths in `.ai/*`,
   root assistant entry points, bridge files, templates, and policies; stale
   statements about whether local Alatyr or adapter checkers exist; duplicate
   required-context references inside context profiles or router entries;
   missing `.ai/assistant/context-router.json` references where bootstrap
   routing is described; unresolved owner placeholders that are not recorded as
   known gaps; and target-local adapter checker evidence that no longer matches
   repository files.
10. Check project blueprint/source-of-truth ownership, registry entries,
   consistency-map nodes and edges when enabled, exact registry Fact Type to
   node-ID and node-`fact_type` agreement, missing facts, stale relationships,
   and drift. Treat registry, map, consistency routing, measured semantic
   context, and generated bootstrap evidence as one adapter sync set. Reject
   live support surfaces that still describe an enabled module as deferred,
   disabled, blocked, or not installed.
    When architecture knowledge is enabled, check catalog ownership, decision
    authority, item states, selected evidence, revision freshness,
    documentation routes, contradictions, and accepted-decision handoff.
11. Check security, live-service, destructive-operation, dependency, credential,
   diagram, generated-artifact, validation, and lifecycle policies.
12. Check task-specific maturity using `.ai/assistant/maturity-profile.md` when
   it exists.
13. Check bridge behavior using `.ai/assistant/bridge-capability-matrix.md`.
    When diagrams are enabled, verify discussion routing, source/visual
    ownership, inline or artifact capability claims, portable ASCII, and
    stale-view evidence for every supported assistant.
14. When team collaboration is enabled, preserve active task IDs and external
    references; check coordination backend direction, actors and authority,
    stale claims, evidence revisions, concurrent changed-fact overlaps,
    checkpoints, handoffs, decisions, review state, and merge-readiness
    invalidation.
    When change packages are enabled, preserve historical target records and
    check semantic approval fields, companion decisions, correction impact,
    provenance quality, and target validator support.
    Preserve durable engineering-evidence IDs and records, then recheck task
    and repository bindings, index synchronization, canonical-owner links,
    privacy flags, external-patch policy, and existing-record accessibility.
    When Debug Mode is enabled, preserve IDs, records, active-scope evidence,
    events, timing, metrics, and target policy; recheck explicit activation and
    expiry, non-canonical authority, causal attribution, privacy, observer
    effect, compact index sync, result binding, clean-upstream projection, and
    validator support. Never reactivate a closed scope during update.
    When test-first development is enabled, preserve target commands, trigger
    severity, modes, levels, isolation, exceptions, policy revision, and
    historical evidence; recheck recommendation and RED/GREEN routing without
    silently enabling new CI or merge requirements.
    When extensions are enabled, preserve catalog and lock IDs, immutable
    source revisions/digests, target bindings, permissions, approvals, local
    deviations, installed-file ownership, and historical lifecycle evidence;
    recheck compatibility and drift without automatic updates.
15. Identify required migrations, approvals, unresolved facts, and skipped
   checks.
   Recheck `.ai/assistant/policies/action-authorization.json`, root assistant
   entry points, operation request, preview, core gate, final-evidence gate,
   bridge matrix, and conformance scenarios. Confirm subject-only issue/backlog
   transitions remain read-only and prior commit/publish authorization is not
   reusable.
16. Use `.ai/assistant/templates/migration-note.md` when a framework update
    requires target migration evidence.
17. Use `.ai/assistant/templates/effectiveness-report.md` only when comparing
    adapter effectiveness across comparable tasks or adapter states.
18. Run target validation that exists. Do not invent commands.
    Use `migration-staging` only while adapting unresolved target facts. It may
    produce a non-blocking work inventory, but it must not produce `ready`,
    accepted, or complete evidence. Before accepting an installation or
    update, resolve active placeholders and rerun strict `acceptance`
    validation on the checked-out branch/revision.
19. Classify final evidence as `current-state`, `historical-record`, or `mixed`.
    Current files prove current structure only; name dated operation, approval,
    validation, or migration records before making historical claims.
20. Report final evidence and residual risk.

## Final Evidence

Report:

- recheck type
- framework baseline or update source
- migration assessment and affected canonical sources selected from it
- candidate context intentionally omitted with reasons
- framework version, adapter schema version, and template version
- files inspected
- evidence basis, observation time, and repository revision when available
- checked-out branch, validation phase, active unresolved-placeholder count,
  manifest/module-profile agreement, acceptance eligibility, and the final
  strict rerun when staging was used
- historical records used and historical claims that remain unverifiable
- adapter references changed or still current
- action-authorization policy and routed surfaces current, including phase
  separation, scope invalidation, explicit publication intent, delegation
  inheritance, and `current_user_authorization` evidence
- adapter drift checks result, including local path leakage, stale checker
  statements, duplicate profile references, context-router references, owner
  placeholders, and target-local checker evidence
- blueprint/source-of-truth registry status
- consistency-map relationship coverage and staleness status
- architecture catalog owner, decision authority, states, selected evidence,
  validation, contradictions, and revision status
- context router and context profile status
- module profile status
- code-documentation profile ownership, source-set match ambiguity, accepted
  state, canonical fact boundaries, generator/output policy, direct-edit rule,
  adapted skill, validation, and evidence revision
- project-vocabulary ownership, term decision authority, scoped state and
  ambiguity, alias/acronym lookup, canonical sources, data links,
  normalization boundaries, adapted skill, validation, and evidence revision
- test-first policy owner, authority, state, trigger severity, modes, levels,
  commands, isolation, exceptions, recommendation behavior, adapted skill,
  RED/GREEN evidence contract, validation, and evidence revision
- extension state owner, catalog/lock consistency, source revision/digest,
  license and compatibility, target bindings, permissions, approval,
  installed-file hashes/ownership, dependents, update/removal safety, and
  lifecycle evidence
- catalog, automatic routing, health, preview, help, AI infrastructure
  inventory/recommendation, bridge, prompt,
  skill, gate, checker, item router, recommendation/adaptation records,
  large-task orchestration, diagram, chat-message, and lifecycle status
- team module owner/backend, active registry schema and references, stale
  claims, overlaps, handoffs, decision destinations, review evidence, and
  revision-bound merge readiness
- change-package index, record schema, target record preservation, semantic
  approval scope, provenance policy, and validator support
- development-pattern index schema, owner, retention/privacy policy, evidence
  references, and target-only optimization boundary
- durable engineering-evidence owner, retained storage and external-patch
  policy, compact index/record synchronization, task/revision binding,
  canonical-owner links, privacy, validation, and unresolved access gaps
- Debug Mode module/dependency state, non-canonical owner/policy, active scope
  or inactive state, index/record synchronization, attribution, timing/capture
  quality, event-derived metrics, result binding, clean-upstream boundary,
  validation, and unresolved gaps
- bridge capability matrix status
- diagram discussion presentation, ASCII readability, and source-revision status
- target validation run or unresolved
- approvals needed
- task-specific maturity level and gaps
- migration note created or not needed
- residual risk

## Rejection Criteria

Reject or revise recheck work that:

- claims success without inspecting the installed target adapter
- overwrites target facts just because the source framework changed
- copies Alatyr Core source-repository commands into the target
- ignores supported assistant bridge drift
- hides missing validation, missing approval, or maturity gaps
