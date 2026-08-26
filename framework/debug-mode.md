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
    - ALATYR-KNOWLEDGE-001
  applies_to:
    - all
---
# Debug Mode

Debug Mode is an optional, explicitly activated observability layer for an
Alatyr-assisted engineering task. It records compact engineering events and
outcomes so a project can evaluate what the active executor discovered, which
results came from deterministic Alatyr system behavior, where human supervision
changed the work, and whether that supervision burden changes across comparable
tasks.

Debug Mode evaluates the assisted process. It does not make the resulting patch
correct, expose private reasoning, or replace project evidence.

## Authority Boundary

Debug records are non-canonical project evidence. They may reference accepted
architecture, business rules, code, tests, approvals, and durable engineering
evidence, but they never own those facts. More detailed debug evidence does not
have greater authority.

Keep these questions separate:

- Durable engineering evidence: why is this change justified and validated?
- Debug Mode: how did the executor, Alatyr system behavior, automation, and
  human supervision contribute to the result?

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

After expiry, a new task needs a new explicit activation. A completed record is
immutable task evidence: do not append later events or silently reopen it. When
authorized work continues the same investigation, create a new record with
`continuation.kind: continued`, reference the one closed predecessor, and state
why a new logical scope was opened. Current-scope action authorization remains
independently required for every engineering action.

Schema-version-5 records also classify lifecycle coverage as `active`,
`phase-complete`, or `full-task-complete`. Record covered and omitted phases
from `analysis`, `implementation`, `validation`, and `finalization`, whether a
continuation is expected, and the next phase. A completed analysis-only record
must not imply that implementation or validation was observed. A full-task
record covers all four phases and cannot claim an expected continuation.

When implementation evidence later shares task or issue lineage with a closed
phase-complete record, create a separately authorized continuation with a new
scope ID. The continuation shares at least one durable task reference with its
one closed predecessor. Do not create cycles, reuse the same scope ID, or use a
new record to mutate the predecessor.

## Normalized Event Model

Record only material events that changed or validated the investigation. Every
new version-4 event has a stable ID, sequence, actor role, actor identity,
actor provenance, causal class, intervention kind, correction disposition,
contribution kind, category, compact material effect, evidence references, and
causal references when applicable.

Keep the attribution dimensions separate:

- `actor_role`: `human`, `executor`, `alatyr-system`, `external-maintainer`, or
  `automation`
- `actor_identity`: a target-local stable actor ID and identity kind; it is not
  the role and must not expose unnecessary personal data
- `actor_provenance`: provider, product, model, and runtime facts when observed
  or declared; unavailable fields stay null and are not inferred
- `causal_class`: `independent-within-scope`, `intervention`,
  `derived-from-human`, `derived-from-external`, `derived-from-executor`,
  `derived-from-alatyr-system`, or `derived-from-automation`
- `intervention_kind`: `line-direction`, `scope-expansion`, `constraint`,
  `correction`, `validation-request`, or `not-applicable`
- `correction_disposition`: `new-guidance-candidate`,
  `known-guidance-routing-failure`, `known-guidance-compliance-failure`,
  `task-local`, `scope-change`, `validation-request`, or `not-applicable`
- `contribution_kind`: `finding`, `decision`, `implementation`, `validation`,
  or `coordination`

Alatyr is the framework and project support system, not the engineering
executor. Use `executor` for the assistant or person performing the requested
engineering work. Use `alatyr-system` only for attributable framework behavior
such as deterministic routing, checking, or record normalization. Use
`automation` for CI, scripts, bots, and other non-Alatyr automated producers.
Provider, model, runtime, and product names belong in provenance and never
replace the target-local actor identity.

The request that activates Debug Mode or states the task scope belongs in the
activation and task metadata. It is not itself a human intervention event.
Create an intervention event only when a human or external maintainer directs,
expands, constrains, corrects, or requests validation for a specific line of
the active investigation.

A `derived-from-human` or `derived-from-external` event must reference the
matching earlier intervention through its causal chain. Other derived classes
must reference an earlier event with the matching actor role. An independent
event must not have a human or external intervention ancestor. A validation
request is not an implementation correction, and external input is not a
maintainer correction unless its intervention kind is `correction`.

Classify every human or external-maintainer intervention before deriving
correction metrics or promoting knowledge:

- `new-guidance-candidate`: the intervention may express a reusable rule or
  decision not already delivered; route it to normal project-knowledge review
  without granting the Debug record authority
- `known-guidance-routing-failure`: applicable accepted guidance existed but
  was not delivered; name at least one guidance ID and route a context-router
  repair
- `known-guidance-compliance-failure`: applicable accepted guidance was
  delivered but the executor did not follow it; name at least one guidance ID
  and preserve delivery evidence
- `task-local`: the correction applies only to the current task and does not
  justify durable project guidance
- `scope-change`: the input changes the requested task or investigation scope;
  reassess current-scope authorization before modification
- `validation-request`: the input requests evidence rather than correcting an
  implementation or decision

Every non-`not-applicable` disposition requires compact evidence. Known-
guidance failure dispositions also require related guidance IDs. Do not count
`scope-change` or `validation-request` as implementation corrections. A
non-intervention event uses `not-applicable`.

Schema versions 1 through 4 remain readable with their original contracts.
Versions 1 through 3 retain their original attribution
semantics. Version 1 keeps `origin`; versions 2 and 3 keep the legacy `actor`
values `alatyr`, `human`, and `external-maintainer` and the legacy
`alatyr_independent_*` metric names. Those values are migration-limited and do
not distinguish executor activity from Alatyr system behavior. Do not silently
rewrite or reinterpret them. Version 4 retains the separated actor model but
does not prove phase coverage or structured candidate closure. New records use
schema version 5, and comparisons across versions must identify both the
attribution and lifecycle-evidence differences.

When a schema-version-5 index retains an older record, project the new
lifecycle scope as `legacy`, keep covered phases and candidate IDs empty, and
set continuation expectation to `false`. Do not synthesize lifecycle or
candidate evidence for the historical record. New schema-version-5 records
require the schema-version-5 index so these projections cannot be omitted.

Schema-version-5 finalization records every new reusable project-knowledge
candidate with a stable candidate ID, source event IDs, statement, disposition,
references, and reason. A candidate must resolve to an indexed promotion
proposal, linked durable engineering evidence, an existing canonical owner, a
documented rejection, or a blocker. Candidate discovery by an executor is
valid and must not be misclassified as a human correction. Promotion remains a
separate target-authorized decision.

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
impact must keep the flag false. Executor, Alatyr-system, automation, and
derived events may record architectural impacts as investigation outcomes, but
they are not human architectural-supervision events.

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
intervention, the invalidated premise, and the derived replacement.

## Capture Discipline

Update the task-local record at material checkpoints, not after every message.
Prefer one normalized event that summarizes a coherent effect over a transcript
or verbose chronology. Debug Mode should not materially alter the engineering
workflow it measures.

Record:

- independently identified invariants, architecture areas, dependencies,
  execution paths, risks, tests, and validation requirements, attributed to
  the executor, Alatyr system behavior, or automation that produced them
- human interventions that materially expanded or corrected the work
- the correction disposition, related guidance IDs, and evidence required to
  distinguish new guidance from routing, compliance, task-local, scope, or
  validation outcomes
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
Record active work time only when the environment measures it reliably. In a
completed schema-version-3-or-newer record, every concrete event timestamp must
remain
within the start/completion interval, follow sequence order, and not precede a
causal ancestor. Active records do not declare a completion timestamp.

Every record also declares event coverage, missing intervals, possible observer
effect, and estimated recording overhead. A partial record is valid evidence of
partial observation; it must not be summarized as complete.

## Metrics

Derive completed-task metrics from recorded events, not from the final diff or
an assistant's impression. Metrics include:

- human interventions and human architectural interventions
- independent executor findings and findings derived after human intervention
- independent executor versus human-requested dependency checks
- dependency expansions derived after human intervention
- hypotheses tested and rejected
- implementation revisions and corrections after human intervention
- validation expansions and regression scenarios added
- external maintainer corrections and post-review rework

Each metric stores its evidence kind and contributing event IDs. Use `estimated`
or `unavailable` only when exact event-derived evidence cannot be claimed.
Completed records with `event-derived` metrics must agree exactly with their
event predicates. Version 4 counts findings only from `finding` contributions,
implementation revisions only from `implementation` contributions, and
validation expansion only from `validation` contributions. Implementation
correction and post-review rework metrics require a causal correction ancestor;
a `scope-change` or `validation-request` disposition does not satisfy that
predicate. Version-2 and version-3 metrics retain their historical predicates
and names for compatibility.

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

Every versioned Debug result records an Engineering Evidence decision as
`pending`, `captured`, `skipped`, or `blocked`. Completion cannot leave it
pending.

Schema version 3 separates two concepts:

- typed `event_links` identify whether a referenced event is a finding,
  decision, implementation, validation, correction, direction change, or
  rejected hypothesis
- `materiality_evaluations` decide whether each durable capture condition is
  applicable, not applicable, or unknown

Evaluate undocumented invariants, rejected hypotheses, non-obvious
dependencies, cross-area impact, broad regression matrices, compatibility or
public-contract reasoning, reviewer corrections, direction changes,
expensive-to-reconstruct conclusions, and unresolved authority or external
contracts. Implementation and validation events support the decision but do
not become material merely because they exist.

Capture applicable or unresolved reusable knowledge, or mark it blocked with a
next safe action. `skipped` is valid only when no materiality remains unknown
and every applicable conclusion names an existing canonical source registered
for that project fact type. A commit message, issue, or regression test alone
does not prove canonical preservation.

Schema version 3 also classifies the implementation claim as
`exact-reproducer`, `representative`, `partial`, `unavailable`, or
`not-applicable`. Exact, representative, and partial claims name both the claim
and validation evidence. Partial or unavailable completed results retain the
gap as residual uncertainty. This classification prevents broad validation
from being presented as proof of an untested original configuration.

Schema-version-2 decisions remain readable as migration-limited historical
evidence. Do not silently infer structured materiality, continuation lineage,
or claim fidelity that the old record did not capture.

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
- independent executor findings
- independent and human-requested dependency checks
- rejected hypotheses
- implementation corrections after human intervention
- external maintainer corrections and post-review rework
- final repository binding and external projection result
- claim-validation fidelity and exact reproducer gap
- durable evidence materiality decision and canonical preservation when skipped
- continuation lineage when the task continues an earlier closed record
- lifecycle completion scope, covered and omitted phases, and expected next phase
- project-knowledge candidate IDs and their dispositions
- residual uncertainty

Report exact numbers only when supported by the record. Finalize or abandon the
record and expire activation before leaving the logical scope.

## Deterministic Checks And Limits

Target validation may check schema shape, event ordering and lifecycle bounds,
role/identity/provenance separation, correction dispositions and required
known-guidance references, causal attribution, typed evidence-event roles,
complete materiality
evaluation, canonical skip references, claim-fidelity evidence, continuation
lineage and cycle freedom, lifecycle phase partition, reciprocal Debug-to-
Engineering-Evidence links, project-knowledge candidate closure, structured architectural-impact consistency, direction-change
hypothesis transitions, metric derivation, timing consistency, privacy
declarations, Debug-to-Engineering-Evidence reference integrity, index/record
sync, repository bindings, and external-patch policy.

It cannot prove that every material event was recorded, that attribution is
semantically correct, that the work was good, that an unrecorded conversation
had no influence, or that reduced supervision caused better Alatyr reasoning.

## Rejection Criteria

Reject or repair Debug Mode use that:

- activates without an explicit current-scope user request
- carries activation or write permission into a new task
- stores transcripts, private reasoning, secrets, or unrelated data
- attributes executor work to `alatyr-system` or treats legacy `alatyr` events
  as proof of executor or system attribution
- counts the initial task request as an intervention without a specific
  investigative effect
- counts a validation request as an implementation correction or generic
  external input as a maintainer correction
- omits a correction disposition for a human or external-maintainer
  intervention, or classifies a non-intervention as a correction
- claims a known-guidance routing or compliance failure without a related
  guidance ID and compact evidence
- treats a new-guidance candidate as accepted project knowledge without normal
  target review and canonical ownership
- finalizes a candidate count without candidate IDs, evidence events, and a
  promotion, preservation, owner, rejection, or blocked disposition
- records derived work without an earlier event from the role named by its
  causal class
- marks a human architectural impact as non-architectural, or claims human
  architectural supervision without structured impact evidence in a new record
- changes an accepted direction without recording the rejected hypothesis and
  its replacement invariant or architecture direction
- links an unknown, duplicate, or Debug-local ID as durable engineering
  evidence
- completes material Debug work without an explicit durable-evidence decision
- appends events after completion instead of opening a linked continuation
- presents phase-complete analysis as full-task implementation evidence, reuses
  a predecessor scope ID, or creates cyclic continuation lineage
- labels an evidence event with a role inconsistent with that event
- skips applicable materiality without registry-backed canonical preservation
- claims an exact reproducer from only representative or partial validation
- rewrites historical attribution or repository-binding lineage silently
- infers metrics from the final patch instead of recorded events
- turns debug evidence into architecture or business-rule authority
- includes Alatyr files in a clean external patch contrary to target policy
- claims complete observation despite missing intervals
- creates enough recording overhead to materially distort the task
