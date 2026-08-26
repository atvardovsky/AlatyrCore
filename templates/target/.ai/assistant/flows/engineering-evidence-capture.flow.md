# Durable Engineering Evidence Capture Flow

Use this lazy finalization flow in `{PROJECT_NAME}` after normal engineering,
logical integrity, and validation work. It does not authorize edits, commits,
publication, or live external actions.

## Sources

- Rule owner: `.ai/framework/engineering-evidence.md`
- Capture gate: `.ai/assistant/gates/engineering-evidence.md`
- Compact index: `.ai/project/engineering-evidence/index.json`
- Record template: `.ai/assistant/templates/engineering-evidence-record.json`
- Target policy: `.ai/project/engineering-evidence/README.md`
- Current task, canonical owners, repository state, and validation evidence

## Steps

1. Ask whether reusable engineering knowledge would be lost when the session
   ends. Evaluate every applicable rule trigger from current task evidence as
   applicable, not applicable, or unknown. Keep supporting implementation and
   validation evidence separate from the materiality reason.
2. Classify the decision as `captured`, `skipped`, or `blocked`. A small,
   self-explanatory local task may skip with one fact-specific reason when no
   trigger applies. A material task may skip only when every applicable
   conclusion resolves to an existing canonical source registered for its
   project fact type; unknown materiality blocks skipping.
3. Under `read-only`, do not create or update records. Return a capture proposal
   or block reason. Writing the target evidence store requires current-scope
   `docs-only`, `adapter-only`, or a broader authorized modify phase compatible
   with target policy.
4. For capture, assign a target-owned evidence ID and normalize task, observed
   failure, affected architecture, invariant, hypotheses and their outcomes,
   root cause, solution rationale, impact, regression matrix, validation, and
   residual uncertainty.
5. Link material rejected alternatives only when they would help prevent a
   plausible future wrong repair. Do not manufacture alternatives.
6. Link canonical knowledge updates. If an accepted fact has no owner, record
   the ownership gap and do not let this historical record become the owner.
7. Bind the result to an exact commit, pull request, Git tree, selected-file
   snapshot, or `unverified` limitation. Mark a working binding provisional and
   a completed reproducible binding final. Final commit and pull-request ranges
   use immutable object IDs and valid ancestry; tree results resolve as Git
   trees. Link the task or issue explicitly.
8. When finalizing or strengthening a binding, append the replaced binding to
   `prior_bindings`. Never silently rewrite lineage. Treat later drift from a
   finalized selected-file snapshot as a historical reproducibility warning,
   not retroactive evidence corruption.
9. Apply the target storage and external-patch policy. Keep support evidence
   outside a clean upstream contribution unless the upstream project accepts
   it. Confirm that the selected retained store remains discoverable.
10. Reject raw chats, chain-of-thought, prompts, secrets, credentials, personal
   data, unrelated session history, complete diffs, and verbose test logs.
11. Validate the record, then add one compact index entry containing evidence
    ID, status, record path or approved external reference, task references,
    changed fact IDs, architecture areas, repository binding, related Debug
    session IDs, and uncertainty. Every Debug link must resolve exactly once,
    share task lineage, and link back to this evidence ID.
12. If a change package is active, link the evidence ID from it instead of
    copying the normalized conclusions.

## Final Evidence

Report capture status, trigger or skip/block reason, evidence ID and path when
captured, task and repository binding state and lineage, canonical owner
updates, reciprocal Debug links or their absence, privacy and publication
result, validation, and residual uncertainty.
