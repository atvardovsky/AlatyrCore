# Workflow Efficiency Tools

Source-maintainer interface reference. Canonical rules remain in
[delivery efficiency](../framework/test-delivery-efficiency.md) and
[delegation](../framework/subagent-delegation.md#dispatch-and-convergence).
These helpers complement agent reasoning; neither is a scheduler or permission
source. Small tasks add no runtime record or bootstrap requirement.

## Early Finalization Checks

```sh
python3 tools/alatyr.py finalize-support --target /path/to/repo --preflight --task-id TASK_ID --task-class standard-task --diff-ref BASE --require-task-acceptance
```

The installed delegate accepts the same finalization options. Use the actual
class and immutable comparison base. Explicit approval bindings can be supplied
with repeatable `--approval-record`. This diagnostic mode is mutually exclusive
with `--write`; it writes no projections, locks or task records.

The helper reuses canonical model/closure schemas, digests, required proofs and
reviews, analysis artifact checks and indexed active/selected incident inputs.
It resolves reviewed retained/lost history through the same canonical functions,
not by copying missing runtime files. With `--require-current-change`, selected
approval-versus-diff checks run before rendering. It does not repeat expensive
result snapshots, architecture reviews, unrelated closed history or generated
projection consistency. Its JSON always has `acceptance_eligible: false`;
human authorization, full archives and final acceptance remain separate.

Write mode performs these selected checks before acquiring the support writer
lock and rechecks their inputs under that lock before mutation. Generated drift
is still repaired by the canonical renderer sequence. Full validation and
conflict-preserving rollback remain in place; final transaction-owned outputs
are rechecked before success. The lock coordinates cooperating writers only;
it is not filesystem-wide atomic compare-and-swap against arbitrary editors.

Keep support convergence, pre-publication checks and final task acceptance
separate. A task that requires publication cannot claim that outcome early.
Do not remove acceptance flags from an unchanged final-completion request to
obtain a passing result. Resolve contradictory target gate order with its owner.

## Parallel Admission

The optional `cooperation-preflight --admission admission.json` input is a
temporary, bounded projection of an existing primary-owned plan, not a second
task registry. Keep stable IDs and statuses synchronized with that plan; its
digest proves byte identity, not semantic correspondence or approved acceptance.

Exact schema-1 shape, with a single illustrative task:

```json
{
  "schema_version": 1,
  "plan": {"path": "task-plan.md", "sha256": "<actual lowercase SHA-256>"},
  "capacity": 2,
  "max_parallel": 2,
  "accepted_ids": [],
  "retry_ids": [],
  "tasks": [
    {"id": "part-a", "requires": [], "state": "READY", "slots": 1,
     "resources": [], "write_scope": []}
  ]
}
```

- Input and referenced plan each fit 64 KiB; 1..64 tasks, capacities/slots
  are integers 1..64, and ID/reference/path lists are bounded to 64 entries.
- States are the existing `PLANNED`, `READY`, `RUNNING`, `REVIEW_REQUIRED`,
  `DONE`, `FAILED`, `CANCELLED`, `BLOCKED`. Planned work is held until the primary
  marks it ready. Only declared primary-accepted `DONE` IDs settle
  dependencies; their entire prerequisite closure must also be accepted.
- `retry_ids` selects only failed tasks for reviewed retry, never extra retry
  allowance. Pending primary reviews retain write/resource claims and consume
  parallel/review capacity, but not running CPU slots.
- `resources` uses the canonical test-resource shape (kind, id, namespace,
  access, isolation). `write_scope` contains literal normalized target-relative
  paths, with enclosing paths conservatively covering descendants, `.` covering
  the repository, and case-folded overlap protecting case-insensitive hosts.
  Resolve filesystem aliases before actual writes. Empty lists
  explicitly declare none; null means unknown and blocks unsafe admission.
- The input order is primary-owned priority. Proposals account for active work
  and previously selected candidates. Oversized or locally blocked tasks do not
  block unrelated compatible work. Active conflicts require reconciliation.

Pass `--scope`, current session identity and any applicable registered test
command IDs as usual. Selected/active resource presence scopes are added by the
helper, with the existing combined eight-scope ceiling; narrow the proposal if
necessary, never omit a resource. Peer conflict or uncertainty clears proposals and retains
hold reasons. Reported resource identities must be reconciled with the same
plan; omission is not evidence of isolation. The report reserves nothing.

Reconsider only at meaningful completion, review, resource-release or dependency
events. Recheck bindings before actual dispatch. Primary chooses capacity from
remaining policy/context budgets, verified native limits, host CPU/RAM, nested
test workers, active peer work and review throughput. Reserve capacity if
backfill would starve a critical task. Missing capacity evidence is not spare
capacity; target/native dispatch remains outside this helper.

Source inspect-only preparation can consume this plan using
`prepare-worker-context --admission admission.json --allocation-id part-a
--admission-sha256 <current lowercase SHA-256>` together with its ordinary packet,
prompt/bootstrap and output arguments. All three bindings are required together.
The selected allocation must be admitted, carry no write scope and respect the
source policy parallel ceiling. Expansion retains original provenance and the
same allocation, prerequisites, resources, slots and empty write scope. It may
follow READY/reviewed-retry to RUNNING with current projection/plan hashes,
without reserving another slot; RUNNING cannot revert to a fresh admission.
Changed allocation or plan path requires primary reconciliation, not expansion.
This verifies declared admission only, not liveness, reservation,
native dispatch, human permission or execution. Recheck peers/capability and the
same exact inputs immediately before separately authorized dispatch.

## Candidate And Phase Boundaries

### Optional Rolling Delivery

Canonical semantics: [Rolling Delivery](../framework/rolling-delivery.md).
Use schema 1 unchanged for ordinary admission. Explicitly selected rolling work
may use schema 2: the same fields plus `delivery`. The existing
`cooperation-preflight --admission` CLI and installed delegate consume both.
Nothing automatically enables a worker, hook or scheduler.

`delivery` has exactly these fields:

- `operation_id`: resolved bounded operation ID.
- `requests`: 1..16 `{id, source: {path, sha256}}` entries. Each source is a
  canonical request brief, limited to its existing 16 KiB/1200-word contract.
- `items`: exactly one `{task_id, request_id, outcome_ids, owner_ref}` per
  admission task. Every source request is used and all of its original outcome
  IDs must be mapped, without invented or omitted outcomes. Owners are declared
  references, not authenticated assignment or authority. Task order remains
  primary-owned admission priority; this view does not rank it again.
- `active_wave`: null or `{id, task_ids, manifest: {path, sha256}}`. Members
  require accepted local results, never inferred final delivery.
- `final_barrier`: null or `{task_id, requires}` naming the complete remaining
  task snapshot. `requires` must match that task's graph dependencies. Later
  arrivals require explicit boundary reconciliation rather than silent extension.
  The helper holds final-barrier dispatch for coordinator review; accepted local
  prerequisites do not establish required publication or runtime outcomes.

The immutable manifest is JSON with exactly `schema_version: 1`,
`record_kind: "alatyr-delivery-wave"`, matching `operation_id`, `wave_id`, ordered
`task_ids`, the exact selected `items` and referenced `requests`, and `inputs`.
`inputs` contains 1..64 unique `{path, sha256}` material-file bindings, excluding
the manifest itself. Freeze and retain it in existing operation evidence, never
rehash old run results to qualify changed source. Declaration completeness and
external build/runtime state still need primary review.

Projection, plan and manifest each fit 64 KiB. Material files fit 1 MiB each;
request/manifest/material reads together fit 8 MiB and are deduplicated by path.
Paths are normalized contained target-relative references of at most 1024
characters; request sources must be distinct from the plan. Hashes are lowercase SHA-256.
The additional delivery view fits 8 KiB/800 words or falls back to counts and
the bound plan without truncating duties into actionable advice. It adds no
default bootstrap requirement and does not scan unrelated historical tasks.

The public CLI verifies brief IDs/outcome coverage, frozen membership/ownership
and actual declared material bytes, then rechecks through peer inspection.
Unknown peer state clears new proposals and delivery advice. Exit zero without
`--require-clear` is not clearance. Direct pure-function reports remain explicitly
unverified until their sources have been inspected. No result grants dispatch,
acceptance, current human intent, permission or exclusive resources.

Source worker preparation may use schema 2 with its existing admission flags.
It retains the extra observed input bindings and selected request/owner mapping;
continuation cannot replace that mapping or downgrade to schema 1. Original
allocation, provenance, empty write scope and policy limits remain unchanged.

Before freezing a candidate, retain a bounded exact-file comparison with relevant
peer corrections. Keep hashes and applied/rejected/deferred reasons in existing
analysis or operation evidence; do not replace actively edited peer files wholesale.
Recheck selected peer/candidate bytes at integration and before consuming build or
validation evidence. New relevant corrections require review and affected proof,
not an automatic whole-task restart. Missing current evidence stays unverified.

Use one build for the same compatible material inputs and environment. Preflight
fixture identity, runner/backend and required tools before expensive qualification.
Reuse a successful child after another child's failure only when the producer
actually supports independent input-bound child evidence and policy permits it;
source-check caches do not implement a target application's cache. Lockfile,
toolchain, generated/ignored inputs, build-time values and external state remain
part of equivalence where material. No HEAD-only cache waiver is introduced.

Write target process guidance as a short index with phase-specific leaves. Existing
context profiles/phase selectors route to the applicable leaf, canonical owners,
current model and open duties; they do not preload every historical solution.
Keep observed performance separate from targets and preserve owner test timing.

## Qualification And Migration

Preserve target-owned test timing, manual review, approval and concurrency.
Upgrade helper/flow pointers without automatically enabling modules, hooks,
workers, expensive tests or retries. Existing model/history schemas are unchanged;
no migration rewrites old evidence into accepted current results.

Compare equivalent workloads for outcomes, companion completeness, escaped
defects, rework, worker preparation/review, wait and end-to-end time. Keep I/O,
context, CPU, latency and billing separate. Fast diagnostics and synthetic
parallel plans do not prove real-agent speedup or provider savings.
