# Rule Ownership

This file is generated from `framework/rule-registry.json`. Source owners
under `framework/` define rule semantics in AlatyrCore. Installed owners under
`.ai/framework/` are deterministic target-adapter projections of those source
owners. Category routing owners group related rules for maintainers and tools
but do not become additional semantic owners.
Derived documents should reference the owner or rule ID and avoid copying
the complete policy language.

## Ownership Rules

- Change the canonical owner document before changing a rule summary.
- Keep installer, template, bridge, and help wording as short references.
- Keep owner front matter aligned with registered IDs and dependencies.
- Record material contract changes in the changelog and migration evidence.

## Category Routing Owners

Category: `CONTEXT`
Source routing owner: `framework/context-profiles.md`
Installed routing owner: `.ai/framework/context-profiles.md`
Rule IDs: `ALATYR-CONTEXT-001`
Derived surfaces: README source context, installation source context, target
context profiles, target context router, recursive contour context indexes,
semantic codebook and resolved context packets, task-scale overlays, operation
packet context receipts, ordered semantic-guidance identity and bundle
receipts, long-task semantic revalidation, consistency relationship routing,
session bootstrap instructions, AI infrastructure capability and recommendation
routing.

Category: `SOURCE`
Source routing owner: `framework/source-of-truth-registry.md`
Installed routing owner: `.ai/framework/source-of-truth-registry.md`
Rule IDs: `ALATYR-SOURCE-001`
Derived surfaces: project adapter contract, logical integrity, blueprint
change, target source-of-truth registry template, invariant constraints,
consistency map.

Category: `RISK`
Source routing owner: `framework/change-risk-model.md`
Installed routing owner: `.ai/framework/change-risk-model.md`
Rule IDs: `ALATYR-RISK-001`
Derived surfaces: installer approval planning, target gates, operation request
templates, external failure observability, final evidence.

Category: `APPROVAL`
Source routing owner: `framework/approval-records.md`
Installed routing owner: `.ai/framework/approval-records.md`
Rule IDs: `ALATYR-APPROVAL-001`
Derived surfaces: installation approval gate, installed-operation allowed
actions, human and machine-readable approval templates, strict target diff
scope validation, security-sensitive profiles.

Category: `AUTHORIZATION`
Source routing owner: `framework/action-authorization.md`
Installed routing owner: `.ai/framework/action-authorization.md`
Rule IDs: `ALATYR-AUTHORIZATION-001`
Derived surfaces: source and target assistant entry points, installed-operation
routing, action-authorization policy, operation request and preview, core and
final-evidence gates, subagent and team boundaries, target structural
validation, authorization conformance scenarios.

Category: `SAFETY`
Source routing owner: `framework/security-safety-guidance.md`
Installed routing owner: `.ai/framework/security-safety-guidance.md`
Rule IDs: `ALATYR-SAFETY-001`, `ALATYR-SAFETY-002`
Derived surfaces: prompt-injection guidance, skill adaptation, source-access
policy, adaptation records, security-sensitive context profile.

Category: `INTEGRITY`
Source routing owner: `framework/logical-integrity.md`
Installed routing owner: `.ai/framework/logical-integrity.md`
Rule IDs: `ALATYR-INTEGRITY-001`
Derived surfaces: target gates, documentation sync, adapter recheck,
relationship or manual invariant impact closure, review-item reconciliation,
workstream convergence, final evidence.

Category: `CHANGE`
Source routing owner: `framework/blueprint-driven-change.md`
Installed routing owner: `.ai/framework/blueprint-driven-change.md`
Rule IDs: `ALATYR-CHANGE-001`
Derived surfaces: product-change operation, blueprint-driven target flow,
large-task orchestration, documentation and diagram sync.

Category: `PACKAGE`
Source routing owner: `framework/change-packages.md`
Installed routing owner: `.ai/framework/change-packages.md`
Rule IDs: `ALATYR-PACKAGE-001`
Derived surfaces: change-package target flow and records, semantic approval
scope, large-task convergence, blueprint change, target validation, installer
module selection, migration evidence.

Category: `ARCHITECTURE`
Source routing owner: `framework/architecture-knowledge.md`
Installed routing owner: `.ai/framework/architecture-knowledge.md`
Rule IDs: `ALATYR-ARCHITECTURE-001`
Derived surfaces: target architecture index and catalog, pattern and area
templates, architecture-assistance operation, architecture intent routing,
architecture discussion result, installation and update planning, target gates,
architecture validation.

Category: `CODEDOC`
Source routing owner: `framework/code-documentation.md`
Installed routing owner: `.ai/framework/code-documentation.md`
Rule IDs: `ALATYR-CODEDOC-001`
Derived surfaces: target code-documentation catalog and profiles, documentation
intent routing, documentation synchronization flow, project-adapted comment
skill, profile review template, generated-output policy, installation and
update planning, target gates, structural validation.

Category: `VOCABULARY`
Source routing owner: `framework/project-vocabulary.md`
Installed routing owner: `.ai/framework/project-vocabulary.md`
Rule IDs: `ALATYR-VOCABULARY-001`
Derived surfaces: target vocabulary catalog, term records, data-dictionary link
records, project semantic-term namespace, vocabulary intent routing,
project-vocabulary operation flow, project-adapted vocabulary skill, term
review template, installation and update planning, target gates, structural
validation.

Category: `TDD`
Source routing owner: `framework/test-first-development.md`
Installed routing owner: `.ai/framework/test-first-development.md`
Rule IDs: `ALATYR-TDD-001`
Derived surfaces: target test-first policy, recommendation gate, configuration
and change operations, test-first intent routing, project-adapted test-first
skill, test-first gate, RED GREEN refactor evidence template, installation and
update planning, structural validation.

Category: `EXTENSION`
Source routing owner: `framework/extensions.md`
Installed routing owner: `.ai/framework/extensions.md`
Rule IDs: `ALATYR-EXTENSION-001`
Derived surfaces: external extension package template, extension inspection
tool, target extension catalog and lock, extension lifecycle flow, extension
intent routing, extension review and lifecycle evidence, module profile, target
gates, installation and update planning, bridge routing, structural validation.

Category: `DEPENDENCY`
Source routing owner: `framework/dependency-knowledge.md`
Installed routing owner: `.ai/framework/dependency-knowledge.md`
Rule IDs: `ALATYR-DEPENDENCY-001`
Derived surfaces: passive dependency export template, target dependency
knowledge policy catalog lock deviations and snapshots, dependency knowledge
intent routing, dependency synchronization flow, dependency knowledge gate,
operation catalog and help, installation and update planning, structural
validation.

Category: `MODE`
Source routing owner: `framework/workspace-modes.md`
Installed routing owner: `.ai/framework/workspace-modes.md`
Rule IDs: `ALATYR-MODE-001`
Derived surfaces: target workspace-mode catalog, shared root context, per-mode
directories and descriptors, workspace-mode intent and flow, mode suggestion
and preflight, workspace-mode gate, installation and update suggestions,
structural validation.

Category: `DIAGRAM`
Source routing owner: `framework/diagram-guidance.md`
Installed routing owner: `.ai/framework/diagram-guidance.md`
Rule IDs: `ALATYR-DIAGRAM-001`
Derived surfaces: portable ASCII diagram grammar, target diagram discussion
flow, ASCII and diagram presentation templates, operation catalog and compact
index, context intent routing, bridge capability matrix, compact assistant
capabilities, operation conformance fixture, installation planning, adapter
recheck, diagram validation evidence.

Category: `ADAPTER`
Source routing owner: `framework/project-adapter-contract.md`
Installed routing owner: `.ai/framework/project-adapter-contract.md`
Rule IDs: `ALATYR-ADAPTER-001`
Derived surfaces: installation plan, readiness checklist, manifest template,
adapter recheck flow, target development-pattern evidence, framework pack and
projected inventory, recursive target context indexes, semantic codebook
binding, context packet template, AI infrastructure router, AI infrastructure
recommendation contract, AI infrastructure item contracts.

Category: `MODULE`
Source routing owner: `framework/module-profile.md`
Installed routing owner: `.ai/framework/module-profile.md`
Rule IDs: `ALATYR-MODULE-001`
Derived surfaces: target module profile, manifest modules, framework pack
catalog, scaffold profile-to-pack mapping, operation help routing, maturity
review.

Category: `OPERATION`
Source routing owner: `framework/operation-help.md`
Installed routing owner: `.ai/framework/operation-help.md`
Rule IDs: `ALATYR-OPERATION-001`
Derived surfaces: target operation catalog, checked compact operation index,
automatic routing flow, compact help, adapter health flow, pre-change preview,
manifest operation paths, assistant bridges.

Category: `TEAM`
Source routing owner: `framework/team-collaboration.md`
Installed routing owner: `.ai/framework/team-collaboration.md`
Rule IDs: `ALATYR-TEAM-001`
Derived surfaces: structured target team policy, human team operating model,
ignored local actor selection, active-work index, work registry metadata,
per-task records, backend contract, task claims, conflict review, checkpoints,
handoffs, decision records, team review, merge-readiness evidence, operation
routes, team-active context overlay, adapted team skill.

Category: `DELEGATION`
Source routing owner: `framework/subagent-delegation.md`
Installed routing owner: `.ai/framework/subagent-delegation.md`
Rule IDs: `ALATYR-DELEGATION-001`
Derived surfaces: target delegation policy, worker role catalog and prompts,
worker execution plan, delegated-execution overlay, subagent task packet,
normalized worker result, large-task workstreams, assistant capability records
and native bindings, bridge capability matrix, operation routing, installation
and update planning, delegation conformance scenarios, structural validation.

Category: `BRIDGE`
Source routing owner: `framework/bridge-capability-matrix.md`
Installed routing owner: `.ai/framework/bridge-capability-matrix.md`
Rule IDs: `ALATYR-BRIDGE-001`
Derived surfaces: assistant bridge templates, bridge renderer, bridge
capability target template, cross-assistant AI item routing.

Category: `LIFECYCLE`
Source routing owner: `framework/lifecycle.md`
Installed routing owner: `.ai/framework/lifecycle.md`
Rule IDs: `ALATYR-LIFECYCLE-001`
Derived surfaces: version files, installed framework pack, migration notes,
framework update recheck, recursive context-index rebuild, semantic-codebook
migration, project-guidance contract migration, Debug attribution migration,
effectiveness and maintenance evidence migration, changelog.

Category: `ENGINEERING_EVIDENCE`
Source routing owner: `framework/engineering-evidence.md`
Installed routing owner: `.ai/framework/engineering-evidence.md`
Rule IDs: `ALATYR-ENGINEERING-EVIDENCE-001`
Derived surfaces: target evidence index and records, capture flow, finalization
gate, task-scale routing, operation help, change-package links, target
validation, installation and migration planning.

Category: `PROJECT_KNOWLEDGE`
Source routing owner: `framework/project-knowledge.md`
Installed routing owner: `.ai/framework/project-knowledge.md`
Rule IDs: `ALATYR-KNOWLEDGE-001`
Derived surfaces: target Project Development Model guidance policy and routing
index, engineering-discovery and direct decision-owner intake, promotion and
route-shard templates, guidance kind and exception semantics, coverage and
known-gap projection, two-stage semantic context routing, knowledge operation
and gate, target validation, shared-will conformance, paired rediscovery
benchmark.

Category: `DEBUG`
Source routing owner: `framework/debug-mode.md`
Installed routing owner: `.ai/framework/debug-mode.md`
Rule IDs: `ALATYR-DEBUG-001`
Derived surfaces: optional target debug index and records, task-local
activation and expiry, executor versus Alatyr-system attribution, actor
identity and runtime provenance, correction disposition and guidance-failure
routing, capture-quality and timing evidence, event-derived supervision
metrics, clean upstream projection, compact debug summary, target validation,
installation and migration planning.

Category: `SUPPORT`
Source routing owner: `framework/support-information.md`
Installed routing owner: `.ai/framework/support-information.md`
Rule IDs: `ALATYR-SUPPORT-001`
Derived surfaces: target support policy and state, consistency-map shards and
reverse index, relationship candidate records, bounded impact reports, optional
support-generation registry and index, logical-integrity and final evidence,
installation update and target validation.

Category: `EVIDENCE`
Source routing owner: `framework/guarantees.md`
Installed routing owner: `.ai/framework/guarantees.md`
Rule IDs: `ALATYR-EVIDENCE-001`
Derived surfaces: final evidence, process commitments, conformance reports,
effectiveness reports, evidence-qualified human attention and executor timing,
later-linked delayed outcomes, adapter-maintenance evidence, operation packets.

## Rule Canonical Owners

Rule: `ALATYR-CONTEXT-001`
Source canonical owner: `framework/context-profiles.md`
Installed canonical owner: `.ai/framework/context-profiles.md`

Rule: `ALATYR-SOURCE-001`
Source canonical owner: `framework/source-of-truth-registry.md`
Installed canonical owner: `.ai/framework/source-of-truth-registry.md`

Rule: `ALATYR-RISK-001`
Source canonical owner: `framework/change-risk-model.md`
Installed canonical owner: `.ai/framework/change-risk-model.md`

Rule: `ALATYR-APPROVAL-001`
Source canonical owner: `framework/approval-records.md`
Installed canonical owner: `.ai/framework/approval-records.md`

Rule: `ALATYR-AUTHORIZATION-001`
Source canonical owner: `framework/action-authorization.md`
Installed canonical owner: `.ai/framework/action-authorization.md`

Rule: `ALATYR-SAFETY-001`
Source canonical owner: `framework/security-safety-guidance.md`
Installed canonical owner: `.ai/framework/security-safety-guidance.md`

Rule: `ALATYR-SAFETY-002`
Source canonical owner: `framework/prompt-injection.md`
Installed canonical owner: `.ai/framework/prompt-injection.md`

Rule: `ALATYR-INTEGRITY-001`
Source canonical owner: `framework/logical-integrity.md`
Installed canonical owner: `.ai/framework/logical-integrity.md`

Rule: `ALATYR-SUPPORT-001`
Source canonical owner: `framework/support-information.md`
Installed canonical owner: `.ai/framework/support-information.md`

Rule: `ALATYR-CHANGE-001`
Source canonical owner: `framework/blueprint-driven-change.md`
Installed canonical owner: `.ai/framework/blueprint-driven-change.md`

Rule: `ALATYR-PACKAGE-001`
Source canonical owner: `framework/change-packages.md`
Installed canonical owner: `.ai/framework/change-packages.md`

Rule: `ALATYR-ENGINEERING-EVIDENCE-001`
Source canonical owner: `framework/engineering-evidence.md`
Installed canonical owner: `.ai/framework/engineering-evidence.md`

Rule: `ALATYR-KNOWLEDGE-001`
Source canonical owner: `framework/project-knowledge.md`
Installed canonical owner: `.ai/framework/project-knowledge.md`

Rule: `ALATYR-DEBUG-001`
Source canonical owner: `framework/debug-mode.md`
Installed canonical owner: `.ai/framework/debug-mode.md`

Rule: `ALATYR-ARCHITECTURE-001`
Source canonical owner: `framework/architecture-knowledge.md`
Installed canonical owner: `.ai/framework/architecture-knowledge.md`

Rule: `ALATYR-CODEDOC-001`
Source canonical owner: `framework/code-documentation.md`
Installed canonical owner: `.ai/framework/code-documentation.md`

Rule: `ALATYR-VOCABULARY-001`
Source canonical owner: `framework/project-vocabulary.md`
Installed canonical owner: `.ai/framework/project-vocabulary.md`

Rule: `ALATYR-TDD-001`
Source canonical owner: `framework/test-first-development.md`
Installed canonical owner: `.ai/framework/test-first-development.md`

Rule: `ALATYR-EXTENSION-001`
Source canonical owner: `framework/extensions.md`
Installed canonical owner: `.ai/framework/extensions.md`

Rule: `ALATYR-DEPENDENCY-001`
Source canonical owner: `framework/dependency-knowledge.md`
Installed canonical owner: `.ai/framework/dependency-knowledge.md`

Rule: `ALATYR-MODE-001`
Source canonical owner: `framework/workspace-modes.md`
Installed canonical owner: `.ai/framework/workspace-modes.md`

Rule: `ALATYR-DIAGRAM-001`
Source canonical owner: `framework/diagram-guidance.md`
Installed canonical owner: `.ai/framework/diagram-guidance.md`

Rule: `ALATYR-ADAPTER-001`
Source canonical owner: `framework/project-adapter-contract.md`
Installed canonical owner: `.ai/framework/project-adapter-contract.md`

Rule: `ALATYR-MODULE-001`
Source canonical owner: `framework/module-profile.md`
Installed canonical owner: `.ai/framework/module-profile.md`

Rule: `ALATYR-OPERATION-001`
Source canonical owner: `framework/operation-help.md`
Installed canonical owner: `.ai/framework/operation-help.md`

Rule: `ALATYR-TEAM-001`
Source canonical owner: `framework/team-collaboration.md`
Installed canonical owner: `.ai/framework/team-collaboration.md`

Rule: `ALATYR-DELEGATION-001`
Source canonical owner: `framework/subagent-delegation.md`
Installed canonical owner: `.ai/framework/subagent-delegation.md`

Rule: `ALATYR-BRIDGE-001`
Source canonical owner: `framework/bridge-capability-matrix.md`
Installed canonical owner: `.ai/framework/bridge-capability-matrix.md`

Rule: `ALATYR-LIFECYCLE-001`
Source canonical owner: `framework/lifecycle.md`
Installed canonical owner: `.ai/framework/lifecycle.md`

Rule: `ALATYR-EVIDENCE-001`
Source canonical owner: `framework/guarantees.md`
Installed canonical owner: `.ai/framework/guarantees.md`

## Change Protocol

1. Update the owning framework document and its `alatyr_doc` metadata.
2. Update `framework/rule-registry.json`.
3. Regenerate this file and `framework/rule-registry.md`.
4. Update affected installer, target, checker, and conformance surfaces.
5. Keep assistant bridges as pointers.
6. Record behavioral changes in `CHANGELOG.md` and migration evidence.
