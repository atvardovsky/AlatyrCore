# Team Decision Flow

Use this flow in `{PROJECT_NAME}` for structured business, architecture, data,
security, adapter, or delivery-priority discussion when the
`team-collaboration` module is enabled.

A proposed decision record is coordination evidence. An accepted decision must
be written to the target canonical source by its authorized decision owner.
With `read-only`, return a draft without persistence. `docs-only` may update
only non-accepted explanatory or coordination documents. Writing an accepted
semantic fact requires the applicable project-change scope and approval.

## Target Sources

- Team operating model: `.ai/project/team-operating-model.md`
- Work registry: `.ai/assistant/team/work-registry.json`
- Decision template: `.ai/assistant/templates/team-decision-record.md`
- Source-of-truth registry: `.ai/project/source-of-truth-registry.md`
- Target decision records: `{TARGET_DECISION_RECORD_DIRECTORY}`
- Approval policy: `{TARGET_APPROVAL_POLICY}`

## Steps

1. Resolve the decision question, decision type, owner, participants, affected
   task IDs, changed or disputed fact IDs, canonical owners, constraints, and
   dependencies.
2. Confirm decision authority from the target operating model. Do not infer it
   from task ownership, priority, review, or commit authorship.
3. Record material options, benefits, costs, risks, evidence, priority
   implications, dependencies, and unresolved concerns.
4. Show a pre-change preview before accepting a semantic or protected project
   fact change. The preview is not approval.
5. Record the selected option, rationale, consequences, dissent, approval
   references, follow-up actions, and review or expiry date.
6. When allowed actions and approval permit, write an accepted decision to the
   target canonical decision or source-of-truth surface. Otherwise report the
   destination and follow-up operation. Keep `proposed`, `deferred`, or
   unresolved records out of accepted project facts.
7. Update affected task references without changing unrelated task state.
8. Route implementation through the applicable product-change,
   logical-integrity, documentation, or large-task operation.

## Priority Rule

Priority may influence option evaluation and scheduling, but it cannot bypass
correctness, safety, source-of-truth ownership, review, validation, or
approval. When priority authority or criteria conflict, stop for the target
decision owner.

## Final Evidence

Report decision and task IDs, owner and participants, changed facts and
canonical owners, options, priority implications, selected result or unresolved
state, approval, canonical destination, follow-up operations, and residual
risk.

## Rejection Criteria

Reject or revise a decision that:

- lacks an authorized target decision owner
- treats priority as authority or approval
- omits material options, consequences, dissent, or unresolved evidence
- leaves an accepted project fact only in an assistant template
- starts implementation without routing changed facts through their owners
