# Source Optimization Workflow

These helpers are scoped to maintaining AlatyrCore. They do not install or
modify an adapter in another project, accept project decisions, or publish.

## Projection Refresh

`python3 tools/alatyr.py refresh-source` calculates a plan in an isolated copy.
The source graph orders existing renderers and checks their fixed-point output
before showing the changed paths. Stabilization is bounded; a cycle, renderer
failure, unowned output, or concurrent source change blocks application.

`--check` reports drift without source writes. `--write` applies only changed,
uniquely owned outputs after rechecking source revision and content. Existing
unchanged files retain their modification times. An interrupted apply is not
accepted; inspect the partial result before rerunning. This is not a filesystem
transaction or a replacement for the documented source checks.

Golden cost baselines, migrations, and release evidence remain separately
reviewed. They are intentionally not accepted by the refresh graph.

The support stage preserves recorded bytes when its canonical freshness check
passes, including historical generation revisions. A commit alone is not drift.
Managed content, policy, and stable provenance changes still trigger refresh;
every stage must pass its final check before a plan is accepted.

## Timing Feedback

Source unit tests retain the same suites, order within each shard, fixtures,
failures, and coverage. The wrapper measures execution of file suites, excluding
discovery and imports; it does not estimate file duration from shard size.
Mixed-module custom suites remain executable but may have no timing observation.

`python3 tools/check_all.py --cache-mode timing` retains runtime/content-bound
timing observations through the existing optional cache. Invalid or missing
hints fall back to normal scheduling. Partial hints use a seconds-based fallback
rather than mixing seconds with bytes. Hints cannot select or skip tests, change
validation outcomes, or establish acceptance.

## Delegation Drafts

`prepare-worker-result` measures explicit context, raw result, and summary
artifacts against the existing source packet and canonical policy budgets.
Its event input is a provider-neutral record copied from real runtime events,
not proof that a provider launched or completed a worker.

Preview is read-only. `--write` creates a new evidence directory without replacing
an existing one. Drafts remain `requires-review`, with unreviewed scope and
authorization and no satisfied proof obligations. Primary review, capability
evidence, the measured execution tree, and final convergence remain mandatory.

## Context Costs

`first_use` is bootstrap-only; `operational_entry` adds policy-selected session
presence. Scenario `end_to_end` includes explicitly activated conditional files.
Hidden client context and unobserved helper output are not measured. Word and
character counts are structural bounds, not tokenizer or billing evidence.
