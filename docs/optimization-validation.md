# Optimization Validation

This source-maintainer guide explains evidence, not portable target policy.
Canonical owners remain [context profiles](../framework/context-profiles.md),
[delegation](../framework/subagent-delegation.md),
[logical integrity](../framework/logical-integrity.md), and the
[source architecture](source-architecture.md).

## Acceptance

Representation can shrink; required obligations cannot. Compare canonical and
optimized paths for selected owners, authorization, validation coverage,
diagnostics, output bytes, freshness, unresolved obligations and residual risk.
Keep valid end-to-end cases as well as malformed, near-match, missing, stale,
below-limit, exact-limit and above-limit cases. Timing hints and shared check
results may optimize execution, never redefine acceptance.

## Local Measurements

Use the same source snapshot, Python/runtime, dependency set and scheduler
capacity for before/after runs. Record cold and warm runs separately. Repeat
representative measurements; publish median and tail latency only with enough
samples. Full source reports already contain per-check and per-file timings:

```sh
python3 tools/check_all.py --profile full --jobs 4 --from-ref HEAD --report tmp/optimization-full.json
python3 tools/alatyr.py context-costs
python3 tools/alatyr.py refresh-source --check
```

Use `python` on Windows. A static context estimate, clean no-op refresh, or
faster source test suite is not proof of agent billing or reasoning gains.

## Reporting Checklist

Apply the existing [effectiveness claim boundaries](../framework/effectiveness-metrics.md#claim-boundaries)
to release notes and completion summaries, not only benchmark records:

- Name the baseline/candidate revisions, workload, measurement boundary and
  whether the fixture is synthetic. Compare identical requests and fixtures;
  percentages from different fixtures are not interchangeable.
- Report planner reads/bytes separately from selected-context bytes/words,
  observed provider tokens, task latency and billed cost. Mark unmeasured
  quantities unavailable, not unchanged or saved.
- Compare the existing context-cost baselines and disclose increased scenarios
  alongside improvements, including their reason. Report bootstrap and budget
  changes separately: unchanged ceilings do not prove unchanged prompt size.
- Keep quality checks and their scope visible. Passing checks do not turn a
  synthetic I/O result into general speed, token-cost or reasoning evidence.

This is a maintainer reporting checklist, not an automatic semantic-claim
validator or a guarantee that an assistant follows the guidance.

## Python Pipeline Qualification

For import scanning, compare dependency sets and completeness flags, including
aliased/literal/dynamic imports, invalid sources and package membership changes.
For planner reuse, compare its emitted command with canonical runner identity;
profile escalation, baseline forwarding, environment and snapshot changes must
not produce false reuse. Missing or malformed evidence remains non-reusable.

Refresh qualification compares bytes, modes, membership and planned changes
against the conservative path. Test same-size/same-mtime edits, input/output
deletion, new inventory members, unknown renderer implementations and Git
HEAD/ref/config/index mutations. Rejection must leave caller metadata intact;
detecting a write after it escaped isolation is insufficient. Keep the clean
post-commit CLI regression and full-snapshot fallback for unproven stages.

Compare adaptive shards against an independent queue simulation, including
partial/invalid/unrelated hints and numeric extremes. Timing affects grouping
only: every selected test still runs exactly once at the assigned capacity.
Benchmark cold execution and timing-only scheduling separately. Do not count
cached results as cold qualification or remove public-path tests for speed.

## Agent Outcome Measurements

Use the existing [paired benchmark suite](../conformance/benchmarks/benchmark-task-suite.json)
for no/minimal/full adapter comparisons. It covers local docs/code, semantic and
architectural changes, upgrade, incident repair, delegated review and team work.
Record preparation, primary review and rework as part of end-to-end cost.

Where the provider exposes usage, preserve actual input, output and cached-token
telemetry with its source. Otherwise report unavailable; do not replace it with
word counts, character estimates, a shared prefix, or a claimed cache hit.
Retain independently reviewed outcome correctness, missed companion updates,
validation failures, authority mistakes, consistency gaps and rework. No cost or
latency improvement qualifies when those quality outcomes regress.

The suite is a coverage contract until real runs are captured. Source regression
tests do not establish cross-assistant conformance or measured user benefits.
