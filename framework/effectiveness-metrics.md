# Effectiveness Metrics

Effectiveness metrics help evaluate whether Alatyr Core improves AI-assisted
work compared with ordinary assistant instructions.

Metrics are evidence, not a guarantee. They should be collected during pilots,
adapter rechecks, conformance runs, or repeated project tasks.

## Pilot Comparison

Compare similar tasks across:

- no Alatyr adapter
- minimal Alatyr adapter
- full Alatyr adapter

Use the same target repository shape and task intent when possible.

Do not generalize a narrow-task result to broad project work. A representative
pilot should cover the task classes defined by the source repository's
`conformance/benchmarks/benchmark-task-suite.json`, use repeated runs where
assistant variability matters, and preserve independent review for every
adapter mode. The suite definition is planning evidence, not execution
evidence.

## Suggested Metrics

Track:

- context files loaded
- approximate context volume
- input/output tokens and monetary cost when host or billing evidence exists
- context budget exceeded, expansion count, and context receipt reuse
- clarification count
- approvals requested
- validation commands or manual checks run
- hallucinated commands avoided or produced
- missed companion updates
- changed facts identified, consistency relationships reviewed, companion
  surfaces checked, and unresolved consistency gaps
- documentation, diagram, prompt, gate, or bridge sync repairs
- rework count
- residual risks reported
- time to usable result
- human active-attention time when it can be bounded without storing raw chat,
  private reasoning, or unrelated activity
- human review cycles and interventions classified by why attention was needed
- executor active time only when host or provider telemetry observes it
- protected changes blocked before approval
- activated change packages, evidence quality, and reapproval events
- implementation discoveries or corrections that invalidated scope
- duration to usable result when comparable timing is available
- human architectural interventions, independent executor findings, findings
  derived after human direction, independently initiated versus human-requested
  dependency checks, maintainer corrections, and post-review rework when an
  explicitly activated Debug Mode record provides normalized event evidence;
  architectural counts require structured impact classification, and direction
  replacements retain their correction, rejected-hypothesis, and replacement
  causal chain

Debug Mode is one optional evidence source for these measures. Compare only
completed records with compatible task classes, capture coverage, timing evidence,
observer effect, and independent result-quality review. A lower intervention
count alone is not proof of improved architecture reasoning.

## Measurement Evidence States

Every human-attention, review-cycle, intervention, executor-time, and adapter-
maintenance measurement must carry one evidence state:

- `observed`: captured directly by a named host, provider, repository, or
  deterministic tool
- `manual`: recorded by a named human from bounded task evidence
- `estimated`: derived through a stated method that is not direct observation
- `unavailable`: not measured; record the reason instead of substituting zero

The recorded value and evidence state must agree. An unavailable measurement
has no numeric value. A numeric estimate must state its method and must not be
presented as observed telemetry. Executor active time permits only `observed`
or `unavailable`: human recollection, wall-clock duration, and task start/end
timestamps are not executor-active-time telemetry.

## Human Attention And Interventions

For comparable pilots, record:

- active human-attention seconds
- review-cycle count
- classified intervention count

Classify each intervention as one of:

- `new-guidance-candidate`
- `known-guidance-routing-failure`
- `known-guidance-compliance-failure`
- `task-local`
- `scope-change`
- `validation-request`
- `other`

Classification is measurement evidence, not automatic project authority. A
new project judgment still requires the target's normal ownership and
acceptance process. A routing or application failure should remain distinct
from a newly discovered rule so effectiveness reports do not falsely claim
project learning.

Review cycles and intervention counts measure required human involvement, not
the quality or value of that involvement. Compare them only across compatible
task classes, acceptance criteria, execution contracts, and independent
quality reviews.

## Delayed Outcome Evidence

Acceptance by a decision owner, pull-request activity, merge, rejection,
regression, revert, or follow-up may occur after a task report or Debug record
is completed. Record each later event as a new immutable
`alatyr-delayed-outcome-evidence` record that links back to the completed
operation and any relevant evidence records.

Never reopen or mutate a completed Debug record to add a delayed outcome.
Later events form an append-only chain through prior outcome IDs. A schema can
check the declared link and immutability fields, but repository history or an
external evidence source is still required to establish that the linked event
actually occurred and the earlier record remained unchanged.

Delayed outcomes are optional and do not block completion of the original
task. Missing later evidence means the long-term outcome is unknown, not that
the work was accepted or rejected.

## Adapter Maintenance Evidence

Framework installation, update, and adapter-recheck work may record one compact
`alatyr-adapter-maintenance-evidence` record containing:

- files touched
- manual corrections
- stale claims found
- routing changes
- validation time
- local deviations requiring review

Each metric uses the same evidence-state contract. Record measurement scope,
evidence references, and limitations. Keep this evidence separate from normal
product-change effort so adapter overhead can be compared without treating
project implementation files as framework maintenance.

## Claim Boundaries

Do not derive a productivity score, output-per-minute value, percentage saving,
or return-on-investment claim from these fields alone. Generated volume is not
engineering output, elapsed duration is not active work, and fewer
interventions can indicate either better guidance or a missed review.

Cost or speed comparisons require compatible tasks, accepted outcomes,
non-regressing quality measures, comparable measurement states, and explicit
limitations. Manual and estimated timing can support investigation, but not a
precision claim equivalent to observed telemetry.

## Reporting Shape

```text
Task: <task name>
Adapter mode: <none/minimal/full>
Context files loaded: <count or unknown>
Approximate context volume: <count or unknown>
Context expansions: <count or unknown>
Context receipt reused: <yes/no/unknown>
Context budget exceeded: <yes/no/unknown>
Clarifications: <count>
Approvals requested: <count>
Validation: <run/skipped/unresolved>
Missed companion updates: <count or unknown>
Rework count: <count or unknown>
Changed facts identified: <count or unknown>
Consistency relationships reviewed: <count or unknown>
Companion surfaces checked: <count or unknown>
Unresolved consistency gaps: <count or unknown>
Duration seconds: <count or unknown>
Human active-attention seconds: <count or unknown>
Human attention evidence state: <observed/manual/estimated/unavailable>
Review cycles: <count or unknown>
Review-cycle evidence state: <observed/manual/estimated/unavailable>
Classified interventions: <classification=count with evidence state>
Executor active seconds: <count or unknown>
Executor-time evidence state: <observed/unavailable>
Input tokens: <count or unknown>
Output tokens: <count or unknown>
Estimated cost and currency: <number/currency or unknown>
Cost evidence: <billing export/host estimate/unknown>
Residual risks: <summary>
Outcome: <accepted/rework/blocked>
Delayed outcome evidence: <separate record IDs or none-yet>
Adapter maintenance evidence: <separate record IDs or not-applicable>
```

## Source-Repository Tooling

The AlatyrCore source repository includes
`tools/summarize_effectiveness_reports.py` for validating and summarizing JSON
or JSONL effectiveness reports during pilots or conformance work. The helper
is evidence tooling only; it does not prove broad framework quality and is not
a portable target validation requirement.

`tools/report_context_costs.py` provides a deterministic static baseline from
the target context-router template. It measures resolved file and whitespace
word counts, not model tokens or real assistant usage. Compare those static
costs with captured assistant-run context evidence before making runtime cost
claims.

For paired runtime pilots, `tools/prepare_effectiveness_benchmark.py` accepts
explicit no/minimal/full repository snapshots and rejects differences outside
declared adapter surfaces. Companion check and summary tools require matching
task/run identities and independently reviewed acceptance criteria. They
report negative or non-computable deltas directly and do not infer savings
from missing measurements.

## Rejection Criteria

Reject effectiveness claims that:

- compare unrelated tasks
- ignore increased context cost
- hide skipped validation
- count generated volume as quality
- treat wall-clock duration as executor active time
- treat unavailable measurements as zero
- compare observed, manual, and estimated values without qualification
- mutate a completed Debug record to append a later outcome
- infer acceptance from the absence of delayed outcome evidence
- publish precise productivity ratios without comparable accepted-quality
  evidence
- treat one successful run as proof of broad reliability
