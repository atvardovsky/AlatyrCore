# Alatyr Debug Mode Flow

Use this flow only when the optional `debug-mode` module is enabled or under
explicit read-only configuration review.

## Modes

- `enable`: explicitly activate one task or session record
- `status`: report current activation and capture quality without editing
- `checkpoint`: append or normalize material events
- `finalize`: bind the result, derive metrics, update the compact index, and
  expire activation
- `disable`: stop capture and mark the record completed or abandoned without
  implying engineering-task completion
- `compare`: compare selected completed records from compact evidence

## Steps

1. Re-evaluate current-scope action authorization. A vague status, analysis,
   backlog, issue-return, or continuation request is read-only and does not
   activate Debug Mode.
2. For `enable`, require an explicit current user request, one task or session
   scope ID, owner, target storage/privacy policy, and `adapter-only` permission
   for record writes. Record start timing as observed, estimated, or unknown.
3. Create one record from the machine template and one compact index entry. A
   continued investigation starts a new explicitly activated record and names
   exactly one closed predecessor; never append to or reopen a completed
   record.
   Activation grants no code, commit, publish, live-external, protected-change,
   or tool permission.
4. During the task, capture only material normalized events at checkpoints.
   Classify actor, causal class, intervention kind, contribution kind, and then
   category. Preserve causal links and evidence. Keep the initial task request
   in activation metadata; it is not an intervention event by itself.
5. Record human or external input as an `intervention` only when it directs,
   expands, constrains, corrects, or requests validation for a specific line.
   Classify concrete Alatyr consequences as `derived-from-human` or
   `derived-from-external`. A validation request is not an implementation
   correction. Generic external input is not a maintainer correction.
6. For each new event, record `decision_effect` and `architectural_impacts`.
   Human or external-maintainer events with accepted-invariant, canonical-
   source-interpretation, public-contract, subsystem-responsibility, solution-
   class, compatibility-strategy, lifecycle-semantics, or authority-boundary
   impact are architectural supervision. If review changes the accepted
   direction, add a later rejected-hypothesis event with counter-evidence and a
   replacement invariant or architecture event in the same causal chain.
7. Reject raw conversations, chain-of-thought, prompts, credentials, secrets,
   unrelated personal data, complete diffs, verbose logs, and speculation that
   did not affect the task.
8. Record timing evidence honestly. Use active work time only when a trusted
   environment measures it. Record partial coverage, missing intervals,
   observer effect, and capture overhead. Before completion, verify every
   concrete event lies inside the start/completion interval and that event and
   causal order agree with timestamps.
9. For `finalize`, derive metrics from the versioned event predicates and run
   the Durable Engineering Evidence decision. Type supporting event links and
   evaluate every materiality condition. Complete it as `captured`, `skipped`,
   or `blocked`; do not leave it pending. A skip requires no unknown conditions
   and registry-backed canonical preservation for every applicable conclusion.
   Implementation and validation links do not by themselves force capture.
10. Classify validation fidelity as exact reproducer, representative, partial,
    unavailable, or not applicable. Name the claim and evidence for exact,
    representative, or partial results. Keep partial and unavailable gaps in
    residual uncertainty.
11. Bind the engineering result as provisional or final. Final commit and
    pull-request ranges use immutable object IDs and valid ancestry; tree
    results resolve as Git trees. Preserve every replaced binding in
    `prior_bindings`. Link only durable evidence IDs that resolve exactly once
    in the target Engineering Evidence index.
12. Record clean-upstream projection evidence, validate the record, synchronize
    the index, and render the compact summary. Later worktree drift may make a
    finalized snapshot not currently reproducible, but does not corrupt its
    historical value.
13. Expire activation when the scope completes, changes, is abandoned, or is
   explicitly disabled. A later task requires a new explicit activation and,
   when related, explicit continuation lineage.
14. For `compare`, use comparable completed records, attribution schema,
    evidence kinds, capture
    quality, task class, and independent quality review. Do not infer framework
    improvement from lower intervention count alone.

## Final Evidence

Report activation/expiry, record ID and path, timing evidence, capture quality,
event-derived metrics, materiality and durable engineering-evidence decision,
claim-validation fidelity, continuation and result-binding lineage, external
projection, privacy and publication result, validation, and residual
uncertainty.
