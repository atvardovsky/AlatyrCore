# Blueprint-Driven Change Flow

Use this flow when a requested change may affect `{PROJECT_NAME}` accepted
behavior, source-of-truth docs, implementation, tests, diagrams, or assistant
governance.

Replace placeholders with target facts before accepting installation.

## Target Sources

- Project source of truth: `{TARGET_PROJECT_SOURCE_OF_TRUTH}`
- Blueprint or equivalent docs: `{TARGET_BLUEPRINT_OR_EQUIVALENT}`
- Project flow docs: `{TARGET_FLOW_DOCS}`
- Test strategy and validation: `{TARGET_TEST_STRATEGY_AND_VALIDATION}`
- Diagram policy: `{TARGET_DIAGRAM_POLICY}`
- Security/live-service policy: `{TARGET_SECURITY_POLICY}`

## Steps

### Analyze

1. State change intent and non-goals.
2. Use `.ai/assistant/context-router.json` to load the smallest matching
   profile and project-area overlays plus the target source-of-truth docs.
   Activate the `large-or-resumable` scale overlay when its conditions apply.
3. Invoke only [Analyze](logical-integrity-review.flow.md#analyze). Reuse its changed
   fact IDs, canonical owners, re-derived invariants, review-item clusters and
   registry/consistency-map impact closure. Do not run repair or finalization.

### Plan

4. Plan blueprint, project flow, use-case, data, runtime, architecture and
   public-documentation updates; proposals do not change accepted facts.
5. Prepare an implementation plan that names affected boundaries, tests,
   contract artifacts, diagrams, visual validation, approvals,
   machine-readable scope records, and validation.
   Invoke only [package planning](change-package.flow.md#plan) when the module
   is enabled and coherent outcome, semantic approval, audit, or provenance
   needs pass its activation gate. For large or resumable work, use
   [orchestration analysis](large-task-orchestration.flow.md#analyze) and
   [planning](large-task-orchestration.flow.md#plan) without persisting a packet.

### Apply

6. Verify current modification authorization and applicable protected approval
   before writing. Commit, publish and live-external actions require separate
   current-scope authorization. Update accepted blueprint and flow owners before
   implementation depends on the new facts, within this approved repair set.
   Initialize an activated package through
   [Initialize](change-package.flow.md#initialize), not its entire lifecycle.
   For large work, create the operation packet through only orchestration
   [Initialize](large-task-orchestration.flow.md#initialize), passing these
   existing operation/package identities and retaining outer finalizer ownership.
7. Evaluate the target test-first recommendation gate. When an enabled required
   trigger applies, or a recommendation is accepted, run
   `.ai/assistant/flows/test-first-change.flow.md` and preserve valid
   policy-authorized RED/GREEN/refactor evidence or an explicit not-run state.
   Manual-review timing may defer execution without fabricating RED or granting
   a strict-mode exception. Otherwise
   record why test-first was not indicated or was declined when material.
8. Invoke [Apply](logical-integrity-review.flow.md#apply) for the smallest
   coherent implementation and companion repair set. This owns applicable
   contract-artifact and visual-validation gates; retain their results once.
   For an initialized large task, use orchestration
   [Workstreams](large-task-orchestration.flow.md#workstreams) instead of this
   direct implementation call; it invokes integrity Apply per workstream.
   Do not execute both paths for the same work.
   Record material package discoveries only through
   [Material Updates](change-package.flow.md#material-updates) when active.
   Review new relationships even for already mapped files. Use selected graph
   evidence and canonical owners, not a graph-derived permission or an accepted
   invariant inferred from a compact view. For recurring incidents, reconcile
   the original outcome and retention rationale before another local repair.

After implementation and local checks, obtain global reconciliation through
[integrity verification](logical-integrity-review.flow.md#verify). Required
repairs remain in authorized Apply. As outer coordinator, finalize an active
package once through [Finalize](change-package.flow.md#finalize). Without a
package, perform authorized support-state synchronization last. Preserve the
canonical finalizer transaction; nested orchestration returns evidence and
does not run a competing finalizer. Refresh final-result validation afterward.
The first review is pre-finalization convergence; the later check is
post-finalization binding validation. They share still-current semantic
evidence, not stale acceptance or permission to skip final validation.

### Verify

9. Invoke [Verify](logical-integrity-review.flow.md#verify) after local checks.
   This owns target validation, global workstream reconciliation, documentation
   sync, Project Contour Sync Decision and engineering-evidence verification.
   Do not invent commands. A required correction returns to authorized Apply
   and invalidates affected verification evidence.
10. When approval was used, compare the complete Git change set with the
    explicitly selected machine-readable approval scope and fail on uncovered
    or excluded paths.
11. Verify support state and validation bind the final result; stale state
    returns to authorized Apply. Invoke [package verification](change-package.flow.md#verify)
    only when active. A workstream-local pass is not the
    final consistency check across the combined changed surfaces.
12. Report final evidence, skipped checks, approvals, and residual risk.

## Approval Gate

Require explicit programmer approval before:

- architecture changes
- accepted business behavior changes
- weakened tests, gates, documentation-sync rules, or approval requirements
- new production dependencies, services, permissions, or credentials
- live, destructive, spend-affecting, data-loss, security, or privacy changes
- overwriting existing AI instructions
- integrating third-party assistant infrastructure into canonical target files

## Final Evidence

Reuse the same task/operation-bound evidence from each phase; these fields are
views, not instructions to create one artifact per field. Do not merge distinct
approval, checkpoint, closure, or publication roles or reuse stale bindings.

Report:

- changed facts
- re-derived invariants and reconciled review-item clusters
- relationship impact closure, missing links, and areas reached
- source-of-truth or blueprint updates
- Project Contour Sync Decision with checked owners, affected surfaces,
  evidence, support-state result, and reason when no update was required
- implementation, test, contract-artifact, diagram, prompt, skill, gate,
  bridge, or checker updates
- validation run or unresolved
- support/product change cost when measured
- contract artifact review result when applicable
- visual validation result when applicable
- test-first policy result, RED/GREEN/refactor evidence, accepted exception, or
  reason not indicated when the recommendation gate was materially evaluated
- approvals used
- changed-path approval scope enforcement result
- skipped checks and residual risk
- for large tasks, workstream convergence, context receipts, and checkpoints
- for activated change packages, semantic and path scope, companion decisions,
  material corrections, provenance quality, and public claim strength
- durable engineering-evidence status, record ID/path and repository binding,
  or a fact-specific skip or blocker
