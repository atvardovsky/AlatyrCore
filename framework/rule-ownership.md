# Rule Ownership

This file names the canonical owner for each Alatyr rule category.

Use it to reduce repeated policy text across README files, installer docs,
target templates, bridges, help files, and checkers. Owning documents contain
the rule meaning. Derived documents should reference the owner, rule ID, or
short summary instead of restating full policy.

The machine-readable ownership map lives in
`framework/rule-registry.json` under `category_owners`.

## Ownership Rules

- Full rule semantics belong in the owning framework document.
- Rule-owner framework documents must carry `alatyr_doc` front matter with a
  stable document ID, owned rule IDs, rule dependencies, and task-profile
  scope.
- `framework/rule-registry.md` and `framework/rule-registry.json` keep stable
  IDs, summaries, category owners, and migration metadata.
- Installer docs may summarize a rule only enough to route installation work.
- Target templates may contain placeholders and local adaptation prompts, but
  must not become portable rule owners.
- Bridge files must stay pointers to canonical target files, not policy
  copies.
- When a rule changes materially, update the owning document first, then the
  registry, affected templates, checkers, and changelog.

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

Category: `ADAPTER`
Owner: `.ai/framework/project-adapter-contract.md`
Rule IDs: `ALATYR-ADAPTER-001`
Derived surfaces: installation plan, readiness checklist, manifest template,
adapter recheck flow, target development-pattern evidence, AI infrastructure
router, recommendation, and item contracts.

Category: `MODULE`
Owner: `.ai/framework/module-profile.md`
Rule IDs: `ALATYR-MODULE-001`
Derived surfaces: target module profile, manifest modules, operation help
routing, maturity review.

Category: `OPERATION`
Owner: `.ai/framework/operation-help.md`
Rule IDs: `ALATYR-OPERATION-001`
Derived surfaces: target operation catalog, automatic routing flow, compact
help, adapter health flow, pre-change preview, manifest operation paths,
assistant bridges.

Category: `TEAM`
Owner: `.ai/framework/team-collaboration.md`
Rule IDs: `ALATYR-TEAM-001`
Derived surfaces: target team operating model, work registry, task claims,
conflict review, checkpoints, handoffs, decision records, team review,
merge-readiness evidence, operation routes, and team-active context overlay.

Category: `BRIDGE`
Owner: `.ai/framework/bridge-capability-matrix.md`
Rule IDs: `ALATYR-BRIDGE-001`
Derived surfaces: assistant bridge templates, bridge renderer, bridge
capability target template, cross-assistant AI item routing.

Category: `LIFECYCLE`
Owner: `.ai/framework/lifecycle.md`
Rule IDs: `ALATYR-LIFECYCLE-001`
Derived surfaces: version files, migration notes, framework update recheck,
changelog.

Category: `EVIDENCE`
Owner: `.ai/framework/guarantees.md`
Rule IDs: `ALATYR-EVIDENCE-001`
Derived surfaces: final evidence, process commitments, conformance reports,
effectiveness reports, operation packets.

## Change Protocol

When changing a rule category:

1. Update the owning framework document.
2. Update the owning document's `alatyr_doc` front matter when owned rules,
   dependencies, or task-profile scope change.
3. Update `framework/rule-registry.md` and
   `framework/rule-registry.json`.
4. Update derived installer docs, target templates, tools, or conformance
   data only when their contract changes.
5. Keep bridges as pointers.
6. Record behavior or contract changes in `CHANGELOG.md`.
