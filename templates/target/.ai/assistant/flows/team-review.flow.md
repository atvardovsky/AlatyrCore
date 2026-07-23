# Team Review And Merge Check Flow

Use this flow in `{PROJECT_NAME}` for team review or merge-readiness requests
when the `team-collaboration` module is enabled.

Review is read-only by default. Route requested fixes through the applicable
product-change, logical-integrity, documentation, or adapter operation.

## Target Sources

- Team operating model: `.ai/project/team-operating-model.md`
- Work registry: `.ai/assistant/team/work-registry.json`
- Team gate: `.ai/assistant/gates/team-collaboration.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Approval records: `.ai/assistant/approvals`
- Target review policy: `{TARGET_REVIEW_POLICY}`
- Target validation: `{TARGET_REVIEW_AND_MERGE_VALIDATION}`

## Team Review

For `Alatyr review {TASK_ID}`:

1. Load the selected task, current revision, compact team overlay, changed-fact
   owners, dependencies, checkpoint, handoff, and approval evidence.
2. Compare the task scope and allowed actions with the actual current diff.
3. Re-run overlap against active tasks and identify assumptions invalidated by
   concurrent work.
4. Verify required role, specialist, and CODEOWNERS-equivalent review.
5. Review implementation, tests, docs, diagrams, generated artifacts,
   blueprints, and AI infrastructure surfaces selected by changed facts.
6. Run target validation or record unavailable checks.
7. Perform one logical integrity review over the combined repair set.
8. Return the review outcome and revision-bound evidence reference separately
   from reviewer assignment. Persist it only through a separately permitted
   adapter-only checkpoint or target backend update.
9. Report findings before summary, with owners and repair operations.

## Merge Check

For `Alatyr merge check {TASK_ID}`:

1. Keep allowed actions `read-only`.
2. Require a current review result bound to the current head and base
   revisions. Reviewer assignment without approved review evidence is not a
   passed review.
3. Verify complete changed-path approval scope when protected changes apply.
4. Verify task dependencies, concurrent overlap, required reviews, handoff
   acceptance, validation, generated artifacts, and residual-risk ownership.
5. Classify the task as `merge-ready`, `attention`, `blocked`, or
   `unverified`.
6. Return `merge-ready` only at the reviewed revision. Persist it only through
   a separately permitted adapter-only checkpoint or target backend update.
   Any diff, base, approval, dependency, or relevant concurrent-task change
   invalidates it.

Merge readiness is evidence, not a universal authorization to merge.

## Final Evidence

Report task and reviewer IDs, head/base revisions, changed facts, active-task
overlap, required reviews, approval coverage, validation, logical integrity,
handoff/checkpoint state, readiness classification, blockers, residual risk,
and next responsible actor.

## Rejection Criteria

Reject or revise review that:

- detects conflicts only from files
- ignores active tasks that share facts, contracts, dependencies, migrations,
  or generated artifacts
- claims required human or specialist review without target evidence
- marks stale evidence merge-ready
- treats review or merge readiness as protected-change approval
