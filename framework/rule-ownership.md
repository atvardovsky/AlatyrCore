# Rule Ownership

This file is generated from `framework/rule-registry.json`. Canonical owner
documents define rule semantics; this map only routes maintainers and tools.
Derived documents should reference the owner or rule ID and avoid copying
the complete policy language.

## Ownership Rules

- Change the canonical owner document before changing a rule summary.
- Keep installer, template, bridge, and help wording as short references.
- Keep owner front matter aligned with registered IDs and dependencies.
- Record material contract changes in the changelog and migration evidence.

## Category Owners

Category: `CONTEXT`
Owner: `.ai/framework/context-profiles.md`
Rule IDs: `ALATYR-CONTEXT-001`
Derived surfaces: README source context, installation source context, target
context profiles, target context router, task-scale overlays, operation packet
context receipts, consistency relationship routing, session bootstrap
instructions, AI infrastructure capability and recommendation routing.

Category: `SOURCE`
Owner: `.ai/framework/source-of-truth-registry.md`
Rule IDs: `ALATYR-SOURCE-001`
Derived surfaces: project adapter contract, logical integrity, blueprint
change, target source-of-truth registry template, invariant constraints,
consistency map.

Category: `RISK`
Owner: `.ai/framework/change-risk-model.md`
Rule IDs: `ALATYR-RISK-001`
Derived surfaces: installer approval planning, target gates, operation request
templates, external failure observability, final evidence.

Category: `APPROVAL`
Owner: `.ai/framework/approval-records.md`
Rule IDs: `ALATYR-APPROVAL-001`
Derived surfaces: installation approval gate, installed-operation allowed
actions, human and machine-readable approval templates, strict target diff
scope validation, security-sensitive profiles.

Category: `SAFETY`
Owner: `.ai/framework/security-safety-guidance.md`
Rule IDs: `ALATYR-SAFETY-001`, `ALATYR-SAFETY-002`
Derived surfaces: prompt-injection guidance, skill adaptation, source-access
policy, adaptation records, security-sensitive context profile.

Category: `INTEGRITY`
Owner: `.ai/framework/logical-integrity.md`
Rule IDs: `ALATYR-INTEGRITY-001`
Derived surfaces: target gates, documentation sync, adapter recheck,
relationship or manual invariant impact closure, review-item reconciliation,
workstream convergence, final evidence.

Category: `CHANGE`
Owner: `.ai/framework/blueprint-driven-change.md`
Rule IDs: `ALATYR-CHANGE-001`
Derived surfaces: product-change operation, blueprint-driven target flow,
large-task orchestration, documentation and diagram sync.

Category: `PACKAGE`
Owner: `.ai/framework/change-packages.md`
Rule IDs: `ALATYR-PACKAGE-001`
Derived surfaces: change-package target flow and records, semantic approval
scope, large-task convergence, blueprint change, target validation, installer
module selection, migration evidence.

Category: `ARCHITECTURE`
Owner: `.ai/framework/architecture-knowledge.md`
Rule IDs: `ALATYR-ARCHITECTURE-001`
Derived surfaces: target architecture index and catalog, pattern and area
templates, architecture-assistance operation, architecture intent routing,
architecture discussion result, installation and update planning, target gates,
architecture validation.

Category: `CODEDOC`
Owner: `.ai/framework/code-documentation.md`
Rule IDs: `ALATYR-CODEDOC-001`
Derived surfaces: target code-documentation catalog and profiles, documentation
intent routing, documentation synchronization flow, project-adapted comment
skill, profile review template, generated-output policy, installation and
update planning, target gates, structural validation.

Category: `VOCABULARY`
Owner: `.ai/framework/project-vocabulary.md`
Rule IDs: `ALATYR-VOCABULARY-001`
Derived surfaces: target vocabulary catalog, term records, data-dictionary link
records, vocabulary intent routing, project-vocabulary operation flow,
project-adapted vocabulary skill, term review template, installation and update
planning, target gates, structural validation.

Category: `TDD`
Owner: `.ai/framework/test-first-development.md`
Rule IDs: `ALATYR-TDD-001`
Derived surfaces: target test-first policy, recommendation gate, configuration
and change operations, test-first intent routing, project-adapted test-first
skill, test-first gate, RED GREEN refactor evidence template, installation and
update planning, structural validation.

Category: `EXTENSION`
Owner: `.ai/framework/extensions.md`
Rule IDs: `ALATYR-EXTENSION-001`
Derived surfaces: external extension package template, extension inspection
tool, target extension catalog and lock, extension lifecycle flow, extension
intent routing, extension review and lifecycle evidence, module profile, target
gates, installation and update planning, bridge routing, structural validation.

Category: `DEPENDENCY`
Owner: `.ai/framework/dependency-knowledge.md`
Rule IDs: `ALATYR-DEPENDENCY-001`
Derived surfaces: passive dependency export template, target dependency
knowledge policy catalog lock deviations and snapshots, dependency knowledge
intent routing, dependency synchronization flow, dependency knowledge gate,
operation catalog and help, installation and update planning, structural
validation.

Category: `MODE`
Owner: `.ai/framework/workspace-modes.md`
Rule IDs: `ALATYR-MODE-001`
Derived surfaces: target workspace-mode catalog, shared root context, per-mode
directories and descriptors, workspace-mode intent and flow, mode suggestion
and preflight, workspace-mode gate, installation and update suggestions,
structural validation.

Category: `DIAGRAM`
Owner: `.ai/framework/diagram-guidance.md`
Rule IDs: `ALATYR-DIAGRAM-001`
Derived surfaces: portable ASCII diagram grammar, target diagram discussion
flow, ASCII and diagram presentation templates, operation catalog and compact
index, context intent routing, bridge capability matrix, compact assistant
capabilities, operation conformance fixture, installation planning, adapter
recheck, diagram validation evidence.

Category: `ADAPTER`
Owner: `.ai/framework/project-adapter-contract.md`
Rule IDs: `ALATYR-ADAPTER-001`
Derived surfaces: installation plan, readiness checklist, manifest template,
adapter recheck flow, target development-pattern evidence, framework pack and
projected inventory, AI infrastructure router, AI infrastructure recommendation
contract, AI infrastructure item contracts.

Category: `MODULE`
Owner: `.ai/framework/module-profile.md`
Rule IDs: `ALATYR-MODULE-001`
Derived surfaces: target module profile, manifest modules, framework pack
catalog, scaffold profile-to-pack mapping, operation help routing, maturity
review.

Category: `OPERATION`
Owner: `.ai/framework/operation-help.md`
Rule IDs: `ALATYR-OPERATION-001`
Derived surfaces: target operation catalog, checked compact operation index,
automatic routing flow, compact help, adapter health flow, pre-change preview,
manifest operation paths, assistant bridges.

Category: `TEAM`
Owner: `.ai/framework/team-collaboration.md`
Rule IDs: `ALATYR-TEAM-001`
Derived surfaces: structured target team policy, human team operating model,
ignored local actor selection, active-work index, work registry metadata,
per-task records, backend contract, task claims, conflict review, checkpoints,
handoffs, decision records, team review, merge-readiness evidence, operation
routes, team-active context overlay, adapted team skill.

Category: `DELEGATION`
Owner: `.ai/framework/subagent-delegation.md`
Rule IDs: `ALATYR-DELEGATION-001`
Derived surfaces: target delegation policy, delegated-execution overlay,
subagent task packet, large-task workstreams, assistant capability records,
bridge capability matrix, operation routing, installation and update planning,
structural validation.

Category: `BRIDGE`
Owner: `.ai/framework/bridge-capability-matrix.md`
Rule IDs: `ALATYR-BRIDGE-001`
Derived surfaces: assistant bridge templates, bridge renderer, bridge
capability target template, cross-assistant AI item routing.

Category: `LIFECYCLE`
Owner: `.ai/framework/lifecycle.md`
Rule IDs: `ALATYR-LIFECYCLE-001`
Derived surfaces: version files, installed framework pack, migration notes,
framework update recheck, changelog.

Category: `EVIDENCE`
Owner: `.ai/framework/guarantees.md`
Rule IDs: `ALATYR-EVIDENCE-001`
Derived surfaces: final evidence, process commitments, conformance reports,
effectiveness reports, operation packets.

## Change Protocol

1. Update the owning framework document and its `alatyr_doc` metadata.
2. Update `framework/rule-registry.json`.
3. Regenerate this file and `framework/rule-registry.md`.
4. Update affected installer, target, checker, and conformance surfaces.
5. Keep assistant bridges as pointers.
6. Record behavioral changes in `CHANGELOG.md` and migration evidence.
