# Rule Ownership

This file is generated from `framework/rule-registry.json`. Per-rule canonical
owners define rule semantics. Category routing owners group related rules for
maintainers and tools but do not become additional semantic owners.
Derived documents should reference the owner or rule ID and avoid copying
the complete policy language.

## Ownership Rules

- Change the canonical owner document before changing a rule summary.
- Keep installer, template, bridge, and help wording as short references.
- Keep owner front matter aligned with registered IDs and dependencies.
- Record material contract changes in the changelog and migration evidence.

## Category Routing Owners

Category: `CONTEXT`
Routing owner: `.ai/framework/context-profiles.md`
Rule IDs: `ALATYR-CONTEXT-001`
Derived surfaces: README source context, installation source context, target
context profiles, target context router, task-scale overlays, operation packet
context receipts, consistency relationship routing, session bootstrap
instructions, AI infrastructure capability and recommendation routing.

Category: `SOURCE`
Routing owner: `.ai/framework/source-of-truth-registry.md`
Rule IDs: `ALATYR-SOURCE-001`
Derived surfaces: project adapter contract, logical integrity, blueprint
change, target source-of-truth registry template, invariant constraints,
consistency map.

Category: `RISK`
Routing owner: `.ai/framework/change-risk-model.md`
Rule IDs: `ALATYR-RISK-001`
Derived surfaces: installer approval planning, target gates, operation request
templates, external failure observability, final evidence.

Category: `APPROVAL`
Routing owner: `.ai/framework/approval-records.md`
Rule IDs: `ALATYR-APPROVAL-001`
Derived surfaces: installation approval gate, installed-operation allowed
actions, human and machine-readable approval templates, strict target diff
scope validation, security-sensitive profiles.

Category: `AUTHORIZATION`
Routing owner: `.ai/framework/action-authorization.md`
Rule IDs: `ALATYR-AUTHORIZATION-001`
Derived surfaces: source and target assistant entry points, installed-operation
routing, action-authorization policy, operation request and preview, core and
final-evidence gates, subagent and team boundaries, target structural
validation, authorization conformance scenarios.

Category: `SAFETY`
Routing owner: `.ai/framework/security-safety-guidance.md`
Rule IDs: `ALATYR-SAFETY-001`, `ALATYR-SAFETY-002`
Derived surfaces: prompt-injection guidance, skill adaptation, source-access
policy, adaptation records, security-sensitive context profile.

Category: `INTEGRITY`
Routing owner: `.ai/framework/logical-integrity.md`
Rule IDs: `ALATYR-INTEGRITY-001`
Derived surfaces: target gates, documentation sync, adapter recheck,
relationship or manual invariant impact closure, review-item reconciliation,
workstream convergence, final evidence.

Category: `CHANGE`
Routing owner: `.ai/framework/blueprint-driven-change.md`
Rule IDs: `ALATYR-CHANGE-001`
Derived surfaces: product-change operation, blueprint-driven target flow,
large-task orchestration, documentation and diagram sync.

Category: `PACKAGE`
Routing owner: `.ai/framework/change-packages.md`
Rule IDs: `ALATYR-PACKAGE-001`
Derived surfaces: change-package target flow and records, semantic approval
scope, large-task convergence, blueprint change, target validation, installer
module selection, migration evidence.

Category: `ARCHITECTURE`
Routing owner: `.ai/framework/architecture-knowledge.md`
Rule IDs: `ALATYR-ARCHITECTURE-001`
Derived surfaces: target architecture index and catalog, pattern and area
templates, architecture-assistance operation, architecture intent routing,
architecture discussion result, installation and update planning, target gates,
architecture validation.

Category: `CODEDOC`
Routing owner: `.ai/framework/code-documentation.md`
Rule IDs: `ALATYR-CODEDOC-001`
Derived surfaces: target code-documentation catalog and profiles, documentation
intent routing, documentation synchronization flow, project-adapted comment
skill, profile review template, generated-output policy, installation and
update planning, target gates, structural validation.

Category: `VOCABULARY`
Routing owner: `.ai/framework/project-vocabulary.md`
Rule IDs: `ALATYR-VOCABULARY-001`
Derived surfaces: target vocabulary catalog, term records, data-dictionary link
records, vocabulary intent routing, project-vocabulary operation flow,
project-adapted vocabulary skill, term review template, installation and update
planning, target gates, structural validation.

Category: `TDD`
Routing owner: `.ai/framework/test-first-development.md`
Rule IDs: `ALATYR-TDD-001`
Derived surfaces: target test-first policy, recommendation gate, configuration
and change operations, test-first intent routing, project-adapted test-first
skill, test-first gate, RED GREEN refactor evidence template, installation and
update planning, structural validation.

Category: `EXTENSION`
Routing owner: `.ai/framework/extensions.md`
Rule IDs: `ALATYR-EXTENSION-001`
Derived surfaces: external extension package template, extension inspection
tool, target extension catalog and lock, extension lifecycle flow, extension
intent routing, extension review and lifecycle evidence, module profile, target
gates, installation and update planning, bridge routing, structural validation.

Category: `DEPENDENCY`
Routing owner: `.ai/framework/dependency-knowledge.md`
Rule IDs: `ALATYR-DEPENDENCY-001`
Derived surfaces: passive dependency export template, target dependency
knowledge policy catalog lock deviations and snapshots, dependency knowledge
intent routing, dependency synchronization flow, dependency knowledge gate,
operation catalog and help, installation and update planning, structural
validation.

Category: `MODE`
Routing owner: `.ai/framework/workspace-modes.md`
Rule IDs: `ALATYR-MODE-001`
Derived surfaces: target workspace-mode catalog, shared root context, per-mode
directories and descriptors, workspace-mode intent and flow, mode suggestion
and preflight, workspace-mode gate, installation and update suggestions,
structural validation.

Category: `DIAGRAM`
Routing owner: `.ai/framework/diagram-guidance.md`
Rule IDs: `ALATYR-DIAGRAM-001`
Derived surfaces: portable ASCII diagram grammar, target diagram discussion
flow, ASCII and diagram presentation templates, operation catalog and compact
index, context intent routing, bridge capability matrix, compact assistant
capabilities, operation conformance fixture, installation planning, adapter
recheck, diagram validation evidence.

Category: `ADAPTER`
Routing owner: `.ai/framework/project-adapter-contract.md`
Rule IDs: `ALATYR-ADAPTER-001`
Derived surfaces: installation plan, readiness checklist, manifest template,
adapter recheck flow, target development-pattern evidence, framework pack and
projected inventory, AI infrastructure router, AI infrastructure recommendation
contract, AI infrastructure item contracts.

Category: `MODULE`
Routing owner: `.ai/framework/module-profile.md`
Rule IDs: `ALATYR-MODULE-001`
Derived surfaces: target module profile, manifest modules, framework pack
catalog, scaffold profile-to-pack mapping, operation help routing, maturity
review.

Category: `OPERATION`
Routing owner: `.ai/framework/operation-help.md`
Rule IDs: `ALATYR-OPERATION-001`
Derived surfaces: target operation catalog, checked compact operation index,
automatic routing flow, compact help, adapter health flow, pre-change preview,
manifest operation paths, assistant bridges.

Category: `TEAM`
Routing owner: `.ai/framework/team-collaboration.md`
Rule IDs: `ALATYR-TEAM-001`
Derived surfaces: structured target team policy, human team operating model,
ignored local actor selection, active-work index, work registry metadata,
per-task records, backend contract, task claims, conflict review, checkpoints,
handoffs, decision records, team review, merge-readiness evidence, operation
routes, team-active context overlay, adapted team skill.

Category: `DELEGATION`
Routing owner: `.ai/framework/subagent-delegation.md`
Rule IDs: `ALATYR-DELEGATION-001`
Derived surfaces: target delegation policy, delegated-execution overlay,
subagent task packet, large-task workstreams, assistant capability records,
bridge capability matrix, operation routing, installation and update planning,
structural validation.

Category: `BRIDGE`
Routing owner: `.ai/framework/bridge-capability-matrix.md`
Rule IDs: `ALATYR-BRIDGE-001`
Derived surfaces: assistant bridge templates, bridge renderer, bridge
capability target template, cross-assistant AI item routing.

Category: `LIFECYCLE`
Routing owner: `.ai/framework/lifecycle.md`
Rule IDs: `ALATYR-LIFECYCLE-001`
Derived surfaces: version files, installed framework pack, migration notes,
framework update recheck, changelog.

Category: `ENGINEERING_EVIDENCE`
Routing owner: `.ai/framework/engineering-evidence.md`
Rule IDs: `ALATYR-ENGINEERING-EVIDENCE-001`
Derived surfaces: target evidence index and records, capture flow, finalization
gate, task-scale routing, operation help, change-package links, target
validation, installation and migration planning.

Category: `EVIDENCE`
Routing owner: `.ai/framework/guarantees.md`
Rule IDs: `ALATYR-EVIDENCE-001`
Derived surfaces: final evidence, process commitments, conformance reports,
effectiveness reports, operation packets.

## Rule Canonical Owners

Rule: `ALATYR-CONTEXT-001`
Canonical owner: `.ai/framework/context-profiles.md`

Rule: `ALATYR-SOURCE-001`
Canonical owner: `.ai/framework/source-of-truth-registry.md`

Rule: `ALATYR-RISK-001`
Canonical owner: `.ai/framework/change-risk-model.md`

Rule: `ALATYR-APPROVAL-001`
Canonical owner: `.ai/framework/approval-records.md`

Rule: `ALATYR-AUTHORIZATION-001`
Canonical owner: `.ai/framework/action-authorization.md`

Rule: `ALATYR-SAFETY-001`
Canonical owner: `.ai/framework/security-safety-guidance.md`

Rule: `ALATYR-SAFETY-002`
Canonical owner: `.ai/framework/prompt-injection.md`

Rule: `ALATYR-INTEGRITY-001`
Canonical owner: `.ai/framework/logical-integrity.md`

Rule: `ALATYR-CHANGE-001`
Canonical owner: `.ai/framework/blueprint-driven-change.md`

Rule: `ALATYR-PACKAGE-001`
Canonical owner: `.ai/framework/change-packages.md`

Rule: `ALATYR-ENGINEERING-EVIDENCE-001`
Canonical owner: `.ai/framework/engineering-evidence.md`

Rule: `ALATYR-ARCHITECTURE-001`
Canonical owner: `.ai/framework/architecture-knowledge.md`

Rule: `ALATYR-CODEDOC-001`
Canonical owner: `.ai/framework/code-documentation.md`

Rule: `ALATYR-VOCABULARY-001`
Canonical owner: `.ai/framework/project-vocabulary.md`

Rule: `ALATYR-TDD-001`
Canonical owner: `.ai/framework/test-first-development.md`

Rule: `ALATYR-EXTENSION-001`
Canonical owner: `.ai/framework/extensions.md`

Rule: `ALATYR-DEPENDENCY-001`
Canonical owner: `.ai/framework/dependency-knowledge.md`

Rule: `ALATYR-MODE-001`
Canonical owner: `.ai/framework/workspace-modes.md`

Rule: `ALATYR-DIAGRAM-001`
Canonical owner: `.ai/framework/diagram-guidance.md`

Rule: `ALATYR-ADAPTER-001`
Canonical owner: `.ai/framework/project-adapter-contract.md`

Rule: `ALATYR-MODULE-001`
Canonical owner: `.ai/framework/module-profile.md`

Rule: `ALATYR-OPERATION-001`
Canonical owner: `.ai/framework/operation-help.md`

Rule: `ALATYR-TEAM-001`
Canonical owner: `.ai/framework/team-collaboration.md`

Rule: `ALATYR-DELEGATION-001`
Canonical owner: `.ai/framework/subagent-delegation.md`

Rule: `ALATYR-BRIDGE-001`
Canonical owner: `.ai/framework/bridge-capability-matrix.md`

Rule: `ALATYR-LIFECYCLE-001`
Canonical owner: `.ai/framework/lifecycle.md`

Rule: `ALATYR-EVIDENCE-001`
Canonical owner: `.ai/framework/guarantees.md`

## Change Protocol

1. Update the owning framework document and its `alatyr_doc` metadata.
2. Update `framework/rule-registry.json`.
3. Regenerate this file and `framework/rule-registry.md`.
4. Update affected installer, target, checker, and conformance surfaces.
5. Keep assistant bridges as pointers.
6. Record behavioral changes in `CHANGELOG.md` and migration evidence.
