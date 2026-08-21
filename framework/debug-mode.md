---
alatyr_doc:
  id: framework.debug-mode
  type: framework-rule-owner
  owns_rules:
    - ALATYR-DEBUG-001
  depends_on:
    - ALATYR-AUTHORIZATION-001
    - ALATYR-ENGINEERING-EVIDENCE-001
    - ALATYR-EVIDENCE-001
  applies_to:
    - all
---
# Debug Mode

Debug Mode is an optional, explicitly activated observability layer for an
Alatyr-assisted engineering task. It records compact engineering events and
outcomes so a project can evaluate what Alatyr discovered independently, where
human supervision changed the work, and whether that supervision burden changes
across comparable tasks.

Debug Mode evaluates the assisted process. It does not make the resulting patch
correct, expose private reasoning, or replace project evidence.

## Authority Boundary

Debug records are non-canonical project evidence. They may reference accepted
architecture, business rules, code, tests, approvals, and durable engineering
evidence, but they never own those facts. More detailed debug evidence does not
have greater authority.

Keep these questions separate:

- Durable engineering evidence: why is this change justified and validated?
- Debug Mode: how did Alatyr and human supervision contribute to the result?

Route an accepted fact discovered during debugging to its canonical project
owner. Link the resulting owner or engineering-evidence record from the debug
record instead of treating the debug event as the decision.

## Activation And Expiry

Debug Mode is opt-in for one named task or session scope. Activation requires an
explicit current user request such as `Enable Alatyr Debug Mode for this task`.
Do not infer activation from broad analysis, a previous task, an installed
module, or the existence of old records.

Activation:

- records the task or session scope, request reference, owner, start evidence,
  and initial repository revision when available
- authorizes only target-approved debug-record writes when the current allowed
  action mode permits `adapter-only` changes
- does not authorize project code changes, commits, publication, live external
  actions, protected changes, or broader data collection
- expires on task completion, logical-scope change, explicit disablement, or
  abandonment

After expiry, a new task needs a new explicit activation. Current-scope action
authorization remains independently required for every engineering action.

## Normalized Event Model

Record only material events that changed or validated the investigation. Every
event has a stable ID, sequence, origin, category, compact summary, material
effect, evidence references, and causal references when applicable.

Origins are:

- `alatyr-initiated`: Alatyr identified the finding or check before a recorded
  human intervention directed that line of work
- `human-initiated`: a human expanded, corrected, constrained, or redirected
  the investigation
- `derived-after-human-intervention`: Alatyr derived a concrete consequence,
  dependency, test, correction, or validation path from a recorded human
  intervention
- `external-maintainer`: a reviewer or maintainer outside the active
  human-assistant loop supplied a correction or requirement

A derived event must reference an earlier human event through its causal chain.
An Alatyr-initiated event must not claim independence when its causal chain
contains a human intervention. Preserve the distinction between a broad human
direction and the concrete consequences Alatyr subsequently derives.

Supported categories include architecture areas, invariants, dependencies,
execution paths, risks, tests, regression scenarios, hypotheses, validation,
implementation revisions, and review corrections. A concise `other` category
may be used only when no supported category fits.

## Capture Discipline

Update the task-local record at material checkpoints, not after every message.
Prefer one normalized event that summarizes a coherent effect over a transcript
or verbose chronology. Debug Mode should not materially alter the engineering
workflow it measures.

Record:

- independently identified invariants, architecture areas, dependencies,
  execution paths, risks, tests, and validation requirements
- human interventions that materially expanded or corrected the work
- concrete consequences derived after those interventions
- hypotheses that were confirmed, rejected, or left unresolved and affected
  the task
- implementation revisions, validation expansion, maintainer corrections, and
  post-review rework
- final implementation and validation outcome plus a reproducible repository
  binding when available

Do not record routine acknowledgements, repeated status text, formatting-only
turns, or speculative reasoning that did not affect the task.

## Privacy Boundary

Debug Mode must not store:

- raw AI or human conversations
- hidden or private chain-of-thought, reasoning traces, or prompts
- secrets, credentials, tokens, or private keys
- unrelated personal data or session history
- complete diffs or verbose logs when a bounded evidence reference is enough
- speculative reasoning that did not materially affect the task

Store normalized engineering outcomes and references only. Apply the target's
retention, visibility, redaction, and access policy. If compliant storage is not
available, mark capture blocked instead of retaining unsafe content.

## Timing And Capture Quality

Timing values must identify their evidence kind:

- `observed`: the host or a trusted task record supplied the value
- `estimated`: the value is a bounded estimate and must not be presented as
  exact
- `unknown`: reliable timing evidence is unavailable

Record start, completion, and elapsed time when trustworthy evidence exists.
Record active work time only when the environment measures it reliably.

Every record also declares event coverage, missing intervals, possible observer
effect, and estimated recording overhead. A partial record is valid evidence of
partial observation; it must not be summarized as complete.

## Metrics

Derive completed-task metrics from recorded events, not from the final diff or
an assistant's impression. Metrics include:

- human interventions and human architectural interventions
- independent Alatyr findings and findings derived after human intervention
- independent versus human-requested dependency checks
- dependency expansions derived after human intervention
- hypotheses tested and rejected
- implementation revisions and corrections after human intervention
- validation expansions and regression scenarios added
- external maintainer corrections and post-review rework

Each metric stores its evidence kind and contributing event IDs. Use `estimated`
or `unavailable` only when exact event-derived evidence cannot be claimed.
Completed records with `event-derived` metrics must agree exactly with their
event predicates.

Cross-task comparison reads compact index summaries and compares like task
classes, capture coverage, result quality, and timing evidence. Do not claim
improvement merely because intervention count fell. A lower supervision burden
is useful only when independent review and result quality remain comparable.

## Final Result And External Projection

Bind the final result to an exact commit, pull request, tree, selected-file
snapshot, or an honest unverified state. Link implementation surfaces,
validation evidence, and durable engineering-evidence IDs when applicable.

Support this boundary:

```text
rich Alatyr/evidence branch -> clean project-native upstream patch
```

Debug records stay in the target-approved evidence store. An external
contribution excludes `.ai/*` debug files unless the receiving project
explicitly accepts them. The debug record describes and evidences the
projection; it does not authorize publication.

## Final Summary

When active Debug Mode reaches completion, report a compact `Alatyr Debug
Summary` containing:

- elapsed time and evidence kind
- capture coverage and observer-effect caveat
- human architectural interventions
- independent Alatyr findings
- independent and human-requested dependency checks
- rejected hypotheses
- implementation corrections after human intervention
- external maintainer corrections and post-review rework
- final repository binding and external projection result
- residual uncertainty

Report exact numbers only when supported by the record. Finalize or abandon the
record and expire activation before leaving the logical scope.

## Deterministic Checks And Limits

Target validation may check schema shape, event ordering, causal attribution,
metric derivation, timing consistency, privacy declarations, index/record sync,
repository bindings, and external-patch policy.

It cannot prove that every material event was recorded, that attribution is
semantically correct, that the work was good, that an unrecorded conversation
had no influence, or that reduced supervision caused better Alatyr reasoning.

## Rejection Criteria

Reject or repair Debug Mode use that:

- activates without an explicit current-scope user request
- carries activation or write permission into a new task
- stores transcripts, private reasoning, secrets, or unrelated data
- counts human-directed work as independently Alatyr-initiated
- records derived work without a causal human event
- infers metrics from the final patch instead of recorded events
- turns debug evidence into architecture or business-rule authority
- includes Alatyr files in a clean external patch contrary to target policy
- claims complete observation despite missing intervals
- creates enough recording overhead to materially distort the task
