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
version-2 event has a stable ID, sequence, actor, causal class, intervention
kind, contribution kind, category, compact material effect, evidence
references, and causal references when applicable.

Keep the attribution dimensions separate:

- `actor`: `alatyr`, `human`, or `external-maintainer`
- `causal_class`: `independent-within-scope`, `intervention`,
  `derived-from-human`, or `derived-from-external`
- `intervention_kind`: `line-direction`, `scope-expansion`, `constraint`,
  `correction`, `validation-request`, or `not-applicable`
- `contribution_kind`: `finding`, `decision`, `implementation`, `validation`,
  or `coordination`

The request that activates Debug Mode or states the task scope belongs in the
activation and task metadata. It is not itself a human intervention event.
Create an intervention event only when a human or external maintainer directs,
expands, constrains, corrects, or requests validation for a specific line of
the active investigation.

A derived event must reference the matching earlier intervention through its
causal chain. An independent event must not have a human or external
intervention ancestor. A validation request is not an implementation
correction, and external input is not a maintainer correction unless its
intervention kind is `correction`.

Schema-version-1 `origin` values remain readable as legacy evidence. Do not
silently rewrite their attribution. Comparisons across versions must identify
the attribution-model difference.

Supported categories include architecture areas, invariants, dependencies,
execution paths, risks, tests, regression scenarios, hypotheses, validation,
implementation revisions, and review corrections. A concise `other` category
may be used only when no supported category fits.

## Architectural Supervision

Do not classify architectural supervision from job titles, message wording, or
the number of files changed. For each new event, record `decision_effect` as
`none`, `confirms-direction`, or `changes-direction`, and record every affected
architectural decision dimension in `architectural_impacts`:

- `accepted-invariant`
- `canonical-source-interpretation`
- `public-contract`
- `subsystem-responsibility`
- `solution-class`
- `compatibility-strategy`
- `lifecycle-semantics`
- `authority-boundary`

A human-initiated or external-maintainer event with one or more of these
impacts is architectural supervision and must set
`architectural_supervision: true`. A human event without an architectural
impact must keep the flag false. Alatyr-initiated and derived events may record
architectural impacts as investigation outcomes, but they are not human
architectural-supervision events.

Existing records that predate these structured fields may retain
`decision_effect` as absent or `not-assessed` and may omit
`architectural_impacts`. Treat that state as migration-limited evidence, not as
proof that no architectural supervision occurred. New and migrated events
should use the structured fields.

When a human or external-maintainer correction changes the accepted direction,
record the causal transition explicitly:

```text
direction-changing correction
        -> rejected hypothesis with counter-evidence
        -> replacement invariant or architecture direction
```

The rejected hypothesis must be a later event caused by the correction. The
replacement invariant or architecture event must be later and descend from
that rejected hypothesis. This preserves the difference between the
intervention, the invalidated premise, and Alatyr's derived replacement.

## Capture Discipline

Update the task-local record at material checkpoints, not after every message.
Prefer one normalized event that summarizes a coherent effect over a transcript
or verbose chronology. Debug Mode should not materially alter the engineering
workflow it measures.

Record:

- independently identified invariants, architecture areas, dependencies,
  execution paths, risks, tests, and validation requirements
- human interventions that materially expanded or corrected the work
- structured architectural impacts and direction changes introduced by human
  or external-maintainer review
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
event predicates. Version 2 counts findings only from `finding` contributions,
implementation revisions only from `implementation` contributions, and
validation expansion only from `validation` contributions. Implementation
correction and post-review rework metrics require a causal correction ancestor;
a validation request alone does not satisfy that predicate.

Cross-task comparison reads compact index summaries and compares like task
classes, capture coverage, result quality, and timing evidence. Do not claim
improvement merely because intervention count fell. A lower supervision burden
is useful only when independent review and result quality remain comparable.

## Final Result And External Projection

Bind the final result to an exact commit, pull request, tree, selected-file
snapshot, or an honest unverified state. Version-2 bindings declare
`provisional` or `final` state and preserve replaced bindings in
`prior_bindings`. Final commit and pull-request bindings use immutable commit
IDs with an ancestor-ordered base/result range. A tree binding resolves its
result as a Git tree object, not as a commit.

A finalized selected-file snapshot is historical evidence. Later legitimate
edits or deletion may make it not currently reproducible, but must not turn the
old record into corrupt evidence. Report that state explicitly. When the
snapshot matches a commit, suggest an explicit lineage-preserving rebind; do
not rewrite it automatically.

Link implementation surfaces, validation evidence, and durable
engineering-evidence IDs when applicable.
Every non-empty durable engineering-evidence ID must resolve exactly once in
the target Engineering Evidence index. A Debug event ID is not a durable
evidence ID.

Every version-2 Debug result also records an Engineering Evidence decision as
`pending`, `captured`, `skipped`, or `blocked`. Completion cannot leave it
pending. Material rejected hypotheses and direction-changing corrections must
be captured or blocked, or skipped only when named canonical project knowledge
already preserves the reusable conclusion. A blocked decision names the next
safe action.

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
structured architectural-impact consistency, direction-change hypothesis
transitions, metric derivation, timing consistency, privacy declarations,
Debug-to-Engineering-Evidence reference integrity, index/record sync,
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
- counts the initial task request as an intervention without a specific
  investigative effect
- counts a validation request as an implementation correction or generic
  external input as a maintainer correction
- records derived work without a causal human event
- marks a human architectural impact as non-architectural, or claims human
  architectural supervision without structured impact evidence in a new record
- changes an accepted direction without recording the rejected hypothesis and
  its replacement invariant or architecture direction
- links an unknown, duplicate, or Debug-local ID as durable engineering
  evidence
- completes material Debug work without an explicit durable-evidence decision
- rewrites historical attribution or repository-binding lineage silently
- infers metrics from the final patch instead of recorded events
- turns debug evidence into architecture or business-rule authority
- includes Alatyr files in a clean external patch contrary to target policy
- claims complete observation despite missing intervals
- creates enough recording overhead to materially distort the task
