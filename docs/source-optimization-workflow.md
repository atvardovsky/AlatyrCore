# Source Optimization Workflow

These helpers are scoped to maintaining AlatyrCore. They do not install or
modify an adapter in another project, accept project decisions, or publish.

## Development Context Contract

Scope: AlatyrCore source development. Load this contract for changes to context
delivery, agent workflows, or their optimization, not for every task. Select
this guide through existing `contract_paths` in `source-tooling` or
`audit_context_paths` in `repository-audit`. The architecture-section pointer
is discovery only. No portable rule or installed adapter is added. Owners remain
[context profiles](../framework/context-profiles.md),
[delivery routing](../framework/context-router.md),
[task decomposition](../framework/task-decomposition.md), and
[delegation](../framework/subagent-delegation.md).

1. Classify before reading. Select task scale, the smallest matching source
   profile, and the immediate decision or unknown. Load linked metadata first,
   then selected sections or files. Expand only for a named dependency,
   uncertainty, conflict, failed check, or proof obligation. A directory match
   is not permission to load its contents.
2. Preserve required closure before ranking optional context. Authorization,
   applicable constraints, canonical owners, unresolved contradictions, and
   required validation stay visible. Exhaustive scope must be enumerated and
   covered within limits or decomposed; top-k selection cannot silently replace
   it. Missing routes or evidence require an explicit blocker and recovery path,
   not full-corpus loading or assumed completion.
3. Add no default bootstrap burden for a conditional capability. Prefer existing
   routes and conditional sections over new always-loaded policies, catalogs,
   or forms. Necessary safety context may grow only with an explicit rationale,
   measured impact, applicable review, and required lifecycle changes; never
   weaken a safeguard to keep a size target. Tiny settled tasks remain direct.
4. Keep one canonical owner. Reference existing rules, task models, active
   projections, and knowledge records instead of creating parallel notebooks
   or repeating policy. Use resolvable versioned semantic terms only when their
   definitions plus references are cheaper and unambiguous. Include definition
   overhead; fall back to canonical prose when resolution fails.
5. Keep active state bounded. Use the existing problem-model projection for
   current decisions, hypotheses, blockers, and obligations. Retain rejected
   explanations and historical evidence as references without deleting durable
   records or hiding unresolved obligations. Replan at phase boundaries or
   material evidence changes, not after every command. Store reviewable
   conclusions and evidence, never private reasoning transcripts.
6. Reuse only within verified freshness boundaries. Do not reread unchanged
   content already available in the session. A digest proves identity, not
   correctness, authority, or comprehension. Relevant input changes invalidate
   reuse. Cross-session reuse follows existing binding and invalidation rules;
   no new persistent permission or acceptance cache is implied. After
   compaction, restore current authorization and selected owners through the
   [continuity contract](../framework/session-continuity.md), not stale approval.
7. Delegate only for net benefit. Give workers bounded questions and selected
   evidence, not inherited whole-session history. Review evidence-linked
   summaries; open raw results only for a named review need. Count cumulative
   worker, retry, summary, and coordination costs. Stop or keep work local when
   overhead exceeds benefit; recursion is never a default fan-out target.
8. Keep deterministic routing and checks outside the prompt where supported.
   Deliver bounded diagnostics, omissions, evidence locations, and recovery
   actions. Structural checks do not replace semantic reasoning. Provider caches
   may reduce billing without reducing attention pressure; actual eviction or
   compaction requires verified host support, not a discarded-file label.
9. Compare equivalent tasks before claiming a benefit. Preserve mandatory
   coverage and acceptance criteria; test valid, invalid, missing, malformed,
   and boundary inputs through public paths where applicable. Separately report
   retrieval I/O, delivered context, cumulative history, total worker usage,
   latency, and billing. Unknown observations stay unknown. No smaller packet,
   single fixture, or passing structural suite proves better task outcomes.

For a material change, include a compact context-impact note in its existing
plan or review: who loads it and when; what it replaces or avoids; required
coverage retained; freshness, overflow, and recovery; paired evidence and a
rollback path. No additional record is required for tiny unchanged-context work.
Do not refresh a cost baseline merely to make a regression pass. Investigate
missing companion updates, rework, or performance regressions before accepting
the optimization. Rules guide agents; checks cannot prove that every agent
understood or followed them.

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
