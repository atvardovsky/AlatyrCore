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

## Suggested Metrics

Track:

- context files loaded
- approximate context volume
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
- protected changes blocked before approval
- duration to usable result when comparable timing is available

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
Residual risks: <summary>
Outcome: <accepted/rework/blocked>
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

## Rejection Criteria

Reject effectiveness claims that:

- compare unrelated tasks
- ignore increased context cost
- hide skipped validation
- count generated volume as quality
- treat one successful run as proof of broad reliability
