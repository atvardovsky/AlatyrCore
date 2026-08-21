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
3. Create one record from the machine template and one compact index entry.
   Activation grants no code, commit, publish, live-external, protected-change,
   or tool permission.
4. During the task, capture only material normalized events at checkpoints.
   Classify origin before category. Preserve causal links and evidence.
5. Classify broad human direction as `human-initiated`. Classify concrete
   consequences independently derived from that direction as
   `derived-after-human-intervention`. Do not count either as an independent
   Alatyr finding.
6. Reject raw conversations, chain-of-thought, prompts, credentials, secrets,
   unrelated personal data, complete diffs, verbose logs, and speculation that
   did not affect the task.
7. Record timing evidence honestly. Use active work time only when a trusted
   environment measures it. Record partial coverage, missing intervals,
   observer effect, and capture overhead.
8. For `finalize`, derive metrics from event predicates, bind the engineering
   result, link durable evidence, record clean-upstream projection evidence,
   validate the record, synchronize the index, and render the compact summary.
9. Expire activation when the scope completes, changes, is abandoned, or is
   explicitly disabled. A later task requires a new explicit activation.
10. For `compare`, use comparable completed records, evidence kinds, capture
    quality, task class, and independent quality review. Do not infer framework
    improvement from lower intervention count alone.

## Final Evidence

Report activation/expiry, record ID and path, timing evidence, capture quality,
event-derived metrics, result binding, external projection, privacy and
publication result, validation, and residual uncertainty.
